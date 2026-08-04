"""Production HTML/CSS/SVG renderer for Persian social assets."""

from __future__ import annotations

import html
import json
from dataclasses import asdict
from pathlib import Path

from ..graphic_engineering import (
    analyze_png,
    build_copy_deck,
    validate_copy_deck,
    validate_visual_metrics,
)
from ..types import Brief
from ..utils.helpers import ensure_dir, project_root

SIZES = {
    "1080x1350": (1080, 1350),
    "1080x1080": (1080, 1080),
    "1080x1920": (1080, 1920),
}


def _document_visual() -> str:
    """Return deterministic inline vector material for document/PDF content."""
    return """
    <svg class="product-visual" viewBox="0 0 620 620" role="img"
         aria-label="نمایش گرافیکی چند سند و ابزارهای مدیریت PDF">
      <defs>
        <linearGradient id="panel" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stop-color="#ffffff"/>
          <stop offset="1" stop-color="#eef2ff"/>
        </linearGradient>
        <linearGradient id="pdf" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#ef4444"/>
          <stop offset="1" stop-color="#b91c1c"/>
        </linearGradient>
        <filter id="shadow" x="-30%" y="-30%" width="160%" height="180%">
          <feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#0f172a" flood-opacity=".18"/>
        </filter>
      </defs>
      <circle cx="310" cy="310" r="270" fill="#dbeafe" opacity=".72"/>
      <circle cx="470" cy="150" r="92" fill="#fef3c7" opacity=".92"/>
      <g filter="url(#shadow)">
        <rect x="78" y="88" width="466" height="420" rx="34" fill="url(#panel)"/>
        <rect x="78" y="88" width="466" height="64" rx="34" fill="#172554"/>
        <circle cx="120" cy="120" r="9" fill="#f59e0b"/>
        <circle cx="150" cy="120" r="9" fill="#60a5fa"/>
        <circle cx="180" cy="120" r="9" fill="#e2e8f0"/>
        <rect x="116" y="184" width="184" height="250" rx="24" fill="#ffffff" stroke="#c7d2fe" stroke-width="4"/>
        <path d="M258 184v58h42" fill="#eef2ff" stroke="#c7d2fe" stroke-width="4"/>
        <rect x="146" y="220" width="70" height="42" rx="10" fill="url(#pdf)"/>
        <text x="181" y="249" text-anchor="middle" font-size="22" font-weight="800" fill="#fff" direction="ltr">PDF</text>
        <rect x="146" y="292" width="118" height="13" rx="7" fill="#94a3b8"/>
        <rect x="146" y="324" width="126" height="13" rx="7" fill="#cbd5e1"/>
        <rect x="146" y="356" width="92" height="13" rx="7" fill="#cbd5e1"/>
        <g transform="translate(330 182)">
          <rect width="174" height="78" rx="19" fill="#eff6ff" stroke="#93c5fd" stroke-width="3"/>
          <circle cx="39" cy="39" r="22" fill="#2563eb"/>
          <path d="M30 39h18M39 30v18" stroke="#fff" stroke-width="5" stroke-linecap="round"/>
          <rect x="76" y="25" width="70" height="11" rx="6" fill="#1e3a8a"/>
          <rect x="76" y="46" width="48" height="9" rx="5" fill="#93c5fd"/>
        </g>
        <g transform="translate(330 280)">
          <rect width="174" height="78" rx="19" fill="#fffbeb" stroke="#fcd34d" stroke-width="3"/>
          <circle cx="39" cy="39" r="22" fill="#f59e0b"/>
          <path d="M28 39h22" stroke="#fff" stroke-width="5" stroke-linecap="round"/>
          <rect x="76" y="25" width="64" height="11" rx="6" fill="#92400e"/>
          <rect x="76" y="46" width="82" height="9" rx="5" fill="#fcd34d"/>
        </g>
        <g transform="translate(330 378)">
          <rect width="174" height="78" rx="19" fill="#f0fdf4" stroke="#86efac" stroke-width="3"/>
          <circle cx="39" cy="39" r="22" fill="#16a34a"/>
          <path d="M29 39l7 7 14-16" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
          <rect x="76" y="25" width="76" height="11" rx="6" fill="#166534"/>
          <rect x="76" y="46" width="55" height="9" rx="5" fill="#86efac"/>
        </g>
      </g>
      <g transform="translate(54 474) rotate(-9)" filter="url(#shadow)">
        <rect width="170" height="104" rx="22" fill="#2563eb"/>
        <path d="M35 52h100M85 28v48" stroke="#fff" stroke-width="8" stroke-linecap="round" opacity=".95"/>
      </g>
      <g transform="translate(398 490) rotate(8)" filter="url(#shadow)">
        <rect width="164" height="96" rx="22" fill="#f59e0b"/>
        <path d="M36 48h92" stroke="#fff" stroke-width="8" stroke-linecap="round"/>
      </g>
    </svg>
    """


def _format_name(width: int, height: int) -> str:
    if height >= 1700:
        return "story"
    if width == height:
        return "square"
    return "feed"


def render_html(brief: Brief, width: int, height: int) -> str:
    """Generate one self-contained, platform-specific RTL composition."""
    deck = build_copy_deck(brief.catalog_record.title, brief.catalog_record.category)
    defects = validate_copy_deck(deck)
    if defects:
        raise ValueError(f"CopyDeck rejected: {'; '.join(defects)}")

    fmt = _format_name(width, height)
    headline = html.escape(deck.headline).replace("\n", "<br>")
    supporting = html.escape(deck.supporting_text)
    cta = html.escape(deck.cta)
    label = html.escape(deck.category_label)
    visual = _document_visual()

    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width={width}, initial-scale=1.0">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
html, body {{ width: {width}px; height: {height}px; overflow: hidden; }}
body {{
  direction: rtl;
  font-family: "Noto Sans Arabic", "DejaVu Sans", sans-serif;
  background: #eaf1ff;
  color: #172554;
  text-rendering: geometricPrecision;
  -webkit-font-smoothing: antialiased;
}}
.canvas {{
  position: relative;
  width: 100%; height: 100%; overflow: hidden;
  background:
    radial-gradient(circle at 16% 12%, rgba(245,158,11,.24), transparent 23%),
    radial-gradient(circle at 91% 82%, rgba(37,99,235,.22), transparent 31%),
    linear-gradient(145deg, #f8fbff 0%, #e7efff 47%, #dce8ff 100%);
}}
.grid {{
  position: absolute; inset: 0; opacity: .12;
  background-image: linear-gradient(#2563eb 1px, transparent 1px), linear-gradient(90deg,#2563eb 1px,transparent 1px);
  background-size: 42px 42px;
  mask-image: linear-gradient(to bottom, black, transparent 76%);
}}
.shell {{ position: absolute; inset: 0; padding: 72px 78px 64px; display: grid; z-index: 2; }}
.brand {{ display:flex; align-items:center; gap:16px; font-size:25px; font-weight:800; color:#1e3a8a; }}
.brand-mark {{ width:45px; height:45px; border-radius:14px; display:grid; place-items:center; background:#2563eb; color:white; box-shadow:0 12px 24px rgba(37,99,235,.24); }}
.badge {{ display:inline-flex; align-items:center; width:max-content; padding:10px 19px; border:2px solid rgba(37,99,235,.18); background:rgba(255,255,255,.82); border-radius:999px; font-size:21px; font-weight:700; color:#1d4ed8; }}
.copy {{ display:flex; flex-direction:column; align-items:flex-start; }}
.headline {{ font-size:72px; line-height:1.32; letter-spacing:-1.7px; font-weight:900; color:#172554; }}
.supporting {{ max-width:560px; font-size:30px; line-height:1.75; font-weight:500; color:#475569; }}
.cta {{ display:inline-flex; align-items:center; gap:14px; background:#2563eb; color:#fff; padding:20px 31px; border-radius:20px; font-size:25px; font-weight:800; box-shadow:0 18px 38px rgba(37,99,235,.28); }}
.cta-arrow {{ font-size:30px; transform:translateY(-1px); }}
.visual-wrap {{ position:relative; display:grid; place-items:center; }}
.product-visual {{ width:100%; height:auto; overflow:visible; }}
.microcopy {{ font-size:19px; color:#64748b; font-weight:600; }}
.feed .shell {{ grid-template-columns: 1.05fr .95fr; grid-template-rows:auto 1fr auto; column-gap:36px; }}
.feed .brand {{ grid-column:1 / 3; }}
.feed .copy {{ grid-column:2; grid-row:2; justify-content:center; gap:26px; }}
.feed .visual-wrap {{ grid-column:1; grid-row:2; padding-top:24px; }}
.feed .microcopy {{ grid-column:1 / 3; align-self:end; }}
.feed .product-visual {{ width:520px; }}
.square .shell {{ padding:58px 62px 52px; grid-template-columns:1fr 1fr; grid-template-rows:auto 1fr auto; column-gap:20px; }}
.square .brand {{ grid-column:1 / 3; }}
.square .copy {{ grid-column:2; grid-row:2; justify-content:center; gap:20px; }}
.square .visual-wrap {{ grid-column:1; grid-row:2; }}
.square .microcopy {{ grid-column:1 / 3; }}
.square .headline {{ font-size:57px; }}
.square .supporting {{ font-size:25px; line-height:1.65; }}
.square .cta {{ font-size:22px; padding:16px 24px; }}
.square .product-visual {{ width:450px; }}
.story .shell {{ padding:88px 72px 110px; grid-template-rows:auto auto 1fr auto auto; }}
.story .brand {{ grid-row:1; }}
.story .copy {{ grid-row:2; gap:24px; padding-top:86px; }}
.story .visual-wrap {{ grid-row:3; min-height:760px; }}
.story .cta {{ grid-row:4; justify-self:stretch; justify-content:center; font-size:29px; padding:24px 34px; }}
.story .microcopy {{ grid-row:5; padding-top:28px; text-align:center; }}
.story .headline {{ font-size:78px; }}
.story .supporting {{ max-width:850px; font-size:32px; }}
.story .product-visual {{ width:720px; }}
</style>
</head>
<body>
<main class="canvas {fmt}" aria-label="دارایی گرافیکی پرشین‌تولباکس">
  <div class="grid"></div>
  <section class="shell">
    <div class="brand"><span class="brand-mark">پ</span><span>پرشین‌تولباکس</span></div>
    <div class="copy">
      <div class="badge">{label}</div>
      <h1 class="headline">{headline}</h1>
      <p class="supporting">{supporting}</p>
      {"" if fmt == "story" else f'<div class="cta">{cta}<span class="cta-arrow">←</span></div>'}
    </div>
    <div class="visual-wrap">{visual}</div>
    {f'<div class="cta">{cta}<span class="cta-arrow">←</span></div>' if fmt == "story" else ""}
    <div class="microcopy">persiantoolbox.ir · ابزار مناسب برای کار مشخص</div>
  </section>
</main>
</body>
</html>"""


class Renderer:
    """Fail-closed renderer with font and pixel-level quality validation."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or project_root() / "outputs"

    def render_html(self, brief: Brief, width: int, height: int) -> str:
        return render_html(brief, width, height)

    async def render_to_png(
        self, brief: Brief, size_key: str, output_path: Path | None = None
    ) -> Path:
        if size_key not in SIZES:
            raise ValueError(f"Unsupported render size: {size_key}")
        width, height = SIZES[size_key]
        html_content = self.render_html(brief, width, height)
        if output_path is None:
            output_path = ensure_dir(self.output_dir / brief.brief_id) / f"feed-{size_key}.png"
        else:
            ensure_dir(output_path.parent)

        from playwright.async_api import async_playwright

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
            )
            try:
                page = await browser.new_page(
                    viewport={"width": width, "height": height}, device_scale_factor=1
                )
                await page.set_content(html_content, wait_until="domcontentloaded")
                await page.evaluate("document.fonts.ready.then(() => true)")
                font_ready = await page.evaluate(
                    "document.fonts.check('32px \\\"Noto Sans Arabic\\\"')"
                )
                if not font_ready:
                    raise RuntimeError(
                        "Required font 'Noto Sans Arabic' is unavailable; rendering blocked"
                    )
                await page.screenshot(path=str(output_path), full_page=False, animations="disabled")
            finally:
                await browser.close()

        metrics = analyze_png(output_path)
        defects = validate_visual_metrics(metrics, (width, height))
        metrics_path = output_path.with_suffix(".metrics.json")
        metrics_path.write_text(
            json.dumps(
                {"size_key": size_key, "metrics": asdict(metrics), "defects": defects},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        if defects:
            output_path.unlink(missing_ok=True)
            raise RuntimeError(
                f"Visual QA failed for {brief.brief_id}/{size_key}: {'; '.join(defects)}"
            )
        return output_path

    async def render_all_sizes(self, brief: Brief) -> dict[str, Path]:
        results: dict[str, Path] = {}
        for size_key in SIZES:
            results[size_key] = await self.render_to_png(brief, size_key)
        self.build_contact_sheet(brief.brief_id, results)
        return results

    def build_contact_sheet(self, brief_id: str, paths: dict[str, Path]) -> Path:
        """Build one human-review proof containing all three platform assets."""
        from PIL import Image, ImageDraw

        background = Image.new("RGB", (1800, 1150), "#e2e8f0")
        draw = ImageDraw.Draw(background)
        placements = {
            "1080x1350": (45, 110, 540, 675),
            "1080x1080": (635, 110, 540, 540),
            "1080x1920": (1225, 110, 500, 890),
        }
        for key, (x, y, max_w, max_h) in placements.items():
            image = Image.open(paths[key]).convert("RGB")
            image.thumbnail((max_w, max_h))
            panel = Image.new("RGB", (max_w + 20, max_h + 20), "white")
            panel.paste(image, ((panel.width - image.width) // 2, 10))
            background.paste(panel, (x - 10, y - 10))
            draw.text((x, 55), key, fill="#172554")
        draw.text((45, 20), f"PersianToolbox visual proof · {brief_id}", fill="#172554")
        proof_dir = ensure_dir(self.output_dir / "review")
        proof_path = proof_dir / f"{brief_id}-contact-sheet.png"
        background.save(proof_path, optimize=False)
        return proof_path

    def render_preview_html(self, briefs: list[Brief]) -> str:
        cards = "".join(
            f"<article><h2>{html.escape(build_copy_deck(b.catalog_record.title, b.catalog_record.category).short_title)}</h2>"
            f"<p>{html.escape(b.caption.primary)}</p></article>"
            for b in briefs
        )
        return (
            "<!DOCTYPE html><html lang='fa' dir='rtl'><meta charset='UTF-8'>"
            "<style>body{font-family:'Noto Sans Arabic',sans-serif;background:#eef2ff;padding:32px}"
            "article{background:white;padding:24px;border-radius:18px;margin:18px}</style>"
            f"<body>{cards}</body></html>"
        )
