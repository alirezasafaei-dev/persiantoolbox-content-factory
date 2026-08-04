"""Quality Assurance engine for content briefs."""

from __future__ import annotations

import json
from pathlib import Path

from ..content_shaping import editorial_issues, publication_text
from ..risk import RiskEngine
from ..types import (
    Brief,
    CheckResult,
    CheckStatus,
    QADecision,
    QAResult,
    RiskLevel,
    utcnow,
)
from ..utils.helpers import project_root
from ..utils.persian import (
    check_zwnj_usage,
    has_arabic_imposters,
    is_valid_persian,
    normalize_persian,
)
from ..visual_qa import audit_render_set


class QAEngine:
    """Deterministic editorial, risk, provenance and visual QA."""

    def __init__(
        self,
        outputs_dir: Path | None = None,
        require_rendered_assets: bool | None = None,
    ) -> None:
        self.outputs_dir = outputs_dir or project_root() / "outputs"
        self.require_rendered_assets = require_rendered_assets

    def check_factuality(self, brief: Brief) -> CheckResult:
        claims = brief.catalog_record.claims
        if not claims:
            return CheckResult(status=CheckStatus.WARN, score=0.5, details="No claims to verify")

        missing_source = [claim for claim in claims if not claim.source_id]
        if missing_source:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details=f"{len(missing_source)} claims missing source_id",
            )
        return CheckResult(status=CheckStatus.PASS, score=1.0, details="All claims have source_id")

    def check_editorial_quality(self, brief: Brief) -> CheckResult:
        """Block malformed, repetitive or internal-facing audience copy."""
        issues = editorial_issues(brief)
        if issues:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details="; ".join(issues),
            )
        return CheckResult(
            status=CheckStatus.PASS,
            score=1.0,
            details="Audience-visible Persian copy passes editorial rules",
        )

    def check_persian_normalization(self, brief: Brief) -> CheckResult:
        text = publication_text(brief)
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
        text = publication_text(brief)
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
        engine = RiskEngine()
        expected_level, expected_decision, expected_tags = engine.assess_publishable_text(
            publication_text(brief),
            cta=brief.caption.cta,
            alt_text=brief.caption.alt_text,
        )

        if brief.risk_level != expected_level or brief.risk_decision != expected_decision:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details=(
                    "Publication risk is stale or incorrectly scoped: "
                    f"stored={brief.risk_level.value}/{brief.risk_decision.value}, "
                    f"expected={expected_level.value}/{expected_decision.value}, "
                    f"tags={sorted(tag.value for tag in expected_tags)}"
                ),
            )

        stored_tags = set(brief.catalog_record.meta.get("publication_risk_tags", []))
        calculated_tags = {tag.value for tag in expected_tags}
        if stored_tags != calculated_tags:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details=(
                    "Stored publication risk tags do not match all audience-visible copy: "
                    f"stored={sorted(stored_tags)}, calculated={sorted(calculated_tags)}"
                ),
            )

        source_level, source_decision = engine.assess(brief.catalog_record)
        return CheckResult(
            status=CheckStatus.PASS,
            score=1.0,
            details=(
                f"Publication={expected_level.value}/{expected_decision.value}, "
                f"source={source_level.value}/{source_decision.value}, "
                f"publish_tags={sorted(calculated_tags)}"
            ),
        )

    def check_source_existence(self, brief: Brief) -> CheckResult:
        record = brief.catalog_record
        if not record.source_id:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing source_id")
        if not record.canonical_url:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing canonical_url")
        if not record.source_hash:
            return CheckResult(status=CheckStatus.WARN, score=0.5, details="Missing source_hash")
        return CheckResult(status=CheckStatus.PASS, score=1.0, details="Source record is complete")

    def check_claim_traceability(self, brief: Brief) -> CheckResult:
        claims = brief.catalog_record.claims
        if not claims:
            return CheckResult(status=CheckStatus.PASS, score=1.0, details="No claims to trace")

        traceable = sum(1 for claim in claims if claim.source_id and claim.verifiable)
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
        """Validate design metadata and, when rendered, all mandatory PNGs."""
        art = brief.art_direction
        if not art.template:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing template")
        if not art.color_palette.primary:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing color palette")
        if not art.typography.heading_font:
            return CheckResult(status=CheckStatus.FAIL, score=0.0, details="Missing typography")

        brief_dir = self.outputs_dir / brief.brief_id
        should_audit = self.require_rendered_assets is True or (
            self.require_rendered_assets is None and brief_dir.exists()
        )
        if not should_audit:
            return CheckResult(
                status=CheckStatus.PASS,
                score=1.0,
                details="Art direction is complete; rendered-asset audit not requested",
            )

        audits = audit_render_set(brief.brief_id, self.outputs_dir)
        failures = {
            size: list(audit.issues) for size, audit in audits.items() if not audit.passed
        }
        if failures:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details="Visual audit failed: " + json.dumps(failures, ensure_ascii=False),
            )

        metrics = {size: audit.metrics.to_dict() for size, audit in audits.items()}
        return CheckResult(
            status=CheckStatus.PASS,
            score=1.0,
            details="Visual audit passed: " + json.dumps(metrics, ensure_ascii=False),
        )

    def check_duplicate(self, brief: Brief, existing_briefs: list[str]) -> CheckResult:
        caption_hash = hash(brief.caption.primary)
        if caption_hash in existing_briefs:
            return CheckResult(
                status=CheckStatus.FAIL,
                score=0.0,
                details="Duplicate caption detected",
            )
        return CheckResult(status=CheckStatus.PASS, score=1.0, details="No duplicate detected")

    def run_all(self, brief: Brief, existing_briefs: list[str] | None = None) -> QAResult:
        checks = {
            "factuality": self.check_factuality(brief),
            "editorial_quality": self.check_editorial_quality(brief),
            "persian_normalization": self.check_persian_normalization(brief),
            "persian_rtl": self.check_persian_rtl(brief),
            "risk_assessment": self.check_risk_assessment(brief),
            "source_existence": self.check_source_existence(brief),
            "claim_traceability": self.check_claim_traceability(brief),
            "visual_render": self.check_visual_render(brief),
        }
        if existing_briefs is not None:
            checks["duplicate_check"] = self.check_duplicate(brief, existing_briefs)

        failures = [name for name, result in checks.items() if result.status == CheckStatus.FAIL]
        failure_reasons = [
            f"{name}: {result.details}"
            for name, result in checks.items()
            if result.status == CheckStatus.FAIL
        ]

        if failures:
            decision = QADecision.FAIL
        elif brief.risk_level == RiskLevel.HIGH:
            decision = QADecision.ESCALATE
        else:
            decision = QADecision.PASS

        return QAResult(
            brief_id=brief.brief_id,
            checks=checks,
            decision=decision,
            failure_reasons=failure_reasons,
            generated_at=utcnow(),
        )
