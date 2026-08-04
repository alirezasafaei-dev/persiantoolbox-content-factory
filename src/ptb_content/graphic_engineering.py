"""Production-grade copy and visual-quality primitives.

This module centralizes audience-visible labels, source-title cleanup, copy
construction, and deterministic visual metrics. It deliberately contains no
network or AI dependency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .types import Category
from .utils.persian import normalize_persian

_TITLE_SUFFIXES = (
    "جعبه ابزار فارسی",
    "جعبه‌ابزار فارسی",
    "پرشین تولباکس",
    "پرشین‌تولباکس",
    "PersianToolbox",
)

CATEGORY_LABELS: dict[Category, str] = {
    Category.TOOL_DEMO: "معرفی ابزار",
    Category.PDF_TUTORIAL: "راهنمای PDF",
    Category.PERSIAN_TEXT: "نگارش فارسی",
    Category.PROFESSIONAL: "ابزارهای حرفه‌ای",
    Category.PRIVACY: "راهنمای استفاده",
    Category.FINANCIAL: "ابزارهای مالی",
    Category.SEASONAL: "محتوای مناسبتی",
    Category.COMPARISON: "راهنمای انتخاب",
}


@dataclass(frozen=True)
class CopyDeck:
    """Audience-visible copy used by both renderer and caption generator."""

    short_title: str
    headline: str
    supporting_text: str
    cta: str
    alt_text: str
    category_label: str


@dataclass(frozen=True)
class VisualMetrics:
    """Deterministic metrics used by the visual QA gate."""

    width: int
    height: int
    file_size: int
    near_white_ratio: float
    foreground_bbox_ratio: float
    edge_density: float
    dominant_color_count: int


def _normalize_multiline(value: str) -> str:
    """Normalize Persian text without destroying intentional layout breaks."""
    return "\n".join(normalize_persian(line) for line in value.splitlines())


def clean_source_title(title: str) -> str:
    """Remove site-brand suffixes and normalize punctuation/spacing."""
    value = normalize_persian(title or "").strip()
    value = re.sub(r"\s*[|–—-]\s*[^|–—-]+$", lambda match: _strip_known_suffix(match.group(0)), value)
    for suffix in _TITLE_SUFFIXES:
        value = re.sub(
            rf"\s*[|–—-]?\s*{re.escape(suffix)}\s*$", "", value, flags=re.IGNORECASE
        )
    value = re.sub(r"\s+", " ", value).strip(" -|–—")
    return value or "ابزارهای پرشین‌تولباکس"


def _strip_known_suffix(fragment: str) -> str:
    candidate = fragment.strip(" -|–—").strip()
    if any(suffix.casefold() in candidate.casefold() for suffix in _TITLE_SUFFIXES):
        return ""
    return fragment


def build_copy_deck(title: str, category: Category) -> CopyDeck:
    """Build concise, natural Persian copy for one source page."""
    short = clean_source_title(title)
    label = CATEGORY_LABELS.get(category, "معرفی ابزار")

    if category == Category.PDF_TUTORIAL or "PDF" in short.upper():
        headline = "برای کارهای روزمره با PDF\nاز کجا شروع کنیم؟"
        supporting = "ابزار مناسبِ ادغام، تقسیم، تبدیل یا مرتب‌سازی فایل را انتخاب کنید."
        cta = "ابزارهای PDF را ببینید"
        alt = "طرح معرفی مجموعه ابزارهای PDF پرشین‌تولباکس با کارت‌های سند و مسیر انتخاب ابزار"
    elif category == Category.PERSIAN_TEXT:
        headline = "متن فارسی مرتب‌تر،\nبا ابزار مناسب"
        supporting = "برای پاک‌سازی، استانداردسازی و آماده‌سازی متن، ابزار مرتبط را پیدا کنید."
        cta = "ابزارهای نگارش را ببینید"
        alt = "طرح معرفی ابزارهای نگارش فارسی پرشین‌تولباکس با کارت‌های متن و ویرایش"
    else:
        headline = f"{short}\nبرای یک کار مشخص"
        supporting = "موضوع کارتان را مشخص کنید و ابزار مرتبط را در پرشین‌تولباکس ببینید."
        cta = "صفحه ابزار را ببینید"
        alt = f"طرح معرفی {short} در پرشین‌تولباکس"

    return CopyDeck(
        short_title=short,
        headline=_normalize_multiline(headline),
        supporting_text=normalize_persian(supporting),
        cta=normalize_persian(cta),
        alt_text=normalize_persian(alt),
        category_label=normalize_persian(label),
    )


def validate_copy_deck(deck: CopyDeck) -> list[str]:
    """Return fail-closed copy defects; empty list means valid."""
    defects: list[str] = []
    joined = " ".join(
        [deck.short_title, deck.headline, deck.supporting_text, deck.cta, deck.alt_text]
    )
    if any(token in joined for token in ("tool-demo", "pdf-tutorial", "privacy-trust")):
        defects.append("internal enum leaked into audience-visible copy")
    if any(suffix in joined for suffix in (" - جعبه ابزار فارسی", "- جعبه‌ابزار فارسی")):
        defects.append("raw site-title suffix leaked into copy")
    if len(deck.headline.replace("\n", " ").strip()) < 12:
        defects.append("headline is too short")
    if len(deck.headline.replace("\n", " ")) > 72:
        defects.append("headline is too long")
    if deck.short_title in deck.supporting_text and len(deck.short_title) > 18:
        defects.append("source title is redundantly repeated")
    if not deck.cta.endswith(("ببینید", "کنید", "شوید")):
        defects.append("CTA is not a complete Persian action phrase")
    return defects


def analyze_png(path: Path) -> VisualMetrics:
    """Compute production visual metrics using Pillow.

    The metric intentionally treats pixels with all channels >= 245 as
    near-white and quantifies content coverage, edges and color structure.
    """
    from PIL import Image, ImageFilter

    image = Image.open(path).convert("RGB")
    width, height = image.size
    pixels = list(image.getdata())
    total = max(1, len(pixels))
    near_white = sum(1 for red, green, blue in pixels if red >= 245 and green >= 245 and blue >= 245)

    background = Image.new("RGB", image.size, (255, 255, 255))
    difference = __import__("PIL.ImageChops", fromlist=["ImageChops"]).difference(image, background)
    bbox = difference.getbbox()
    if bbox:
        bbox_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
    else:
        bbox_area = 0

    edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_pixels = list(edges.getdata())
    edge_density = sum(1 for value in edge_pixels if value > 24) / total

    quantized = image.quantize(colors=12)
    palette_counts = quantized.getcolors(maxcolors=12) or []
    dominant_count = sum(1 for count, _ in palette_counts if count / total >= 0.02)

    return VisualMetrics(
        width=width,
        height=height,
        file_size=path.stat().st_size,
        near_white_ratio=near_white / total,
        foreground_bbox_ratio=bbox_area / (width * height),
        edge_density=edge_density,
        dominant_color_count=dominant_count,
    )


def validate_visual_metrics(metrics: VisualMetrics, expected: tuple[int, int]) -> list[str]:
    """Return visual defects for a rendered production PNG."""
    defects: list[str] = []
    if (metrics.width, metrics.height) != expected:
        defects.append(f"wrong dimensions: {metrics.width}x{metrics.height}")
    if metrics.near_white_ratio > 0.88:
        defects.append(f"near-white ratio too high: {metrics.near_white_ratio:.3f}")
    if metrics.foreground_bbox_ratio < 0.22:
        defects.append(f"foreground coverage too low: {metrics.foreground_bbox_ratio:.3f}")
    if metrics.file_size < 45_000:
        defects.append(f"PNG is suspiciously small: {metrics.file_size} bytes")
    if metrics.edge_density < 0.01:
        defects.append(f"edge density too low: {metrics.edge_density:.3f}")
    if metrics.dominant_color_count < 3:
        defects.append("insufficient visual material/color structure")
    return defects
