"""Editorial content shaping for audience-visible Persian copy.

This module is the single source of truth for display titles, captions, alt text,
and in-canvas visual copy. Source-page titles are never rendered verbatim.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .types import Brief, Caption, CatalogRecord, Category
from .utils.persian import normalize_persian

_BRAND_SUFFIXES = (
    "جعبه ابزار فارسی",
    "جعبه‌ابزار فارسی",
    "پرشین تولباکس",
    "پرشین‌تولباکس",
    "persiantoolbox",
)
_SEPARATOR_RE = re.compile(r"\s+(?:\||[-–—])\s+")
_WHITESPACE_RE = re.compile(r"[ \t\u00a0]+")
_BAD_INTERNAL_TOKENS = ("tool-demo", "pdf-tutorial", "persian-text", "common-mistake")


@dataclass(frozen=True)
class VisualCopy:
    """Exact audience-visible copy rendered inside a social image."""

    eyebrow: str
    headline: str
    subheadline: str
    feature_labels: tuple[str, ...]
    cta: str
    motif: str

    def audience_text(self) -> str:
        return "\n".join(
            part
            for part in (
                self.eyebrow,
                self.headline,
                self.subheadline,
                *self.feature_labels,
                self.cta,
            )
            if part
        )


def clean_display_title(raw_title: str) -> str:
    """Convert a crawler/page title into a short human-facing product title."""
    title = unicodedata.normalize("NFKC", raw_title or "")
    title = normalize_persian(title)
    title = _WHITESPACE_RE.sub(" ", title).strip(" |–—-")

    parts = [part.strip() for part in _SEPARATOR_RE.split(title) if part.strip()]
    if len(parts) > 1:
        for index, part in enumerate(parts[1:], start=1):
            lowered = part.casefold()
            if any(suffix.casefold() in lowered for suffix in _BRAND_SUFFIXES):
                title = " — ".join(parts[:index])
                break

    for suffix in _BRAND_SUFFIXES:
        title = re.sub(
            rf"(?:\s*[|–—-]\s*)?{re.escape(suffix)}\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        )

    return _WHITESPACE_RE.sub(" ", title).strip(" |–—-")


def _motif(record: CatalogRecord) -> str:
    haystack = f"{record.title} {record.canonical_url} {record.summary}".casefold()
    if "pdf" in haystack:
        return "pdf"
    if any(word in haystack for word in ("نگارش", "متن فارسی", "نامه اداری", "ویرایشگر")):
        return "writing"
    if any(word in haystack for word in ("رزومه", "استخدام", "اداری")):
        return "office"
    return "toolbox"


def build_visual_copy(record: CatalogRecord) -> VisualCopy:
    """Build concise, semantic and claim-safe copy for the graphic canvas."""
    display_title = clean_display_title(record.title)
    motif = _motif(record)

    if motif == "pdf":
        return VisualCopy(
            eyebrow="مجموعه ابزارهای PDF",
            headline="برای کارهای اداری با PDF\nاز کجا شروع کنیم؟",
            subheadline="ابزارهای مربوط به مدیریت فایل‌های PDF را در یک صفحه ببینید.",
            feature_labels=("ادغام فایل‌ها", "تقسیم صفحات", "فشرده‌سازی", "تبدیل فرمت"),
            cta="مشاهده ابزارهای PDF",
            motif=motif,
        )

    if motif == "writing":
        return VisualCopy(
            eyebrow="ابزارهای نگارش فارسی",
            headline="برای نوشتن و ویرایش متن فارسی\nابزار مناسب را پیدا کنید",
            subheadline="از آماده‌سازی نامه اداری تا پاک‌سازی و استانداردسازی متن.",
            feature_labels=("نامه اداری", "ویرایش متن", "نرمال‌سازی", "نگارش فارسی"),
            cta="مشاهده ابزارهای نگارش",
            motif=motif,
        )

    if motif == "office":
        return VisualCopy(
            eyebrow="ابزارهای اداری",
            headline="ابزارهای موردنیاز کارهای اداری\nدر یک مجموعه",
            subheadline="برای آماده‌سازی اسناد و فایل‌های کاری، ابزار مرتبط را انتخاب کنید.",
            feature_labels=("اسناد اداری", "فایل‌های کاری", "رزومه", "نامه رسمی"),
            cta="مشاهده ابزارهای اداری",
            motif=motif,
        )

    safe_title = display_title or "ابزارهای پرشین‌تولباکس"
    if len(safe_title) > 46:
        safe_title = safe_title[:45].rstrip() + "…"
    return VisualCopy(
        eyebrow="معرفی ابزار",
        headline=f"با {safe_title}\nآشنا شوید",
        subheadline="صفحه ابزار را ببینید و گزینه متناسب با کارتان را انتخاب کنید.",
        feature_labels=("انتخاب ابزار", "شروع کار", "راهنمای استفاده"),
        cta="مشاهده صفحه ابزار",
        motif=motif,
    )


def build_caption(record: CatalogRecord) -> Caption:
    """Build a readable Persian caption without repeating raw page titles."""
    visual = build_visual_copy(record)

    if visual.motif == "pdf":
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
    elif visual.motif == "writing":
        primary = (
            "برای نوشتن و ویرایش متن‌های فارسی، مجموعه ابزارهای نگارش پرشین‌تولباکس "
            "را ببینید.\n\n"
            "از آماده‌سازی نامه اداری تا پاک‌سازی و استانداردسازی متن، ابزار مرتبط را "
            "از صفحه نگارش فارسی انتخاب کنید.\n\n"
            "لینک در بیو"
        )
        alt = "طرح گرافیکی معرفی ابزارهای نگارش فارسی با کارت‌های نامه و ویرایش متن"
    elif visual.motif == "office":
        primary = (
            "برای آماده‌سازی فایل‌ها و اسناد کاری، ابزارهای اداری پرشین‌تولباکس را "
            "بررسی کنید.\n\n"
            "صفحه مجموعه را باز کنید و ابزار مرتبط با کارتان را انتخاب کنید.\n\n"
            "لینک در بیو"
        )
        alt = "طرح گرافیکی معرفی مجموعه ابزارهای اداری و فایل‌های کاری"
    else:
        display_title = clean_display_title(record.title) or "این ابزار"
        primary = (
            f"{display_title} را در مجموعه ابزارهای پرشین‌تولباکس ببینید.\n\n"
            "صفحه ابزار را باز کنید و با کاربرد آن آشنا شوید.\n\n"
            "لینک در بیو"
        )
        alt = f"طرح گرافیکی معرفی {display_title} در پرشین‌تولباکس"

    return Caption(primary=normalize_persian(primary), alt_text=normalize_persian(alt), cta="لینک در بیو")


def publication_text(brief: Brief) -> str:
    """Return every audience-visible text fragment used for risk/QA evaluation."""
    visual = build_visual_copy(brief.catalog_record)
    return "\n".join(
        (
            brief.caption.primary,
            brief.caption.cta,
            brief.caption.alt_text,
            visual.audience_text(),
        )
    )


def editorial_issues(brief: Brief) -> list[str]:
    """Return deterministic editorial defects that must block publication."""
    issues: list[str] = []
    raw_title = brief.catalog_record.title
    display_title = clean_display_title(raw_title)
    caption = brief.caption.primary.strip()
    visual = build_visual_copy(brief.catalog_record)
    all_visible = publication_text(brief)

    if not display_title:
        issues.append("display title is empty after source-title cleanup")
    if display_title and len(display_title) > 70:
        issues.append("display title is too long for social content")
    if any(token in all_visible for token in _BAD_INTERNAL_TOKENS):
        issues.append("internal category token is exposed to the audience")
    if re.search(r"با\s+.+\s[-–—|]\s.+\sآشنا شوید", caption):
        issues.append("malformed source title is embedded in the opening sentence")
    if display_title and caption.count(display_title) > 1:
        issues.append("display title is repeated in the caption")
    if raw_title == display_title and any(s.casefold() in raw_title.casefold() for s in _BRAND_SUFFIXES):
        issues.append("brand/page suffix was not removed from the source title")
    if len(caption) < 80:
        issues.append("caption is too short to communicate a useful message")
    if len(visual.headline.replace("\n", " ")) > 74:
        issues.append("visual headline is too long")
    if "  " in all_visible:
        issues.append("double whitespace found in audience-visible copy")
    if all_visible.count("|") or all_visible.count(" - "):
        issues.append("raw title separator found in audience-visible copy")

    return issues
