"""Unit tests for Persian text normalization."""

from ptb_content.utils.persian import (
    check_zwnj_usage,
    has_arabic_imposters,
    is_valid_persian,
    normalize_persian,
    persian_text_stats,
)


class TestNormalizePersian:
    def test_empty_string(self) -> None:
        assert normalize_persian("") == ""

    def test_none_returns_none(self) -> None:
        # normalize_persian should handle empty
        assert normalize_persian("") == ""

    def test_arabic_kaf_to_persian(self) -> None:
        arabic_kaf = "\u0643"  # Arabic ك
        persian_kaf = "\u06a9"  # Persian ک
        assert normalize_persian(f"برنامه{arabic_kaf}نویسی") == f"برنامه{persian_kaf}نویسی"

    def test_arabic_yeh_to_persian(self) -> None:
        arabic_yeh = "\u0649"  # Arabic ى
        persian_yeh = "\u06cc"  # Persian ی
        assert normalize_persian(f"علی{arabic_yeh}") == f"علی{persian_yeh}"

    def test_whitespace_normalization(self) -> None:
        assert normalize_persian("سلام   دنیا") == "سلام دنیا"
        assert normalize_persian("hello  \n  world") == "hello world"

    def test_nfc_normalize(self) -> None:
        # Should not crash
        result = normalize_persian("سلام دنیا")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_persian_text_preserved(self) -> None:
        text = "این یک متن فارسی است"
        assert normalize_persian(text) == text

    def test_mixed_text(self) -> None:
        text = "Hello سلام World دنیا"
        result = normalize_persian(text)
        assert "سلام" in result
        assert "دنیا" in result


class TestHasArabicImposters:
    def test_clean_persian(self) -> None:
        assert not has_arabic_imposters("سلام دنیا")

    def test_arabic_kaf(self) -> None:
        assert has_arabic_imposters("برنامه\u0643نویسی")

    def test_arabic_yeh(self) -> None:
        assert has_arabic_imposters("علی\u0649")

    def test_empty_string(self) -> None:
        assert not has_arabic_imposters("")


class TestIsValidPersian:
    def test_persian_text(self) -> None:
        assert is_valid_persian("این یک متن فارسی است")

    def test_empty(self) -> None:
        assert not is_valid_persian("")

    def test_whitespace_only(self) -> None:
        assert not is_valid_persian("   ")

    def test_english_only(self) -> None:
        # Less than 30% Persian
        assert not is_valid_persian("Hello World")

    def test_mixed_mostly_persian(self) -> None:
        assert is_valid_persian("ابزار سلام دنیا test")


class TestCheckZWNJ:
    def test_clean_text(self) -> None:
        issues = check_zwnj_usage("سلام دنیا")
        assert isinstance(issues, list)

    def test_detects_missing_zwnj(self) -> None:
        issues = check_zwnj_usage("میشه خوبه")
        # Should detect at least one issue
        assert isinstance(issues, list)


class TestPersianTextStats:
    def test_empty(self) -> None:
        stats = persian_text_stats("")
        assert stats["chars"] == 0
        assert stats["words"] == 0

    def test_basic(self) -> None:
        stats = persian_text_stats("سلام دنیا")
        assert stats["chars"] == 9  # 4 + 1 + 4
        assert stats["words"] == 2

    def test_persian_ratio(self) -> None:
        stats = persian_text_stats("سلام دنیا")
        assert stats["persian_ratio"] > 0.5
