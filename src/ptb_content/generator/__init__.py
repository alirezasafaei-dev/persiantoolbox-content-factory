"""Deterministic, publication-safe content generator."""

from __future__ import annotations

import random

from ..graphic_engineering import build_copy_deck, validate_copy_deck
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
        {
            "segment": "کاربران عمومی",
            "pain_point": "انتخاب ابزار مناسب",
            "desire": "دسترسی ساده",
        },
        {
            "segment": "دانشجویان",
            "pain_point": "نیاز به ابزارهای متنی",
            "desire": "انتخاب ابزار مناسب",
        },
        {
            "segment": "فریلنسرها",
            "pain_point": "کارهای تکراری",
            "desire": "دسترسی منظم به ابزارها",
        },
    ],
    Category.PDF_TUTORIAL: [
        {
            "segment": "کاربران مبتدی",
            "pain_point": "پیچیدگی PDF",
            "desire": "راهنمای روشن",
        },
        {
            "segment": "کاربران اداری",
            "pain_point": "مدیریت اسناد",
            "desire": "انتخاب ابزار مناسب",
        },
    ],
    Category.PERSIAN_TEXT: [
        {
            "segment": "نویسندگان",
            "pain_point": "مشکلات متن فارسی",
            "desire": "متن استاندارد",
        },
        {
            "segment": "برنامه‌نویسان",
            "pain_point": "نرمال‌سازی متن",
            "desire": "ابزار مشخص",
        },
    ],
    Category.PROFESSIONAL: [
        {
            "segment": "مدیران",
            "pain_point": "انتخاب ابزار",
            "desire": "دسترسی منظم",
        },
        {
            "segment": "تیم‌ها",
            "pain_point": "هماهنگی",
            "desire": "ابزار مشترک",
        },
    ],
    Category.PRIVACY: [
        {
            "segment": "کاربران حساس",
            "pain_point": "انتخاب آگاهانه",
            "desire": "اطلاعات روشن",
        },
    ],
}

PSYCHOLOGY: list[dict[str, str]] = [
    {"principle": "سادگی", "expected_effect": "کاهش اصطکاک در انتخاب ابزار"},
    {"principle": "وضوح", "expected_effect": "درک بهتر موضوع محتوا"},
    {"principle": "ارتباط", "expected_effect": "تطابق بهتر محتوا با نیاز کاربر"},
    {"principle": "راهنمایی", "expected_effect": "هدایت کاربر به صفحه مرتبط"},
]


class DeterministicGenerator:
    """Generate complete briefs with one canonical audience-visible copy deck."""

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

    def _generate_caption(self, record: CatalogRecord) -> Caption:
        deck = build_copy_deck(record.title, record.category)
        defects = validate_copy_deck(deck)
        if defects:
            raise ValueError(f"CopyDeck rejected for {record.source_id}: {'; '.join(defects)}")

        headline = deck.headline.replace("\n", " ")
        primary = f"{headline}\n\n{deck.supporting_text}\n\n{deck.cta}"
        variants = {
            "concise": f"{headline}\n\n{deck.cta}",
            "editorial": f"{deck.supporting_text}\n\n{deck.cta}",
        }
        return Caption(
            primary=primary,
            variants=variants,
            alt_text=deck.alt_text,
            cta=deck.cta,
        )

    def _generate_art_direction(self, template: TemplateType) -> ArtDirection:
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
                heading_font="Noto Sans Arabic",
                body_font="Noto Sans Arabic",
                heading_size_px=64,
                body_size_px=30,
            ),
            layout_notes=(
                "graphic-engineering-v2; editorial-product composition; "
                "platform-specific layout; vector document material; RTL"
            ),
        )

    def generate_brief(self, record: CatalogRecord) -> Brief:
        category = record.category
        template = self._pick_template(category)
        hook_type = self._pick_hook_type(category)
        rng = self._rng(record)
        deck = build_copy_deck(record.title, category)

        audience_list = AUDIENCES.get(category, AUDIENCES[Category.TOOL_DEMO])
        audience_data = rng.choice(audience_list)
        psychology = rng.choice(PSYCHOLOGY)
        caption = self._generate_caption(record)
        art_direction = self._generate_art_direction(template)

        from ..risk import RiskEngine

        risk_engine = RiskEngine()
        source_level, source_decision = risk_engine.assess(record)
        risk_level, risk_decision, publish_tags = risk_engine.assess_publishable_text(
            caption.primary,
            cta=caption.cta,
            alt_text=caption.alt_text,
        )
        record.meta = {
            **record.meta,
            "source_risk_level": source_level.value,
            "source_risk_decision": source_decision.value,
            "source_risk_tags": sorted(tag.value for tag in record.risk_tags),
            "publication_risk_tags": sorted(tag.value for tag in publish_tags),
            "risk_scope_version": 2,
            "graphic_engineering_version": 2,
            "copy_deck": {
                "short_title": deck.short_title,
                "headline": deck.headline,
                "supporting_text": deck.supporting_text,
                "cta": deck.cta,
                "alt_text": deck.alt_text,
                "category_label": deck.category_label,
            },
        }

        return Brief(
            brief_id=generate_id("brief"),
            catalog_record=record,
            audience=Audience(**audience_data),
            content_strategy=ContentStrategy(
                angle=f"معرفی کاربردی {deck.short_title} برای {audience_data['segment']}",
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
