"""Approval gate tests — all scenarios from the spec.

Covers:
- ESCALATE without approval → blocked
- FAIL → always blocked
- Checksum invalid → blocked
- No approval → blocked
- Expired approval → blocked
- Version mismatch → blocked
- Brief changed after approval → approval invalidated
- Default is always fail-closed
- All publishers are mocked (no external publish)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from ptb_content.publisher import (
    ApprovalError,
    ApprovalGate,
    ChecksumError,
    ExpiredApprovalError,
    MockPublisher,
    VersionError,
)
from ptb_content.types import (
    Approval,
    Brief,
    CatalogRecord,
    Category,
    Claim,
    QADecision,
    QAResult,
    RiskDecision,
    RiskLevel,
    utcnow,
)


def _make_brief(
    risk_level: RiskLevel = RiskLevel.HIGH,
    risk_decision: RiskDecision = RiskDecision.ESCALATE,
    version: int = 1,
    caption_text: str = "متن تست",
) -> Brief:
    """Create a test brief."""
    from ptb_content.generator import DeterministicGenerator

    gen = DeterministicGenerator()
    cr = CatalogRecord(
        canonical_url="https://example.com/approval-test",
        title="تست approval gate",
        summary="تست بررسی approval gate برای انتشار",
        category=Category.TOOL_DEMO,
        source_id="approval-test",
        source_hash="c" * 64,
        crawled_at=utcnow(),
        claims=[Claim(text="ادعای تست", source_id="approval-test", verifiable=True)],
    )
    brief = gen.generate_briefs([cr])[0]
    brief.risk_level = risk_level
    brief.risk_decision = risk_decision
    brief.version = version
    if caption_text:
        brief.caption.primary = caption_text
    return brief


def _make_qa(decision: QADecision = QADecision.ESCALATE) -> QAResult:
    """Create a QA result."""
    return QAResult(
        brief_id="test-qa",
        checks={},
        decision=decision,
    )


class TestFailClosed:
    """Default behavior must always be fail-closed."""

    def test_no_approval_blocks_escalate(self) -> None:
        """ESCALATE without approval must be blocked."""
        gate = ApprovalGate()
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)

        with pytest.raises(ApprovalError):
            gate.validate(brief, qa)

    def test_no_approval_blocks_auto_approve_escalate(self) -> None:
        """AUTO_APPROVE brief with ESCALATE decision must be blocked."""
        gate = ApprovalGate()
        brief = _make_brief(risk_decision=RiskDecision.ESCALATE)
        qa = _make_qa(QADecision.PASS)

        with pytest.raises(ApprovalError):
            gate.validate(brief, qa)


class TestFAILNeverPublishes:
    """FAIL QA decision → never publish under any condition."""

    def test_fail_always_blocked(self) -> None:
        """FAIL is blocked even with valid approval."""
        gate = ApprovalGate()
        brief = _make_brief()
        qa = _make_qa(QADecision.FAIL)

        # Even if we had an approval, FAIL should still be blocked
        with pytest.raises(ApprovalError, match="FAIL"):
            gate.validate(brief, qa)

    def test_fail_with_approval_still_blocked(self) -> None:
        """FAIL with approval still blocked."""
        gate = ApprovalGate()
        brief = _make_brief()

        # Create approval
        checksum = gate.compute_brief_checksum(brief)
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test")
        gate.save_approval(approval, checksum)

        qa = _make_qa(QADecision.FAIL)
        with pytest.raises(ApprovalError, match="FAIL"):
            gate.validate(brief, qa)


class TestESCALATERequiresApproval:
    """ESCALATE must have valid approval."""

    def test_escalate_without_approval_blocked(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)

        with pytest.raises(ApprovalError, match="No approval found"):
            gate.validate(brief, qa)

    def test_escalate_with_valid_approval_passes(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)

        checksum = gate.compute_brief_checksum(brief)
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test")
        gate.save_approval(approval, checksum)

        # Should not raise
        gate.validate(brief, qa)

    def test_escalate_with_unapproved_approval_blocked(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)

        checksum = gate.compute_brief_checksum(brief)
        approval = Approval(brief_id=brief.brief_id, approved=False, reviewer="test")
        gate.save_approval(approval, checksum)

        with pytest.raises(ApprovalError, match="not approved"):
            gate.validate(brief, qa)


class TestChecksumValidation:
    """Checksum must match current brief."""

    def test_checksum_mismatch_blocks(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)

        # Save approval with wrong checksum
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test")
        gate.save_approval(approval, "wrong_checksum")

        with pytest.raises(ChecksumError):
            gate.validate(brief, qa)

    def test_brief_changed_after_approval_blocks(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief(caption_text="متن اصلی")
        qa = _make_qa(QADecision.ESCALATE)

        checksum = gate.compute_brief_checksum(brief)
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test")
        gate.save_approval(approval, checksum)

        # Change the brief
        brief.caption.primary = "متن تغییر یافته"

        with pytest.raises(ChecksumError, match="changed after approval"):
            gate.validate(brief, qa)


class TestExpiredApproval:
    """Approval must not be expired."""

    def test_expired_approval_blocks(self) -> None:
        gate = ApprovalGate(approval_ttl_hours=1)
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)

        checksum = gate.compute_brief_checksum(brief)
        # Create approval 2 hours ago (expired)
        old_time = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        approval = Approval(
            brief_id=brief.brief_id, approved=True, reviewer="test", created_at=old_time
        )
        gate.save_approval(approval, checksum)

        with pytest.raises(ExpiredApprovalError):
            gate.validate(brief, qa)

    def test_fresh_approval_passes(self) -> None:
        gate = ApprovalGate(approval_ttl_hours=168)
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)

        checksum = gate.compute_brief_checksum(brief)
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test")
        gate.save_approval(approval, checksum)

        # Should not raise (fresh approval)
        gate.validate(brief, qa)


class TestVersionMismatch:
    """Approval version must match brief version."""

    def test_version_mismatch_blocks(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief(version=2)
        qa = _make_qa(QADecision.ESCALATE)

        checksum = gate.compute_brief_checksum(brief)
        # Approval for version 1 (but brief is version 2)
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test", version=1)
        gate.save_approval(approval, checksum)

        with pytest.raises(VersionError):
            gate.validate(brief, qa)

    def test_matching_version_passes(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief(version=1)
        qa = _make_qa(QADecision.ESCALATE)

        checksum = gate.compute_brief_checksum(brief)
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test", version=1)
        gate.save_approval(approval, checksum)

        # Should not raise
        gate.validate(brief, qa)


class TestMockPublisher:
    """Mock publisher never actually publishes."""

    def test_mock_publisher_records_blocked(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)
        publisher = MockPublisher()

        result = publisher.publish(brief, gate, qa)
        assert result["status"] == "blocked"
        assert result["mock"] is True
        assert len(publisher.published) == 0

    def test_mock_publisher_records_published(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief()
        qa = _make_qa(QADecision.ESCALATE)
        publisher = MockPublisher()

        # Add valid approval
        checksum = gate.compute_brief_checksum(brief)
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test")
        gate.save_approval(approval, checksum)

        result = publisher.publish(brief, gate, qa)
        assert result["status"] == "published"
        assert result["mock"] is True
        assert brief.brief_id in publisher.published

    def test_mock_publisher_never_sends_external(self) -> None:
        """Mock publisher should not have any network methods."""
        publisher = MockPublisher()
        assert not hasattr(publisher, "send")
        assert not hasattr(publisher, "post")
        assert not hasattr(publisher, "request")


class TestApprovalRevocation:
    """Test approval revocation."""

    def test_revoke_approval(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief()

        checksum = gate.compute_brief_checksum(brief)
        approval = Approval(brief_id=brief.brief_id, approved=True, reviewer="test")
        gate.save_approval(approval, checksum)

        # Verify exists
        loaded = gate.load_approval(brief.brief_id)
        assert loaded is not None

        # Revoke
        revoked = gate.revoke_approval(brief.brief_id)
        assert revoked is True

        # Verify gone
        loaded = gate.load_approval(brief.brief_id)
        assert loaded is None

    def test_revoke_nonexistent_returns_false(self) -> None:
        gate = ApprovalGate()
        revoked = gate.revoke_approval("nonexistent-brief-id")
        assert revoked is False


class TestNoApprovalForPASS:
    """PASS decisions with AUTO_APPROVE don't require approval."""

    def test_pass_auto_approve_no_approval_needed(self) -> None:
        gate = ApprovalGate()
        brief = _make_brief(risk_decision=RiskDecision.AUTO_APPROVE)
        qa = _make_qa(QADecision.PASS)

        # Should not raise
        gate.validate(brief, qa)
