"""Publisher with mandatory approval and visual-proof gates."""

from __future__ import annotations

import hashlib
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

    An approval is valid only for the exact brief JSON and the exact visual
    contact sheet reviewed at approval time.
    """

    def __init__(self, approval_ttl_hours: int = 168) -> None:
        self.approval_ttl_hours = approval_ttl_hours
        self.approvals_dir = ensure_dir(project_root() / "data" / "approvals")

    def compute_brief_checksum(self, brief: Brief) -> str:
        payload = json.dumps(brief.to_dict(), sort_keys=True, ensure_ascii=False)
        return generate_hash(payload)

    def compute_checksum_from_file(self, brief_path: Path) -> str:
        data = json.loads(brief_path.read_text(encoding="utf-8"))
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return generate_hash(payload)

    @staticmethod
    def _proof_condition(conditions: list[str]) -> str:
        return next((item for item in conditions if item.startswith("visual-proof-sha256:")), "")

    def _contact_sheet_path(self, brief_id: str) -> Path:
        return project_root() / "outputs" / "review" / f"{brief_id}-contact-sheet.png"

    def save_approval(self, approval: Approval, checksum: str) -> Path:
        """Persist approval and bind it to the current contact-sheet checksum."""
        if approval.approved:
            proof_path = self._contact_sheet_path(approval.brief_id)
            if not proof_path.exists():
                raise ApprovalError(
                    f"Missing visual contact sheet for {approval.brief_id}. "
                    "Render and review all platform assets before approval."
                )
            proof_checksum = hashlib.sha256(proof_path.read_bytes()).hexdigest()
            approval.conditions = [
                condition
                for condition in approval.conditions
                if not condition.startswith("visual-proof-sha256:")
            ]
            approval.conditions.append(f"visual-proof-sha256:{proof_checksum}")
            approval.conditions.append(f"visual-proof-path:{proof_path}")

        data = approval.to_dict()
        data["checksum"] = checksum
        path = self.approvals_dir / f"{approval.brief_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load_approval(self, brief_id: str) -> tuple[Approval, str] | None:
        path = self.approvals_dir / f"{brief_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        checksum = data.pop("checksum", "")
        approval = Approval(
            **{
                key: value
                for key, value in data.items()
                if key in Approval.__dataclass_fields__
            }
        )
        return approval, checksum

    def validate(
        self,
        brief: Brief,
        qa_result: QAResult,
        brief_path: Path | None = None,
    ) -> None:
        current_checksum = (
            self.compute_checksum_from_file(brief_path)
            if brief_path is not None
            else self.compute_brief_checksum(brief)
        )
        if qa_result.decision == QADecision.FAIL:
            raise ApprovalError(
                f"QA decision is FAIL for {brief.brief_id}. FAIL results are never publishable."
            )
        if (
            brief.risk_decision == RiskDecision.ESCALATE
            or qa_result.decision == QADecision.ESCALATE
        ):
            self._require_valid_approval(brief, current_checksum)

        loaded = self.load_approval(brief.brief_id)
        if loaded is not None:
            approval, stored_checksum = loaded
            if stored_checksum != current_checksum:
                raise ChecksumError(
                    f"Checksum mismatch for {brief.brief_id}. Re-approval required."
                )
            self._validate_visual_proof(approval)

    def _validate_visual_proof(self, approval: Approval) -> None:
        proof_condition = self._proof_condition(approval.conditions)
        if not proof_condition:
            raise ApprovalError(
                f"Approval for {approval.brief_id} is not bound to a visual contact sheet."
            )
        expected = proof_condition.split(":", 1)[1]
        proof_path = self._contact_sheet_path(approval.brief_id)
        if not proof_path.exists():
            raise ApprovalError(f"Visual contact sheet missing for {approval.brief_id}.")
        actual = hashlib.sha256(proof_path.read_bytes()).hexdigest()
        if actual != expected:
            raise ChecksumError(
                f"Visual assets changed after approval for {approval.brief_id}. Re-approval required."
            )

    def _require_valid_approval(self, brief: Brief, current_checksum: str | None = None) -> None:
        loaded = self.load_approval(brief.brief_id)
        if loaded is None:
            raise ApprovalError(
                f"No approval found for {brief.brief_id}. Human approval required."
            )
        approval, stored_checksum = loaded
        if not approval.approved:
            raise ApprovalError(
                f"Approval for {brief.brief_id} is not approved (approved={approval.approved})."
            )
        try:
            created = datetime.fromisoformat(approval.created_at)
        except (ValueError, TypeError):
            raise ApprovalError(f"Invalid approval timestamp for {brief.brief_id}.") from None
        expires = created + timedelta(hours=self.approval_ttl_hours)
        if datetime.now(UTC) > expires:
            raise ExpiredApprovalError(
                f"Approval for {brief.brief_id} expired at {expires.isoformat()}."
            )
        if approval.version != brief.version:
            raise VersionError(
                f"Approval version ({approval.version}) does not match brief version ({brief.version})."
            )
        if current_checksum is None:
            current_checksum = self.compute_brief_checksum(brief)
        if stored_checksum != current_checksum:
            raise ChecksumError(
                f"Brief changed after approval for {brief.brief_id}. Re-approval required."
            )
        self._validate_visual_proof(approval)

    def revoke_approval(self, brief_id: str) -> bool:
        path = self.approvals_dir / f"{brief_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False


class MockPublisher:
    """Mock publisher for testing — never sends external requests."""

    def __init__(self) -> None:
        self.published: list[str] = []

    def publish(
        self,
        brief: Brief,
        gate: ApprovalGate,
        qa_result: QAResult,
        brief_path: Path | None = None,
    ) -> dict:
        try:
            gate.validate(brief, qa_result, brief_path=brief_path)
            self.published.append(brief.brief_id)
            return {
                "status": "published",
                "brief_id": brief.brief_id,
                "mock": True,
                "published_at": utcnow(),
            }
        except ApprovalError as exc:
            return {
                "status": "blocked",
                "brief_id": brief.brief_id,
                "mock": True,
                "reason": str(exc),
            }


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
