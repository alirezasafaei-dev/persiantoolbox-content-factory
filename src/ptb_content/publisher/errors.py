"""Custom errors for the publisher module."""

from __future__ import annotations


class PublisherError(Exception):
    """Base error for all publisher operations."""


class AuthenticationError(PublisherError):
    """OAuth token missing, invalid, or expired."""


class TokenExpiredError(AuthenticationError):
    """Access token has expired and needs refresh."""


class ContainerError(PublisherError):
    """Media container creation or processing failed."""


class ContainerExpiredError(ContainerError):
    """Container was not published within 24 hours."""


class ContainerProcessingError(ContainerError):
    """Container is still processing (timeout)."""


class PublishError(PublisherError):
    """media_publish call failed."""


class RateLimitError(PublisherError):
    """Instagram API rate limit exceeded."""


class MediaGatewayError(PublisherError):
    """Media gateway (signed URL) operation failed."""


class IdempotencyViolationError(PublisherError):
    """Duplicate publish attempt detected (same idempotency key)."""


class QueueError(PublisherError):
    """Publish queue operation failed."""


class ValidationError(PublisherError):
    """Input validation failed."""
