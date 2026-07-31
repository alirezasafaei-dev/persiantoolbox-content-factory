"""Deterministic HTML/CSS/SVG renderer for social media images."""

from __future__ import annotations

from pathlib import Path

from ..types import Brief, TemplateType
from ..utils.helpers import ensure_dir, project_root

# ─── HTML Templates for each size ────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width={width}, initial-scale=1.0">
<style>
@font-face {{
    font-family: 'Vazirmatn';
    src: url('https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css');
}}
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}
body {{
    width: {width}px;
    height: {height}px;
    font-family: 'Vazirmatn', 'Tahoma', sans-serif;
    direction: rtl;
    background: {background};
    color: {text_color};
    overflow: hidden;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    padding: {padding}px;
}}
.container {{
    width: 100%;
    max-width: {max_content_width}px;
    display: flex;
    flex-direction: column;
    gap: {gap}px;
}}
.badge {{
    display: inline-block;
    background: {accent};
    color: white;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
    align-self: flex-start;
}}
.heading {{
    font-size: {heading_size}px;
    font-weight: 700;
    line-height: 1.5;
    color: {text_color};
    word-wrap: break-word;
}}
.body-text {{
    font-size: {body_size}px;
    font-weight: 400;
    line-height: 1.75;
    color: {secondary_text};
    word-wrap: break-word;
}}
.cta-button {{
    display: inline-block;
    background: {primary};
    color: white;
    padding: 14px 32px;
    border-radius: 12px;
    font-size: 18px;
    font-weight: 600;
    text-align: center;
    align-self: flex-start;
    margin-top: {cta_margin}px;
}}
.logo-area {{
    position: absolute;
    top: {logo_top}px;
    {logo_position}: {logo_side}px;
    opacity: 0.85;
}}
.logo-text {{
    font-size: 20px;
    font-weight: 700;
    color: {primary};
}}
.divider {{
    width: 60px;
    height: 4px;
    background: {accent};
    border-radius: 2px;
}}
.step {{
    display: flex;
    align-items: flex-start;
    gap: 12px;
}}
.step-number {{
    width: 32px;
    height: 32px;
    background: {primary};
    color: white;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 16px;
    flex-shrink: 0;
}}
.step-text {{
    font-size: {body_size}px;
    line-height: 1.6;
}}
.warning-box {{
    background: #FEF3C7;
    border: 1px solid #F59E0B;
    border-radius: 12px;
    padding: 16px;
    margin-top: 8px;
}}
.warning-text {{
    color: #92400E;
    font-size: {body_size}px;
}}
.trust-badge {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: #ECFDF5;
    padding: 12px 20px;
    border-radius: 12px;
    border: 1px solid #10B981;
}}
.trust-text {{
    color: #065F46;
    font-size: 14px;
    font-weight: 500;
}}
</style>
</head>
<body>
<div class="logo-area">
    <div class="logo-text">جعبه‌ابزار فارسی</div>
</div>
<div class="container">
    {content}
</div>
</body>
</html>"""


def _render_tool_demo(brief: Brief, width: int, height: int) -> str:
    """Render tool demo template."""
    art = brief.art_direction
    colors = art.color_palette
    typo = art.typography

    heading = brief.caption.primary.split("\n")[0][:60]
    body = brief.catalog_record.summary[:200]
    cta = brief.caption.cta or "همین حالا امتحان کن"

    content = f"""
    <div class="badge">ابزار رایگان</div>
    <div class="heading" style="font-size: {min(typo.heading_size_px + 4, 36)}px">{heading}</div>
    <div class="divider"></div>
    <div class="body-text">{body}</div>
    <div class="cta-button">{cta}</div>
    """

    return HTML_TEMPLATE.format(
        width=width,
        height=height,
        background=colors.background,
        text_color=colors.text,
        primary=colors.primary,
        accent=colors.accent,
        secondary_text="#64748B",
        heading_size=typo.heading_size_px + 4,
        body_size=typo.body_size_px,
        padding=40,
        max_content_width=width - 80,
        gap=20,
        cta_margin=20,
        logo_top=30,
        logo_position="right" if width > height else "right",
        logo_side=40,
        content=content,
    )


def _render_step_by_step(brief: Brief, width: int, height: int) -> str:
    """Render step-by-step template."""
    art = brief.art_direction
    colors = art.color_palette
    typo = art.typography

    steps = [
        "ابزار رو باز کن",
        "متن رو وارد کن",
        "نتیجه رو کپی کن",
    ]

    heading = brief.catalog_record.title[:50]
    cta = brief.caption.cta or "شروع کن"

    steps_html = ""
    for i, step in enumerate(steps, 1):
        steps_html += f"""
        <div class="step">
            <div class="step-number">{i}</div>
            <div class="step-text">{step}</div>
        </div>
        """

    content = f"""
    <div class="badge">آموزش گام‌به‌گام</div>
    <div class="heading" style="font-size: {min(typo.heading_size_px + 2, 34)}px">{heading}</div>
    <div class="divider"></div>
    {steps_html}
    <div class="cta-button">{cta}</div>
    """

    return HTML_TEMPLATE.format(
        width=width,
        height=height,
        background=colors.background,
        text_color=colors.text,
        primary=colors.primary,
        accent=colors.accent,
        secondary_text="#64748B",
        heading_size=typo.heading_size_px + 2,
        body_size=typo.body_size_px,
        padding=40,
        max_content_width=width - 80,
        gap=16,
        cta_margin=20,
        logo_top=30,
        logo_position="right",
        logo_side=40,
        content=content,
    )


def _render_common_mistake(brief: Brief, width: int, height: int) -> str:
    """Render common mistake template."""
    art = brief.art_direction
    colors = art.color_palette
    typo = art.typography

    heading = brief.catalog_record.title[:50]
    body = brief.catalog_record.summary[:150]
    cta = brief.caption.cta or "راه‌حل رو ببین"

    content = f"""
    <div class="badge">خطای رایج</div>
    <div class="heading" style="font-size: {min(typo.heading_size_px + 2, 34)}px">{heading}</div>
    <div class="warning-box">
        <div class="warning-text">⚠️ {body}</div>
    </div>
    <div class="body-text">این مشکل خیلی رایجه ولی راه‌حل ساده‌ای داره.</div>
    <div class="cta-button">{cta}</div>
    """

    return HTML_TEMPLATE.format(
        width=width,
        height=height,
        background=colors.background,
        text_color=colors.text,
        primary=colors.primary,
        accent=colors.accent,
        secondary_text="#64748B",
        heading_size=typo.heading_size_px + 2,
        body_size=typo.body_size_px,
        padding=40,
        max_content_width=width - 80,
        gap=20,
        cta_margin=20,
        logo_top=30,
        logo_position="right",
        logo_side=40,
        content=content,
    )


def _render_privacy_trust(brief: Brief, width: int, height: int) -> str:
    """Render privacy/trust template."""
    art = brief.art_direction
    colors = art.color_palette
    typo = art.typography

    heading = brief.catalog_record.title[:50]
    body = brief.catalog_record.summary[:150]
    cta = brief.caption.cta or "امتحان کن"

    content = f"""
    <div class="badge">حریم خصوصی</div>
    <div class="heading" style="font-size: {min(typo.heading_size_px + 2, 34)}px">{heading}</div>
    <div class="trust-badge">
        <div class="trust-text">✓ تمام پردازش‌ها روی دستگاه شما انجام می‌شود</div>
    </div>
    <div class="body-text">{body}</div>
    <div class="cta-button">{cta}</div>
    """

    return HTML_TEMPLATE.format(
        width=width,
        height=height,
        background=colors.background,
        text_color=colors.text,
        primary=colors.primary,
        accent=colors.accent,
        secondary_text="#64748B",
        heading_size=typo.heading_size_px + 2,
        body_size=typo.body_size_px,
        padding=40,
        max_content_width=width - 80,
        gap=20,
        cta_margin=20,
        logo_top=30,
        logo_position="right",
        logo_side=40,
        content=content,
    )


def _render_professional_seasonal(brief: Brief, width: int, height: int) -> str:
    """Render professional/seasonal template."""
    art = brief.art_direction
    colors = art.color_palette
    typo = art.typography

    heading = brief.catalog_record.title[:50]
    body = brief.catalog_record.summary[:150]
    cta = brief.caption.cta or "بیشتر بدانید"

    content = f"""
    <div class="badge">حرفه‌ای</div>
    <div class="heading" style="font-size: {min(typo.heading_size_px + 2, 34)}px">{heading}</div>
    <div class="divider"></div>
    <div class="body-text">{body}</div>
    <div class="cta-button">{cta}</div>
    """

    return HTML_TEMPLATE.format(
        width=width,
        height=height,
        background=colors.background,
        text_color=colors.text,
        primary=colors.primary,
        accent=colors.accent,
        secondary_text="#64748B",
        heading_size=typo.heading_size_px + 2,
        body_size=typo.body_size_px,
        padding=40,
        max_content_width=width - 80,
        gap=20,
        cta_margin=20,
        logo_top=30,
        logo_position="right",
        logo_side=40,
        content=content,
    )


RENDERERS = {
    TemplateType.TOOL_DEMO: _render_tool_demo,
    TemplateType.STEP_BY_STEP: _render_step_by_step,
    TemplateType.COMMON_MISTAKE: _render_common_mistake,
    TemplateType.PRIVACY_TRUST: _render_privacy_trust,
    TemplateType.PROFESSIONAL_SEASONAL: _render_professional_seasonal,
}

SIZES = {
    "1080x1350": (1080, 1350),
    "1080x1080": (1080, 1080),
    "1080x1920": (1080, 1920),
}


class Renderer:
    """Render social media images using HTML/CSS + Playwright."""

    def __init__(self) -> None:
        self.output_dir = project_root() / "outputs"

    def render_html(self, brief: Brief, width: int, height: int) -> str:
        """Generate HTML for a brief and size."""
        renderer = RENDERERS.get(brief.art_direction.template, _render_tool_demo)
        return renderer(brief, width, height)

    async def render_to_png(
        self, brief: Brief, size_key: str, output_path: Path | None = None
    ) -> Path:
        """Render HTML to PNG using Playwright."""
        width, height = SIZES[size_key]
        html_content = self.render_html(brief, width, height)

        # Write temporary HTML
        tmp_dir = ensure_dir(self.output_dir / "tmp")
        tmp_html = tmp_dir / f"{brief.brief_id}_{size_key}.html"
        tmp_html.write_text(html_content, encoding="utf-8")

        if output_path is None:
            output_path = ensure_dir(self.output_dir / brief.brief_id) / f"feed-{size_key}.png"

        # Try Playwright first
        try:
            from playwright.async_api import async_playwright

            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    executable_path="/snap/bin/chromium",
                    args=[
                        "--no-sandbox",
                        "--disable-gpu",
                        "--disable-dev-shm-usage",
                    ],
                )
                page = await browser.new_page(viewport={"width": width, "height": height})
                await page.goto(f"file://{tmp_html.absolute()}")
                # Wait for fonts to load
                await page.wait_for_timeout(1000)
                await page.screenshot(path=str(output_path), full_page=False)
                await browser.close()
        except ImportError:
            # Fallback: save HTML only (no PNG rendering)
            html_path = output_path.with_suffix(".html")
            html_path.write_text(html_content, encoding="utf-8")
            output_path = html_path
        except Exception:
            # Playwright failed, save HTML
            html_path = output_path.with_suffix(".html")
            html_path.write_text(html_content, encoding="utf-8")
            output_path = html_path

        return output_path

    async def render_all_sizes(self, brief: Brief) -> dict[str, Path]:
        """Render all three sizes for a brief."""
        results = {}
        for size_key in SIZES:
            results[size_key] = await self.render_to_png(brief, size_key)
        return results

    def render_preview_html(self, briefs: list[Brief]) -> str:
        """Generate a review gallery HTML page."""
        cards = []
        for brief in briefs:
            html = self.render_html(brief, 1080, 1350)
            card = f"""
            <div class="card">
                <h3>{brief.catalog_record.title}</h3>
                <p class="risk risk-{brief.risk_level.value.lower()}">{brief.risk_level.value}</p>
                <div class="preview">{html}</div>
                <p class="caption">{brief.caption.primary[:100]}...</p>
            </div>
            """
            cards.append(card)

        return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="UTF-8">
<title>Review Gallery — PersianToolbox Content Factory</title>
<style>
body {{ font-family: 'Vazirmatn', sans-serif; direction: rtl; background: #f5f5f5; padding: 20px; }}
.gallery {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 20px; }}
.card {{ background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.card h3 {{ margin-bottom: 8px; }}
.risk {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
.risk-low {{ background: #ECFDF5; color: #065F46; }}
.risk-medium {{ background: #FEF3C7; color: #92400E; }}
.risk-high {{ background: #FEE2E2; color: #991B1B; }}
.preview {{ width: 100%; height: 300px; overflow: hidden; border: 1px solid #eee; border-radius: 8px; margin: 12px 0; }}
.preview iframe {{ width: 1080px; height: 1350px; transform: scale(0.32); transform-origin: top left; border: none; }}
.caption {{ font-size: 14px; color: #666; line-height: 1.6; }}
</style>
</head>
<body>
<h1>گالری بازبینی محتوا</h1>
<p>تعداد پست‌ها: {len(briefs)}</p>
<div class="gallery">
{''.join(cards)}
</div>
</body>
</html>"""
