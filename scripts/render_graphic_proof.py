"""Render a production graphic proof for CI artifact review."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ptb_content.generator import DeterministicGenerator
from ptb_content.renderer import Renderer
from ptb_content.types import CatalogRecord, Category, utcnow


def build_record() -> CatalogRecord:
    return CatalogRecord(
        canonical_url="https://persiantoolbox.ir/topics/pdf-tools",
        title="ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی",
        summary="مجموعه ابزارهای مرتبط با مدیریت فایل‌های PDF.",
        category=Category.PDF_TUTORIAL,
        source_id="ci-graphic-proof-pdf",
        source_hash="ci-source-hash",
        content_hash="ci-content-hash",
        crawled_at=utcnow(),
        visible_text_length=256,
    )


async def main() -> None:
    artifact_root = Path("artifacts/graphic-proof")
    artifact_root.mkdir(parents=True, exist_ok=True)
    brief = DeterministicGenerator().generate_brief(build_record())
    renderer = Renderer(output_dir=artifact_root)
    paths = await renderer.render_all_sizes(brief)

    (artifact_root / "brief.json").write_text(
        json.dumps(brief.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (artifact_root / "caption.txt").write_text(brief.caption.primary, encoding="utf-8")
    proof = artifact_root / "review" / f"{brief.brief_id}-contact-sheet.png"
    summary = {
        "brief_id": brief.brief_id,
        "contact_sheet": str(proof),
        "assets": {key: str(path) for key, path in paths.items()},
    }
    (artifact_root / "proof-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
