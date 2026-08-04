"""Deterministic, publication-safe content generator."""

from __future__ import annotations

from dataclasses import asdict

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

AUDIENCE_PROFILES: dict[Category, Audience] = {
    Category.TOOL_DEMO: Audience(
        segment="کاربرانی که برای یک نیاز مشخص دنبال ابزار هستند",
        pain_point="پیش از روشن‌شدن کاربرد، میان ابزارهای مختلف انتخاب می‌کنند",
        desire="درک کاربرد و تناسب ابزار پیش از اقدام",
    ),
    Category.PDF_TUTORIAL: Audience(
        segment="کاربران اداری، دانشجویان و متقاضیان استخدام",
        pain_point="برای مدیریت فایل PDF نمی‌دانند کدام ابزار با کار فعلی‌شان مرتبط است",
        desire="دیدن مجموعه ابزارهای PDF و انتخاب بر اساس نیاز فعلی",
    ),
    Category.PERSIAN_TEXT: Audience(
        segment="نویسندگان، تولیدکنندگان محتوا و کاربران متن فارسی",
        pain_point="متن فارسی پیش از استفاده یا انتشار ناهماهنگ و نامرتب است",
        desire="رسیدن به متن استاندارد و خوانا با ابزار مرتبط",
    ),
    Category.PROFESSIONAL: Audience(
        segment="کاربران حرفه‌ای و تیم‌های کاری",
        pain_point="انتخاب ابزار بدون سنجش کاربرد و تناسب با فرایند کاری",
        desire="بررسی روشن کاربرد ابزار پیش از استفاده",
    ),
    Category.PRIVACY: Audience(
        segment="کاربرانی که با داده‌های شخصی یا حساس کار می‌کنند",
        pain_point="نحوه استفاده یا پردازش داده برایشان روشن نیست",
        desire="تصمیم‌گیری آگاهانه پیش از واردکردن داده",
    ),
    Category.FINANCIAL: Audience(
        segment="کاربرانی که با داده‌ها و محاسبات مالی کار می‌کنند",
        pain_point="انتخاب ابزار بدون شناخت محدودیت و کاربرد آن",
        desire="بررسی کاربرد و جزئیات پیش از استفاده",
    ),
    Category.SEASONAL: Audience(
        segment="کاربرانی که محتوای مناسبتی یا زمان‌مند می‌خواهند",
        pain_point="پیام عمومی با نیاز فعلی آن‌ها ارتباط روشنی ندارد",
        desire="محتوای مرتبط با موقعیت و اقدام مشخص",
    ),
    Category.COMPARISON: Audience(
        segment="کاربرانی که میان چند راه‌حل تصمیم می‌گیرند",
        pain_point="معیار انتخاب و تفاوت کاربرد گزینه‌ها برایشان روشن نیست",
        desire="مقایسه بر اساس نیاز و معیار مشخص",
    ),
}


class DeterministicGenerator:
    """Generate complete briefs from one semantic messaging contract."""

    def __init__(self) -> None:
        self.brand = load_config("brand")
        self.colors = self.brand["colors"]
        self.typography = self.brand["typography"]

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
            Category.TOOL_DEMO: HookType.EDUCATIONAL,
            Category.PDF_TUTORIAL: HookType.PROBLEM_SOLUTION,
            Category.PERSIAN_TEXT: HookType.PROBLEM_SOLUTION,
            Category.PROFESSIONAL: HookType.EDUCATIONAL,
            Category.PRIVACY: HookType.PROBLEM_SOLUTION,
            Category.COMPARISON: HookType.PROBLEM_SOLUTION,
        }
        return mapping.get(category, HookType.EDUCATIONAL)

    @staticmethod
    def _audience_for(category: Category) -> Audience:
        return AUDIENCE_PROFILES.get(category, AUDIENCE_PROFILES[Category.TOOL_DEMO])

    def _generate_caption(self, record: CatalogRecord) -> Caption:
        deck = build_copy_deck(record.title, record.category, record.summary)
        defects = validate_copy_deck(deck)
        if defects:
            raise ValueError(f"CopyDeck rejected for {record.source_id}: {'; '.join(defects)}")

        primary = f"{deck.caption_lead}\n\n{deck.value_proposition}.\n\n{deck.cta}."
        variants = {
            "concise": f"{deck.headline.replace(chr(10), ' ')}\n\n{deck.cta}.",
            "problem-solution": (f"{deck.problem}.\n\n{deck.value_proposition}.\n\n{deck.cta}."),
            "editorial": (f"{deck.caption_lead}\n\n{deck.supporting_text}\n\n{deck.cta}."),
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
        deck = build_copy_deck(record.title, category, record.summary)
        defects = validate_copy_deck(deck)
        if defects:
            raise ValueError(f"CopyDeck rejected for {record.source_id}: {'; '.join(defects)}")

        audience = self._audience_for(category)
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
            "semantic_messaging_version": 1,
            "copy_deck": asdict(deck),
        }

        return Brief(
            brief_id=generate_id("brief"),
            catalog_record=record,
            audience=audience,
            content_strategy=ContentStrategy(
                angle=(
                    f"مسئله: {deck.problem} | ارزش: {deck.value_proposition} | "
                    f"هدف: {deck.marketing_goal}"
                ),
                hook_type=hook_type,
                template_type=template,
            ),
            psychology_hypothesis=PsychologyHypothesis(
                principle=deck.psychology_principle,
                expected_effect=deck.psychology_effect,
            ),
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
            version=3,
        )

    def generate_briefs(self, records: list[CatalogRecord]) -> list[Brief]:
        return [self.generate_brief(record) for record in records]
