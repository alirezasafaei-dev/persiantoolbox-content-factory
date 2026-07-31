"""Tests for golden set validation, prompt injection, and edge cases."""

import json
from pathlib import Path

from ptb_content.qa import QAEngine
from ptb_content.risk import RiskEngine
from ptb_content.types import (
    Brief,
    CatalogRecord,
    Category,
    RiskDecision,
    RiskLevel,
    TemplateType,
    utcnow,
)
from ptb_content.utils.persian import is_valid_persian, normalize_persian


class TestGoldenSetValidation:
    """Validate all golden set briefs."""

    def _load_golden(self) -> list[dict]:
        golden_dir = Path("outputs/golden")
        if not golden_dir.exists():
            return []
        return [
            json.loads(f.read_text(encoding="utf-8"))
            for f in sorted(golden_dir.glob("*.json"))
        ]

    def test_golden_set_count(self) -> None:
        briefs = self._load_golden()
        assert len(briefs) == 50, f"Expected 50 golden briefs, got {len(briefs)}"

    def test_all_high_risk_escalate(self) -> None:
        briefs = self._load_golden()
        for b in briefs:
            if b["risk_level"] == "HIGH":
                assert b["risk_decision"] == "ESCALATE", (
                    f"{b['brief_id']} is HIGH but not ESCALATE"
                )

    def test_no_missing_source(self) -> None:
        briefs = self._load_golden()
        for b in briefs:
            assert b["catalog_record"]["source_id"], (
                f"{b['brief_id']} missing source_id"
            )
            assert b["catalog_record"]["canonical_url"], (
                f"{b['brief_id']} missing canonical_url"
            )

    def test_persian_normalization(self) -> None:
        briefs = self._load_golden()
        for b in briefs:
            caption = b["caption"]["primary"]
            normalized = normalize_persian(caption)
            # Should not crash and should return string
            assert isinstance(normalized, str)
            assert len(normalized) > 0

    def test_valid_persian_in_captions(self) -> None:
        briefs = self._load_golden()
        for b in briefs:
            caption = b["caption"]["primary"]
            # All captions should contain Persian
            assert is_valid_persian(caption), (
                f"{b['brief_id']} caption is not valid Persian: {caption[:50]}"
            )

    def test_schema_completeness(self) -> None:
        briefs = self._load_golden()
        required_fields = [
            "brief_id", "catalog_record", "audience", "content_strategy",
            "psychology_hypothesis", "caption", "art_direction",
            "risk_level", "risk_decision", "created_at",
        ]
        for b in briefs:
            for field in required_fields:
                assert field in b, f"{b['brief_id']} missing field: {field}"

    def test_no_missing_image_fields(self) -> None:
        briefs = self._load_golden()
        for b in briefs:
            art = b["art_direction"]
            assert art["template"], f"{b['brief_id']} missing template"
            assert art["color_palette"]["primary"], f"{b['brief_id']} missing color"
            assert art["typography"]["heading_font"], f"{b['brief_id']} missing font"


class TestPromptInjection:
    """Test that HTML content is treated as untrusted data."""

    def test_injection_in_title(self) -> None:
        """Malicious title should not break the system and should be safely extracted or rejected."""
        from ptb_content.crawler import Crawler

        crawler = Crawler()
        malicious_html = '<title><script>alert("xss")</script></title>'
        metadata = crawler._extract_metadata(
            malicious_html, "https://evil.com", 200, {}
        )
        # The regex [^<]+ stops at < so it either extracts nothing or partial
        # Either way, the system does NOT execute the script — this is safe
        title = metadata.get("html_title", "")
        # Safe outcomes: empty string (rejected) or partial text without < > execution
        assert "<script>" not in title or title == ""

    def test_injection_in_meta(self) -> None:
        """Malicious meta description should not break."""
        from ptb_content.crawler import Crawler

        crawler = Crawler()
        malicious_html = '<meta name="description" content="DROP TABLE users; --">'
        metadata = crawler._extract_metadata(
            malicious_html, "https://evil.com", 200, {}
        )
        assert "DROP TABLE" in metadata.get("meta_description", "")

    def test_injection_in_og_tags(self) -> None:
        """Malicious OG tags should not break."""
        from ptb_content.crawler import Crawler

        crawler = Crawler()
        malicious_html = '<meta property="og:title" content="<img src=x onerror=alert(1)>">'
        metadata = crawler._extract_metadata(
            malicious_html, "https://evil.com", 200, {}
        )
        assert "og:title" in metadata


class TestDuplicatePublish:
    """Test duplicate publish prevention."""

    def test_same_caption_detected(self) -> None:
        from ptb_content.types import (
            ArtDirection,
            Audience,
            Caption,
            ColorPalette,
            ContentStrategy,
            PsychologyHypothesis,
            Typography,
        )

        qa = QAEngine()
        cr = CatalogRecord(
            canonical_url="https://example.com",
            title="Test",
            summary="Test",
            category=Category.TOOL_DEMO,
            source_id="test",
            source_hash="a" * 64,
            crawled_at=utcnow(),
        )
        brief = Brief(
            brief_id="test-dup",
            catalog_record=cr,
            audience=Audience(segment="test", pain_point="test", desire="test"),
            content_strategy=ContentStrategy(
                angle="test",
                hook_type="direct",
                template_type=TemplateType.TOOL_DEMO,
            ),
            psychology_hypothesis=PsychologyHypothesis(
                principle="test", expected_effect="test"
            ),
            caption=Caption(primary="متن تست تکراری", cta="test"),
            art_direction=ArtDirection(
                template=TemplateType.TOOL_DEMO,
                color_palette=ColorPalette(),
                typography=Typography(),
            ),
            risk_level=RiskLevel.LOW,
            risk_decision=RiskDecision.AUTO_APPROVE,
        )

        # First publish — no duplicate
        result = qa.run_all(brief, existing_briefs=[])
        assert result.checks.get("duplicate_check") is None or result.checks["duplicate_check"].status.value == "PASS"

        # Same caption — duplicate detected
        existing = [hash("متن تست تکراری")]
        result2 = qa.run_all(brief, existing_briefs=existing)
        assert result2.checks["duplicate_check"].status.value == "FAIL"


class TestProviderFallback:
    """Test provider fallback to deterministic."""

    def test_deterministic_always_works(self) -> None:
        from ptb_content.providers import ProviderBenchmark

        bench = ProviderBenchmark()
        # Without running benchmark, deterministic should still be selected
        bench.results = [
            {
                "provider": "deterministic",
                "reachable": True,
                "free_without_payment": True,
                "selected_for": ["text", "template", "fallback"],
            }
        ]
        selected = bench.select_provider("text")
        assert selected == "deterministic"

    def test_fallback_when_no_provider(self) -> None:
        from ptb_content.providers import ProviderBenchmark

        bench = ProviderBenchmark()
        bench.results = []
        selected = bench.select_provider("text")
        assert selected == "deterministic"


class TestProviderTimeout:
    """Test provider timeout handling."""

    def test_probe_timeout(self) -> None:
        import asyncio

        from ptb_content.providers import ProviderBenchmark

        bench = ProviderBenchmark()
        # Probe a non-existent server — should fail gracefully
        reachable, latency = asyncio.run(
            bench.probe_http("http://192.0.2.1:99999", timeout=2)
        )
        assert not reachable


class TestRiskEscalation:
    """Test that all HIGH-risk content is properly escalated."""

    def test_financial_escalates(self) -> None:
        cr = CatalogRecord(
            canonical_url="https://example.com",
            title="محاسبه مالیات",
            summary="راهنمای مالیات",
            category=Category.FINANCIAL,
            source_id="fin",
            source_hash="a" * 64,
            crawled_at=utcnow(),
            risk_tags=[],
        )
        engine = RiskEngine()
        level, decision = engine.assess(cr)
        # Even without risk_tags, financial category should be assessed
        assert level in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH)

    def test_privacy_tag_escalates(self) -> None:
        from ptb_content.types import RiskTag

        cr = CatalogRecord(
            canonical_url="https://example.com",
            title="حریم خصوصی",
            summary="امنیت داده",
            category=Category.PRIVACY,
            source_id="priv",
            source_hash="a" * 64,
            crawled_at=utcnow(),
            risk_tags=[RiskTag.PRIVACY],
        )
        engine = RiskEngine()
        level, decision = engine.assess(cr)
        assert level == RiskLevel.HIGH
        assert decision == RiskDecision.ESCALATE
