"""Regression coverage for production graphic engineering gates."""

from pathlib import Path

from PIL import Image, ImageDraw

from ptb_content.graphic_engineering import (
    analyze_png,
    build_copy_deck,
    clean_source_title,
    validate_copy_deck,
    validate_visual_metrics,
)
from ptb_content.types import Category


def test_clean_source_title_removes_brand_suffix() -> None:
    assert (
        clean_source_title("ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی")
        == "ابزارهای PDF اداری و استخدامی"
    )


def test_pdf_copy_is_natural_and_does_not_repeat_raw_title() -> None:
    deck = build_copy_deck(
        "ابزارهای PDF اداری و استخدامی - جعبه ابزار فارسی",
        Category.PDF_TUTORIAL,
    )
    assert deck.headline == "برای کارهای روزمره با PDF\nاز کجا شروع کنیم؟"
    assert "جعبه ابزار فارسی" not in deck.headline
    assert "tool-demo" not in " ".join(deck.__dict__.values())
    assert validate_copy_deck(deck) == []


def test_internal_enum_and_bad_suffix_fail_copy_gate() -> None:
    deck = build_copy_deck("tool-demo - جعبه ابزار فارسی", Category.TOOL_DEMO)
    defects = validate_copy_deck(deck)
    assert any("internal enum" in defect for defect in defects)


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
    draw.rounded_rectangle((650, 180, 940, 980), radius=30, fill="#FFFFFF", outline="#2563EB", width=12)
    draw.rectangle((150, 680, 580, 760), fill="#2563EB")
    draw.rectangle((150, 820, 500, 875), fill="#F59E0B")
    for y in range(250, 900, 90):
        draw.line((700, y, 900, y), fill="#334155", width=10)
    image.save(path, optimize=False)

    metrics = analyze_png(path)
    defects = validate_visual_metrics(metrics, (1080, 1350))
    assert not any("near-white ratio" in defect for defect in defects)
    assert not any("foreground coverage" in defect for defect in defects)
