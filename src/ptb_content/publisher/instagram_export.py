"""Instagram bundle exporter — generates publish-ready packages for manual scheduling."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from ..types import Brief, generate_hash, utcnow
from ..utils.helpers import ensure_dir, project_root
from . import ApprovalGate
from .errors import PublishError, ValidationError


class InstagramExporter:
    """Export a brief as a publish-ready Instagram bundle.

    Bundle contents:
        feed-1080x1350.png
        square-1080x1080.png
        story-1080x1920.png
        caption.txt
        hashtags.txt
        alt-text.txt
        publish-instructions.md
        manifest.json
        checksums.sha256
    """

    def __init__(self, outputs_dir: Path | None = None) -> None:
        self.outputs_dir = outputs_dir or project_root() / "outputs"
        self.bundles_dir = ensure_dir(project_root() / "outputs" / "bundles")

    def export(self, brief: Brief, approval_id: str = "", brief_path: Path | None = None) -> Path:
        """Export a brief as an Instagram bundle.

        Returns the bundle directory path.
        Validates that the brief has approval and checksums match.
        """
        gate = ApprovalGate()

        # Validate approval exists
        loaded = gate.load_approval(brief.brief_id)
        if loaded is None:
            raise ValidationError(f"No approval found for {brief.brief_id}. Cannot export.")
        approval, stored_checksum = loaded

        # Compute current checksum (prefer file-based to avoid reconstruction drift)
        if brief_path is not None and brief_path.exists():
            current_checksum = gate.compute_checksum_from_file(brief_path)
        else:
            current_checksum = gate.compute_brief_checksum(brief)
        if stored_checksum != current_checksum:
            raise ValidationError(
                f"Checksum mismatch for {brief.brief_id}. Brief changed after approval."
            )

        # Find rendered images
        brief_output_dir = self.outputs_dir / brief.brief_id
        images = self._find_images(brief_output_dir)

        # Build bundle
        bundle_dir = ensure_dir(self.bundles_dir / brief.brief_id)
        self._copy_images(images, bundle_dir)
        self._write_caption(brief, bundle_dir)
        self._write_hashtags(brief, bundle_dir)
        self._write_alt_text(brief, bundle_dir)
        self._write_instructions(brief, bundle_dir)
        self._write_manifest(brief, approval_id, current_checksum, bundle_dir)
        self._write_checksums(bundle_dir)

        return bundle_dir

    def _find_images(self, brief_dir: Path) -> dict[str, Path]:
        """Find the three required image sizes."""
        mapping = {
            "feed-1080x1350.png": "feed-1080x1350.png",
            "square-1080x1080.png": "feed-1080x1080.png",
            "story-1080x1920.png": "feed-1080x1920.png",
        }
        found: dict[str, Path] = {}
        for bundle_name, source_name in mapping.items():
            source = brief_dir / source_name
            if source.exists():
                found[bundle_name] = source
        if not found:
            raise PublishError(f"No rendered images found in {brief_dir}")
        return found

    def _copy_images(self, images: dict[str, Path], bundle_dir: Path) -> None:
        for bundle_name, source_path in images.items():
            shutil.copy2(source_path, bundle_dir / bundle_name)

    def _write_caption(self, brief: Brief, bundle_dir: Path) -> None:
        caption = brief.caption.primary or ""
        (bundle_dir / "caption.txt").write_text(caption, encoding="utf-8")

    def _write_hashtags(self, brief: Brief, bundle_dir: Path) -> None:
        caption = brief.caption.primary or ""
        hashtags = [word for word in caption.split() if word.startswith("#")]
        if not hashtags:
            category = brief.catalog_record.category.value
            defaults = {
                "tool-demo": [
                    "#ابزار_آفلاین",
                    "#جعبه_ابزار_فارسی",
                    "#ابزار_رایگان",
                    "#پرشین_تولباکس",
                ],
                "how-to": ["#آموزش", "#جعبه_ابزار_فارسی", "#پرشین_تولباکس"],
                "comparison": ["#مقایسه", "#جعبه_ابزار_فارسی", "#پرشین_تولباکس"],
                "announcement": ["#اخبار", "#جعبه_ابزار_فارسی", "#پرشین_تولباکس"],
            }
            hashtags = defaults.get(category, ["#جعبه_ابزار_فارسی", "#پرشین_تولباکس"])
        (bundle_dir / "hashtags.txt").write_text("\n".join(hashtags), encoding="utf-8")

    def _write_alt_text(self, brief: Brief, bundle_dir: Path) -> None:
        alt = brief.caption.alt_text or brief.catalog_record.title
        (bundle_dir / "alt-text.txt").write_text(alt, encoding="utf-8")

    def _write_instructions(self, brief: Brief, bundle_dir: Path) -> None:
        content = f"""# Instagram Publish Instructions

**Brief ID:** {brief.brief_id}
**Title:** {brief.catalog_record.title}
**Category:** {brief.catalog_record.category.value}
**Risk:** {brief.risk_level.value} / {brief.risk_decision.value}

## Steps

1. Open Instagram app
2. Create → Post
3. Select `feed-1080x1350.png` (or `square-1080x1080.png` for square)
4. Paste caption from `caption.txt`
5. Add hashtags from `hashtags.txt`
6. Set alt text from `alt-text.txt`
7. Schedule or publish immediately

## Notes

- Caption: {len(brief.caption.primary or "")} characters
- Hashtags: {len([w for w in (brief.caption.primary or "").split() if w.startswith("#")])} tags
- ZWNJ: Verify Persian text has proper half-spaces
- Generated: {utcnow()}
"""
        (bundle_dir / "publish-instructions.md").write_text(content, encoding="utf-8")

    def _write_manifest(
        self, brief: Brief, approval_id: str, image_checksum: str, bundle_dir: Path
    ) -> None:
        caption_text = brief.caption.primary or ""
        caption_checksum = generate_hash(caption_text)

        meta = brief.catalog_record.meta or {}
        manifest = {
            "brief_id": brief.brief_id,
            "approval_id": approval_id,
            "publication_risk_level": brief.risk_level.value,
            "publication_risk_decision": brief.risk_decision.value,
            "publication_risk_tags": meta.get("publication_risk_tags", []),
            "source_risk_level": meta.get("source_risk_level", "unknown"),
            "source_risk_decision": meta.get("source_risk_decision", "unknown"),
            "source_risk_tags": meta.get("source_risk_tags", [])
            or [t.value for t in brief.catalog_record.risk_tags],
            "scheduled_at": None,
            "image_checksum": image_checksum,
            "caption_checksum": caption_checksum,
            "generated_at": utcnow(),
            "publish_status": "READY_FOR_MANUAL_SCHEDULING",
            "api_status": "BLOCKED_BY_META_DEVELOPER_VERIFICATION",
            "caption_length": len(caption_text),
            "category": brief.catalog_record.category.value,
            "title": brief.catalog_record.title,
        }
        (bundle_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _write_checksums(self, bundle_dir: Path) -> None:
        lines = []
        for f in sorted(bundle_dir.iterdir()):
            if f.is_file() and f.name != "checksums.sha256":
                data = f.read_bytes()
                sha = hashlib.sha256(data).hexdigest()
                lines.append(f"{sha}  {f.name}")
        (bundle_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
