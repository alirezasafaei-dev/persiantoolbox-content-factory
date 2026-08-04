"""Regression coverage for production graphic engineering gates."""

from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageDraw

from ptb_content.generator import DeterministicGenerator
from ptb_content.graphic_engineering import (
    analyze_png,
    build_copy_deck,
    clean_source_title,
    validate_copy_deck,
    validate_visual_metrics,
)
from ptb_content.types import CatalogRecord, Category, HookType, utcnow


def test_clean_source_title_removes_brand_suffix() -> None:
    assert (
        clean_source_title("ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی")
        == "ابزارهای PDF اداری و استخدامی"
    )


def test_pdf_copy_is_concrete_source_grounded_and_actionable() -> None:
    deck = build_copy_deck(
        "ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی",
        Category.PDF_TUTORIAL,
        "مجموعه ابزارهای مرتبط با مدیریت فایل‌های PDF.",
    )
    assert deck.headline == "فایل PDF دارید؟\nابزار مربوط به کارتان را پیدا کنید"
    assert deck.category_label == "ابزارهای PDF"
    assert "ابزارهای اداری و استخدامی مرتبط با PDF" in deck.supporting_text
    assert deck.cta == "ابزارهای PDF را ببینید"
    assert "جعبه ابزار فارسی" not in deck.headline
    assert deck.short_title not in deck.supporting_text
    assert "tool-demo" not in " ".join(deck.__dict__.values())
    assert "مجموعه ابزارهای مرتبط با مدیریت فایل‌های PDF" in deck.reason_to_believe
    assert "نیاز شخصی" in deck.psychology_principle
    assert deck.value_proposition.startswith("در صفحه ابزارهای PDF")
    assert validate_copy_deck(deck) == []


def test_vague_placeholder_headline_fails_semantic_gate() -> None:
    deck = build_copy_deck("ابزارهای PDF", Category.PDF_TUTORIAL)
    vague = replace(deck, headline="کار با PDF\nاز کجا شروع کنیم؟")
    defects = validate_copy_deck(vague)
    assert any("vague" in defect for defect in defects)


def test_generic_option_language_fails_semantic_gate() -> None:
    deck = build_copy_deck("ابزارهای PDF", Category.PDF_TUTORIAL)
    vague = replace(deck, supporting_text="گزینه مرتبط را برای نیاز خود بررسی کنید.")
    defects = validate_copy_deck(vague)
    assert any("vague" in defect for defect in defects)


def test_unsupported_superlative_fails_copy_gate() -> None:
    deck = build_copy_deck("ابزارهای PDF", Category.PDF_TUTORIAL)
    exaggerated = replace(deck, supporting_text="بهترین و سریع‌ترین ابزار PDF را پیدا کنید.")
    defects = validate_copy_deck(exaggerated)
    assert any("unsupported" in defect for defect in defects)


def test_internal_enum_and_bad_suffix_fail_copy_gate() -> None:
    deck = build_copy_deck("tool-demo - جعبه ابزار فارسی", Category.TOOL_DEMO)
    defects = validate_copy_deck(deck)
    assert any("internal enum" in defect for defect in defects)


def test_generator_uses_problem_solution_and_non_random_psychology() -> None:
    record = CatalogRecord(
        canonical_url="https://persiantoolbox.ir/topics/pdf-tools",
        title="ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی",
        summary="مجموعه ابزارهای مرتبط با مدیریت فایل‌های PDF.",
        category=Category.PDF_TUTORIAL,
        source_id="semantic-pdf-test",
        source_hash="semantic-source-hash",
        content_hash="semantic-content-hash",
        crawled_at=utcnow(),
    )
    brief = DeterministicGenerator().generate_brief(record)

    assert brief.content_strategy.hook_type == HookType.PROBLEM_SOLUTION
    assert "کاربران اداری" in brief.audience.segment
    assert "کدام ابزار" in brief.audience.pain_point
    assert brief.psychology_hypothesis.principle == "فعال‌سازی نیاز شخصی و کاهش اضافه‌بار انتخاب"
    assert "فایل PDF دارید و نمی‌دانید" in brief.caption.primary
    assert "مسیله" not in brief.content_strategy.angle
    assert brief.catalog_record.meta["semantic_messaging_version"] == 1


def test_blank_white_render_fails_visual_gate(tmp_path: Path) -> None:
    path = tmp_path / "blank.png"
    Image.new("RGB", (1080, 1350), "white").save(path)
    defects = validate_visual_metrics(analyze_png(path), (1080, 1350))
    assert any("near-white ratio" in defect for defect in defects)
    assert any("foreground coverage" in defect for defect in defects)


def test_structured_render_passes_density_thresholds(tmp_path: Path) -> None:
    path = tmp_path / "structured.png"
    image = Image.new("RGB", (1080, 1350), "#F3F4F6")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 1000, 1270), fill="#E0E7FF")
    draw.rounded_rectangle((110, 130, 620, 540), radius=36, fill="#172554")
    draw.rounded_rectangle(
        (650, 180, 940, 980), radius=30, fill="#FFFFFF", outline="#2563EB", width=12
    )
    draw.rectangle((150, 680, 580, 760), fill="#2563EB")
    draw.rectangle((150, 820, 500, 875), fill="#F59E0B")
    for y in range(250, 900, 90):
        draw.line((700, y, 900, y), fill="#334155", width=10)
    image.save(path, optimize=False)

    metrics = analyze_png(path)
    defects = validate_visual_metrics(metrics, (1080, 1350))
    assert not any("near-white ratio" in defect for defect in defects)
    assert not any("foreground coverage" in defect for defect in defects)
