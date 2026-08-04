"""Editorial shaping for all audience-visible Persian copy."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .types import Brief, Caption, CatalogRecord
from .utils.persian import normalize_persian

_BRANDS = (
    "جعبه ابزار فارسی",
    "جعبه‌ابزار فارسی",
    "پرشین تولباکس",
    "پرشین‌تولباکس",
    "persiantoolbox",
)
_SEPARATORS = re.compile(r"\s+(?:\||[-–—])\s+")
_SPACE = re.compile(r"[ \t\u00a0]+")
_INTERNAL = ("tool-demo", "pdf-tutorial", "persian-text", "common-mistake")


@dataclass(frozen=True)
class VisualCopy:
    eyebrow: str
    headline: str
    subheadline: str
    feature_labels: tuple[str, ...]
    cta: str
    motif: str

    def audience_text(self) -> str:
        return "\n".join(
            text
            for text in (
                self.eyebrow,
                self.headline,
                self.subheadline,
                *self.feature_labels,
                self.cta,
            )
            if text
        )


def clean_display_title(raw_title: str) -> str:
    """Strip SEO/brand suffixes and return a human-facing title."""
    title = normalize_persian(unicodedata.normalize("NFKC", raw_title or ""))
    title = _SPACE.sub(" ", title).strip(" |–—-")
    parts = [part.strip() for part in _SEPARATORS.split(title) if part.strip()]
    for index, part in enumerate(parts[1:], start=1):
        if any(brand.casefold() in part.casefold() for brand in _BRANDS):
            title = " — ".join(parts[:index])
            break
    for brand in _BRANDS:
        title = re.sub(
            rf"(?:\s*[|–—-]\s*)?{re.escape(brand)}\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        )
    return _SPACE.sub(" ", title).strip(" |–—-")


def _motif(record: CatalogRecord) -> str:
    text = f"{record.title} {record.canonical_url} {record.summary}".casefold()
    if "pdf" in text:
        return "pdf"
    if any(token in text for token in ("نگارش", "متن فارسی", "نامه اداری", "ویرایشگر")):
        return "writing"
    if any(token in text for token in ("رزومه", "استخدام", "اداری")):
        return "office"
    return "toolbox"


def build_visual_copy(record: CatalogRecord) -> VisualCopy:
    motif = _motif(record)
    if motif == "pdf":
        return VisualCopy(
            "مجموعه ابزارهای PDF",
            "برای کارهای اداری با PDF\nاز کجا شروع کنیم؟",
            "ابزارهای مربوط به مدیریت فایل‌های PDF را در یک صفحه ببینید.",
            ("ادغام فایل‌ها", "تقسیم صفحات", "فشرده‌سازی", "تبدیل فرمت"),
            "مشاهده ابزارهای PDF",
            motif,
        )
    if motif == "writing":
        return VisualCopy(
            "ابزارهای نگارش فارسی",
            "برای نوشتن و ویرایش متن فارسی\nابزار مناسب را پیدا کنید",
            "از آماده‌سازی نامه اداری تا پاک‌سازی و استانداردسازی متن.",
            ("نامه اداری", "ویرایش متن", "نرمال‌سازی", "نگارش فارسی"),
            "مشاهده ابزارهای نگارش",
            motif,
        )
    if motif == "office":
        return VisualCopy(
            "ابزارهای اداری",
            "ابزارهای موردنیاز کارهای اداری\nدر یک مجموعه",
            "برای آماده‌سازی اسناد و فایل‌های کاری، ابزار مرتبط را انتخاب کنید.",
            ("اسناد اداری", "فایل‌های کاری", "رزومه", "نامه رسمی"),
            "مشاهده ابزارهای اداری",
            motif,
        )
    title = clean_display_title(record.title) or "ابزارهای پرشین‌تولباکس"
    title = title if len(title) <= 46 else title[:45].rstrip() + "…"
    return VisualCopy(
        "معرفی ابزار",
        f"با {title}\nآشنا شوید",
        "صفحه ابزار را ببینید و گزینه متناسب با کارتان را انتخاب کنید.",
        ("انتخاب ابزار", "شروع کار", "راهنمای استفاده"),
        "مشاهده صفحه ابزار",
        motif,
    )


def build_caption(record: CatalogRecord) -> Caption:
    motif = _motif(record)
    if motif == "pdf":
        primary = (
            "برای آماده‌کردن اسناد اداری، گاهی لازم است فایل‌های PDF را ادغام، "
            "تقسیم، فشرده یا به قالب دیگری تبدیل کنید.\n\n"
            "در بخش ابزارهای PDF پرشین‌تولباکس می‌توانید ابزار مرتبط با کارتان را پیدا کنید.\n\n"
            "لینک در بیو"
        )
        alt = (
            "طرح گرافیکی معرفی ابزارهای PDF با کارت‌های سند و گزینه‌های ادغام، "
            "تقسیم، فشرده‌سازی و تبدیل فرمت"
        )
    elif motif == "writing":
        primary = (
            "برای نوشتن و ویرایش متن‌های فارسی، مجموعه ابزارهای نگارش پرشین‌تولباکس "
            "را ببینید.\n\n"
            "از آماده‌سازی نامه اداری تا پاک‌سازی و استانداردسازی متن، ابزار مرتبط را "
            "از صفحه نگارش فارسی انتخاب کنید.\n\nلینک در بیو"
        )
        alt = "طرح گرافیکی معرفی ابزارهای نگارش فارسی با کارت‌های نامه و ویرایش متن"
    elif motif == "office":
        primary = (
            "برای آماده‌سازی فایل‌ها و اسناد کاری، ابزارهای اداری پرشین‌تولباکس را "
            "بررسی کنید.\n\nصفحه مجموعه را باز کنید و ابزار مرتبط با کارتان را انتخاب کنید."
            "\n\nلینک در بیو"
        )
        alt = "طرح گرافیکی معرفی مجموعه ابزارهای اداری و فایل‌های کاری"
    else:
        title = clean_display_title(record.title) or "این ابزار"
        primary = (
            f"{title} را در مجموعه ابزارهای پرشین‌تولباکس ببینید.\n\n"
            "صفحه ابزار را باز کنید و با کاربرد آن آشنا شوید.\n\nلینک در بیو"
        )
        alt = f"طرح گرافیکی معرفی {title} در پرشین‌تولباکس"
    return Caption(
        primary=normalize_persian(primary),
        alt_text=normalize_persian(alt),
        cta="لینک در بیو",
    )


def publication_text(brief: Brief) -> str:
    visual = build_visual_copy(brief.catalog_record)
    return "\n".join(
        (brief.caption.primary, brief.caption.cta, brief.caption.alt_text, visual.audience_text())
    )


def editorial_issues(brief: Brief) -> list[str]:
    issues: list[str] = []
    raw = brief.catalog_record.title
    title = clean_display_title(raw)
    caption = brief.caption.primary.strip()
    visible = publication_text(brief)
    visual = build_visual_copy(brief.catalog_record)

    if not title:
        issues.append("display title is empty after source-title cleanup")
    if len(title) > 70:
        issues.append("display title is too long for social content")
    if any(token in visible for token in _INTERNAL):
        issues.append("internal category token is exposed to the audience")
    if re.search(r"با\s+.+\s[-–—|]\s.+\sآشنا شوید", caption):
        issues.append("malformed source title is embedded in the opening sentence")
    if title and caption.count(title) > 1:
        issues.append("display title is repeated in the caption")
    if raw == title and any(brand.casefold() in raw.casefold() for brand in _BRANDS):
        issues.append("brand/page suffix was not removed from the source title")
    if len(caption) < 80:
        issues.append("caption is too short to communicate a useful message")
    if len(visual.headline.replace("\n", " ")) > 74:
        issues.append("visual headline is too long")
    if "  " in visible:
        issues.append("double whitespace found in audience-visible copy")
    if "|" in visible or " - " in visible:
        issues.append("raw title separator found in audience-visible copy")
    return issues
