"""Unit tests for QA engine."""

from ptb_content.qa import QAEngine
from ptb_content.types import (
    ArtDirection,
    Audience,
    Brief,
    Caption,
    CatalogRecord,
    Category,
    Claim,
    ColorPalette,
    ContentStrategy,
    HookType,
    PsychologyHypothesis,
    RiskDecision,
    RiskLevel,
    TemplateType,
    Typography,
    utcnow,
)


def _make_brief(
    risk_level: RiskLevel = RiskLevel.LOW,
    risk_decision: RiskDecision = RiskDecision.AUTO_APPROVE,
    claims: list[Claim] | None = None,
    caption_text: str = "این یک متن تست فارسی است",
) -> Brief:
    """Create a minimal brief for testing."""
    record = CatalogRecord(
        canonical_url="https://example.com/test",
        title="ابزار تست",
        summary="یک ابزار برای تست",
        category=Category.TOOL_DEMO,
        source_id="test-tool",
        source_hash="a" * 64,
        crawled_at=utcnow(),
        claims=claims or [],
    )
    return Brief(
        brief_id="brief-test-001",
        catalog_record=record,
        audience=Audience(segment="تست", pain_point="تست", desire="تست"),
        content_strategy=ContentStrategy(
            angle="تست",
            hook_type=HookType.DIRECT,
            template_type=TemplateType.TOOL_DEMO,
        ),
        psychology_hypothesis=PsychologyHypothesis(principle="تست", expected_effect="تست"),
        caption=Caption(primary=caption_text, cta="تست"),
        art_direction=ArtDirection(
            template=TemplateType.TOOL_DEMO,
            color_palette=ColorPalette(),
            typography=Typography(),
        ),
        risk_level=risk_level,
        risk_decision=risk_decision,
    )


class TestQAEngine:
    def setup_method(self) -> None:
        self.qa = QAEngine()

    def test_factuality_pass(self) -> None:
        claims = [Claim(text="test", source_id="src", verifiable=True)]
        brief = _make_brief(claims=claims)
        result = self.qa.check_factuality(brief)
        assert result.status.value == "PASS"

    def test_factuality_fail_no_source(self) -> None:
        claims = [Claim(text="test", source_id="", verifiable=True)]
        brief = _make_brief(claims=claims)
        result = self.qa.check_factuality(brief)
        assert result.status.value == "FAIL"

    def test_persian_normalization(self) -> None:
        brief = _make_brief(caption_text="این یک متن فارسی است")
        result = self.qa.check_persian_normalization(brief)
        assert result.status.value in ("PASS", "WARN")

    def test_risk_assessment_consistent(self) -> None:
        brief = _make_brief(risk_level=RiskLevel.LOW, risk_decision=RiskDecision.AUTO_APPROVE)
        result = self.qa.check_risk_assessment(brief)
        assert result.status.value == "PASS"

    def test_risk_high_must_escalate(self) -> None:
        brief = _make_brief(risk_level=RiskLevel.HIGH, risk_decision=RiskDecision.AUTO_APPROVE)
        result = self.qa.check_risk_assessment(brief)
        assert result.status.value == "FAIL"

    def test_source_existence(self) -> None:
        brief = _make_brief()
        result = self.qa.check_source_existence(brief)
        assert result.status.value == "PASS"

    def test_visual_render(self) -> None:
        brief = _make_brief()
        result = self.qa.check_visual_render(brief)
        assert result.status.value == "PASS"

    def test_run_all_pass(self) -> None:
        brief = _make_brief()
        result = self.qa.run_all(brief)
        assert result.decision.value in ("PASS", "ESCALATE")
        assert len(result.checks) > 0

    def test_run_all_high_risk_escalates(self) -> None:
        claims = [Claim(text="test", source_id="src", verifiable=True)]
        brief = _make_brief(
            risk_level=RiskLevel.HIGH,
            risk_decision=RiskDecision.ESCALATE,
            claims=claims,
            caption_text="این ابزار رایگان است",
        )
        result = self.qa.run_all(brief)
        assert result.decision.value == "ESCALATE"

    def test_duplicate_check(self) -> None:
        brief = _make_brief()
        result = self.qa.check_duplicate(brief, ["existing-hash"])
        assert result.status.value == "PASS"

    def test_duplicate_check_found(self) -> None:
        brief = _make_brief()
        existing_hash = hash(brief.caption.primary)
        result = self.qa.check_duplicate(brief, [existing_hash])
        assert result.status.value == "FAIL"
