"""Generate golden set of 50 reference briefs."""

import json
import sys
from pathlib import Path

sys.path.insert(0, "src")

from ptb_content.types import (
    CatalogRecord, Category, Claim, RiskTag, RiskLevel, RiskDecision,
    Audience, ContentStrategy, PsychologyHypothesis, Caption, ArtDirection,
    ColorPalette, Typography, Brief, generate_id, utcnow,
    TemplateType, HookType,
)
from ptb_content.risk import RiskEngine

risk_engine = RiskEngine()
brand_colors = ColorPalette()
brand_typo = Typography()

PROFESSIONAL_SEGMENTS = [
    "مدیران", "تیم‌ها", "فریلنسرها", "دانشجویان", "حسابداران"
]

TOOL_TOPICS = [
    "متن فارسی", "تاریخ شمسی", "PDF", "تصویر", "JSON"
]

PDF_ACTIONS = [
    "ادغام", "فشرده‌سازی", "تبدیل", "ویرایش", "OCR"
]

PERSIAN_TOPICS = [
    "نیم‌فاصله", "املای فارسی", "تبدیل اعداد", "ترتیب کلمات", "نرم‌افزار فارسی"
]

PRIVACY_TOPICS = [
    "پردازش محلی", "بدون سرور", "رمزنگاری", "داده شخصی", "امنیت فایل"
]

FINANCIAL_DATA = [
    ("محاسبه مالیات حقوق", "راهنمای محاسبه مالیات حقوق در سال ۱۴۰۵", RiskTag.FINANCIAL),
    ("قانون کار", "مروری بر مهم‌ترین مفاد قانون کار", RiskTag.LEGAL),
    ("نرخ سود بانکی", "مقایسه نرخ سود بانک‌های مختلف", RiskTag.STATISTICAL),
    ("هزینه استخدام", "محاسبه هزینه واقعی استخدام", RiskTag.FINANCIAL),
    ("بیمه تامین اجتماعی", "راهنمای کامل بیمه تامین اجتماعی", RiskTag.LEGAL),
]


def make_brief(
    title: str,
    summary: str,
    category: Category,
    source_id: str,
    audience_seg: str,
    pain: str,
    desire: str,
    hook: HookType,
    template: TemplateType,
    risk_tags: list[RiskTag] | None = None,
) -> Brief:
    cr = CatalogRecord(
        canonical_url=f"https://persiantoolbox.ir/golden/{source_id}",
        title=title,
        summary=summary,
        category=category,
        source_id=source_id,
        source_hash="a" * 64,
        crawled_at=utcnow(),
        risk_tags=risk_tags or [],
    )
    level, decision = risk_engine.assess(cr)
    return Brief(
        brief_id=generate_id("golden"),
        catalog_record=cr,
        audience=Audience(segment=audience_seg, pain_point=pain, desire=desire),
        content_strategy=ContentStrategy(angle=title, hook_type=hook, template_type=template),
        psychology_hypothesis=PsychologyHypothesis(principle="تست", expected_effect="تست"),
        caption=Caption(primary=f"{title} — {summary[:50]}", cta="همین حالا امتحان کن"),
        art_direction=ArtDirection(template=template, color_palette=brand_colors, typography=brand_typo),
        risk_level=level,
        risk_decision=decision,
    )


def main() -> None:
    briefs: list[Brief] = []

    # 10 tool demos
    for i in range(10):
        briefs.append(make_brief(
            title=f"ابزار رایگان {TOOL_TOPICS[i % 5]}",
            summary=f"توضیحات ابزار رایگان برای {TOOL_TOPICS[i % 5]}",
            category=Category.TOOL_DEMO,
            source_id=f"golden-tool-{i+1}",
            audience_seg="کاربران عمومی",
            pain="ابزارهای پیچیده",
            desire="سادگی",
            hook=HookType.DIRECT,
            template=TemplateType.TOOL_DEMO,
        ))

    # 10 PDF tutorials
    for i in range(10):
        briefs.append(make_brief(
            title=f"آموزش {PDF_ACTIONS[i % 5]} PDF",
            summary=f"راهنمای {PDF_ACTIONS[i % 5]} فایل PDF",
            category=Category.PDF_TUTORIAL,
            source_id=f"golden-pdf-{i+1}",
            audience_seg="کاربران اداری",
            pain="پیچیدگی PDF",
            desire="آموزش ساده",
            hook=HookType.EDUCATIONAL,
            template=TemplateType.STEP_BY_STEP,
        ))

    # 10 Persian text posts
    for i in range(10):
        briefs.append(make_brief(
            title=f"نکته {PERSIAN_TOPICS[i % 5]}",
            summary=f"نکته مهم درباره {PERSIAN_TOPICS[i % 5]}",
            category=Category.PERSIAN_TEXT,
            source_id=f"golden-persian-{i+1}",
            audience_seg="نویسندگان",
            pain="مشکلات متن فارسی",
            desire="متن تمیز",
            hook=HookType.PROBLEM_SOLUTION,
            template=TemplateType.COMMON_MISTAKE,
        ))

    # 10 professional posts
    for i in range(10):
        briefs.append(make_brief(
            title=f"ابزار حرفه‌ای {PROFESSIONAL_SEGMENTS[i % 5]}",
            summary=f"ابزار مناسب {PROFESSIONAL_SEGMENTS[i % 5]}",
            category=Category.PROFESSIONAL,
            source_id=f"golden-pro-{i+1}",
            audience_seg="مدیران",
            pain="زمان محدود",
            desire="ابزار سریع",
            hook=HookType.DIRECT,
            template=TemplateType.PROFESSIONAL_SEASONAL,
        ))

    # 5 privacy posts
    for i in range(5):
        briefs.append(make_brief(
            title=f"حریم خصوصی {PRIVACY_TOPICS[i]}",
            summary=f"چرا {PRIVACY_TOPICS[i]} مهم است",
            category=Category.PRIVACY,
            source_id=f"golden-privacy-{i+1}",
            audience_seg="کاربران حساس",
            pain="نگرانی حریم خصوصی",
            desire="امنیت",
            hook=HookType.CURIOSITY,
            template=TemplateType.PRIVACY_TRUST,
            risk_tags=[RiskTag.PRIVACY],
        ))

    # 5 financial/legal HIGH-risk posts
    for i, (title, summary, rtag) in enumerate(FINANCIAL_DATA):
        briefs.append(make_brief(
            title=title,
            summary=summary,
            category=Category.FINANCIAL,
            source_id=f"golden-financial-{i+1}",
            audience_seg="حسابداران",
            pain="پیچیدگی مالی",
            desire="دقت",
            hook=HookType.EDUCATIONAL,
            template=TemplateType.PROFESSIONAL_SEASONAL,
            risk_tags=[rtag],
        ))

    # Save
    golden_dir = Path("outputs/golden")
    golden_dir.mkdir(parents=True, exist_ok=True)

    for b in briefs:
        (golden_dir / f"{b.brief_id}.json").write_text(
            json.dumps(b.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    low = sum(1 for b in briefs if b.risk_level == RiskLevel.LOW)
    medium = sum(1 for b in briefs if b.risk_level == RiskLevel.MEDIUM)
    high = sum(1 for b in briefs if b.risk_level == RiskLevel.HIGH)
    escalate = sum(1 for b in briefs if b.risk_decision == RiskDecision.ESCALATE)

    print(f"Golden set: {len(briefs)} briefs")
    print(f"  LOW: {low}, MEDIUM: {medium}, HIGH: {high}")
    print(f"  ESCALATE: {escalate}")

    for b in briefs:
        if b.risk_level == RiskLevel.HIGH:
            assert b.risk_decision == RiskDecision.ESCALATE, f"{b.brief_id} HIGH but not ESCALATE"
    print("All HIGH-risk briefs are ESCALATE ✓")


if __name__ == "__main__":
    main()
