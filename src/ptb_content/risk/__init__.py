"""Risk assessment engine for content briefs."""

from __future__ import annotations

import re

from ..types import (
    CatalogRecord,
    RiskDecision,
    RiskLevel,
    RiskTag,
)
from ..utils.helpers import load_config

# Publication risk is assessed only against text that will actually be shown to
# the audience. Source-page tags remain available on CatalogRecord for provenance
# and source review, but they must not automatically contaminate a clean caption.
_PUBLISH_TEXT_KEYWORDS: dict[RiskTag, tuple[str, ...]] = {
    RiskTag.FINANCIAL: (
        "رایگان",
        "قیمت",
        "هزینه",
        "پرداخت",
        "درآمد",
        "سود",
        "زیان",
        "مالی",
    ),
    RiskTag.LEGAL: ("قانون", "حقوقی", "وکیل", "قرارداد", "تعهد", "دادگاه"),
    RiskTag.TAX: ("مالیات", "مالیاتی", "اظهارنامه", "معافیت"),
    RiskTag.SECURITY: (
        "امن",
        "امنیت",
        "رمزگذاری",
        "محافظت",
        "بدون آپلود",
        "پردازش محلی",
    ),
    RiskTag.PRIVACY: (
        "حریم خصوصی",
        "اطلاعات شخصی",
        "داده‌های شخصی",
        "بدون ثبت‌نام",
        "پردازش محلی",
    ),
    RiskTag.TESTIMONIAL: ("نظر مشتری", "تجربه کاربر", "رضایت کاربران", "توصیه‌نامه"),
    RiskTag.COMPARATIVE: (
        "بهترین",
        "سریع‌ترین",
        "سریع‌تر",
        "بهتر",
        "برتر",
        "بیشتر",
        "کمتر",
        "رقیب",
        "بقیه ندارن",
    ),
    RiskTag.STATISTICAL: ("آمار", "درصد", "٪", "میانگین", "نرخ"),
    RiskTag.MEDICAL: ("پزشکی", "درمان", "دارو", "بیماری", "سلامت"),
}

_NUMERIC_CLAIM = re.compile(r"(?<![#\w])\d+(?:[.,]\d+)?\s*(?:٪|درصد|ثانیه|دقیقه|ساعت|روز|برابر)?")


class RiskEngine:
    """Deterministic risk assessment engine.

    Two scopes are intentionally supported:

    - ``assess(record)`` evaluates the full source page and is used for source
      governance and provenance.
    - ``assess_publishable_text(...)`` evaluates only text that will be
      published. This is the risk used by a generated Brief and by QA.

    This is not a risk override: both assessments are retained and independently
    reproducible from their respective inputs.
    """

    def __init__(self) -> None:
        self.config = load_config("risk")
        self.risk_config = self.config["risk_engine"]
        self.escalate_tags = {RiskTag(t) for t in self.risk_config["escalate_tags"]}
        self.always_review = set(self.risk_config["always_review"])

    def _decision_for_tags(self, risk_tags: set[RiskTag]) -> tuple[RiskLevel, RiskDecision]:
        if risk_tags & self.escalate_tags:
            return RiskLevel.HIGH, RiskDecision.ESCALATE
        if risk_tags:
            return RiskLevel.MEDIUM, RiskDecision.REVIEW_REQUIRED
        return RiskLevel.LOW, RiskDecision.AUTO_APPROVE

    def assess(self, record: CatalogRecord) -> tuple[RiskLevel, RiskDecision]:
        """Assess source-page risk for a catalog record."""
        risk_tags = set(record.risk_tags)

        level, decision = self._decision_for_tags(risk_tags)
        if risk_tags:
            return level, decision

        # Source claims still matter for source governance.
        unverified_claims = [c for c in record.claims if c.verifiable and not c.evidence_url]
        if len(unverified_claims) > 2:
            return RiskLevel.MEDIUM, RiskDecision.REVIEW_REQUIRED

        return RiskLevel.LOW, RiskDecision.AUTO_APPROVE

    def detect_publishable_tags(self, text: str) -> set[RiskTag]:
        """Detect risk tags only in audience-visible publication text."""
        normalized = " ".join(text.split()).casefold()
        tags: set[RiskTag] = set()

        for tag, keywords in _PUBLISH_TEXT_KEYWORDS.items():
            if any(keyword.casefold() in normalized for keyword in keywords):
                tags.add(tag)

        # Standalone numbers can imply a factual/statistical claim. Hashtag digits
        # are ignored by the negative lookbehind in _NUMERIC_CLAIM.
        if _NUMERIC_CLAIM.search(normalized):
            tags.add(RiskTag.STATISTICAL)

        return tags

    def assess_publishable_text(
        self,
        caption: str,
        *,
        cta: str = "",
        alt_text: str = "",
    ) -> tuple[RiskLevel, RiskDecision, set[RiskTag]]:
        """Assess the exact text intended for publication.

        Source-page words that are not present in the caption, CTA, or alt text
        do not affect this result. Source risk remains available through
        ``assess(record)``.
        """
        text = "\n".join(part for part in (caption, cta, alt_text) if part)
        tags = self.detect_publishable_tags(text)
        level, decision = self._decision_for_tags(tags)
        return level, decision, tags

    def should_escalate(self, level: RiskLevel, decision: RiskDecision) -> bool:
        """Check if content should be escalated for human review."""
        return decision == RiskDecision.ESCALATE or level == RiskLevel.HIGH
