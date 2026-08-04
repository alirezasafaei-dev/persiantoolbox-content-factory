"""Regression tests for editorial shaping and Graphics Engine v2."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from ptb_content.content_shaping import (
    build_caption,
    build_visual_copy,
    clean_display_title,
    editorial_issues,
)
from ptb_content.generator import DeterministicGenerator
from ptb_content.qa import QAEngine
from ptb_content.renderer import Renderer
from ptb_content.types import CatalogRecord, Category, HTTPMetadata
from ptb_content.visual_qa import analyze_png


def _record(title: str = "ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی") -> CatalogRecord:
    return CatalogRecord(
        canonical_url="https://persiantoolbox.ir/topics/pdf-tools",
        title=title,
        summary="ابزارهای مرتبط با مدیریت فایل‌های PDF و اسناد اداری.",
        category=Category.TOOL_DEMO,
        source_id="source-pdf-tools",
        source_hash="a" * 64,
        content_hash="b" * 64,
        crawled_at="2026-08-04T00:00:00+00:00",
        visible_text_length=320,
        http_metadata=HTTPMetadata(status_code=200, content_type="text/html"),
    )


def test_source_brand_suffix_is_removed() -> None:
    assert clean_display_title(_record().title) == "ابزارهای PDF اداری و استخدامی"
    assert clean_display_title("ویرایشگر فارسی | پرشین‌تولباکس") == "ویرایشگر فارسی"


def test_pdf_caption_is_meaningful_and_does_not_repeat_raw_title() -> None:
    record = _record()
    caption = build_caption(record)

    assert "جعبه ابزار فارسی" not in caption.primary
    assert " - " not in caption.primary
    assert caption.primary.count("ابزارهای PDF اداری و استخدامی") == 0
    assert "ادغام" in caption.primary
    assert "تقسیم" in caption.primary
    assert "لینک در بیو" in caption.primary


def test_visual_copy_is_semantic_and_persian() -> None:
    copy = build_visual_copy(_record())

    assert copy.eyebrow == "مجموعه ابزارهای PDF"
    assert "از کجا شروع کنیم؟" in copy.headline
    assert copy.motif == "pdf"
    assert "ادغام فایل‌ها" in copy.feature_labels
    assert "tool-demo" not in copy.audience_text()


def test_renderer_html_contains_real_visual_material_not_sparse_text() -> None:
    brief = DeterministicGenerator().generate_brief(_record())
    rendered = Renderer().render_html(brief, 1080, 1350)

    assert "document-front" in rendered
    assert "floating-badge" in rendered
    assert "radial-gradient" in rendered
    assert "<svg" in rendered
    assert "پرشین‌تولباکس" in rendered
    assert "tool-demo" not in rendered
    assert "جعبه ابزار فارسی آشنا شوید" not in rendered
    assert "cdn.jsdelivr.net" not in rendered
    assert "window.__PTB_RENDER_READY__" in rendered
    assert "document.fonts.ready" in rendered


def test_generator_records_graphics_and_risk_scope_versions() -> None:
    brief = DeterministicGenerator().generate_brief(_record())

    assert brief.catalog_record.meta["graphics_engine_version"] == 2
    assert brief.catalog_record.meta["risk_scope_version"] == 3
    assert brief.catalog_record.meta["display_title"] == "ابزارهای PDF اداری و استخدامی"
    assert brief.catalog_record.meta["visual_copy"]["motif"] == "pdf"
    assert editorial_issues(brief) == []


def test_editorial_qa_blocks_the_rejected_canary_sentence() -> None:
    brief = DeterministicGenerator().generate_brief(_record())
    brief.caption.primary = (
        "با ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی آشنا شوید\n\n"
        "برای آشنایی با ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی، صفحه را ببینید."
    )

    result = QAEngine().check_editorial_quality(brief)
    assert result.status.value == "FAIL"
    assert "malformed source title" in result.details


def test_visual_qa_rejects_mostly_white_sparse_canary(tmp_path: Path) -> None:
    path = tmp_path / "sparse.png"
    image = Image.new("RGB", (1080, 1350), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((420, 570, 660, 650), fill="#2563EB")
    image.save(path)

    audit = analyze_png(path, (1080, 1350))
    assert audit.passed is False
    assert audit.metrics.near_white_ratio > 0.92
    assert any("blank/white" in issue for issue in audit.issues)


def test_visual_qa_accepts_dense_high_contrast_design(tmp_path: Path) -> None:
    path = tmp_path / "designed.png"
    width, height = 1080, 1350
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for y in range(height):
        for x in range(width):
            pixels[x, y] = (
                7 + int(25 * x / width),
                17 + int(35 * y / height),
                31 + int(70 * (x + y) / (width + height)),
            )
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((70, 150, 650, 1150), radius=48, fill="#17386B", outline="#60A5FA", width=8)
    draw.rounded_rectangle((700, 230, 1010, 980), radius=42, fill="#F8FAFC", outline="#F59E0B", width=9)
    for index in range(8):
        top = 310 + index * 74
        draw.rounded_rectangle((745, top, 960 - index * 10, top + 28), radius=14, fill="#94A3B8")
    for index in range(5):
        draw.ellipse((110 + index * 105, 870, 180 + index * 105, 940), fill="#F59E0B")
    image.save(path)

    audit = analyze_png(path, (1080, 1350))
    assert audit.passed is True, audit.issues
