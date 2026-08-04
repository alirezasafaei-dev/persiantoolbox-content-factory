"""Pixel-level visual quality checks for rendered social assets."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat

EXPECTED_SIZES: dict[str, tuple[int, int]] = {
    "1080x1350": (1080, 1350),
    "1080x1080": (1080, 1080),
    "1080x1920": (1080, 1920),
}


@dataclass(frozen=True)
class VisualMetrics:
    """Objective metrics used to reject blank or visually broken renders."""

    width: int
    height: int
    entropy: float
    near_white_ratio: float
    dominant_color_ratio: float
    edge_density: float
    foreground_coverage: float
    color_stddev: float
    unique_palette_colors: int

    def to_dict(self) -> dict[str, float | int]:
        return asdict(self)


@dataclass(frozen=True)
class VisualAudit:
    path: str
    passed: bool
    metrics: VisualMetrics
    issues: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "passed": self.passed,
            "metrics": self.metrics.to_dict(),
            "issues": list(self.issues),
        }


def _entropy(image: Image.Image) -> float:
    histogram = image.convert("L").histogram()
    total = sum(histogram)
    if not total:
        return 0.0
    result = 0.0
    for count in histogram:
        if count:
            probability = count / total
            result -= probability * math.log2(probability)
    return result


def analyze_png(path: Path, expected_size: tuple[int, int]) -> VisualAudit:
    """Analyze a PNG and fail obvious blank, sparse or low-complexity layouts."""
    image = Image.open(path).convert("RGB")
    width, height = image.size
    pixels = list(image.getdata())
    total = max(len(pixels), 1)

    near_white = sum(1 for r, g, b in pixels if r >= 245 and g >= 245 and b >= 245) / total

    quantized = image.quantize(colors=64)
    color_counts = quantized.getcolors(maxcolors=64) or []
    dominant = max((count for count, _ in color_counts), default=total) / total
    unique_colors = len(color_counts)

    edges = image.convert("L").filter(ImageFilter.FIND_EDGES)
    edge_histogram = edges.histogram()
    edge_pixels = sum(edge_histogram[26:])
    edge_density = edge_pixels / total

    corner = image.resize((1, 1)).getpixel((0, 0))
    threshold = 24
    foreground = sum(
        1
        for r, g, b in pixels
        if abs(r - corner[0]) + abs(g - corner[1]) + abs(b - corner[2]) > threshold
    )
    foreground_coverage = foreground / total

    stat = ImageStat.Stat(image)
    color_stddev = sum(stat.stddev) / 3
    metrics = VisualMetrics(
        width=width,
        height=height,
        entropy=_entropy(image),
        near_white_ratio=near_white,
        dominant_color_ratio=dominant,
        edge_density=edge_density,
        foreground_coverage=foreground_coverage,
        color_stddev=color_stddev,
        unique_palette_colors=unique_colors,
    )

    issues: list[str] = []
    if (width, height) != expected_size:
        issues.append(f"wrong dimensions: {(width, height)} != {expected_size}")
    if near_white > 0.92:
        issues.append(f"canvas is mostly blank/white: {near_white:.1%}")
    if dominant > 0.90:
        issues.append(f"single color dominates the canvas: {dominant:.1%}")
    if metrics.entropy < 3.4:
        issues.append(f"visual entropy is too low: {metrics.entropy:.2f}")
    if edge_density < 0.012:
        issues.append(f"insufficient visual structure: edge density {edge_density:.3f}")
    if foreground_coverage < 0.16:
        issues.append(f"foreground coverage is too low: {foreground_coverage:.1%}")
    if color_stddev < 18:
        issues.append(f"color contrast is too low: stddev {color_stddev:.1f}")
    if unique_colors < 12:
        issues.append(f"palette complexity is too low: {unique_colors} colors")

    return VisualAudit(
        path=str(path),
        passed=not issues,
        metrics=metrics,
        issues=tuple(issues),
    )


def audit_render_set(brief_id: str, outputs_dir: Path) -> dict[str, VisualAudit]:
    """Audit all mandatory social sizes for one brief."""
    brief_dir = outputs_dir / brief_id
    audits: dict[str, VisualAudit] = {}
    for size_key, expected_size in EXPECTED_SIZES.items():
        path = brief_dir / f"feed-{size_key}.png"
        if not path.exists():
            empty_metrics = VisualMetrics(0, 0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0)
            audits[size_key] = VisualAudit(
                path=str(path),
                passed=False,
                metrics=empty_metrics,
                issues=("required PNG is missing",),
            )
            continue
        audits[size_key] = analyze_png(path, expected_size)
    return audits
