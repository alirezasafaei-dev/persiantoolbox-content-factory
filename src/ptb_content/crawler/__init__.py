"""Web crawler for PersianToolbox catalog discovery."""

from __future__ import annotations

import asyncio
import html
import re
import time
from datetime import UTC, datetime
from typing import Any

import httpx
from bs4 import BeautifulSoup, Comment

from ..types import CatalogRecord, Category, Claim, HTTPMetadata, RiskTag, generate_hash
from ..utils.helpers import ensure_dir, load_config, write_json, write_jsonl

# Patterns that indicate HTML/CSS/JS contamination in visible text
_CONTAMINATION_PATTERNS = re.compile(
    r"<!DOCTYPE|<html|<script|</script|__NEXT_DATA__|webpack|self\.__next_f|"
    r"font-family:|display:flex|className=|stylesheet|<style|</style|"
    r"<link |<meta |charset|viewport|nonce=|data-precedence|fetchPriority",
    re.IGNORECASE,
)

# Tags to completely remove from visible text
_STRIP_TAGS = {
    "script",
    "style",
    "noscript",
    "template",
    "svg",
    "canvas",
    "iframe",
    "head",
    "link",
    "meta",
    "base",
    "source",
    "track",
}

# Preferred content containers (in order)
_CONTENT_SELECTORS = ["main", "article", '[role="main"]', "body"]


def _extract_visible_text(raw_html: str) -> str:
    """Extract clean, human-visible text from HTML.

    - Strips script, style, noscript, template, SVG, canvas, iframe, head, link, meta
    - Prioritizes main > article > [role=main] > body
    - Decodes HTML entities
    - Normalizes whitespace and zero-width characters
    - Removes duplicate lines
    - Returns only visible, readable text
    """
    if not raw_html or not raw_html.strip():
        return ""

    soup = BeautifulSoup(raw_html, "lxml")

    # Remove all strip-level tags
    for tag_name in _STRIP_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove HTML comments
    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    # Try to find the main content container
    content_root = None
    for selector in _CONTENT_SELECTORS:
        if selector.startswith("["):
            # Attribute selector
            attr_match = re.match(r'\[role="(\w+)"\]', selector)
            if attr_match:
                content_root = soup.find(attrs={"role": attr_match.group(1)})
        else:
            content_root = soup.find(selector)
        if content_root:
            break

    if content_root is None:
        content_root = soup.find("body") or soup

    # Get text
    text = content_root.get_text(separator="\n", strip=True)

    # Decode HTML entities that survived parsing
    text = html.unescape(text)

    # Normalize zero-width and special whitespace (keep ZWNJ for Persian)
    text = re.sub(r"[\u200B\u200D\u200E\u200F\uFEFF]", "", text)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n", "\n", text)

    # Remove duplicate consecutive lines
    lines = text.split("\n")
    deduped: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and (not deduped or stripped != deduped[-1]):
            deduped.append(stripped)

    text = "\n".join(deduped)

    # Truncate to reasonable length (50KB max)
    if len(text) > 50_000:
        text = text[:50_000]

    return text.strip()


def validate_visible_text(text: str) -> list[str]:
    """Validate that visible text is clean of HTML/CSS/JS contamination.

    Returns list of contamination issues found. Empty list means clean.
    """
    issues: list[str] = []

    if not text or len(text.strip()) < 80:
        issues.append(f"visible_text_too_short: {len(text)} chars (need >= 80)")

    if _CONTAMINATION_PATTERNS.search(text):
        matches = _CONTAMINATION_PATTERNS.findall(text)
        issues.append(f"html_contamination: {len(matches)} pattern(s) found")

    # Check for raw HTML tags
    if re.search(r"<[a-zA-Z][^>]*>", text):
        issues.append("raw_html_tags: HTML tags found in visible text")

    return issues


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

    def _extract_metadata(
        self, raw_html: str, url: str, status: int, headers: dict[str, str]
    ) -> dict[str, Any]:
        """Extract metadata from HTML. Treats HTML as UNTRUSTED DATA."""
        meta: dict[str, Any] = {
            "url": url,
            "status_code": status,
            "content_type": headers.get("content-type", ""),
            "content_length": int(headers.get("content-length", 0)),
            "last_modified": headers.get("last-modified"),
            "etag": headers.get("etag"),
        }

        # Extract title (simple regex, no HTML parsing library needed)
        title_match = re.search(r"<title[^>]*>([^<]+)</title>", raw_html, re.IGNORECASE)
        if title_match:
            meta["html_title"] = html.unescape(title_match.group(1).strip())

        # Extract meta description
        desc_match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
            raw_html,
            re.IGNORECASE,
        )
        if desc_match:
            meta["meta_description"] = html.unescape(desc_match.group(1).strip())

        # Extract og tags
        for og_name in ["og:title", "og:description", "og:image", "og:type"]:
            og_match = re.search(
                rf'<meta\s+property=["\']{og_name}["\']\s+content=["\']([^"\']+)["\']',
                raw_html,
                re.IGNORECASE,
            )
            if og_match:
                meta[og_name] = html.unescape(og_match.group(1).strip())

        return meta

    def _detect_risk_tags(self, text: str) -> list[RiskTag]:
        """Detect risk tags in CLEAN visible text only."""
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
        """Extract verifiable claims from CLEAN visible text only.

        Rules:
        - Claim must not contain < or > (HTML tags)
        - Claim must not contain CSS or JS tokens
        - Claim must be a readable sentence (>= 10 chars)
        - Claim max 300 chars
        - Deduplicate claims
        - Empty claims list is valid (not all pages have claims)
        """
        claims: list[Claim] = []
        seen: set[str] = set()

        # Split into sentences on Persian/English punctuation
        sentences = re.split(r"[.!?؟\n]", text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10 or len(sentence) > 300:
                continue

            # Reject if contains HTML tags
            if "<" in sentence or ">" in sentence:
                continue

            # Reject if contains CSS/JS tokens
            if re.search(r"font-family:|display:|className:|function\(|const |let |var ", sentence):
                continue

            # Reject if mostly non-Persian (less than 20% Persian/Arabic chars)
            persian_count = sum(1 for c in sentence if "\u0600" <= c <= "\u06ff")
            alpha_count = sum(1 for c in sentence if c.isalpha())
            if alpha_count > 0 and persian_count / alpha_count < 0.2:
                continue

            # Deduplicate
            normalized = re.sub(r"\s+", " ", sentence).strip()
            if normalized in seen:
                continue
            seen.add(normalized)

            # Check if it contains a verifiable element (number or comparison)
            has_number = bool(re.search(r"\d+", sentence))
            has_comparison = any(
                word in sentence for word in ["بیشتر", "کمتر", "بهتر", "سریع‌تر", "اول", "بزرگتر"]
            )

            if has_number or has_comparison:
                claims.append(
                    Claim(
                        text=sentence[:300],
                        source_id=source_id,
                        verifiable=True,
                        confidence=0.6,
                    )
                )

        return claims[:10]

    async def crawl_pilot(self) -> dict[str, Any]:
        """Crawl pilot items (20-30 low-risk tools)."""
        from ..utils.helpers import project_root

        tools: list[dict[str, Any]] = []
        all_claims: list[dict[str, Any]] = []
        report: dict[str, Any] = {
            "started_at": datetime.now(UTC).isoformat(),
            "items_crawled": 0,
            "items_skipped": 0,
            "items_contaminated": 0,
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
                    raw_html, status, headers = await self.fetch(full_url, client)

                    if status != 200:
                        report["errors"].append({"url": full_url, "status": status})
                        report["items_skipped"] += 1
                        continue

                    metadata = self._extract_metadata(raw_html, full_url, status, headers)

                    # Generate source_id from URL
                    source_id = url_path.strip("/").replace("/", "-") or "home"

                    # Source hash from raw HTML (for provenance)
                    source_hash = generate_hash(raw_html)

                    # Extract CLEAN visible text
                    visible_text = _extract_visible_text(raw_html)

                    # Content hash from clean text
                    content_hash = generate_hash(visible_text) if visible_text else ""

                    # Validate for contamination
                    contamination_issues = validate_visible_text(visible_text)
                    if contamination_issues:
                        report["items_contaminated"] += 1
                        report["errors"].append(
                            {
                                "url": full_url,
                                "contamination": contamination_issues,
                            }
                        )
                        # Still record but mark — don't skip entirely,
                        # just flag for review
                        pass

                    # Extract title from clean text or metadata
                    title = metadata.get("html_title", metadata.get("og:title", source_id))

                    # Summary from meta description (clean)
                    summary = metadata.get("meta_description", metadata.get("og:description", ""))
                    if not summary and visible_text:
                        # Use first 200 chars of visible text as summary
                        summary = visible_text[:200]

                    # Detect risk tags from CLEAN text only
                    risk_tags = self._detect_risk_tags(visible_text)

                    # Extract claims from CLEAN text only
                    claims = self._extract_claims(visible_text, source_id)

                    record = CatalogRecord(
                        canonical_url=full_url,
                        title=title,
                        summary=summary[:500],
                        category=Category.TOOL_DEMO,
                        source_id=source_id,
                        source_hash=source_hash,
                        content_hash=content_hash,
                        visible_text_length=len(visible_text),
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
                csv_lines.append(
                    f'"{item["source_id"]}","{item["title"]}","{tags}","{item["canonical_url"]}"'
                )
            with open(output_dir / "manual-review.csv", "w", encoding="utf-8") as f:
                f.write("\n".join(csv_lines))

        return report
