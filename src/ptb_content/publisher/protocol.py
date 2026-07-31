"""Publisher Protocol and PublishJob state machine."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from ..types import Brief, QAResult, utcnow


class PublishState(str, Enum):
    """State machine for publish lifecycle."""

    DRAFT = "DRAFT"
    QA_PASSED = "QA_PASSED"
    ESCALATED = "ESCALATED"
    APPROVED = "APPROVED"
    SCHEDULED = "SCHEDULED"
    VALIDATING = "VALIDATING"
    MEDIA_EXPOSED = "MEDIA_EXPOSED"
    CONTAINER_CREATED = "CONTAINER_CREATED"
    PROCESSING = "PROCESSING"
    PUBLISHED = "PUBLISHED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_PERMANENT = "FAILED_PERMANENT"
    REVOKED = "REVOKED"
    CANCELLED = "CANCELLED"


# Valid state transitions
_VALID_TRANSITIONS: dict[PublishState, set[PublishState]] = {
    PublishState.DRAFT: {
        PublishState.QA_PASSED,
        PublishState.FAILED_PERMANENT,
        PublishState.CANCELLED,
    },
    PublishState.QA_PASSED: {PublishState.ESCALATED, PublishState.APPROVED, PublishState.CANCELLED},
    PublishState.ESCALATED: {PublishState.APPROVED, PublishState.REVOKED, PublishState.CANCELLED},
    PublishState.APPROVED: {PublishState.SCHEDULED, PublishState.CANCELLED},
    PublishState.SCHEDULED: {PublishState.VALIDATING, PublishState.CANCELLED},
    PublishState.VALIDATING: {
        PublishState.MEDIA_EXPOSED,
        PublishState.FAILED_RETRYABLE,
        PublishState.FAILED_PERMANENT,
    },
    PublishState.MEDIA_EXPOSED: {
        PublishState.CONTAINER_CREATED,
        PublishState.FAILED_RETRYABLE,
        PublishState.FAILED_PERMANENT,
    },
    PublishState.CONTAINER_CREATED: {
        PublishState.PROCESSING,
        PublishState.FAILED_RETRYABLE,
        PublishState.FAILED_PERMANENT,
    },
    PublishState.PROCESSING: {
        PublishState.PUBLISHED,
        PublishState.FAILED_RETRYABLE,
        PublishState.FAILED_PERMANENT,
    },
    PublishState.FAILED_RETRYABLE: {PublishState.VALIDATING, PublishState.CANCELLED},
    PublishState.FAILED_PERMANENT: set(),
    PublishState.PUBLISHED: set(),
    PublishState.REVOKED: set(),
    PublishState.CANCELLED: set(),
}


def can_transition(from_state: PublishState, to_state: PublishState) -> bool:
    return to_state in _VALID_TRANSITIONS.get(from_state, set())


@dataclass
class PublishJob:
    """Immutable publish job with state machine transitions."""

    job_id: str
    brief_id: str
    content_checksum: str
    instagram_account_id: str
    state: PublishState = PublishState.DRAFT
    media_id: str | None = None
    container_id: str | None = None
    instagram_media_id: str | None = None
    idempotency_key: str = ""
    error_message: str | None = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = field(default_factory=utcnow)
    updated_at: str = field(default_factory=utcnow)
    published_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.idempotency_key:
            self.idempotency_key = (
                f"publish:{self.brief_id}:{self.content_checksum}:{self.instagram_account_id}"
            )

    def transition(self, new_state: PublishState, error_message: str | None = None) -> None:
        if not can_transition(self.state, new_state):
            raise InvalidStateTransitionError(
                f"Cannot transition from {self.state.value} to {new_state.value}"
            )
        self.state = new_state
        self.updated_at = utcnow()
        if error_message:
            self.error_message = error_message
        if new_state == PublishState.PUBLISHED:
            self.published_at = utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "brief_id": self.brief_id,
            "content_checksum": self.content_checksum,
            "instagram_account_id": self.instagram_account_id,
            "state": self.state.value,
            "media_id": self.media_id,
            "container_id": self.container_id,
            "instagram_media_id": self.instagram_media_id,
            "idempotency_key": self.idempotency_key,
            "error_message": self.error_message,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "published_at": self.published_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PublishJob:
        data = data.copy()
        data["state"] = PublishState(data["state"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class InvalidStateTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""


@runtime_checkable
class Publisher(Protocol):
    """Protocol that all publishers must implement."""

    def validate(self, brief: Brief, qa_result: QAResult) -> None:
        """Validate that a brief is ready for publishing. Raises on failure."""
        ...

    def publish(self, brief: Brief, qa_result: QAResult) -> PublishJob:
        """Publish a brief. Returns a PublishJob with final state set."""
        ...

    def get_status(self, job_id: str) -> PublishJob | None:
        """Get the status of a publish job. Returns None if not found."""
        ...
