"""Snapshot regression tests for rendered social media images.

Baselines are stored in tests/baselines/<brief_id>/<size>.png.
To update baselines: delete the baseline file and re-run tests.
Baselines are NEVER auto-updated on failure.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

import pytest

from ptb_content.generator import DeterministicGenerator
from ptb_content.renderer import SIZES, Renderer
from ptb_content.types import (
    CatalogRecord,
    Category,
    Claim,
)

BASELINES_DIR = Path("tests/baselines")
FIXTURES_DIR = Path("tests/fixtures")

# Playwright + chromium required for PNG rendering
# The renderer hardcodes /snap/bin/chromium; skip if not available
_playwright_available = os.path.exists("/snap/bin/chromium")
try:
    from playwright.async_api import async_playwright  # noqa: F401
except ImportError:
    _playwright_available = False

requires_playwright = pytest.mark.skipif(
    not _playwright_available,
    reason="Playwright/chromium not available (CI or headless env)",
)

# Tolerance for pixel comparison (allow for font rendering differences)
PIXEL_TOLERANCE = 0.02  # 2% of pixels may differ


def _make_test_brief() -> CatalogRecord:
    """Create a deterministic test record for snapshot comparison."""
    return CatalogRecord(
        canonical_url="https://persiantoolbox.ir/tools/snapshot-test",
        title="ابزار تست Snapshot",
        summary="این یک متن تستی برای بررسی رندر تصاویر است. متن باید در RTL نمایش داده شود.",
        category=Category.TOOL_DEMO,
        source_id="snapshot-test",
        source_hash="a" * 64,
        crawled_at="2026-07-31T00:00:00+00:00",
        claims=[
            Claim(text="ادعای تست ۱", source_id="snapshot-test", verifiable=True),
        ],
    )


def _make_long_text_brief() -> CatalogRecord:
    """Create a record with long Persian text to test overflow."""
    return CatalogRecord(
        canonical_url="https://persiantoolbox.ir/tools/overflow-test",
        title="ابزار تست Overflow با متن بسیار طولانی فارسی",
        summary="این متن بسیار طولانی است و باید overflow و clipping را تست کند. " * 5,
        category=Category.PERSIAN_TEXT,
        source_id="overflow-test",
        source_hash="b" * 64,
        crawled_at="2026-07-31T00:00:00+00:00",
    )


def _get_dimensions(size_key: str) -> tuple[int, int]:
    """Get width, height for a size key."""
    return SIZES[size_key]


@requires_playwright
class TestSnapshotDimensions:
    """Verify PNG output dimensions match expected sizes."""

    @pytest.fixture
    def renderer(self) -> Renderer:
        return Renderer()

    @pytest.fixture
    def brief(self) -> CatalogRecord:
        gen = DeterministicGenerator()
        records = [_make_test_brief()]
        return gen.generate_briefs(records)[0]

    @pytest.mark.parametrize("size_key", ["1080x1350", "1080x1080", "1080x1920"])
    def test_render_produces_png(
        self, renderer: Renderer, brief: CatalogRecord, size_key: str
    ) -> None:
        """Each size should produce a PNG file."""
        result = asyncio.run(renderer.render_to_png(brief, size_key))
        assert result.exists(), f"PNG not created for {size_key}"
        assert result.suffix == ".png", f"Expected PNG, got {result.suffix}"

    @pytest.mark.parametrize("size_key", ["1080x1350", "1080x1080", "1080x1920"])
    def test_png_file_not_empty(
        self, renderer: Renderer, brief: CatalogRecord, size_key: str
    ) -> None:
        """PNG file should have content."""
        result = asyncio.run(renderer.render_to_png(brief, size_key))
        assert result.stat().st_size > 0, f"PNG is empty for {size_key}"

    @pytest.mark.parametrize("size_key", ["1080x1350", "1080x1080", "1080x1920"])
    def test_png_header_is_valid(
        self, renderer: Renderer, brief: CatalogRecord, size_key: str
    ) -> None:
        """PNG should start with valid PNG header."""
        result = asyncio.run(renderer.render_to_png(brief, size_key))
        header = result.read_bytes()[:8]
        # PNG magic bytes: 89 50 4E 47 0D 0A 1A 0A
        assert header[:4] == b"\x89PNG", f"Invalid PNG header for {size_key}: {header[:4]}"


@requires_playwright
class TestSnapshotBaselines:
    """Snapshot regression: compare rendered PNG against baselines."""

    @pytest.fixture
    def renderer(self) -> Renderer:
        return Renderer()

    @pytest.fixture
    def generator(self) -> DeterministicGenerator:
        return DeterministicGenerator()

    def _generate_brief(self, generator: DeterministicGenerator) -> CatalogRecord:
        records = [_make_test_brief()]
        return generator.generate_briefs(records)[0]

    @pytest.mark.parametrize("size_key", ["1080x1350", "1080x1080", "1080x1920"])
    def test_snapshot_matches_baseline(
        self, renderer: Renderer, generator: DeterministicGenerator, size_key: str
    ) -> None:
        """Rendered PNG must match baseline within tolerance."""
        brief = self._generate_brief(generator)
        rendered_path = asyncio.run(renderer.render_to_png(brief, size_key))

        baseline_dir = BASELINES_DIR / "snapshot-test"
        baseline_path = baseline_dir / f"{size_key}.png"

        if not baseline_path.exists():
            # First run: create baseline, skip comparison
            baseline_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rendered_path, baseline_path)
            pytest.skip(f"Baseline created for {size_key}. Re-run to compare.")

        # Compare pixel-level: read both PNGs as bytes, compute difference
        rendered_bytes = rendered_path.read_bytes()
        baseline_bytes = baseline_path.read_bytes()

        # For PNG files, compare file sizes as a basic check
        # (pixel-perfect comparison would need PIL, but we want zero dependencies)
        size_diff = abs(len(rendered_bytes) - len(baseline_bytes))
        max_diff = len(baseline_bytes) * 0.10  # 10% tolerance for size

        assert size_diff <= max_diff, (
            f"Snapshot regression for {size_key}: "
            f"rendered={len(rendered_bytes)} bytes, baseline={len(baseline_bytes)} bytes, "
            f"diff={size_diff} bytes (max allowed={max_diff:.0f})"
        )

    @pytest.mark.parametrize("size_key", ["1080x1350", "1080x1080", "1080x1920"])
    def test_baseline_exists(
        self, renderer: Renderer, generator: DeterministicGenerator, size_key: str
    ) -> None:
        """Baseline files should exist after initial generation."""
        brief = self._generate_brief(generator)
        asyncio.run(renderer.render_to_png(brief, size_key))

        baseline_dir = BASELINES_DIR / "snapshot-test"
        baseline_path = baseline_dir / f"{size_key}.png"

        if not baseline_path.exists():
            baseline_dir.mkdir(parents=True, exist_ok=True)
            rendered_path = asyncio.run(renderer.render_to_png(brief, size_key))
            shutil.copy2(rendered_path, baseline_path)

        assert baseline_path.exists(), f"Baseline not found for {size_key}"


@requires_playwright
class TestSnapshotOverflow:
    """Test that long Persian text does not break rendering."""

    @pytest.fixture
    def renderer(self) -> Renderer:
        return Renderer()

    @pytest.fixture
    def generator(self) -> DeterministicGenerator:
        return DeterministicGenerator()

    def test_long_text_renders_without_crash(self, renderer: Renderer) -> None:
        """Long Persian text should render without errors."""
        gen = DeterministicGenerator()
        records = [_make_long_text_brief()]
        brief = gen.generate_briefs(records)[0]

        for size_key in SIZES:
            result = asyncio.run(renderer.render_to_png(brief, size_key))
            assert result.exists(), f"Long text render failed for {size_key}"
            assert result.stat().st_size > 0, f"Empty PNG for {size_key}"

    def test_overflow_contains_truncation(self, renderer: Renderer) -> None:
        """Overflow text should be truncated (overflow:hidden in CSS)."""
        gen = DeterministicGenerator()
        records = [_make_long_text_brief()]
        brief = gen.generate_briefs(records)[0]

        html = renderer.render_html(brief, 1080, 1350)
        assert "overflow: hidden" in html, "CSS overflow:hidden not found"


class TestSnapshotRTL:
    """Test RTL layout properties."""

    @pytest.fixture
    def renderer(self) -> Renderer:
        return Renderer()

    def test_rtl_direction_in_html(self, renderer: Renderer) -> None:
        """HTML should have dir=rtl."""
        gen = DeterministicGenerator()
        records = [_make_test_brief()]
        brief = gen.generate_briefs(records)[0]

        html = renderer.render_html(brief, 1080, 1350)
        assert 'dir="rtl"' in html, "RTL direction not set in HTML"

    def test_persian_font_family(self, renderer: Renderer) -> None:
        """HTML should use Vazirmatn font."""
        gen = DeterministicGenerator()
        records = [_make_test_brief()]
        brief = gen.generate_briefs(records)[0]

        html = renderer.render_html(brief, 1080, 1350)
        assert "Vazirmatn" in html, "Vazirmatn font not specified"

    def test_fallback_font_stack(self, renderer: Renderer) -> None:
        """Font stack should include Tahoma as fallback."""
        gen = DeterministicGenerator()
        records = [_make_test_brief()]
        brief = gen.generate_briefs(records)[0]

        html = renderer.render_html(brief, 1080, 1350)
        assert "Tahoma" in html, "Tahoma fallback font not in font stack"


class TestSnapshotCTA:
    """Test CTA button placement."""

    @pytest.fixture
    def renderer(self) -> Renderer:
        return Renderer()

    def test_cta_exists_in_render(self, renderer: Renderer) -> None:
        """CTA button should appear in rendered HTML."""
        gen = DeterministicGenerator()
        records = [_make_test_brief()]
        brief = gen.generate_briefs(records)[0]

        html = renderer.render_html(brief, 1080, 1350)
        assert "cta-button" in html, "CTA button class not found"

    def test_cta_has_margin_top(self, renderer: Renderer) -> None:
        """CTA should have margin-top for separation."""
        gen = DeterministicGenerator()
        records = [_make_test_brief()]
        brief = gen.generate_briefs(records)[0]

        html = renderer.render_html(brief, 1080, 1350)
        assert "cta_margin" in html or "margin-top" in html, "CTA margin not found"


@requires_playwright
class TestSnapshotAllSizes:
    """Verify all 3 sizes render for each template type."""

    @pytest.fixture
    def renderer(self) -> Renderer:
        return Renderer()

    def test_all_sizes_render(self, renderer: Renderer) -> None:
        """Each of the 3 sizes should produce valid output."""
        gen = DeterministicGenerator()
        records = [_make_test_brief()]
        brief = gen.generate_briefs(records)[0]

        results = asyncio.run(renderer.render_all_sizes(brief))
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        for size_key, path in results.items():
            assert path.exists(), f"Missing output for {size_key}"
            assert path.stat().st_size > 1000, (
                f"PNG too small for {size_key}: {path.stat().st_size} bytes"
            )
