"""Risk assessment engine for content briefs."""

from __future__ import annotations

from ..types import (
    CatalogRecord,
    RiskDecision,
    RiskLevel,
    RiskTag,
)
from ..utils.helpers import load_config


class RiskEngine:
    """Deterministic risk assessment engine."""

    def __init__(self) -> None:
        self.config = load_config("risk")
        self.risk_config = self.config["risk_engine"]
        self.escalate_tags = {RiskTag(t) for t in self.risk_config["escalate_tags"]}
        self.always_review = set(self.risk_config["always_review"])

    def assess(self, record: CatalogRecord) -> tuple[RiskLevel, RiskDecision]:
        """Assess risk level and decision for a catalog record."""
        risk_tags = set(record.risk_tags)

        # HIGH: any escalate tag present
        if risk_tags & self.escalate_tags:
            return RiskLevel.HIGH, RiskDecision.ESCALATE

        # MEDIUM: has risk tags but not escalate-level
        if risk_tags:
            return RiskLevel.MEDIUM, RiskDecision.REVIEW_REQUIRED

        # Check claims for unverified assertions
        unverified_claims = [c for c in record.claims if c.verifiable and not c.evidence_url]
        if len(unverified_claims) > 2:
            return RiskLevel.MEDIUM, RiskDecision.REVIEW_REQUIRED

        # LOW: no risk tags, no problematic claims
        return RiskLevel.LOW, RiskDecision.AUTO_APPROVE

    def should_escalate(self, level: RiskLevel, decision: RiskDecision) -> bool:
        """Check if content should be escalated for human review."""
        return decision == RiskDecision.ESCALATE or level == RiskLevel.HIGH
