"""Production-grade copy, messaging and visual-quality primitives.

This module centralizes audience-visible labels, source-title cleanup,
source-grounded messaging, Persian copy validation, and deterministic visual
metrics. It deliberately contains no network or AI dependency.
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
    Category.PDF_TUTORIAL: "راهنمای انتخاب PDF",
    Category.PERSIAN_TEXT: "نگارش فارسی",
    Category.PROFESSIONAL: "ابزارهای حرفه‌ای",
    Category.PRIVACY: "حریم خصوصی",
    Category.FINANCIAL: "ابزارهای مالی",
    Category.SEASONAL: "محتوای مناسبتی",
    Category.COMPARISON: "راهنمای انتخاب",
}

_VAGUE_COPY = (
    "از کجا شروع کنیم",
    "برای یک کار مشخص",
    "موضوع کارتان را مشخص کنید",
    "ابزار مرتبط را پیدا کنید",
    "گزینه مرتبط",
    "بیشتر بدانید",
    "همین حالا امتحان کنید",
)


@dataclass(frozen=True)
class CopyDeck:
    """Source-grounded messaging used by renderer, caption and QA.

    The visible asset uses ``headline``, ``supporting_text`` and ``cta``. The
    remaining fields make the marketing and psychology rationale explicit so
    a generic sentence cannot pass as a complete content strategy.
    """

    short_title: str
    headline: str
    supporting_text: str
    cta: str
    alt_text: str
    category_label: str
    problem: str
    value_proposition: str
    reason_to_believe: str
    marketing_goal: str
    psychology_principle: str
    psychology_effect: str
    caption_lead: str


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
    value = re.sub(
        r"\s*[|–—-]\s*[^|–—-]+$", lambda match: _strip_known_suffix(match.group(0)), value
    )
    for suffix in _TITLE_SUFFIXES:
        value = re.sub(rf"\s*[|–—-]?\s*{re.escape(suffix)}\s*$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+", " ", value).strip(" -|–—")
    return value or "ابزارهای پرشین‌تولباکس"


def _strip_known_suffix(fragment: str) -> str:
    candidate = fragment.strip(" -|–—").strip()
    if any(suffix.casefold() in candidate.casefold() for suffix in _TITLE_SUFFIXES):
        return ""
    return fragment


def _source_reason(short_title: str, summary: str) -> str:
    source_summary = normalize_persian(summary or "").strip()
    if source_summary:
        return f"منبع، «{short_title}» را با این توضیح معرفی می‌کند: {source_summary}"
    return f"عنوان منبع، موضوع محتوا را «{short_title}» معرفی می‌کند."


def build_copy_deck(title: str, category: Category, summary: str = "") -> CopyDeck:
    """Build a concrete, source-grounded Persian marketing message.

    The contract follows: problem -> value -> reason to believe -> action. It
    avoids unsupported performance claims, urgency, superlatives and invented
    product capabilities.
    """
    short = clean_source_title(title)
    label = CATEGORY_LABELS.get(category, "معرفی ابزار")
    reason = _source_reason(short, summary)

    if category == Category.PDF_TUTORIAL or "PDF" in short.upper():
        headline = "PDF اداری یا استخدامی؟\nابزار مناسب را پیدا کنید"
        supporting = "ابزارهای این مجموعه را یک‌جا ببینید و بر اساس کاری که دارید، انتخاب کنید."
        cta = "ابزارهای PDF را ببینید"
        alt = "طرح راهنمای انتخاب ابزار PDF برای کارهای اداری و مدارک استخدامی"
        problem = (
            "کاربر برای یک کار اداری یا استخدامی فایل PDF دارد، اما ابزار متناسب با همان "
            "کار را نمی‌شناسد"
        )
        value = (
            "در صفحه ابزارهای PDF، ابزارهای اداری و استخدامی را یک‌جا می‌بینید و انتخاب را "
            "از نوع کارتان شروع می‌کنید"
        )
        goal = "ترغیب کاربر به مشاهده صفحه ابزارهای PDF پس از تشخیص موقعیت خود"
        principle = "خودارجاعی موقعیتی و کاهش پیچیدگی انتخاب"
        effect = (
            "دو موقعیت روشنِ اداری و استخدامی، مخاطب را به تشخیص سریع نیاز خود و ادامه مسیر "
            "هدایت می‌کنند."
        )
        lead = (
            "با یک فایل PDF ممکن است کار اداری داشته باشید یا بخواهید مدارک استخدامی را آماده کنید."
        )
    elif category == Category.PERSIAN_TEXT:
        headline = "متن فارسی را\nپیش از انتشار مرتب کنید"
        supporting = (
            "ابزارهای پاک‌سازی و استانداردسازی متن را متناسب با مسئله‌ای که دارید بررسی کنید."
        )
        cta = "ابزارهای نگارش را بررسی کنید"
        alt = "طرح معرفی ابزارهای نگارش فارسی با کارت‌های متن، پاک‌سازی و ویرایش"
        problem = "ناهماهنگی نویسه‌ها و بی‌نظمی متن فارسی پیش از استفاده یا انتشار"
        value = "ابزارهای پاک‌سازی و استانداردسازی متن فارسی را بر اساس مسئله‌تان بررسی می‌کنید"
        goal = "تبدیل آگاهی از خطای متن به بررسی ابزار نگارشی مرتبط"
        principle = "برجسته‌سازی مسئله و کاهش ابهام راه‌حل"
        effect = "کاربر خطای قابل‌تشخیص را به یک اقدام اصلاحی مشخص وصل می‌کند."
        lead = "متن فارسی نامرتب، خواندن و استفاده از محتوا را دشوار می‌کند."
    elif category == Category.PRIVACY:
        headline = "پیش از استفاده،\nنحوه پردازش داده را بررسی کنید"
        supporting = "اطلاعات منبع را بخوانید و متناسب با حساسیت داده‌های خود تصمیم بگیرید."
        cta = "جزئیات استفاده را بررسی کنید"
        alt = "طرح راهنمای بررسی نحوه استفاده و پردازش داده پیش از انتخاب ابزار"
        problem = "تصمیم‌گیری درباره ابزار بدون شناخت نحوه استفاده از داده"
        value = "اطلاعات منبع را پیش از واردکردن داده می‌خوانید و آگاهانه تصمیم می‌گیرید"
        goal = "هدایت کاربر به مطالعه جزئیات پیش از استفاده از ابزار"
        principle = "افزایش حس کنترل و کاهش عدم‌قطعیت"
        effect = "کاربر پیش از اقدام، اطلاعات مرتبط با حساسیت داده را بررسی می‌کند."
        lead = "برای داده‌های حساس، انتخاب ابزار باید با اطلاعات روشن انجام شود."
    else:
        headline = f"{short}\nبرای چه کاری مناسب است؟"
        supporting = (
            "کاربرد معرفی‌شده در منبع را بررسی کنید و ببینید با نیاز فعلی شما هم‌خوانی دارد یا نه."
        )
        cta = "جزئیات ابزار را بررسی کنید"
        alt = f"طرح معرفی {short} و دعوت به بررسی کاربرد آن در پرشین‌تولباکس"
        problem = "انتخاب ابزار پیش از روشن‌شدن کاربرد و تناسب آن با نیاز کاربر"
        value = "کاربرد ابزار را می‌خوانید و پیش از اقدام با نیاز خود مقایسه می‌کنید"
        goal = "هدایت کاربر از آگاهی اولیه به بررسی آگاهانه صفحه ابزار"
        principle = "کاهش ابهام و تقویت خودارزیابی تناسب"
        effect = "کاربر پیش از اقدام، کاربرد ابزار را با نیاز خود مقایسه می‌کند."
        lead = f"پیش از انتخاب {short}، بهتر است کاربرد آن را با نیازتان مقایسه کنید."

    return CopyDeck(
        short_title=short,
        headline=_normalize_multiline(headline),
        supporting_text=normalize_persian(supporting),
        cta=normalize_persian(cta),
        alt_text=normalize_persian(alt),
        category_label=normalize_persian(label),
        problem=normalize_persian(problem),
        value_proposition=normalize_persian(value),
        reason_to_believe=normalize_persian(reason),
        marketing_goal=normalize_persian(goal),
        psychology_principle=normalize_persian(principle),
        psychology_effect=normalize_persian(effect),
        caption_lead=normalize_persian(lead),
    )


def validate_copy_deck(deck: CopyDeck) -> list[str]:
    """Return fail-closed semantic and Persian-copy defects."""
    defects: list[str] = []
    visible = " ".join([deck.headline, deck.supporting_text, deck.cta])
    all_copy = " ".join(str(value) for value in deck.__dict__.values())

    if any(token in all_copy for token in ("tool-demo", "pdf-tutorial", "privacy-trust")):
        defects.append("internal enum leaked into audience-visible copy")
    if any(suffix in all_copy for suffix in (" - جعبه ابزار فارسی", "- جعبه‌ابزار فارسی")):
        defects.append("raw site-title suffix leaked into copy")
    if any(phrase in visible for phrase in _VAGUE_COPY):
        defects.append("vague or placeholder marketing copy detected")
    if len(deck.headline.replace("\n", " ").strip()) < 18:
        defects.append("headline is too short to communicate a concrete value")
    if len(deck.headline.replace("\n", " ")) > 74:
        defects.append("headline is too long")
    if len(deck.supporting_text) < 45:
        defects.append("supporting text does not explain enough value")
    if deck.short_title in deck.supporting_text and len(deck.short_title) > 18:
        defects.append("source title is redundantly repeated")
    if not deck.problem or not deck.value_proposition:
        defects.append("problem/value proposition is missing")
    if not deck.reason_to_believe:
        defects.append("reason to believe is missing")
    if not deck.marketing_goal:
        defects.append("marketing goal is missing")
    if not deck.psychology_principle or not deck.psychology_effect:
        defects.append("psychology rationale is missing")
    if not deck.caption_lead.endswith((".", "؟")):
        defects.append("caption lead is not a complete Persian sentence")
    if not deck.cta.endswith(("بررسی کنید", "ببینید", "بخوانید", "مقایسه کنید")):
        defects.append("CTA is not a precise Persian action phrase")
    if any(claim in visible for claim in ("بهترین", "سریع‌ترین", "تضمینی", "بدون خطا")):
        defects.append("unsupported superlative or absolute claim detected")
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
    near_white = sum(
        1 for red, green, blue in pixels if red >= 245 and green >= 245 and blue >= 245
    )

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
