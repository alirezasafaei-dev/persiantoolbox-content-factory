"""Deterministic content generator — no AI needed."""

from __future__ import annotations

import random

from ..types import (
    ArtDirection,
    Audience,
    Brief,
    Caption,
    CatalogRecord,
    Category,
    ColorPalette,
    ContentStrategy,
    HookType,
    PsychologyHypothesis,
    TemplateType,
    Typography,
    generate_id,
    utcnow,
)
from ..utils.helpers import load_config

# ─── Persian content templates ───────────────────────────────────────────────

HOOKS: dict[str, list[str]] = {
    "direct": [
        "با این ابزار رایگان {tool_name} کارت رو سریع‌تر انجام بده",
        "{tool_name} — یه ابزار ساده برای {use_case}",
        "دیگه نیازی به {pain_point} نیست",
    ],
    "educational": [
        "آیا می‌دونستی می‌تونی {use_case} رو رایگان انجام بدی؟",
        "روش {use_case} رو قدم‌به‌قدم یاد بگیر",
        "یه ترفند ساده برای {use_case}",
    ],
    "curiosity": [
        "چطور بدون {pain_point} می‌تونی {use_case}؟",
        "این ابزار رایگان یه چیزی داره که بقیه ندارن",
        "یه راه‌حل ساده برای یه مشکل قدیمی",
    ],
    "problem-solution": [
        "مشکل {pain_point}؟ این راه‌حل رو امتحان کن",
        "وقتی {pain_point} داری، {tool_name} کمکت می‌کنه",
        "دیگه درگیر {pain_point} نباش",
    ],
    "before-after": [
        "قبل: {pain_point} | بعد: {use_case} آسان",
        "از {pain_point} تا {use_case} در چند ثانیه",
    ],
}

CTAS = [
    "همین حالا امتحان کن 👇",
        "لینک در بیو",
        "سایت رو ببین 👇",
        "رایگان امتحان کن",
        "شروع کن 👇",
]

AUDIENCES: dict[Category, list[dict[str, str]]] = {
    Category.TOOL_DEMO: [
        {"segment": "کاربران عمومی", "pain_point": "ابزارهای پیچیده", "desire": "سادگی و سرعت"},
        {"segment": "دانشجویان", "pain_point": "نیاز به ابزارهای متنی", "desire": "ابزار رایگان و سریع"},
        {"segment": "فریلنسرها", "pain_point": "وقت‌گیری کارهای ساده", "desire": "خودکارسازی"},
    ],
    Category.PDF_TUTORIAL: [
        {"segment": "کاربران مبتدی", "pain_point": "پیچیدگی PDF", "desire": "آموزش ساده"},
        {"segment": "اداری", "pain_point": "مدیریت اسناد", "desire": "سرعت در کار"},
    ],
    Category.PERSIAN_TEXT: [
        {"segment": "نویسندگان", "pain_point": "مشکلات متن فارسی", "desire": "متن تمیز و حرفه‌ای"},
        {"segment": "برنامه‌نویسان", "pain_point": "نرمال‌سازی متن", "desire": "ابزار دقیق"},
    ],
    Category.PROFESSIONAL: [
        {"segment": "مدیران", "pain_point": "زمان محدود", "desire": "ابزار سریع"},
        {"segment": "تیم‌ها", "pain_point": "هماهنگی", "desire": "ابزار مشترک"},
    ],
    Category.PRIVACY: [
        {"segment": "کاربران حساس", "pain_point": "نگرانی حریم خصوصی", "desire": "امنیت و اعتماد"},
    ],
}

PSYCHOLOGY: list[dict[str, str]] = [
    {"principle": "سادگی", "expected_effect": "کاهش اصطکاک و افزایش تبدیل"},
    {"principle": "اثبات اجتماعی", "expected_effect": "افزایش اعتماد"},
    {"principle": "کمیابی", "expected_effect": "افزایش فوریت (فقط برای محتوای فصلی)"},
    {"principle": "پاداش", "expected_effect": "ارزش درک‌شده بالاتر"},
    {"principle": "تعهد", "expected_effect": "پیگیری و بازگشت"},
]


class DeterministicGenerator:
    """Generate content briefs deterministically without AI."""

    def __init__(self) -> None:
        self.brand = load_config("brand")
        self.colors = self.brand["colors"]
        self.typography = self.brand["typography"]

    def _pick_template(self, category: Category) -> TemplateType:
        """Pick template type based on category."""
        mapping = {
            Category.TOOL_DEMO: TemplateType.TOOL_DEMO,
            Category.PDF_TUTORIAL: TemplateType.STEP_BY_STEP,
            Category.PERSIAN_TEXT: TemplateType.COMMON_MISTAKE,
            Category.PROFESSIONAL: TemplateType.PROFESSIONAL_SEASONAL,
            Category.PRIVACY: TemplateType.PRIVACY_TRUST,
            Category.SEASONAL: TemplateType.PROFESSIONAL_SEASONAL,
            Category.COMPARISON: TemplateType.COMMON_MISTAKE,
            Category.FINANCIAL: TemplateType.PROFESSIONAL_SEASONAL,
        }
        return mapping.get(category, TemplateType.TOOL_DEMO)

    def _pick_hook_type(self, category: Category) -> HookType:
        """Pick hook type based on category."""
        mapping = {
            Category.TOOL_DEMO: HookType.DIRECT,
            Category.PDF_TUTORIAL: HookType.EDUCATIONAL,
            Category.PERSIAN_TEXT: HookType.PROBLEM_SOLUTION,
            Category.PROFESSIONAL: HookType.DIRECT,
            Category.PRIVACY: HookType.CURIOSITY,
        }
        return mapping.get(category, HookType.DIRECT)

    def _generate_caption(self, record: CatalogRecord, hook_type: HookType) -> Caption:
        """Generate caption variants."""
        tool_name = record.title
        use_case = record.summary[:100]
        pain_point = record.summary[:50] if record.summary else "پیچیدگی"

        hook_templates = HOOKS.get(hook_type.value, HOOKS["direct"])
        primary_hook = random.choice(hook_templates).format(
            tool_name=tool_name, use_case=use_case, pain_point=pain_point
        )

        # Build full caption
        caption_text = f"{primary_hook}\n\n"
        if record.summary:
            caption_text += f"{record.summary[:200]}\n\n"
        cta = random.choice(CTAS)
        caption_text += cta

        # Generate variants
        variants = {}
        for h_type, templates in HOOKS.items():
            hook = random.choice(templates).format(
                tool_name=tool_name, use_case=use_case, pain_point=pain_point
            )
            variant_text = f"{hook}\n\n"
            if record.summary:
                variant_text += f"{record.summary[:200]}\n\n"
            variant_text += random.choice(CTAS)
            variants[f"{h_type}_variant"] = variant_text

        return Caption(
            primary=caption_text,
            variants=variants,
            alt_text=f"تصویر پست {tool_name} — {use_case}",
            cta=cta,
        )

    def _generate_art_direction(self, template: TemplateType) -> ArtDirection:
        """Generate art direction for the template."""
        return ArtDirection(
            template=template,
            color_palette=ColorPalette(
                primary=self.colors["primary"],
                secondary=self.colors["secondary"],
                accent=self.colors["accent"],
                background=self.colors["background"],
                text=self.colors["text"],
            ),
            typography=Typography(
                heading_font=self.typography["heading_font"],
                body_font=self.typography["body_font"],
                heading_size_px=28,
                body_size_px=16,
            ),
            layout_notes=f"Template: {template.value}. RTL layout. Persian text prominent.",
        )

    def generate_brief(self, record: CatalogRecord) -> Brief:
        """Generate a complete brief from a catalog record."""
        category = record.category
        template = self._pick_template(category)
        hook_type = self._pick_hook_type(category)

        audience_list = AUDIENCES.get(category, AUDIENCES[Category.TOOL_DEMO])
        audience_data = random.choice(audience_list)

        psychology = random.choice(PSYCHOLOGY)

        caption = self._generate_caption(record, hook_type)

        art_direction = self._generate_art_direction(template)

        # Risk assessment
        from ..risk import RiskEngine
        risk_engine = RiskEngine()
        risk_level, risk_decision = risk_engine.assess(record)

        return Brief(
            brief_id=generate_id("brief"),
            catalog_record=record,
            audience=Audience(**audience_data),
            content_strategy=ContentStrategy(
                angle=f"معرفی {record.title} برای {audience_data['segment']}",
                hook_type=hook_type,
                template_type=template,
            ),
            psychology_hypothesis=PsychologyHypothesis(**psychology),
            caption=caption,
            art_direction=art_direction,
            risk_level=risk_level,
            risk_decision=risk_decision,
            utm={
                "source": "instagram",
                "medium": "social",
                "campaign": "content-factory-pilot",
                "content": record.source_id,
            },
            created_at=utcnow(),
            version=1,
        )

    def generate_briefs(self, records: list[CatalogRecord]) -> list[Brief]:
        """Generate briefs for multiple catalog records."""
        return [self.generate_brief(r) for r in records]
