"""Media gateway: signed HTTPS URLs with HMAC tokens for secure media delivery."""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse
from pathlib import Path

from .errors import MediaGatewayError
from .settings import MetaInstagramSettings


class MediaGateway:
    """Signs local media files for temporary public access via HMAC tokens.

    Token format: ?token=<hmac>&expires=<unix_timestamp>&path=<url_encoded_path>
    Validation: recomputes HMAC and checks expiry.
    """

    def __init__(self, settings: MetaInstagramSettings | None = None) -> None:
        self.settings = settings or MetaInstagramSettings()
        self._secret = self.settings.media_gateway_secret
        self._ttl_hours = self.settings.media_gateway_ttl_hours
        self._host = self.settings.media_gateway_host

    @property
    def enabled(self) -> bool:
        return bool(self._secret and self._host)

    def sign_url(self, local_path: Path, expires_at: float | None = None) -> str:
        """Generate a signed URL for a local media file.

        Args:
            local_path: Absolute path to the media file on disk.
            expires_at: Unix timestamp for expiry. Defaults to ttl_hours from now.

        Returns:
            Signed URL string.
        """
        if not self.enabled:
            raise MediaGatewayError("Media gateway not configured (missing secret or host)")

        path_str = str(local_path)
        if expires_at is None:
            expires_at = time.time() + (self._ttl_hours * 3600)

        payload = f"{path_str}:{int(expires_at)}"
        token = hmac.new(
            self._secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        encoded_path = urllib.parse.quote(path_str, safe="")
        return f"{self._host}/media?token={token}&expires={int(expires_at)}&path={encoded_path}"

    def validate_token(self, url: str) -> tuple[bool, str | None]:
        """Validate a signed URL's HMAC token.

        Returns:
            (is_valid, error_message_or_none)
        """
        if not self.enabled:
            return False, "Media gateway not configured"

        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        token = params.get("token", [None])[0]
        expires = params.get("expires", [None])[0]
        path_str = params.get("path", [None])[0]

        if not all([token, expires, path_str]):
            return False, "Missing required query parameters (token, expires, path)"

        try:
            expires_float = float(expires)
        except (ValueError, TypeError):
            return False, "Invalid expires parameter"

        if time.time() > expires_float:
            return False, "Token expired"

        decoded_path = urllib.parse.unquote(path_str)
        payload = f"{decoded_path}:{int(expires_float)}"
        expected_token = hmac.new(
            self._secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(token, expected_token):
            return False, "Invalid token"

        return True, None

    def get_local_path(self, url: str) -> Path | None:
        """Extract the local file path from a signed URL."""
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        path_str = params.get("path", [None])[0]
        if path_str:
            return Path(urllib.parse.unquote(path_str))
        return None
