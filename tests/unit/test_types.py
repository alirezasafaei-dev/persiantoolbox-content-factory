"""Unit tests for core types."""

from ptb_content.types import (
    CatalogRecord,
    Category,
    Claim,
    ClaimVerdict,
    RiskTag,
    generate_hash,
    generate_id,
    utcnow,
)


class TestGenerateId:
    def test_has_prefix(self) -> None:
        id_ = generate_id("brief")
        assert id_.startswith("brief-")
        assert len(id_) > 7

    def test_no_prefix(self) -> None:
        id_ = generate_id()
        assert len(id_) == 12

    def test_unique(self) -> None:
        ids = {generate_id() for _ in range(100)}
        assert len(ids) == 100


class TestGenerateHash:
    def test_deterministic(self) -> None:
        h1 = generate_hash("hello")
        h2 = generate_hash("hello")
        assert h1 == h2

    def test_different_inputs(self) -> None:
        h1 = generate_hash("hello")
        h2 = generate_hash("world")
        assert h1 != h2

    def test_length(self) -> None:
        h = generate_hash("test")
        assert len(h) == 64  # SHA-256 hex


class TestUtcnow:
    def test_returns_string(self) -> None:
        result = utcnow()
        assert isinstance(result, str)
        assert "T" in result


class TestCatalogRecord:
    def test_creation(self) -> None:
        record = CatalogRecord(
            canonical_url="https://example.com",
            title="Test Tool",
            summary="A test tool",
            category=Category.TOOL_DEMO,
            source_id="test-tool",
            source_hash="a" * 64,
            crawled_at=utcnow(),
        )
        assert record.title == "Test Tool"
        assert record.category == Category.TOOL_DEMO

    def test_to_dict(self) -> None:
        record = CatalogRecord(
            canonical_url="https://example.com",
            title="Test",
            summary="Summary",
            category=Category.TOOL_DEMO,
            source_id="test",
            source_hash="a" * 64,
            crawled_at=utcnow(),
        )
        d = record.to_dict()
        assert d["category"] == "tool-demo"
        assert "claims" in d
        assert "risk_tags" in d

    def test_from_dict_roundtrip(self) -> None:
        record = CatalogRecord(
            canonical_url="https://example.com",
            title="Test",
            summary="Summary",
            category=Category.TOOL_DEMO,
            source_id="test",
            source_hash="a" * 64,
            crawled_at=utcnow(),
            claims=[Claim(text="claim", source_id="test", verifiable=True)],
            risk_tags=[RiskTag.FINANCIAL],
        )
        d = record.to_dict()
        restored = CatalogRecord.from_dict(d)
        assert restored.title == record.title
        assert restored.category == record.category
        assert len(restored.claims) == 1
        assert restored.risk_tags == [RiskTag.FINANCIAL]


class TestClaim:
    def test_creation(self) -> None:
        claim = Claim(text="test claim", source_id="src", verifiable=True)
        assert claim.text == "test claim"
        assert claim.verdict == ClaimVerdict.UNVERIFIED

    def test_to_dict(self) -> None:
        claim = Claim(text="test", source_id="s", verifiable=False, confidence=0.8)
        d = claim.to_dict()
        assert d["confidence"] == 0.8
        assert d["verifiable"] is False
