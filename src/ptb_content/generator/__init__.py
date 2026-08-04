"""Deterministic editorial content generator."""

from __future__ import annotations

import random

from ..content_shaping import build_caption, build_visual_copy, clean_display_title
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
    """Generate publication-safe briefs from catalog records."""

    def __init__(self) -> None:
        self.brand = load_config("brand")
        self.colors = self.brand["colors"]
        self.typography = self.brand["typography"]

    @staticmethod
    def _rng(record: CatalogRecord) -> random.Random:
        seed = f"{record.source_id}:{record.content_hash or record.source_hash}"
        return random.Random(seed)

    def _pick_template(self, category: Category) -> TemplateType:
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
        mapping = {
            Category.TOOL_DEMO: HookType.DIRECT,
            Category.PDF_TUTORIAL: HookType.EDUCATIONAL,
            Category.PERSIAN_TEXT: HookType.PROBLEM_SOLUTION,
            Category.PROFESSIONAL: HookType.DIRECT,
            Category.PRIVACY: HookType.CURIOSITY,
        }
        return mapping.get(category, HookType.DIRECT)

    def _generate_caption(self, record: CatalogRecord, _hook_type: HookType) -> Caption:
        return build_caption(record)

    def _generate_art_direction(self, template: TemplateType) -> ArtDirection:
        return ArtDirection(
            template=template,
            color_palette=ColorPalette(
                primary=self.colors["primary"],
                secondary=self.colors["secondary"],
                accent=self.colors["accent"],
                background=self.colors["background_dark"],
                text=self.colors["text_inverse"],
            ),
            typography=Typography(
                heading_font=self.typography["heading_font"],
                body_font=self.typography["body_font"],
                heading_size_px=72,
                body_size_px=32,
            ),
            layout_notes=(
                "Graphics Engine v2; size-specific RTL composition; semantic motif; "
                "local font stack; visual-density QA required"
            ),
        )

    def generate_brief(self, record: CatalogRecord) -> Brief:
        category = record.category
        template = self._pick_template(category)
        hook_type = self._pick_hook_type(category)
        rng = self._rng(record)

        audience_list = AUDIENCES.get(category, AUDIENCES[Category.TOOL_DEMO])
        audience_data = rng.choice(audience_list)
        psychology = rng.choice(PSYCHOLOGY)
        caption = self._generate_caption(record, hook_type)
        visual_copy = build_visual_copy(record)
        art_direction = self._generate_art_direction(template)

        from ..risk import RiskEngine

        risk_engine = RiskEngine()
        source_level, source_decision = risk_engine.assess(record)

        publication_payload = f"{caption.primary}\n{visual_copy.audience_text()}"
        risk_level, risk_decision, publish_tags = risk_engine.assess_publishable_text(
            publication_payload,
            cta=caption.cta,
            alt_text=caption.alt_text,
        )
        record.meta = {
            **record.meta,
            "display_title": clean_display_title(record.title),
            "visual_copy": {
                "eyebrow": visual_copy.eyebrow,
                "headline": visual_copy.headline,
                "subheadline": visual_copy.subheadline,
                "feature_labels": list(visual_copy.feature_labels),
                "cta": visual_copy.cta,
                "motif": visual_copy.motif,
            },
            "source_risk_level": source_level.value,
            "source_risk_decision": source_decision.value,
            "source_risk_tags": sorted(tag.value for tag in record.risk_tags),
            "publication_risk_tags": sorted(tag.value for tag in publish_tags),
            "risk_scope_version": 3,
            "graphics_engine_version": 2,
        }

        display_title = clean_display_title(record.title) or "ابزار"
        return Brief(
            brief_id=generate_id("brief"),
            catalog_record=record,
            audience=Audience(**audience_data),
            content_strategy=ContentStrategy(
                angle=f"معرفی {display_title} برای {audience_data['segment']}",
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
            version=2,
        )

    def generate_briefs(self, records: list[CatalogRecord]) -> list[Brief]:
        return [self.generate_brief(record) for record in records]
