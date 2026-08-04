"""Persian text normalization and QA utilities."""

from __future__ import annotations

import re
import unicodedata

# Arabic glyph variants that have unambiguous Persian equivalents.
ARABIC_TO_PERSIAN: dict[str, str] = {
    "\u0643": "\u06a9",  # Arabic ك → Persian ک
    "\u064a": "\u06cc",  # Arabic ي → Persian ی
    "\u0649": "\u06cc",  # Arabic ى → Persian ی
    "\u0629": "\u0647",  # Arabic ة → Persian ه
}

# Persian-specific characters that should NOT be replaced.
_PERSIAN_RANGE = "".join(chr(c) for c in range(0x0600, 0x0700))
PERSIAN_CHARS = set(_PERSIAN_RANGE)

# Half-space (ZWNJ)
ZWNJ = "\u200c"

# Only normalize glyph variants whose replacement does not alter meaning or
# accepted Persian spelling. Hamza-bearing letters such as ئ، ؤ and أ must be
# preserved; replacing them corrupts words such as مسئله، مسئول and تأثیر.
IMPOSTER_MAP = dict(ARABIC_TO_PERSIAN)


def normalize_persian(text: str) -> str:
    """Normalize Persian glyph variants, whitespace, digits and zero-width marks."""
    if not text:
        return text

    text = unicodedata.normalize("NFC", text)

    for arabic, persian in IMPOSTER_MAP.items():
        text = text.replace(arabic, persian)

    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[\u200B\u200D\uFEFF]", "", text)

    for i, persian_digit in enumerate("۰۱۲۳۴۵۶۷۸۹"):
        text = text.replace(str(i), persian_digit)

    return text.strip()


def has_arabic_imposters(text: str) -> bool:
    """Check for Arabic glyph variants with unambiguous Persian replacements."""
    return any(char in IMPOSTER_MAP for char in text)


def is_valid_persian(text: str) -> bool:
    """Check if text contains a meaningful proportion of Persian-script letters."""
    if not text or not text.strip():
        return False

    persian_chars = sum(
        1 for char in text if "\u0600" <= char <= "\u06ff" or "\u0750" <= char <= "\u077f"
    )
    total_alpha = sum(1 for char in text if char.isalpha())

    if total_alpha == 0:
        return False

    return persian_chars / max(total_alpha, 1) >= 0.3


def check_zwnj_usage(text: str) -> list[str]:
    """Check for missing ZWNJ in common Persian compound words."""
    issues = []

    zwnj_words = {
        "خودش": "خودش",
        "خودت": "خودت",
        "خودم": "خودم",
        "خودتان": "خودتان",
        "خودمان": "خودمان",
        "میشه": "می‌شه",
        "میکنه": "می‌کنه",
        "میخوام": "می‌خوام",
        "داره": "داره",
        "نداره": "نداره",
    }

    for wrong, correct in zwnj_words.items():
        if wrong in text and correct not in text:
            issues.append(f"Missing ZWNJ: '{wrong}' should be '{correct}'")

    return issues


def persian_text_stats(text: str) -> dict[str, int | float]:
    """Get statistics about Persian text."""
    if not text:
        return {"chars": 0, "words": 0, "lines": 0, "persian_ratio": 0.0}

    chars = len(text)
    words = len(text.split())
    lines = text.count("\n") + 1

    persian_chars = sum(1 for char in text if "\u0600" <= char <= "\u06ff")
    total_alpha = sum(1 for char in text if char.isalpha())
    persian_ratio = persian_chars / max(total_alpha, 1)

    return {
        "chars": chars,
        "words": words,
        "lines": lines,
        "persian_ratio": round(persian_ratio, 3),
    }
