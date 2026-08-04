"""Production-grade deterministic HTML/CSS/SVG graphics engine."""

from __future__ import annotations

import html
import json
from dataclasses import dataclass
from pathlib import Path

from ..content_shaping import VisualCopy, build_visual_copy
from ..types import Brief
from ..utils.helpers import ensure_dir, project_root
from ..visual_qa import EXPECTED_SIZES, analyze_png

SIZES = EXPECTED_SIZES


class RenderError(RuntimeError):
    """Raised when a social asset cannot be rendered safely."""


@dataclass(frozen=True)
class RenderProfile:
    width: int
    height: int
    canvas_padding: int
    headline_size: int
    body_size: int
    eyebrow_size: int
    card_width: int
    card_height: int
    visual_scale: float
    stack_layout: bool


PROFILES: dict[str, RenderProfile] = {
    "1080x1350": RenderProfile(1080, 1350, 72, 78, 31, 24, 390, 520, 1.0, False),
    "1080x1080": RenderProfile(1080, 1080, 62, 67, 28, 22, 350, 430, 0.88, False),
    "1080x1920": RenderProfile(1080, 1920, 76, 86, 34, 25, 480, 620, 1.08, True),
}


def _safe(value: str) -> str:
    return html.escape(value, quote=True)


def _multiline(value: str) -> str:
    return "<br>".join(_safe(part) for part in value.splitlines())


def _feature_chips(copy: VisualCopy) -> str:
    return "".join(
        f'<span class="feature-chip" data-fit>{_safe(label)}</span>'
        for label in copy.feature_labels
    )


def _pdf_art() -> str:
    return """
    <div class="art-stage art-pdf" aria-hidden="true">
      <div class="halo halo-one"></div>
      <div class="halo halo-two"></div>
      <div class="document document-back">
        <div class="doc-top"><span class="pdf-pill">PDF</span><span class="doc-dot"></span></div>
        <div class="doc-line wide"></div><div class="doc-line"></div><div class="doc-line short"></div>
      </div>
      <div class="document document-middle">
        <div class="doc-top"><span class="pdf-pill">PDF</span><span class="doc-dot"></span></div>
        <div class="doc-line wide"></div><div class="doc-line"></div><div class="doc-line short"></div>
      </div>
      <div class="document document-front">
        <div class="doc-fold"></div>
        <div class="doc-top"><span class="pdf-pill">PDF</span><span class="doc-dot"></span></div>
        <div class="doc-title">پرونده اداری</div>
        <div class="doc-line wide"></div><div class="doc-line"></div><div class="doc-line short"></div>
        <div class="operation-row">
          <span class="op-icon">↔</span><span class="op-icon">✂</span><span class="op-icon">↓</span>
        </div>
      </div>
      <div class="floating-badge badge-merge">ادغام</div>
      <div class="floating-badge badge-compress">فشرده‌سازی</div>
      <svg class="connector" viewBox="0 0 220 160" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M16 127C70 45 132 35 204 27" stroke="rgba(255,255,255,.65)" stroke-width="4" stroke-linecap="round" stroke-dasharray="8 12"/>
        <path d="M188 18L207 27L193 43" stroke="rgba(255,255,255,.8)" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </div>
    """


def _writing_art() -> str:
    return """
    <div class="art-stage art-writing" aria-hidden="true">
      <div class="halo halo-one"></div><div class="halo halo-two"></div>
      <div class="editor-window">
        <div class="window-bar"><span></span><span></span><span></span></div>
        <div class="editor-toolbar"><b>ب</b><i>ک</i><span>¶</span><span class="toolbar-pill">فا</span></div>
        <div class="editor-paper">
          <div class="paper-title">نامه اداری</div>
          <div class="paper-line wide"></div><div class="paper-line"></div>
          <div class="paper-line medium"></div><div class="paper-line short"></div>
          <div class="cursor"></div>
        </div>
      </div>
      <div class="floating-badge badge-merge">ویرایش متن</div>
      <div class="floating-badge badge-compress">نگارش فارسی</div>
    </div>
    """


def _office_art() -> str:
    return """
    <div class="art-stage art-office" aria-hidden="true">
      <div class="halo halo-one"></div><div class="halo halo-two"></div>
      <div class="folder-shape"><div class="folder-tab"></div></div>
      <div class="office-card card-one"><span class="office-icon">✓</span><div><b>فایل کاری</b><small>آماده‌سازی سند</small></div></div>
      <div class="office-card card-two"><span class="office-icon">Aa</span><div><b>نامه رسمی</b><small>متن اداری</small></div></div>
      <div class="office-card card-three"><span class="office-icon">▤</span><div><b>رزومه</b><small>مدارک استخدامی</small></div></div>
    </div>
    """


def _toolbox_art() -> str:
    return """
    <div class="art-stage art-toolbox" aria-hidden="true">
      <div class="halo halo-one"></div><div class="halo halo-two"></div>
      <div class="toolbox-body"><div class="toolbox-handle"></div><div class="toolbox-lock"></div></div>
      <div class="tool-card tool-one">Aa</div><div class="tool-card tool-two">PDF</div><div class="tool-card tool-three">✓</div>
    </div>
    """


def _visual_art(motif: str) -> str:
    return {
        "pdf": _pdf_art,
        "writing": _writing_art,
        "office": _office_art,
        "toolbox": _toolbox_art,
    }.get(motif, _toolbox_art)()


class Renderer:
    """Render polished social media assets with deterministic browser output."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or project_root() / "outputs"

    def render_html(self, brief: Brief, width: int, height: int) -> str:
        size_key = f"{width}x{height}"
        if size_key not in PROFILES:
            raise RenderError(f"Unsupported render size: {size_key}")
        profile = PROFILES[size_key]
        copy = build_visual_copy(brief.catalog_record)
        colors = brief.art_direction.color_palette
        layout_class = "stack-layout" if profile.stack_layout else "split-layout"

        return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={width},height={height},initial-scale=1">
<style>
:root {{
  --primary: {_safe(colors.primary)};
  --secondary: {_safe(colors.secondary)};
  --accent: {_safe(colors.accent)};
  --ink: #F8FAFC;
  --muted: #CBD5E1;
  --canvas-padding: {profile.canvas_padding}px;
  --headline: {profile.headline_size}px;
  --body: {profile.body_size}px;
  --eyebrow: {profile.eyebrow_size}px;
  --card-width: {profile.card_width}px;
  --card-height: {profile.card_height}px;
  --visual-scale: {profile.visual_scale};
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; width: {width}px; height: {height}px; overflow: hidden; }}
body {{
  direction: rtl;
  color: var(--ink);
  font-family: "Vazirmatn", "Noto Sans Arabic", "Noto Sans", Tahoma, Arial, sans-serif;
  font-synthesis: none;
  text-rendering: geometricPrecision;
  background:
    radial-gradient(circle at 14% 16%, rgba(37,99,235,.50), transparent 33%),
    radial-gradient(circle at 88% 78%, rgba(245,158,11,.20), transparent 30%),
    linear-gradient(145deg, #07111F 0%, #0F1F3D 52%, #111827 100%);
}}
.canvas {{
  position: relative;
  width: 100%; height: 100%;
  padding: var(--canvas-padding);
  isolation: isolate;
  overflow: hidden;
}}
.canvas::before {{
  content: ""; position: absolute; inset: 0; z-index: -2;
  background-image: radial-gradient(rgba(255,255,255,.11) 1.3px, transparent 1.3px);
  background-size: 34px 34px; opacity: .42;
  mask-image: linear-gradient(120deg, rgba(0,0,0,.8), transparent 72%);
}}
.canvas::after {{
  content: ""; position: absolute; width: 620px; height: 620px; border: 1px solid rgba(255,255,255,.08);
  border-radius: 50%; left: -260px; bottom: -260px; box-shadow: 0 0 0 110px rgba(255,255,255,.025), 0 0 0 220px rgba(255,255,255,.018); z-index: -1;
}}
.brand-row {{ display: flex; align-items: center; justify-content: space-between; height: 68px; position: relative; z-index: 5; }}
.brand {{ display: flex; align-items: center; gap: 16px; font-size: 25px; font-weight: 800; letter-spacing: -.4px; }}
.brand-mark {{ width: 48px; height: 48px; border-radius: 16px; display: grid; place-items: center; background: linear-gradient(145deg, var(--primary), #60A5FA); box-shadow: 0 14px 36px rgba(37,99,235,.36); }}
.brand-mark svg {{ width: 28px; height: 28px; }}
.domain {{ direction: ltr; font-size: 19px; color: #94A3B8; font-weight: 600; }}
.composition {{ position: relative; height: calc(100% - 122px); display: grid; align-items: center; gap: 42px; }}
.split-layout .composition {{ grid-template-columns: minmax(0, 1.12fr) minmax(360px, .88fr); }}
.stack-layout .composition {{ grid-template-rows: minmax(0, .88fr) minmax(560px, 1.12fr); align-items: stretch; padding-top: 54px; }}
.copy-panel {{ position: relative; z-index: 4; min-width: 0; align-self: center; }}
.stack-layout .copy-panel {{ align-self: end; }}
.eyebrow {{ display: inline-flex; align-items: center; gap: 11px; padding: 11px 19px; border-radius: 999px; background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.15); backdrop-filter: blur(12px); color: #FDE68A; font-size: var(--eyebrow); font-weight: 750; margin-bottom: 28px; }}
.eyebrow::before {{ content: ""; width: 10px; height: 10px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 7px rgba(245,158,11,.15); }}
.headline {{ margin: 0; max-width: 650px; font-size: var(--headline); line-height: 1.29; letter-spacing: -2.2px; font-weight: 900; text-wrap: balance; }}
.headline em {{ color: #93C5FD; font-style: normal; }}
.subheadline {{ max-width: 620px; margin: 27px 0 0; color: var(--muted); font-size: var(--body); line-height: 1.75; font-weight: 450; }}
.features {{ display: flex; flex-wrap: wrap; gap: 13px; margin-top: 28px; max-width: 650px; }}
.feature-chip {{ display: inline-flex; align-items: center; gap: 9px; padding: 11px 16px; border-radius: 13px; color: #E2E8F0; background: rgba(15,23,42,.55); border: 1px solid rgba(148,163,184,.24); font-size: {max(profile.body_size - 8, 18)}px; font-weight: 650; white-space: nowrap; }}
.feature-chip::before {{ content: "✓"; width: 25px; height: 25px; display: grid; place-items: center; border-radius: 8px; color: #052E16; background: #86EFAC; font-size: 16px; font-weight: 900; }}
.cta {{ display: inline-flex; align-items: center; gap: 15px; margin-top: 34px; padding: 17px 24px 17px 19px; border-radius: 17px; color: #07111F; background: linear-gradient(135deg, #FDE68A, var(--accent)); box-shadow: 0 18px 40px rgba(245,158,11,.24); font-size: {max(profile.body_size - 3, 22)}px; font-weight: 850; }}
.cta-arrow {{ width: 36px; height: 36px; display: grid; place-items: center; border-radius: 12px; color: white; background: rgba(15,23,42,.88); font-size: 22px; }}
.visual-panel {{ position: relative; min-width: 0; height: 100%; display: grid; place-items: center; z-index: 2; }}
.stack-layout .visual-panel {{ grid-row: 2; min-height: 650px; }}
.art-stage {{ position: relative; width: 520px; height: 650px; transform: scale(var(--visual-scale)); transform-origin: center; }}
.halo {{ position: absolute; border-radius: 50%; filter: blur(2px); }}
.halo-one {{ width: 460px; height: 460px; right: 18px; top: 96px; background: radial-gradient(circle, rgba(37,99,235,.42), rgba(37,99,235,.04) 70%); }}
.halo-two {{ width: 250px; height: 250px; left: 0; bottom: 60px; background: radial-gradient(circle, rgba(245,158,11,.28), transparent 70%); }}
.document {{ position: absolute; width: var(--card-width); height: var(--card-height); border-radius: 30px; padding: 31px; background: linear-gradient(160deg, rgba(255,255,255,.98), rgba(226,232,240,.94)); color: #0F172A; border: 1px solid rgba(255,255,255,.75); box-shadow: 0 36px 80px rgba(2,6,23,.42); overflow: hidden; }}
.document-back {{ right: 65px; top: 54px; transform: rotate(10deg) scale(.91); opacity: .48; }}
.document-middle {{ right: 23px; top: 82px; transform: rotate(-8deg) scale(.95); opacity: .72; }}
.document-front {{ right: 54px; top: 112px; transform: rotate(1.2deg); }}
.doc-fold {{ position: absolute; left: 0; top: 0; width: 88px; height: 88px; background: linear-gradient(225deg, #CBD5E1 50%, transparent 51%); }}
.doc-top {{ display: flex; justify-content: space-between; align-items: center; }}
.pdf-pill {{ direction: ltr; display: inline-flex; align-items: center; justify-content: center; min-width: 82px; height: 43px; border-radius: 13px; color: white; background: #EF4444; font: 900 21px/1 Arial, sans-serif; letter-spacing: .7px; }}
.doc-dot {{ width: 17px; height: 17px; border-radius: 50%; background: #CBD5E1; box-shadow: 31px 0 0 #E2E8F0, 62px 0 0 #E2E8F0; }}
.doc-title {{ margin: 54px 0 27px; font-size: 29px; font-weight: 900; }}
.doc-line, .paper-line {{ height: 13px; border-radius: 999px; background: #CBD5E1; margin-top: 17px; width: 78%; }}
.doc-line.wide, .paper-line.wide {{ width: 100%; }} .doc-line.short, .paper-line.short {{ width: 44%; }} .paper-line.medium {{ width: 64%; }}
.operation-row {{ position: absolute; right: 31px; left: 31px; bottom: 34px; display: flex; gap: 13px; }}
.op-icon {{ width: 55px; height: 55px; display: grid; place-items: center; border-radius: 17px; color: #1D4ED8; background: #DBEAFE; font-size: 27px; font-weight: 900; }}
.floating-badge {{ position: absolute; z-index: 8; padding: 13px 20px; border-radius: 15px; color: white; font-size: 22px; font-weight: 800; border: 1px solid rgba(255,255,255,.25); box-shadow: 0 19px 45px rgba(2,6,23,.35); backdrop-filter: blur(14px); }}
.badge-merge {{ right: -2px; top: 76px; background: rgba(37,99,235,.92); transform: rotate(-5deg); }}
.badge-compress {{ left: 6px; bottom: 80px; background: rgba(245,158,11,.92); color: #172033; transform: rotate(4deg); }}
.connector {{ position: absolute; width: 220px; left: -18px; top: 5px; }}
.editor-window {{ position: absolute; right: 36px; top: 78px; width: 450px; height: 520px; border-radius: 31px; overflow: hidden; background: #F8FAFC; box-shadow: 0 36px 90px rgba(2,6,23,.45); transform: rotate(-2deg); }}
.window-bar {{ height: 55px; padding: 19px; display: flex; gap: 9px; direction: ltr; background: #E2E8F0; }} .window-bar span {{ width: 16px; height: 16px; border-radius: 50%; background: #F87171; }} .window-bar span:nth-child(2) {{ background: #FBBF24; }} .window-bar span:nth-child(3) {{ background: #34D399; }}
.editor-toolbar {{ height: 64px; padding: 12px 24px; display: flex; align-items: center; gap: 21px; color: #334155; border-bottom: 1px solid #E2E8F0; font-size: 23px; }} .toolbar-pill {{ margin-right: auto; padding: 7px 13px; border-radius: 10px; color: #1D4ED8; background: #DBEAFE; font-weight: 800; }}
.editor-paper {{ position: absolute; inset: 146px 43px 40px; padding: 30px; border-radius: 18px; color: #0F172A; background: white; box-shadow: 0 14px 40px rgba(15,23,42,.10); }} .paper-title {{ font-size: 28px; font-weight: 900; margin-bottom: 34px; }} .cursor {{ width: 3px; height: 31px; margin-top: 22px; background: #2563EB; animation: blink 1s steps(1) infinite; }} @keyframes blink {{ 50% {{ opacity: .25; }} }}
.folder-shape {{ position: absolute; right: 35px; top: 118px; width: 445px; height: 380px; border-radius: 32px; background: linear-gradient(150deg, #FBBF24, #F59E0B); box-shadow: 0 35px 80px rgba(2,6,23,.38); transform: rotate(-3deg); }} .folder-tab {{ position: absolute; right: 0; top: -57px; width: 210px; height: 90px; border-radius: 25px 25px 0 0; background: #FBBF24; }}
.office-card {{ position: absolute; z-index: 3; width: 330px; padding: 22px; display: flex; align-items: center; gap: 18px; border-radius: 22px; color: #0F172A; background: rgba(255,255,255,.96); box-shadow: 0 22px 55px rgba(2,6,23,.27); }} .office-card b {{ display: block; font-size: 24px; }} .office-card small {{ display: block; margin-top: 5px; color: #64748B; font-size: 17px; }} .office-icon {{ width: 58px; height: 58px; display: grid; place-items: center; border-radius: 17px; color: white; background: #2563EB; font: 800 21px/1 Arial, sans-serif; }} .card-one {{ right: 95px; top: 87px; }} .card-two {{ right: 14px; top: 250px; }} .card-three {{ right: 116px; top: 416px; }}
.toolbox-body {{ position: absolute; right: 49px; top: 210px; width: 420px; height: 260px; border-radius: 36px; background: linear-gradient(145deg, #2563EB, #1E40AF); box-shadow: 0 37px 90px rgba(2,6,23,.46); }} .toolbox-handle {{ position: absolute; right: 122px; top: -104px; width: 176px; height: 115px; border: 26px solid #60A5FA; border-bottom: 0; border-radius: 36px 36px 0 0; }} .toolbox-lock {{ position: absolute; right: 183px; top: 103px; width: 54px; height: 43px; border-radius: 13px; background: #FBBF24; }}
.tool-card {{ position: absolute; z-index: 3; width: 112px; height: 112px; display: grid; place-items: center; border-radius: 28px; color: #0F172A; background: white; box-shadow: 0 18px 45px rgba(2,6,23,.28); font: 900 25px/1 Arial, sans-serif; }} .tool-one {{ right: 65px; top: 112px; transform: rotate(8deg); }} .tool-two {{ left: 62px; top: 125px; transform: rotate(-9deg); color: #DC2626; }} .tool-three {{ left: 205px; bottom: 74px; color: #059669; }}
.footer-line {{ position: absolute; right: var(--canvas-padding); left: var(--canvas-padding); bottom: 34px; display: flex; justify-content: space-between; align-items: center; color: #64748B; font-size: 16px; letter-spacing: .2px; }}
.footer-line strong {{ color: #94A3B8; }}
.stack-layout .brand-row {{ height: 76px; }}
.stack-layout .copy-panel {{ text-align: right; }}
.stack-layout .headline {{ max-width: 850px; }}
.stack-layout .subheadline {{ max-width: 820px; }}
.stack-layout .features {{ max-width: 840px; }}
.stack-layout .art-stage {{ transform: scale(1.17); }}
</style>
</head>
<body>
<main class="canvas {layout_class}" data-size="{size_key}">
  <header class="brand-row">
    <div class="brand" data-fit>
      <span class="brand-mark">
        <svg viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="M8 12h16a3 3 0 0 1 3 3v9a3 3 0 0 1-3 3H8a3 3 0 0 1-3-3v-9a3 3 0 0 1 3-3Z" stroke="white" stroke-width="2.4"/>
          <path d="M11 12V9.5A3.5 3.5 0 0 1 14.5 6h3A3.5 3.5 0 0 1 21 9.5V12M5 18h22M14 18v3h4v-3" stroke="white" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
      <span>پرشین‌تولباکس</span>
    </div>
    <div class="domain" data-fit>persiantoolbox.ir</div>
  </header>
  <section class="composition">
    <div class="copy-panel">
      <div class="eyebrow" data-fit>{_safe(copy.eyebrow)}</div>
      <h1 class="headline" data-fit>{_multiline(copy.headline)}</h1>
      <p class="subheadline" data-fit>{_safe(copy.subheadline)}</p>
      <div class="features">{_feature_chips(copy)}</div>
      <div class="cta" data-fit><span>{_safe(copy.cta)}</span><span class="cta-arrow">←</span></div>
    </div>
    <div class="visual-panel">{_visual_art(copy.motif)}</div>
  </section>
  <footer class="footer-line"><strong>ابزارهای کاربردی برای کارهای روزمره</strong><span>لینک در بیو</span></footer>
</main>
<script>
(async () => {{
  await document.fonts.ready;
  const fitNodes = [...document.querySelectorAll('[data-fit]')];
  const overflow = fitNodes.filter((node) => node.scrollWidth > node.clientWidth + 2 || node.scrollHeight > node.clientHeight + 2);
  window.__PTB_RENDER_DIAGNOSTICS__ = {{
    fontStatus: document.fonts.status,
    overflowCount: overflow.length,
    overflowText: overflow.map((node) => node.textContent.trim()).filter(Boolean)
  }};
  window.__PTB_RENDER_READY__ = true;
}})();
</script>
</body>
</html>"""

    async def render_to_png(
        self, brief: Brief, size_key: str, output_path: Path | None = None
    ) -> Path:
        if size_key not in PROFILES:
            raise RenderError(f"Unsupported render size: {size_key}")
        profile = PROFILES[size_key]
        html_content = self.render_html(brief, profile.width, profile.height)
        target_dir = ensure_dir(self.output_dir / brief.brief_id)
        output_path = output_path or target_dir / f"feed-{size_key}.png"
        ensure_dir(output_path.parent)

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RenderError("Playwright is required for production PNG rendering") from exc

        diagnostics: dict[str, object] = {}
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"],
            )
            try:
                page = await browser.new_page(
                    viewport={"width": profile.width, "height": profile.height},
                    device_scale_factor=1,
                )
                await page.set_content(html_content, wait_until="load")
                await page.wait_for_function("window.__PTB_RENDER_READY__ === true", timeout=10_000)
                diagnostics = await page.evaluate("window.__PTB_RENDER_DIAGNOSTICS__")
                if diagnostics.get("overflowCount", 0):
                    raise RenderError(
                        f"Text overflow detected for {brief.brief_id}/{size_key}: "
                        f"{diagnostics.get('overflowText', [])}"
                    )
                await page.screenshot(path=str(output_path), full_page=False, animations="disabled")
            finally:
                await browser.close()

        audit = analyze_png(output_path, (profile.width, profile.height))
        metadata = {
            "brief_id": brief.brief_id,
            "size": size_key,
            "graphics_engine_version": 2,
            "diagnostics": diagnostics,
            "visual_audit": audit.to_dict(),
        }
        (target_dir / f"render-{size_key}.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        if not audit.passed:
            output_path.unlink(missing_ok=True)
            raise RenderError(
                f"Visual QA failed for {brief.brief_id}/{size_key}: {', '.join(audit.issues)}"
            )
        return output_path

    async def render_all_sizes(self, brief: Brief) -> dict[str, Path]:
        results: dict[str, Path] = {}
        for size_key in SIZES:
            results[size_key] = await self.render_to_png(brief, size_key)
        return results

    def render_preview_html(self, briefs: list[Brief]) -> str:
        cards = []
        for brief in briefs:
            rendered = self.render_html(brief, 1080, 1350)
            cards.append(
                "<article class='preview-card'><iframe sandbox srcdoc=\""
                + html.escape(rendered, quote=True)
                + '"></iframe></article>'
            )
        return (
            "<!doctype html><html lang='fa' dir='rtl'><meta charset='utf-8'>"
            "<style>body{margin:0;padding:32px;background:#0f172a;display:grid;gap:28px;"
            "grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}.preview-card{"
            "background:#111827;padding:12px;border-radius:20px}iframe{border:0;width:100%;"
            "aspect-ratio:4/5;border-radius:14px}</style><body>" + "".join(cards) + "</body></html>"
        )
