"""Regression tests for source-risk vs publication-risk separation."""

from ptb_content.generator import DeterministicGenerator
from ptb_content.qa import QAEngine
from ptb_content.risk import RiskEngine
from ptb_content.types import (
    CatalogRecord,
    Category,
    CheckStatus,
    RiskDecision,
    RiskLevel,
    RiskTag,
    utcnow,
)


def _record(*tags: RiskTag) -> CatalogRecord:
    return CatalogRecord(
        canonical_url="https://persiantoolbox.ir/topics/pdf-tools",
        title="ابزارهای PDF پرشین‌تولباکس",
        summary="صفحه معرفی مجموعه ابزارهای PDF",
        category=Category.TOOL_DEMO,
        source_id="topics-pdf-tools",
        source_hash="a" * 64,
        content_hash="b" * 64,
        crawled_at=utcnow(),
        risk_tags=list(tags),
    )


def test_clean_caption_is_low_even_when_source_is_high() -> None:
    engine = RiskEngine()
    record = _record(RiskTag.SECURITY, RiskTag.PRIVACY, RiskTag.COMPARATIVE)

    source_level, source_decision = engine.assess(record)
    publish_level, publish_decision, publish_tags = engine.assess_publishable_text(
        "برای کار با فایل‌های PDF، ابزار موردنیازتان را انتخاب کنید.\n\nلینک در بیو",
        alt_text="تصویر معرفی ابزارهای PDF پرشین‌تولباکس",
    )

    assert source_level == RiskLevel.HIGH
    assert source_decision == RiskDecision.ESCALATE
    assert publish_level == RiskLevel.LOW
    assert publish_decision == RiskDecision.AUTO_APPROVE
    assert publish_tags == set()


def test_price_claim_escalates_publication() -> None:
    level, decision, tags = RiskEngine().assess_publishable_text(
        "این ابزار را رایگان امتحان کنید"
    )
    assert level == RiskLevel.HIGH
    assert decision == RiskDecision.ESCALATE
    assert RiskTag.FINANCIAL in tags


def test_security_and_privacy_claims_escalate_publication() -> None:
    level, decision, tags = RiskEngine().assess_publishable_text(
        "پردازش محلی و بدون ثبت‌نام"
    )
    assert level == RiskLevel.HIGH
    assert decision == RiskDecision.ESCALATE
    assert RiskTag.SECURITY in tags
    assert RiskTag.PRIVACY in tags


def test_statistical_words_escalate_publication() -> None:
    level, decision, tags = RiskEngine().assess_publishable_text(
        "تحلیل آمار متن را ببینید"
    )
    assert level == RiskLevel.HIGH
    assert decision == RiskDecision.ESCALATE
    assert RiskTag.STATISTICAL in tags


def test_numeric_claim_escalates_publication() -> None:
    level, decision, tags = RiskEngine().assess_publishable_text(
        "پردازش فایل در 3 ثانیه"
    )
    assert level == RiskLevel.HIGH
    assert decision == RiskDecision.ESCALATE
    assert RiskTag.STATISTICAL in tags


def test_generator_produces_claim_free_publication_risk() -> None:
    record = _record(RiskTag.SECURITY, RiskTag.PRIVACY, RiskTag.COMPARATIVE)
    brief = DeterministicGenerator().generate_brief(record)

    assert brief.risk_level == RiskLevel.LOW
    assert brief.risk_decision == RiskDecision.AUTO_APPROVE
    assert brief.catalog_record.meta["source_risk_level"] == "HIGH"
    assert brief.catalog_record.meta["source_risk_decision"] == "ESCALATE"
    assert brief.catalog_record.meta["publication_risk_tags"] == []

    forbidden = (
        "رایگان",
        "بهترین",
        "سریع‌تر",
        "سریع‌ترین",
        "امن",
        "حریم خصوصی",
        "بدون ثبت‌نام",
    )
    all_text = "\n".join(
        [brief.caption.primary, brief.caption.alt_text, *brief.caption.variants.values()]
    )
    assert not any(term in all_text for term in forbidden)


def test_generator_is_deterministic_for_same_record() -> None:
    first = DeterministicGenerator().generate_brief(_record())
    second = DeterministicGenerator().generate_brief(_record())

    assert first.caption == second.caption
    assert first.audience == second.audience
    assert first.psychology_hypothesis == second.psychology_hypothesis


def test_qa_accepts_high_source_risk_with_clean_publication() -> None:
    brief = DeterministicGenerator().generate_brief(
        _record(RiskTag.SECURITY, RiskTag.PRIVACY, RiskTag.COMPARATIVE)
    )
    result = QAEngine().check_risk_assessment(brief)

    assert result.status == CheckStatus.PASS
    assert "Publication=LOW/AUTO_APPROVE" in result.details
    assert "source=HIGH/ESCALATE" in result.details


def test_qa_rejects_stale_brief_risk() -> None:
    brief = DeterministicGenerator().generate_brief(_record())
    brief.risk_level = RiskLevel.HIGH
    brief.risk_decision = RiskDecision.ESCALATE

    result = QAEngine().check_risk_assessment(brief)
    assert result.status == CheckStatus.FAIL
    assert "stale or incorrectly scoped" in result.details
