"""Instagram bundle exporter with fail-closed copy, visual and approval gates."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict
from pathlib import Path

from ..graphic_engineering import analyze_png, validate_visual_metrics
from ..qa import QAEngine
from ..risk import RiskEngine
from ..types import Brief, QADecision, generate_hash, utcnow
from ..utils.helpers import ensure_dir, project_root
from . import ApprovalGate
from .errors import PublishError, ValidationError

_DEFAULT_HASHTAGS: dict[str, tuple[str, ...]] = {
    "tool-demo": ("#پرشین_تولباکس", "#معرفی_ابزار", "#ابزار_فارسی"),
    "pdf-tutorial": ("#پرشین_تولباکس", "#PDF", "#راهنمای_PDF", "#ابزار_فارسی"),
    "persian-text": ("#پرشین_تولباکس", "#متن_فارسی", "#نگارش_فارسی"),
    "professional": ("#پرشین_تولباکس", "#معرفی_ابزار", "#ابزار_حرفه‌ای"),
    "seasonal": ("#پرشین_تولباکس", "#محتوای_فصلی", "#معرفی_ابزار"),
}
_GENERIC_HASHTAGS = ("#پرشین_تولباکس", "#معرفی_ابزار", "#ابزار_فارسی")
_EXPECTED_IMAGES = {
    "feed-1080x1350.png": (1080, 1350),
    "square-1080x1080.png": (1080, 1080),
    "story-1080x1920.png": (1080, 1920),
}
_SOURCE_NAMES = {
    "feed-1080x1350.png": "feed-1080x1350.png",
    "square-1080x1080.png": "feed-1080x1080.png",
    "story-1080x1920.png": "feed-1080x1920.png",
}


class InstagramExporter:
    """Export only fully reviewed, pixel-validated briefs."""

    def __init__(self, outputs_dir: Path | None = None) -> None:
        self.outputs_dir = outputs_dir or project_root() / "outputs"
        self.bundles_dir = ensure_dir(self.outputs_dir / "bundles")
        self.gate = ApprovalGate()

    @staticmethod
    def _proof_condition(conditions: list[str]) -> str:
        return next((value for value in conditions if value.startswith("visual-proof-sha256:")), "")

    @staticmethod
    def _approval_reference(
        brief_id: str, reviewer: str | None, created_at: str, checksum: str
    ) -> str:
        payload = f"{brief_id}|{reviewer or 'unknown'}|{created_at}|{checksum}"
        return f"approval-{generate_hash(payload)[:20]}"

    def export(self, brief: Brief, approval_id: str = "", brief_path: Path | None = None) -> Path:
        if brief_path is None or not brief_path.exists():
            raise ValidationError("A persisted brief JSON path is required for production export")

        loaded = self.gate.load_approval(brief.brief_id)
        if loaded is None:
            raise ValidationError(f"No approval found for {brief.brief_id}. Cannot export.")
        approval, stored_checksum = loaded
        if not approval.approved:
            raise ValidationError(f"Approval for {brief.brief_id} is not approved")
        if approval.version != brief.version:
            raise ValidationError(
                f"Approval version {approval.version} does not match brief version {brief.version}"
            )

        current_checksum = self.gate.compute_checksum_from_file(brief_path)
        if stored_checksum != current_checksum:
            raise ValidationError(
                f"Checksum mismatch for {brief.brief_id}. Brief changed after approval."
            )

        proof_condition = self._proof_condition(approval.conditions)
        if not proof_condition:
            raise ValidationError(
                f"Approval for {brief.brief_id} has no visual proof checksum; re-review required"
            )
        proof_checksum = proof_condition.split(":", 1)[1]
        contact_sheet = self.outputs_dir / "review" / f"{brief.brief_id}-contact-sheet.png"
        if not contact_sheet.exists():
            raise ValidationError(f"Missing contact sheet for {brief.brief_id}")
        actual_proof_checksum = hashlib.sha256(contact_sheet.read_bytes()).hexdigest()
        if proof_checksum != actual_proof_checksum:
            raise ValidationError("Contact sheet changed after approval; re-approval required")

        qa_result = QAEngine(outputs_dir=self.outputs_dir).run_all(brief)
        if qa_result.decision != QADecision.PASS:
            raise ValidationError(
                f"QA decision must be PASS before export; got {qa_result.decision.value}"
            )

        derived_approval_id = self._approval_reference(
            brief.brief_id, approval.reviewer, approval.created_at, stored_checksum
        )
        if approval_id and approval_id != derived_approval_id:
            raise ValidationError("Supplied approval reference does not match persisted approval")

        images = self._find_and_validate_images(self.outputs_dir / brief.brief_id)
        hashtags = self._select_hashtags(brief)
        self._validate_all_audience_text(brief, hashtags)

        bundle_dir = self.bundles_dir / brief.brief_id
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        ensure_dir(bundle_dir)
        self._copy_images(images, bundle_dir)
        shutil.copy2(contact_sheet, bundle_dir / "review-contact-sheet.png")
        self._write_caption(brief, bundle_dir)
        self._write_hashtags(hashtags, bundle_dir)
        self._write_alt_text(brief, bundle_dir)
        self._write_instructions(brief, hashtags, bundle_dir)
        self._write_manifest(
            brief=brief,
            approval_id=derived_approval_id,
            brief_checksum=current_checksum,
            visual_proof_checksum=actual_proof_checksum,
            images=images,
            bundle_dir=bundle_dir,
        )
        self._write_checksums(bundle_dir)
        return bundle_dir

    def approval_reference_for(self, brief: Brief, brief_path: Path) -> str:
        loaded = self.gate.load_approval(brief.brief_id)
        if loaded is None:
            raise ValidationError(f"No approval found for {brief.brief_id}")
        approval, stored_checksum = loaded
        current_checksum = self.gate.compute_checksum_from_file(brief_path)
        if stored_checksum != current_checksum:
            raise ValidationError("Approval checksum mismatch")
        return self._approval_reference(
            brief.brief_id, approval.reviewer, approval.created_at, stored_checksum
        )

    def _find_and_validate_images(self, brief_dir: Path) -> dict[str, Path]:
        found: dict[str, Path] = {}
        defects: list[str] = []
        for bundle_name, source_name in _SOURCE_NAMES.items():
            source = brief_dir / source_name
            if not source.exists():
                defects.append(f"missing {source_name}")
                continue
            metrics = analyze_png(source)
            image_defects = validate_visual_metrics(metrics, _EXPECTED_IMAGES[bundle_name])
            defects.extend(f"{source_name}: {defect}" for defect in image_defects)
            found[bundle_name] = source
        if defects:
            raise PublishError("Visual assets rejected: " + "; ".join(defects))
        if set(found) != set(_EXPECTED_IMAGES):
            raise PublishError("All three platform PNGs are required")
        return found

    def _copy_images(self, images: dict[str, Path], bundle_dir: Path) -> None:
        for bundle_name, source_path in images.items():
            shutil.copy2(source_path, bundle_dir / bundle_name)

    def _write_caption(self, brief: Brief, bundle_dir: Path) -> None:
        (bundle_dir / "caption.txt").write_text(brief.caption.primary, encoding="utf-8")

    def _select_hashtags(self, brief: Brief) -> list[str]:
        caption_hashtags = [word for word in brief.caption.primary.split() if word.startswith("#")]
        hashtags = caption_hashtags or list(
            _DEFAULT_HASHTAGS.get(brief.catalog_record.category.value, _GENERIC_HASHTAGS)
        )
        detected = RiskEngine().detect_publishable_tags(" ".join(hashtags))
        if detected:
            names = ", ".join(sorted(tag.value for tag in detected))
            raise ValidationError(f"Hashtags introduce publication risk ({names})")
        return hashtags

    def _validate_all_audience_text(self, brief: Brief, hashtags: list[str]) -> None:
        combined = "\n".join(
            [brief.caption.primary, brief.caption.cta, brief.caption.alt_text, " ".join(hashtags)]
        )
        detected = RiskEngine().detect_publishable_tags(combined)
        if detected:
            names = ", ".join(sorted(tag.value for tag in detected))
            raise ValidationError(f"Audience-visible bundle text introduces risk ({names})")

    def _write_hashtags(self, hashtags: list[str], bundle_dir: Path) -> None:
        (bundle_dir / "hashtags.txt").write_text("\n".join(hashtags), encoding="utf-8")

    def _write_alt_text(self, brief: Brief, bundle_dir: Path) -> None:
        (bundle_dir / "alt-text.txt").write_text(brief.caption.alt_text, encoding="utf-8")

    def _write_instructions(self, brief: Brief, hashtags: list[str], bundle_dir: Path) -> None:
        content = f"""# Instagram Publish Instructions

**Brief ID:** {brief.brief_id}
**Title:** {brief.catalog_record.title}
**Publication risk:** {brief.risk_level.value} / {brief.risk_decision.value}

## Human steps

1. Open `review-contact-sheet.png` and compare all three layouts.
2. Select `feed-1080x1350.png` for the Instagram feed.
3. Paste `caption.txt` and `hashtags.txt`.
4. Set accessibility text from `alt-text.txt`.
5. Schedule in the Instagram application.

## Integrity

- Visual proof is mandatory and checksum-bound to approval.
- Caption length: {len(brief.caption.primary)} characters
- Hashtags: {len(hashtags)}
- Generated: {utcnow()}
"""
        (bundle_dir / "publish-instructions.md").write_text(content, encoding="utf-8")

    def _write_manifest(
        self,
        brief: Brief,
        approval_id: str,
        brief_checksum: str,
        visual_proof_checksum: str,
        images: dict[str, Path],
        bundle_dir: Path,
    ) -> None:
        if not approval_id:
            raise ValidationError("Empty approval_id is never publishable")
        meta = brief.catalog_record.meta or {}
        image_metrics = {
            bundle_name: asdict(analyze_png(source_path))
            for bundle_name, source_path in images.items()
        }
        manifest = {
            "brief_id": brief.brief_id,
            "approval_id": approval_id,
            "brief_checksum": brief_checksum,
            "visual_proof_checksum": visual_proof_checksum,
            "graphic_engineering_version": meta.get("graphic_engineering_version", 0),
            "publication_risk_level": brief.risk_level.value,
            "publication_risk_decision": brief.risk_decision.value,
            "publication_risk_tags": meta.get("publication_risk_tags", []),
            "source_risk_level": meta.get("source_risk_level", "unknown"),
            "source_risk_decision": meta.get("source_risk_decision", "unknown"),
            "source_risk_tags": meta.get("source_risk_tags", []),
            "image_metrics": image_metrics,
            "caption_checksum": generate_hash(brief.caption.primary),
            "generated_at": utcnow(),
            "scheduled_at": None,
            "publish_status": "READY_FOR_MANUAL_SCHEDULING",
            "api_status": "BLOCKED_BY_META_DEVELOPER_VERIFICATION",
            "category": brief.catalog_record.category.value,
            "title": brief.catalog_record.title,
        }
        (bundle_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _write_checksums(self, bundle_dir: Path) -> None:
        lines = []
        for path in sorted(bundle_dir.iterdir()):
            if path.is_file() and path.name != "checksums.sha256":
                lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
        (bundle_dir / "checksums.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
