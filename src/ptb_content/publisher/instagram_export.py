"""Instagram bundle exporter — fail-closed production packages for manual scheduling."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from ..content_shaping import build_visual_copy, clean_display_title, publication_text
from ..qa import QAEngine
from ..risk import RiskEngine
from ..types import Brief, QADecision, generate_hash, utcnow
from ..utils.helpers import ensure_dir, project_root
from ..visual_qa import VisualAudit, audit_render_set
from . import ApprovalGate
from .errors import PublishError, ValidationError

_DEFAULT_HASHTAGS: dict[str, tuple[str, ...]] = {
    "tool-demo": (
        "#پرشین_تولباکس",
        "#معرفی_ابزار",
        "#ابزار_فارسی",
        "#جعبه_ابزار_فارسی",
    ),
    "pdf-tutorial": (
        "#پرشین_تولباکس",
        "#PDF",
        "#راهنمای_PDF",
        "#ابزار_فارسی",
    ),
    "persian-text": (
        "#پرشین_تولباکس",
        "#متن_فارسی",
        "#نگارش_فارسی",
        "#ابزار_فارسی",
    ),
    "professional": (
        "#پرشین_تولباکس",
        "#معرفی_ابزار",
        "#ابزار_حرفه‌ای",
        "#ابزار_فارسی",
    ),
    "seasonal": (
        "#پرشین_تولباکس",
        "#محتوای_فصلی",
        "#معرفی_ابزار",
        "#ابزار_فارسی",
    ),
}
_GENERIC_HASHTAGS = (
    "#پرشین_تولباکس",
    "#معرفی_ابزار",
    "#ابزار_فارسی",
)


class InstagramExporter:
    """Export one approved, QA-passed brief as a complete Instagram bundle."""

    def __init__(self, outputs_dir: Path | None = None) -> None:
        self.outputs_dir = outputs_dir or project_root() / "outputs"
        self.bundles_dir = ensure_dir(self.outputs_dir / "bundles")

    def export(self, brief: Brief, approval_id: str = "", brief_path: Path | None = None) -> Path:
        gate = ApprovalGate()
        loaded = gate.load_approval(brief.brief_id)
        if loaded is None:
            raise ValidationError(f"No approval found for {brief.brief_id}. Cannot export.")
        approval, stored_checksum = loaded
        if not approval.approved:
            raise ValidationError(f"Approval for {brief.brief_id} is not approved.")

        if brief_path is not None and brief_path.exists():
            current_checksum = gate.compute_checksum_from_file(brief_path)
        else:
            current_checksum = gate.compute_brief_checksum(brief)
        if stored_checksum != current_checksum:
            raise ValidationError(
                f"Checksum mismatch for {brief.brief_id}. Brief changed after approval."
            )

        qa_result = QAEngine(
            outputs_dir=self.outputs_dir,
            require_rendered_assets=True,
        ).run_all(brief)
        if qa_result.decision != QADecision.PASS:
            raise ValidationError(
                f"QA decision is {qa_result.decision.value} for {brief.brief_id}: "
                + "; ".join(qa_result.failure_reasons)
            )

        visual_audits = audit_render_set(brief.brief_id, self.outputs_dir)
        failed_visuals = {
            size: list(audit.issues) for size, audit in visual_audits.items() if not audit.passed
        }
        if failed_visuals:
            raise ValidationError(
                "Visual QA failed before export: " + json.dumps(failed_visuals, ensure_ascii=False)
            )

        hashtags = self._select_hashtags(brief)
        all_publication_text = f"{publication_text(brief)}\n{' '.join(hashtags)}"
        detected_tags = RiskEngine().detect_publishable_tags(all_publication_text)
        if detected_tags:
            names = ", ".join(sorted(tag.value for tag in detected_tags))
            raise ValidationError(
                f"Audience-visible bundle text introduces publication risk ({names})."
            )

        images = self._find_images(self.outputs_dir / brief.brief_id)
        bundle_dir = self.bundles_dir / brief.brief_id
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        ensure_dir(bundle_dir)

        self._copy_images(images, bundle_dir)
        self._write_caption(brief, bundle_dir)
        self._write_hashtags(hashtags, bundle_dir)
        self._write_alt_text(brief, bundle_dir)
        self._write_instructions(brief, len(hashtags), bundle_dir)

        approval_ref = approval_id.strip() or f"approval-{brief.brief_id}-{stored_checksum[:12]}"
        image_checksum = self._combined_image_checksum(bundle_dir)
        self._write_manifest(
            brief=brief,
            approval_id=approval_ref,
            brief_checksum=current_checksum,
            image_checksum=image_checksum,
            visual_audits=visual_audits,
            bundle_dir=bundle_dir,
        )
        self._write_checksums(bundle_dir)
        return bundle_dir

    def _find_images(self, brief_dir: Path) -> dict[str, Path]:
        mapping = {
            "feed-1080x1350.png": "feed-1080x1350.png",
            "square-1080x1080.png": "feed-1080x1080.png",
            "story-1080x1920.png": "feed-1080x1920.png",
        }
        found: dict[str, Path] = {}
        missing: list[str] = []
        for bundle_name, source_name in mapping.items():
            source = brief_dir / source_name
            if source.exists():
                found[bundle_name] = source
            else:
                missing.append(source_name)
        if missing:
            raise PublishError(
                f"Required rendered images missing in {brief_dir}: {', '.join(missing)}"
            )
        return found

    def _copy_images(self, images: dict[str, Path], bundle_dir: Path) -> None:
        for bundle_name, source_path in images.items():
            shutil.copy2(source_path, bundle_dir / bundle_name)

    def _write_caption(self, brief: Brief, bundle_dir: Path) -> None:
        (bundle_dir / "caption.txt").write_text(
            brief.caption.primary.strip() + "\n", encoding="utf-8"
        )

    def _select_hashtags(self, brief: Brief) -> list[str]:
        hashtags = [
            word.strip("،,.؛;!")
            for word in (brief.caption.primary or "").split()
            if word.startswith("#")
        ]
        if not hashtags:
            category = brief.catalog_record.category.value
            hashtags = list(_DEFAULT_HASHTAGS.get(category, _GENERIC_HASHTAGS))

        detected_tags = RiskEngine().detect_publishable_tags(" ".join(hashtags))
        if detected_tags:
            tag_names = ", ".join(sorted(tag.value for tag in detected_tags))
            raise ValidationError(
                "Hashtags introduce publication risk "
                f"({tag_names}) for {brief.brief_id}. Export blocked."
            )
        return hashtags

    def _write_hashtags(self, hashtags: list[str], bundle_dir: Path) -> None:
        (bundle_dir / "hashtags.txt").write_text("\n".join(hashtags) + "\n", encoding="utf-8")

    def _write_alt_text(self, brief: Brief, bundle_dir: Path) -> None:
        alt = brief.caption.alt_text.strip() or clean_display_title(brief.catalog_record.title)
        (bundle_dir / "alt-text.txt").write_text(alt + "\n", encoding="utf-8")

    def _write_instructions(self, brief: Brief, hashtag_count: int, bundle_dir: Path) -> None:
        visual = build_visual_copy(brief.catalog_record)
        content = f"""# راهنمای انتشار در Instagram

**Brief ID:** {brief.brief_id}
**عنوان:** {clean_display_title(brief.catalog_record.title)}
**موضوع طراحی:** {visual.eyebrow}
**ریسک انتشار:** {brief.risk_level.value} / {brief.risk_decision.value}

## مراحل

1. در Instagram یک Post جدید بسازید.
2. فایل `feed-1080x1350.png` را انتخاب کنید.
3. متن `caption.txt` را وارد کنید.
4. هشتگ‌های `hashtags.txt` را اضافه کنید.
5. متن جایگزین `alt-text.txt` را ثبت کنید.
6. پیش‌نمایش نهایی را بررسی و سپس زمان‌بندی کنید.

## کنترل نهایی

- Caption: {len(brief.caption.primary or "")} کاراکتر
- Hashtags: {hashtag_count}
- Graphics Engine: v2
- Visual QA: PASS برای هر سه اندازه
- Generated: {utcnow()}
"""
        (bundle_dir / "publish-instructions.md").write_text(content, encoding="utf-8")

    def _combined_image_checksum(self, bundle_dir: Path) -> str:
        digest = hashlib.sha256()
        for name in ("feed-1080x1350.png", "square-1080x1080.png", "story-1080x1920.png"):
            digest.update((bundle_dir / name).read_bytes())
        return digest.hexdigest()

    def _write_manifest(
        self,
        brief: Brief,
        approval_id: str,
        brief_checksum: str,
        image_checksum: str,
        visual_audits: dict[str, VisualAudit],
        bundle_dir: Path,
    ) -> None:
        caption_text = brief.caption.primary or ""
        meta = brief.catalog_record.meta or {}
        visual = build_visual_copy(brief.catalog_record)
        manifest = {
            "brief_id": brief.brief_id,
            "approval_id": approval_id,
            "brief_checksum": brief_checksum,
            "publication_risk_level": brief.risk_level.value,
            "publication_risk_decision": brief.risk_decision.value,
            "publication_risk_tags": meta.get("publication_risk_tags", []),
            "source_risk_level": meta.get("source_risk_level", "unknown"),
            "source_risk_decision": meta.get("source_risk_decision", "unknown"),
            "source_risk_tags": meta.get("source_risk_tags", [])
            or [tag.value for tag in brief.catalog_record.risk_tags],
            "graphics_engine_version": 2,
            "visual_motif": visual.motif,
            "visual_qa": {size: audit.to_dict() for size, audit in visual_audits.items()},
            "scheduled_at": None,
            "image_checksum": image_checksum,
            "caption_checksum": generate_hash(caption_text),
            "generated_at": utcnow(),
            "publish_status": "READY_FOR_MANUAL_SCHEDULING",
            "api_status": "BLOCKED_BY_META_DEVELOPER_VERIFICATION",
            "caption_length": len(caption_text),
            "category": brief.catalog_record.category.value,
            "title": clean_display_title(brief.catalog_record.title),
        }
        (bundle_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _write_checksums(self, bundle_dir: Path) -> None:
        lines: list[str] = []
        for file_path in sorted(bundle_dir.iterdir()):
            if file_path.is_file() and file_path.name != "checksums.sha256":
                sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
                lines.append(f"{sha}  {file_path.name}")
        (bundle_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
