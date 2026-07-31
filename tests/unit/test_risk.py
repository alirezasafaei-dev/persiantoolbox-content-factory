"""Unit tests for risk engine."""

from ptb_content.risk import RiskEngine
from ptb_content.types import (
    CatalogRecord,
    Category,
    Claim,
    RiskDecision,
    RiskLevel,
    RiskTag,
    utcnow,
)


def _make_record(
    risk_tags: list[RiskTag] | None = None, claims: list[Claim] | None = None
) -> CatalogRecord:
    return CatalogRecord(
        canonical_url="https://example.com/test",
        title="Test",
        summary="Test summary",
        category=Category.TOOL_DEMO,
        source_id="test",
        source_hash="a" * 64,
        crawled_at=utcnow(),
        risk_tags=risk_tags or [],
        claims=claims or [],
    )


class TestRiskEngine:
    def setup_method(self) -> None:
        self.engine = RiskEngine()

    def test_low_risk_no_tags(self) -> None:
        record = _make_record()
        level, decision = self.engine.assess(record)
        assert level == RiskLevel.LOW
        assert decision == RiskDecision.AUTO_APPROVE

    def test_high_risk_financial(self) -> None:
        record = _make_record(risk_tags=[RiskTag.FINANCIAL])
        level, decision = self.engine.assess(record)
        assert level == RiskLevel.HIGH
        assert decision == RiskDecision.ESCALATE

    def test_high_risk_legal(self) -> None:
        record = _make_record(risk_tags=[RiskTag.LEGAL])
        level, decision = self.engine.assess(record)
        assert level == RiskLevel.HIGH

    def test_high_risk_privacy(self) -> None:
        record = _make_record(risk_tags=[RiskTag.PRIVACY])
        level, decision = self.engine.assess(record)
        assert level == RiskLevel.HIGH

    def test_medium_risk_statistical(self) -> None:
        record = _make_record(risk_tags=[RiskTag.STATISTICAL])
        level, decision = self.engine.assess(record)
        # Statistical is in escalate_tags, so HIGH
        assert level == RiskLevel.HIGH

    def test_medium_risk_comparative(self) -> None:
        record = _make_record(risk_tags=[RiskTag.COMPARATIVE])
        level, decision = self.engine.assess(record)
        # Comparative is in escalate_tags, so HIGH
        assert level == RiskLevel.HIGH

    def test_should_escalate(self) -> None:
        assert self.engine.should_escalate(RiskLevel.HIGH, RiskDecision.ESCALATE)
        assert not self.engine.should_escalate(RiskLevel.LOW, RiskDecision.AUTO_APPROVE)

    def test_unverified_claims_medium(self) -> None:
        claims = [
            Claim(text="claim1", source_id="s", verifiable=True),
            Claim(text="claim2", source_id="s", verifiable=True),
            Claim(text="claim3", source_id="s", verifiable=True),
        ]
        record = _make_record(claims=claims)
        level, decision = self.engine.assess(record)
        assert level == RiskLevel.MEDIUM
