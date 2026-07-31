"""Base publisher shared logic."""

from __future__ import annotations

import json
from pathlib import Path

from ..types import Brief, generate_hash
from ..utils.helpers import project_root
from .settings import MetaInstagramSettings


class BasePublisher:
    """Shared validation logic for all publishers."""

    def __init__(self, settings: MetaInstagramSettings | None = None) -> None:
        self.settings = settings or MetaInstagramSettings()

    def _compute_checksum(self, brief: Brief) -> str:
        payload = json.dumps(brief.to_dict(), sort_keys=True, ensure_ascii=False)
        return generate_hash(payload)

    def _get_image_path(self, brief: Brief) -> Path:
        """Find the rendered image for a brief."""
        image_dir = project_root() / "outputs" / brief.brief_id
        for size in ["feed-1080x1080.png", "feed-1080x1350.png", "feed-1080x1920.png"]:
            path = image_dir / size
            if path.exists():
                return path
        from .errors import PublishError

        raise PublishError(f"No rendered image found for {brief.brief_id}")
