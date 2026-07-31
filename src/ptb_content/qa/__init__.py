"""Quality Assurance engine for content briefs."""

from __future__ import annotations

from ..types import (
    Brief,
    CheckResult,
    CheckStatus,
    QADecision,
    QAResult,
    RiskDecision,
    RiskLevel,
    utcnow,
)
from ..utils.persian import (
    check_zwnj_usage,
    has_arabic_imposters,
    is_valid_persian,
    normalize_persian,
)


class QAEngine:
    """Deterministic QA checks for content briefs."""

    def check_factuality(self, brief: Brief) -> CheckResult:
        """Check that all claims have source_id and are traceable."""
        claims = brief.catalog_record.claims
        if not claims:
            return CheckResult(status=CheckStatus.WARN, score=0.5, details="No claims to verify")

        missing_source = [c for c in claims if not c.source_id]
        if missing_source:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details=f"{len(missing_source)} claims missing source_id",
            )

        return CheckResult(status=CheckStatus.PASS, score=1.0, details="All claims have source_id")

    def check_persian_normalization(self, brief: Brief) -> CheckResult:
        """Check Persian text normalization."""
        text = brief.caption.primary
        normalized = normalize_persian(text)

        if has_arabic_imposters(text):
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.3,
                details="Arabic imposter characters found",
            )

        if text != normalized:
            return CheckResult(
                status=CheckStatus.WARN,
                score=0.7,
                details=f"Text needs normalization. Diff: {len(text)} → {len(normalized)} chars",
            )

        return CheckResult(status=CheckStatus.PASS, score=1.0, details="Persian text is normalized")

    def check_persian_rtl(self, brief: Brief) -> CheckResult:
        """Check RTL compliance."""
        text = brief.caption.primary
        if not is_valid_persian(text):
            return CheckResult(
                status=CheckStatus.WARN,
                score=0.6,
                details="Text may not be valid Persian",
            )

        zwnj_issues = check_zwnj_usage(text)
        if zwnj_issues:
            return CheckResult(
                status=CheckStatus.WARN,
                score=0.7,
                details=f"ZWNJ issues: {'; '.join(zwnj_issues[:3])}",
            )

        return CheckResult(status=CheckStatus.PASS, score=1.0, details="RTL and ZWNJ look correct")

    def check_risk_assessment(self, brief: Brief) -> CheckResult:
        """Check risk level is correctly assigned."""
        if brief.risk_level == RiskLevel.HIGH and brief.risk_decision != RiskDecision.ESCALATE:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details="HIGH risk content must be ESCALATE",
            )

        if brief.risk_level == RiskLevel.LOW and brief.risk_decision == RiskDecision.ESCALATE:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.2,
                details="LOW risk content should not be ESCALATE",
            )

        return CheckResult(
            status=CheckStatus.PASS, score=1.0, details="Risk assessment is consistent"
        )

    def check_source_existence(self, brief: Brief) -> CheckResult:
        """Check that source catalog record exists."""
        record = brief.catalog_record
        if not record.source_id:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing source_id")
        if not record.canonical_url:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing canonical_url")
        if not record.source_hash:
            return CheckResult(status=CheckStatus.WARN, score=0.5, details="Missing source_hash")

        return CheckResult(status=CheckStatus.PASS, score=1.0, details="Source record is complete")

    def check_claim_traceability(self, brief: Brief) -> CheckResult:
        """Check that claims are traceable."""
        claims = brief.catalog_record.claims
        if not claims:
            return CheckResult(status=CheckStatus.PASS, score=1.0, details="No claims to trace")

        traceable = sum(1 for c in claims if c.source_id and c.verifiable)
        ratio = traceable / len(claims)

        if ratio < 0.5:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=ratio,
                details=f"Only {ratio:.0%} of claims are traceable",
            )

        return CheckResult(
            status=CheckStatus.PASS,
            score=ratio,
            details=f"{ratio:.0%} of claims are traceable",
        )

    def check_visual_render(self, brief: Brief) -> CheckResult:
        """Check that art direction is complete for rendering."""
        art = brief.art_direction
        if not art.template:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing template")
        if not art.color_palette.primary:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing color palette")
        if not art.typography.heading_font:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing typography")

        return CheckResult(status=CheckStatus.PASS, score=1.0, details="Art direction is complete")

    def check_duplicate(self, brief: Brief, existing_briefs: list[str]) -> CheckResult:
        """Check for duplicate content."""
        caption_hash = hash(brief.caption.primary)
        if caption_hash in existing_briefs:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details="Duplicate caption detected",
            )
        return CheckResult(status=CheckStatus.PASS, score=1.0, details="No duplicate detected")

    def run_all(self, brief: Brief, existing_briefs: list[str] | None = None) -> QAResult:
        """Run all QA checks and return result."""
        checks = {
            "factuality": self.check_factuality(brief),
            "persian_normalization": self.check_persian_normalization(brief),
            "persian_rtl": self.check_persian_rtl(brief),
            "risk_assessment": self.check_risk_assessment(brief),
            "source_existence": self.check_source_existence(brief),
            "claim_traceability": self.check_claim_traceability(brief),
            "visual_render": self.check_visual_render(brief),
        }

        if existing_briefs is not None:
            checks["duplicate_check"] = self.check_duplicate(brief, existing_briefs)

        # Determine overall decision
        failures = [k for k, v in checks.items() if v.status == CheckStatus.FAIL]

        failure_reasons = [
            f"{k}: {v.details}" for k, v in checks.items() if v.status == CheckStatus.FAIL
        ]

        if brief.risk_level == RiskLevel.HIGH:
            decision = QADecision.ESCALATE
        elif failures:
            decision = QADecision.FAIL
        else:
            decision = QADecision.PASS

        return QAResult(
            brief_id=brief.brief_id,
            checks=checks,
            decision=decision,
            failure_reasons=failure_reasons,
            generated_at=utcnow(),
        )
