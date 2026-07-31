"""Web crawler for PersianToolbox catalog discovery."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from ..types import CatalogRecord, Category, Claim, HTTPMetadata, RiskTag, generate_hash
from ..utils.helpers import ensure_dir, load_config, write_json, write_jsonl


class Crawler:
    """Rate-limited web crawler for PersianToolbox."""

    def __init__(self, config_name: str = "crawler") -> None:
        self.config = load_config(config_name)
        self.crawler_config = self.config["crawler"]
        self.base_url = self.crawler_config["base_url"]
        self.concurrency = self.crawler_config["concurrency"]
        self.rate_limit = self.crawler_config["rate_limit_rps"]
        self.timeout = self.crawler_config["timeout_seconds"]
        self.max_retries = self.crawler_config["max_retries"]
        self.user_agent = self.crawler_config["user_agent"]
        self._last_request_time = 0.0

    async def _rate_limit_wait(self) -> None:
        """Enforce rate limiting between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        min_interval = 1.0 / self.rate_limit
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def fetch(self, url: str, client: httpx.AsyncClient) -> tuple[str, int, dict[str, str]]:
        """Fetch a URL with retries and rate limiting."""
        last_error = None
        for attempt in range(self.max_retries):
            await self._rate_limit_wait()
            try:
                response = await client.get(
                    url,
                    follow_redirects=True,
                    timeout=self.timeout,
                )
                return response.text, response.status_code, dict(response.headers)
            except (httpx.TimeoutException, httpx.HTTPError) as e:
                last_error = e
                backoff = self.crawler_config["retry_backoff_base"] ** attempt
                await asyncio.sleep(backoff)
        raise RuntimeError(f"Failed after {self.max_retries} retries: {last_error}")

    def _extract_metadata(self, html: str, url: str, status: int, headers: dict[str, str]) -> dict[str, Any]:
        """Extract metadata from HTML. Treats HTML as UNTRUSTED DATA."""
        import re

        meta: dict[str, Any] = {
            "url": url,
            "status_code": status,
            "content_type": headers.get("content-type", ""),
            "content_length": int(headers.get("content-length", 0)),
            "last_modified": headers.get("last-modified"),
            "etag": headers.get("etag"),
        }

        # Extract title (simple regex, no HTML parsing library needed)
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if title_match:
            meta["html_title"] = title_match.group(1).strip()

        # Extract meta description
        desc_match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if desc_match:
            meta["meta_description"] = desc_match.group(1).strip()

        # Extract og tags
        for og_name in ["og:title", "og:description", "og:image", "og:type"]:
            og_match = re.search(
                rf'<meta\s+property=["\']{og_name}["\']\s+content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            if og_match:
                meta[og_name] = og_match.group(1).strip()

        return meta

    def _detect_risk_tags(self, text: str) -> list[RiskTag]:
        """Detect risk tags in content text."""
        text_lower = text.lower()
        tags = []

        risk_keywords = {
            RiskTag.FINANCIAL: ["قیمت", "هزینه", "درآمد", "سود", "زیان", "بودجه", "مالی", "پرداخت"],
            RiskTag.LEGAL: ["قانون", "حقوقی", "دادگاه", "وکیل", "قرارداد", "تعهد"],
            RiskTag.TAX: ["مالیات", "مالیاتی", "اظهارنامه", "معافیت"],
            RiskTag.SECURITY: ["امنیت", "رمز", "گذرواژه", "هک", "protect"],
            RiskTag.PRIVACY: ["حریم خصوصی", "Privacy", "اطلاعات شخصی", "داده‌های شخصی"],
            RiskTag.TESTIMONIAL: ["نظر مشتری", "تجربه کاربر", "رضایت", "توصیه‌نامه"],
            RiskTag.COMPARATIVE: ["مقایسه", "بهترین", "بدترین", "برتر", "رقیب"],
            RiskTag.STATISTICAL: ["آمار", "درصد", "٪", "نرخ", "میانگین"],
            RiskTag.MEDICAL: ["پزشکی", "درمان", "دارو", "بیماری", "سلامت"],
        }

        for tag, keywords in risk_keywords.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)

        return tags

    def _extract_claims(self, text: str, source_id: str) -> list[Claim]:
        """Extract verifiable claims from text."""
        import re

        claims = []
        # Simple heuristic: sentences with numbers or specific patterns
        sentences = re.split(r"[.!?؟\n]", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:
                continue

            # Check if it contains a verifiable claim
            has_number = bool(re.search(r"\d+", sentence))
            has_comparison = any(
                word in sentence for word in ["بیشتر", "کمتر", "بهتر", "سریع‌تر", "اول", "بزرگتر"]
            )

            if has_number or has_comparison:
                claims.append(
                    Claim(
                        text=sentence[:200],
                        source_id=source_id,
                        verifiable=True,
                        confidence=0.6,
                    )
                )

        return claims[:10]  # Limit to 10 claims

    async def crawl_pilot(self) -> dict[str, Any]:
        """Crawl pilot items (20-30 low-risk tools)."""
        from ..utils.helpers import project_root

        tools = []
        all_claims = []
        report = {
            "started_at": datetime.now(UTC).isoformat(),
            "items_crawled": 0,
            "items_skipped": 0,
            "errors": [],
            "duration_seconds": 0,
        }

        start_time = time.monotonic()

        # Verified working URLs from persiantoolbox.ir sitemap
        pilot_urls = [
            "/",
            "/blog",
            "/about",
            "/pricing",
            "/tools/specialized",
            "/pdf-tools/uses",
            "/business-tools",
            "/business-tools/document-studio",
            "/career-tools",
            "/career-tools/resume-builder",
            "/writing-tools",
            "/writing-tools/persian-writing-studio",
            "/topics/validation-tools",
            "/topics/contract-tools",
            "/topics/business-tools",
            "/topics/career-tools",
            "/topics/writing-tools",
            "/topics/seo-tools",
        ]

        pilot_urls = pilot_urls[: self.crawler_config["pilot_max_items"]]

        async with httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            follow_redirects=True,
            trust_env=False,
        ) as client:
            for url_path in pilot_urls:
                full_url = f"{self.base_url}{url_path}"
                try:
                    html, status, headers = await self.fetch(full_url, client)

                    if status != 200:
                        report["errors"].append({"url": full_url, "status": status})
                        report["items_skipped"] += 1
                        continue

                    metadata = self._extract_metadata(html, full_url, status, headers)

                    # Generate source_id from URL
                    source_id = url_path.strip("/").replace("/", "-")

                    # Generate source hash
                    source_hash = generate_hash(html)

                    # Detect risk tags
                    risk_tags = self._detect_risk_tags(html)

                    # Risk assessment deferred to RiskEngine — keep all items for pilot

                    # Extract title
                    title = metadata.get("html_title", metadata.get("og:title", source_id))
                    summary = metadata.get("meta_description", metadata.get("og:description", title))

                    # Extract claims
                    claims = self._extract_claims(html, source_id)

                    record = CatalogRecord(
                        canonical_url=full_url,
                        title=title,
                        summary=summary[:500],
                        category=Category.TOOL_DEMO,
                        source_id=source_id,
                        source_hash=source_hash,
                        crawled_at=datetime.now(UTC).isoformat(),
                        claims=claims,
                        risk_tags=risk_tags,
                        http_metadata=HTTPMetadata(
                            status_code=status,
                            content_type=metadata.get("content_type", ""),
                            content_length=metadata.get("content_length", 0),
                            last_modified=metadata.get("last_modified"),
                            etag=metadata.get("etag"),
                        ),
                        meta={k: v for k, v in metadata.items() if k.startswith("og:")},
                    )

                    tools.append(record.to_dict())
                    all_claims.extend([c.to_dict() for c in claims])
                    report["items_crawled"] += 1

                except Exception as e:
                    report["errors"].append({"url": full_url, "error": str(e)})
                    report["items_skipped"] += 1

        # Save outputs
        output_dir = project_root() / self.crawler_config["catalog_dir"]
        ensure_dir(output_dir)

        write_jsonl(tools, output_dir / "tools.jsonl")
        write_jsonl(all_claims, output_dir / "claims.jsonl")

        report["finished_at"] = datetime.now(UTC).isoformat()
        report["duration_seconds"] = round(time.monotonic() - start_time, 2)
        report["total_claims"] = len(all_claims)

        write_json(report, output_dir / "crawl-report.json")

        # Generate manual review CSV for items with risk tags
        review_items = [t for t in tools if t.get("risk_tags")]
        if review_items:
            csv_lines = ["source_id,title,risk_tags,canonical_url"]
            for item in review_items:
                tags = ";".join(item.get("risk_tags", []))
                csv_lines.append(f'"{item["source_id"]}","{item["title"]}","{tags}","{item["canonical_url"]}"')
            with open(output_dir / "manual-review.csv", "w", encoding="utf-8") as f:
                f.write("\n".join(csv_lines))

        return report
