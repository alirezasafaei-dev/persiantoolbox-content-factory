"""Publisher with mandatory approval gate. Fail-closed by default."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..types import (
    Approval,
    Brief,
    QADecision,
    QAResult,
    RiskDecision,
    generate_hash,
    utcnow,
)
from ..utils.helpers import ensure_dir, project_root


class ApprovalError(Exception):
    """Raised when approval gate blocks publishing."""


class ChecksumError(ApprovalError):
    """Raised when brief/checksum mismatch detected."""


class VersionError(ApprovalError):
    """Raised when approval version does not match brief version."""


class ExpiredApprovalError(ApprovalError):
    """Raised when approval has expired."""


class ApprovalGate:
    """Mandatory approval gate — fail-closed by default.

    Rules:
    - ESCALATE → never publish without human approval.
    - FAIL → never publish under any condition.
    - Checksum mismatch → block.
    - No approval → block.
    - Expired approval → block.
    - Version mismatch → block.
    - Brief changed after approval → approval invalidated.
    """

    def __init__(self, approval_ttl_hours: int = 168) -> None:
        self.approval_ttl_hours = approval_ttl_hours
        self.approvals_dir = ensure_dir(project_root() / "data" / "approvals")

    def compute_brief_checksum(self, brief: Brief) -> str:
        """Compute deterministic checksum for a brief from its serialized dict."""
        payload = json.dumps(brief.to_dict(), sort_keys=True, ensure_ascii=False)
        return generate_hash(payload)

    def compute_checksum_from_file(self, brief_path: Path) -> str:
        """Compute checksum directly from a brief JSON file (avoids reconstruction drift)."""
        data = json.loads(brief_path.read_text(encoding="utf-8"))
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return generate_hash(payload)

    def save_approval(self, approval: Approval, checksum: str) -> Path:
        """Persist approval with checksum."""
        data = approval.to_dict()
        data["checksum"] = checksum
        path = self.approvals_dir / f"{approval.brief_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_approval(self, brief_id: str) -> tuple[Approval, str] | None:
        """Load approval + checksum. Returns None if not found."""
        path = self.approvals_dir / f"{brief_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        checksum = data.pop("checksum", "")
        approval = Approval(**{k: v for k, v in data.items() if k in Approval.__dataclass_fields__})
        return approval, checksum

    def validate(
        self,
        brief: Brief,
        qa_result: QAResult,
        brief_path: Path | None = None,
    ) -> None:
        """Validate all gate conditions. Raises ApprovalError on failure.

        This method is the single entry point for publishing gating.
        If brief_path is provided, checksums are computed from the file directly
        to avoid reconstruction drift.
        """
        # Compute current checksum
        if brief_path is not None:
            current_checksum = self.compute_checksum_from_file(brief_path)
        else:
            current_checksum = self.compute_brief_checksum(brief)

        # 1. FAIL → never publish
        if qa_result.decision == QADecision.FAIL:
            raise ApprovalError(
                f"QA decision is FAIL for {brief.brief_id}. FAIL results are never publishable."
            )

        # 2. ESCALATE → must have valid approval
        if (
            brief.risk_decision == RiskDecision.ESCALATE
            or qa_result.decision == QADecision.ESCALATE
        ):
            self._require_valid_approval(brief, current_checksum)

        # 3. Checksum must match current brief
        loaded = self.load_approval(brief.brief_id)
        if loaded is not None:
            approval, stored_checksum = loaded

            if stored_checksum != current_checksum:
                raise ChecksumError(
                    f"Checksum mismatch for {brief.brief_id}. "
                    "Brief has changed since approval. Re-approval required."
                )

        # 4. AUTO_APPROVE with no issues passes

    def _require_valid_approval(self, brief: Brief, current_checksum: str | None = None) -> None:
        """Require a valid, non-expired approval for the exact brief version."""
        loaded = self.load_approval(brief.brief_id)
        if loaded is None:
            raise ApprovalError(
                f"No approval found for {brief.brief_id}. "
                "Human approval required for ESCALATE content."
            )

        approval, stored_checksum = loaded

        # 5. Approval must be approved
        if not approval.approved:
            raise ApprovalError(
                f"Approval for {brief.brief_id} is not approved (approved={approval.approved})."
            )

        # 6. Check expiry
        try:
            created = datetime.fromisoformat(approval.created_at)
        except (ValueError, TypeError):
            raise ApprovalError(f"Invalid approval timestamp for {brief.brief_id}.") from None

        expires = created + timedelta(hours=self.approval_ttl_hours)
        if datetime.now(UTC) > expires:
            raise ExpiredApprovalError(
                f"Approval for {brief.brief_id} expired at {expires.isoformat()}. "
                "Re-approval required."
            )

        # 7. Version must match
        if hasattr(approval, "version") and approval.version != brief.version:
            raise VersionError(
                f"Approval version ({approval.version}) does not match "
                f"brief version ({brief.version}) for {brief.brief_id}."
            )

        # 8. Checksum must match (brief not changed after approval)
        if current_checksum is None:
            current_checksum = self.compute_brief_checksum(brief)
        if stored_checksum != current_checksum:
            raise ChecksumError(
                f"Brief changed after approval for {brief.brief_id}. "
                "Checksum mismatch. Re-approval required."
            )

    def revoke_approval(self, brief_id: str) -> bool:
        """Revoke (delete) an approval."""
        path = self.approvals_dir / f"{brief_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False


class MockPublisher:
    """Mock publisher for testing — never actually publishes."""

    def __init__(self) -> None:
        self.published: list[str] = []

    def publish(
        self,
        brief: Brief,
        gate: ApprovalGate,
        qa_result: QAResult,
        brief_path: Path | None = None,
    ) -> dict:
        """Attempt to publish. Returns status dict. Never sends external requests."""
        try:
            gate.validate(brief, qa_result, brief_path=brief_path)
            self.published.append(brief.brief_id)
            return {
                "status": "published",
                "brief_id": brief.brief_id,
                "mock": True,
                "published_at": utcnow(),
            }
        except ApprovalError as e:
            return {
                "status": "blocked",
                "brief_id": brief.brief_id,
                "mock": True,
                "reason": str(e),
            }


# --- New Instagram publisher exports ---
__all__ = [
    "AuthenticationError",
    "ContainerError",
    "ContainerExpiredError",
    "ContainerProcessingError",
    "IdempotencyViolationError",
    "MediaGateway",
    "MediaGatewayError",
    "MetaInstagramPublisher",
    "MetaInstagramSettings",
    "PublishError",
    "PublishJob",
    "PublishQueue",
    "PublishState",
    "Publisher",
    "PublisherError",
    "RateLimitError",
    "TokenExpiredError",
    "can_transition",
]

from .errors import AuthenticationError as AuthenticationError  # noqa: E402
from .errors import ContainerError as ContainerError  # noqa: E402
from .errors import ContainerExpiredError as ContainerExpiredError  # noqa: E402
from .errors import ContainerProcessingError as ContainerProcessingError  # noqa: E402
from .errors import IdempotencyViolationError as IdempotencyViolationError  # noqa: E402
from .errors import MediaGatewayError as MediaGatewayError  # noqa: E402
from .errors import PublisherError as PublisherError  # noqa: E402
from .errors import PublishError as PublishError  # noqa: E402
from .errors import RateLimitError as RateLimitError  # noqa: E402
from .errors import TokenExpiredError as TokenExpiredError  # noqa: E402
from .media_gateway import MediaGateway as MediaGateway  # noqa: E402
from .meta_instagram import MetaInstagramPublisher as MetaInstagramPublisher  # noqa: E402
from .protocol import Publisher as Publisher  # noqa: E402
from .protocol import PublishJob as PublishJob  # noqa: E402
from .protocol import PublishState as PublishState  # noqa: E402
from .protocol import can_transition as can_transition  # noqa: E402
from .queue import PublishQueue as PublishQueue  # noqa: E402
from .settings import MetaInstagramSettings as MetaInstagramSettings  # noqa: E402
