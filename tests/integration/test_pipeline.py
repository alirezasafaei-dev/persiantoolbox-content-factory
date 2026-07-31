"""Integration tests for the content generation pipeline."""

import json

from ptb_content.generator import DeterministicGenerator
from ptb_content.qa import QAEngine
from ptb_content.risk import RiskEngine
from ptb_content.types import (
    CatalogRecord,
    Category,
    Claim,
    RiskLevel,
    utcnow,
)


def _make_records(count: int = 5) -> list[CatalogRecord]:
    """Create sample catalog records."""
    records = []
    categories = [Category.TOOL_DEMO, Category.PDF_TUTORIAL, Category.PERSIAN_TEXT]
    for i in range(count):
        records.append(
            CatalogRecord(
                canonical_url=f"https://persiantoolbox.ir/tools/tool-{i}",
                title=f"ابزار شماره {i + 1}",
                summary=f"توضیحات ابزار شماره {i + 1} برای تست",
                category=categories[i % len(categories)],
                source_id=f"tool-{i + 1}",
                source_hash="a" * 64,
                crawled_at=utcnow(),
                claims=[
                    Claim(text=f"ادعای تست {i + 1}", source_id=f"tool-{i + 1}", verifiable=True)
                ],
            )
        )
    return records


class TestFullPipeline:
    def test_generate_briefs(self) -> None:
        records = _make_records(3)
        gen = DeterministicGenerator()
        briefs = gen.generate_briefs(records)

        assert len(briefs) == 3
        for brief in briefs:
            assert brief.brief_id.startswith("brief-")
            assert brief.catalog_record.title
            assert brief.caption.primary
            assert brief.risk_level

    def test_qa_on_generated_briefs(self) -> None:
        records = _make_records(2)
        gen = DeterministicGenerator()
        briefs = gen.generate_briefs(records)

        qa_engine = QAEngine()
        for brief in briefs:
            result = qa_engine.run_all(brief)
            assert result.decision.value in ("PASS", "FAIL", "ESCALATE")
            assert len(result.checks) > 0

    def test_risk_engine_on_records(self) -> None:
        records = _make_records(3)
        risk_engine = RiskEngine()

        for record in records:
            level, decision = risk_engine.assess(record)
            assert level in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH)

    def test_serialization_roundtrip(self) -> None:
        records = _make_records(1)
        gen = DeterministicGenerator()
        brief = gen.generate_briefs(records)[0]

        # Serialize
        d = brief.to_dict()
        json_str = json.dumps(d, ensure_ascii=False)

        # Deserialize
        parsed = json.loads(json_str)
        assert parsed["brief_id"] == brief.brief_id
        assert parsed["catalog_record"]["title"] == brief.catalog_record.title
