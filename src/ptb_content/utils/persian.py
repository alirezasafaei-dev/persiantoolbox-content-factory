"""Persian text normalization and QA utilities."""

from __future__ import annotations

import re
import unicodedata

# Arabic → Persian character mapping
ARABIC_TO_PERSIAN: dict[str, str] = {
    "\u0627": "\u0627",  # ا (same)
    "\u0628": "\u0628",  # ب (same)
    "\u062A": "\u062A",  # ت (same)
    "\u062B": "\u062B",  # ث (same)
    "\u062C": "\u062C",  # ج (same)
    "\u062D": "\u062D",  # ح (same)
    "\u062E": "\u062E",  # خ (same)
    "\u062F": "\u062F",  # د (same)
    "\u0630": "\u0630",  # ذ (same)
    "\u0631": "\u0631",  # ر (same)
    "\u0632": "\u0632",  # ز (same)
    "\u0633": "\u0633",  # س (same)
    "\u0634": "\u0634",  # ش (same)
    "\u0635": "\u0635",  # ص (same)
    "\u0636": "\u0636",  # ض (same)
    "\u0637": "\u0637",  # ط (same)
    "\u0638": "\u0638",  # ظ (same)
    "\u0639": "\u0639",  # ع (same)
    "\u063A": "\u063A",  # غ (same)
    "\u0641": "\u0641",  # ف (same)
    "\u0642": "\u0642",  # ق (same)
    "\u0644": "\u0644",  # ل (same)
    "\u0645": "\u0645",  # م (same)
    "\u0646": "\u0646",  # ن (same)
    "\u0647": "\u0647",  # ه (same)
    "\u0648": "\u0648",  # و (same)
    "\u06CC": "\u06CC",  # ی (same)
    # Arabic-only characters → Persian equivalents
    "\u0643": "\u06A9",  # ك → ک
    "\u0649": "\u06CC",  # ى → ی
    "\u0629": "\u0647",  # ة → ه
    "\u0623": "\u0627",  # أ → ا
    "\u0622": "\u0627",  # آ (already Persian, keep)
    "\u0624": "\u0648",  # ؤ → و
    "\u0626": "\u06CC",  # ئ → ی
}

# Persian-specific characters that should NOT be replaced
_PERSIAN_RANGE = "".join(chr(c) for c in range(0x0600, 0x0700))
PERSIAN_CHARS = set(_PERSIAN_RANGE)

# Half-space (ZWNJ)
ZWNJ = "\u200C"

# Common Arabic-letter imposters in Persian text
IMPOSTER_MAP = {
    "\u0643": "\u06A9",  # Arabic ك → Persian ک
    "\u0649": "\u06CC",  # Arabic ى → Persian ی
    "\u0629": "\u0647",  # Arabic ة → Persian ه
    "\u0623": "\u0627",  # Arabic أ → Persian ا
    "\u0624": "\u0648",  # Arabic ؤ → Persian و
    "\u0626": "\u06CC",  # Arabic ئ → Persian ی
}


def normalize_persian(text: str) -> str:
    """Normalize Persian text: fix Arabic characters, normalize whitespace, etc."""
    if not text:
        return text

    # NFC normalize
    text = unicodedata.normalize("NFC", text)

    # Replace Arabic imposter characters
    for arabic, persian in IMPOSTER_MAP.items():
        text = text.replace(arabic, persian)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove zero-width characters except ZWNJ
    text = re.sub(r"[\u200B\u200D\uFEFF]", "", text)
    # Keep existing ZWNJ but don't add new ones aggressively

    # Normalize digits to Persian
    for i, p in enumerate("۰۱۲۳۴۵۶۷۸۹"):
        text = text.replace(str(i), p)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text


def has_arabic_imposters(text: str) -> bool:
    """Check if text contains Arabic imposter characters that should be Persian."""
    for char in text:
        if char in IMPOSTER_MAP:
            return True
    return False


def is_valid_persian(text: str) -> bool:
    """Check if text is valid Persian (RTL, correct characters, etc.)."""
    if not text or not text.strip():
        return False

    # Check for basic Persian character presence
    persian_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF" or "\u0750" <= c <= "\u077F")
    total_alpha = sum(1 for c in text if c.isalpha())

    if total_alpha == 0:
        return False

    # At least 30% should be Persian/Arabic characters for it to be Persian text
    return persian_chars / max(total_alpha, 1) >= 0.3


def check_zwnj_usage(text: str) -> list[str]:
    """Check for missing ZWNJ in common Persian compound words."""
    issues = []

    # Common words that need ZWNJ
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

    persian_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    total_alpha = sum(1 for c in text if c.isalpha())
    persian_ratio = persian_chars / max(total_alpha, 1)

    return {
        "chars": chars,
        "words": words,
        "lines": lines,
        "persian_ratio": round(persian_ratio, 3),
    }
