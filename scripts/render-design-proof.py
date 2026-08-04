#!/usr/bin/env python3
"""Render and audit a canonical PDF social-design proof for CI artifacts."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from ptb_content.generator import DeterministicGenerator
from ptb_content.renderer import Renderer
from ptb_content.types import CatalogRecord, Category, HTTPMetadata
from ptb_content.visual_qa import audit_render_set


async def main() -> None:
    root = Path("artifacts/design-proof")
    root.mkdir(parents=True, exist_ok=True)
    record = CatalogRecord(
        canonical_url="https://persiantoolbox.ir/topics/pdf-tools",
        title="ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی",
        summary="ابزارهای مرتبط با مدیریت فایل‌های PDF و اسناد اداری.",
        category=Category.TOOL_DEMO,
        source_id="design-proof-pdf",
        source_hash="a" * 64,
        content_hash="b" * 64,
        crawled_at="2026-08-04T00:00:00+00:00",
        visible_text_length=320,
        http_metadata=HTTPMetadata(status_code=200, content_type="text/html"),
    )
    brief = DeterministicGenerator().generate_brief(record)
    renderer = Renderer(output_dir=root)
    await renderer.render_all_sizes(brief)

    audits = audit_render_set(brief.brief_id, root)
    report = {
        "brief": brief.to_dict(),
        "audits": {size: audit.to_dict() for size, audit in audits.items()},
    }
    (root / "design-proof-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if not all(audit.passed for audit in audits.values()):
        raise SystemExit("Design proof failed visual QA")


if __name__ == "__main__":
    asyncio.run(main())
