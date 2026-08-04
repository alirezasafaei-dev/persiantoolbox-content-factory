"""Regression tests for publication-safe Instagram hashtags."""

from types import SimpleNamespace

import pytest

from ptb_content.publisher.errors import ValidationError
from ptb_content.publisher.instagram_export import (
    _DEFAULT_HASHTAGS,
    _GENERIC_HASHTAGS,
    InstagramExporter,
)
from ptb_content.risk import RiskEngine


def _brief(caption: str = "", category: str = "tool-demo") -> SimpleNamespace:
    return SimpleNamespace(
        brief_id="brief-hashtag-test",
        caption=SimpleNamespace(primary=caption),
        catalog_record=SimpleNamespace(category=SimpleNamespace(value=category)),
    )


def test_all_default_hashtags_are_publication_safe() -> None:
    engine = RiskEngine()
    hashtag_sets = [*_DEFAULT_HASHTAGS.values(), _GENERIC_HASHTAGS]

    for hashtags in hashtag_sets:
        assert engine.detect_publishable_tags(" ".join(hashtags)) == set()


def test_tool_demo_defaults_do_not_claim_free_or_offline() -> None:
    hashtags = InstagramExporter()._select_hashtags(_brief())
    joined = " ".join(hashtags)

    assert "رایگان" not in joined
    assert "آفلاین" not in joined
    assert hashtags == list(_DEFAULT_HASHTAGS["tool-demo"])


def test_risky_caption_hashtag_blocks_export() -> None:
    brief = _brief(caption="معرفی ابزار #ابزار_رایگان")

    with pytest.raises(ValidationError, match="publication risk"):
        InstagramExporter()._select_hashtags(brief)


def test_safe_caption_hashtags_are_preserved() -> None:
    brief = _brief(caption="معرفی ابزار #پرشین_تولباکس #ابزار_فارسی")

    assert InstagramExporter()._select_hashtags(brief) == [
        "#پرشین_تولباکس",
        "#ابزار_فارسی",
    ]
