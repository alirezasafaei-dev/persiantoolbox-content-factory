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

# Publication-safe templates. They intentionally avoid price, performance,
# security, privacy, comparison, and outcome claims. Product-page source risk is
# assessed separately and remains attached to the catalog record.
HOOKS: dict[str, list[str]] = {
    "direct": [
        "{tool_name} را در پرشین‌تولباکس ببینید",
        "با {tool_name} آشنا شوید",
        "ابزار {tool_name} برای کارهای فارسی و روزمره",
    ],
    "educational": [
        "با کاربرد {tool_name} آشنا شوید",
        "راهنمای شروع کار با {tool_name}",
        "یک معرفی کوتاه از {tool_name}",
    ],
    "curiosity": [
        "{tool_name} چه کاربردی دارد؟",
        "نگاهی به {tool_name} در پرشین‌تولباکس",
        "این بار با {tool_name} آشنا شوید",
    ],
    "problem-solution": [
        "برای کار با متن فارسی، {tool_name} را ببینید",
        "{tool_name}؛ یکی از ابزارهای نگارش پرشین‌تولباکس",
        "ابزار مناسب کارتان را در {tool_name} پیدا کنید",
    ],
    "before-after": [
        "از انتخاب ابزار تا شروع کار با {tool_name}",
        "پیش از شروع، با امکانات {tool_name} آشنا شوید",
    ],
}

CTAS = [
    "لینک در بیو",
    "صفحه ابزار را ببینید",
    "در پرشین‌تولباکس مشاهده کنید",
    "برای آشنایی بیشتر، صفحه ابزار را ببینید",
]

AUDIENCES: dict[Category, list[dict[str, str]]] = {
    Category.TOOL_DEMO: [
        {"segment": "کاربران عمومی", "pain_point": "انتخاب ابزار مناسب", "desire": "دسترسی ساده"},
        {
            "segment": "دانشجویان",
            "pain_point": "نیاز به ابزارهای متنی",
            "desire": "انتخاب ابزار مناسب",
        },
        {"segment": "فریلنسرها", "pain_point": "کارهای تکراری", "desire": "دسترسی منظم به ابزارها"},
    ],
    Category.PDF_TUTORIAL: [
        {"segment": "کاربران مبتدی", "pain_point": "پیچیدگی PDF", "desire": "راهنمای روشن"},
        {"segment": "کاربران اداری", "pain_point": "مدیریت اسناد", "desire": "انتخاب ابزار مناسب"},
    ],
    Category.PERSIAN_TEXT: [
        {"segment": "نویسندگان", "pain_point": "مشکلات متن فارسی", "desire": "متن استاندارد"},
        {"segment": "برنامه‌نویسان", "pain_point": "نرمال‌سازی متن", "desire": "ابزار مشخص"},
    ],
    Category.PROFESSIONAL: [
        {"segment": "مدیران", "pain_point": "انتخاب ابزار", "desire": "دسترسی منظم"},
        {"segment": "تیم‌ها", "pain_point": "هماهنگی", "desire": "ابزار مشترک"},
    ],
    Category.PRIVACY: [
        {"segment": "کاربران حساس", "pain_point": "انتخاب آگاهانه", "desire": "اطلاعات روشن"},
    ],
}

PSYCHOLOGY: list[dict[str, str]] = [
    {"principle": "سادگی", "expected_effect": "کاهش اصطکاک در انتخاب ابزار"},
    {"principle": "وضوح", "expected_effect": "درک بهتر موضوع محتوا"},
    {"principle": "ارتباط", "expected_effect": "تطابق بهتر محتوا با نیاز کاربر"},
    {"principle": "راهنمایی", "expected_effect": "هدایت کاربر به صفحه مرتبط"},
]


class DeterministicGenerator:
    """Generate content briefs deterministically without AI."""

    def __init__(self) -> None:
        self.brand = load_config("brand")
        self.colors = self.brand["colors"]
        self.typography = self.brand["typography"]

    @staticmethod
    def _rng(record: CatalogRecord) -> random.Random:
        """Create a stable RNG from immutable source identity."""
        seed = f"{record.source_id}:{record.content_hash or record.source_hash}"
        return random.Random(seed)

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
        """Generate claim-free caption variants from source identity."""
        tool_name = record.title.strip() or "این ابزار"
        rng = self._rng(record)

        hook_templates = HOOKS.get(hook_type.value, HOOKS["direct"])
        primary_hook = rng.choice(hook_templates).format(tool_name=tool_name)
        body = (
            f"برای آشنایی با {tool_name} و انتخاب ابزار متناسب با کارتان، "
            "صفحه مربوط را در پرشین‌تولباکس ببینید."
        )
        cta = rng.choice(CTAS)
        caption_text = f"{primary_hook}\n\n{body}\n\n{cta}"

        variants: dict[str, str] = {}
        for h_type, templates in HOOKS.items():
            hook = rng.choice(templates).format(tool_name=tool_name)
            variants[f"{h_type}_variant"] = f"{hook}\n\n{body}\n\n{rng.choice(CTAS)}"

        return Caption(
            primary=caption_text,
            variants=variants,
            alt_text=f"تصویر معرفی {tool_name} در پرشین‌تولباکس",
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
        rng = self._rng(record)

        audience_list = AUDIENCES.get(category, AUDIENCES[Category.TOOL_DEMO])
        audience_data = rng.choice(audience_list)
        psychology = rng.choice(PSYCHOLOGY)
        caption = self._generate_caption(record, hook_type)
        art_direction = self._generate_art_direction(template)

        from ..risk import RiskEngine

        risk_engine = RiskEngine()

        # Preserve source-page risk for provenance and review.
        source_level, source_decision = risk_engine.assess(record)

        # Brief risk represents only the exact audience-visible publication text.
        risk_level, risk_decision, publish_tags = risk_engine.assess_publishable_text(
            caption.primary,
            cta=caption.cta,
            alt_text=caption.alt_text,
        )
        record.meta = {
            **record.meta,
            "source_risk_level": source_level.value,
            "source_risk_decision": source_decision.value,
            "publication_risk_tags": sorted(tag.value for tag in publish_tags),
            "risk_scope_version": 2,
        }

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
