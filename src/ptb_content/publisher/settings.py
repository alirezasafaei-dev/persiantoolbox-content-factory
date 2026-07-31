"""Publisher settings loaded from environment variables. Fail-closed defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_bool(key: str, default: bool = False) -> bool:
    val = os.environ.get(key, "").lower()
    if val in ("true", "1", "yes"):
        return True
    if val in ("false", "0", "no"):
        return False
    return default


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (ValueError, TypeError):
        return default


@dataclass(frozen=True)
class MetaInstagramSettings:
    """Settings for Meta Instagram Graph API integration.

    All secrets loaded from environment — never hardcoded.
    Fail-closed: empty/missing values mean publishing is blocked.
    """

    # Credentials
    app_id: str = field(default_factory=lambda: _env("META_INSTAGRAM_APP_ID"))
    app_secret: str = field(default_factory=lambda: _env("META_INSTAGRAM_APP_SECRET"))
    access_token: str = field(default_factory=lambda: _env("META_INSTAGRAM_ACCESS_TOKEN"))
    instagram_account_id: str = field(default_factory=lambda: _env("META_INSTAGRAM_ACCOUNT_ID"))

    # API config
    api_version: str = field(default_factory=lambda: _env("META_API_VERSION", "v21.0"))
    host_url: str = field(
        default_factory=lambda: _env("META_HOST_URL", "https://graph.facebook.com")
    )

    # Publish controls
    auto_publish: bool = field(default_factory=lambda: _env_bool("PTB_AUTO_PUBLISH", False))
    live_canary_approved: bool = field(
        default_factory=lambda: _env_bool("PTB_LIVE_CANARY_APPROVED", False)
    )
    generation_enabled: bool = field(
        default_factory=lambda: _env_bool("PTB_GENERATION_ENABLED", True)
    )
    scheduler_enabled: bool = field(
        default_factory=lambda: _env_bool("PTB_SCHEDULER_ENABLED", False)
    )
    real_publish_enabled: bool = field(
        default_factory=lambda: _env_bool("PTB_REAL_PUBLISH_ENABLED", False)
    )

    # Publisher selection
    publisher_backend: str = field(default_factory=lambda: _env("PTB_PUBLISHER", "mock"))

    # Rate limiting
    max_posts_per_24h: int = field(default_factory=lambda: _env_int("PTB_MAX_POSTS_PER_24H", 50))
    container_timeout_seconds: int = field(
        default_factory=lambda: _env_int("PTB_CONTAINER_TIMEOUT", 600)
    )
    poll_interval_seconds: int = field(default_factory=lambda: _env_int("PTB_POLL_INTERVAL", 10))

    # Media gateway
    media_gateway_secret: str = field(default_factory=lambda: _env("PTB_MEDIA_GATEWAY_SECRET"))
    media_gateway_ttl_hours: int = field(
        default_factory=lambda: _env_int("PTB_MEDIA_GATEWAY_TTL_HOURS", 24)
    )
    media_gateway_host: str = field(default_factory=lambda: _env("PTB_MEDIA_GATEWAY_HOST", ""))

    # Queue
    queue_db_path: str = field(
        default_factory=lambda: _env("PTB_QUEUE_DB", "data/publish-queue.db")
    )

    # OAuth redirect
    oauth_redirect_uri: str = field(
        default_factory=lambda: _env("PTB_OAUTH_REDIRECT_URI", "http://localhost:8080/callback")
    )

    @property
    def base_url(self) -> str:
        return f"{self.host_url}/{self.api_version}"

    @property
    def has_credentials(self) -> bool:
        return bool(
            self.app_id and self.app_secret and self.access_token and self.instagram_account_id
        )

    @property
    def can_publish(self) -> bool:
        return (
            self.has_credentials
            and self.real_publish_enabled
            and self.auto_publish
            and self.live_canary_approved
        )
