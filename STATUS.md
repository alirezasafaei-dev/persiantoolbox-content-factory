# وضعیت پروژه — PersianToolbox Content Factory

**آخرین بروزرسانی:** 2026-07-31T18:20:00+03:30
**نسخه:** 0.2.0
**وضعیت کلی:** ✅ آماده برای تولید محتوای واقعی — انتشار غیرفعال

## خلاصه

سیستم تولید محتوای اجتماعی **کاملاً deterministic** برای سایت persiantoolbox.ir.
بدون نیاز به API پولی، GPU، یا اینترنت دائمی.

## وضعیت مراحل

| مرحله | وضعیت | جزئیات |
|-------|-------|--------|
| Preflight | ✅ | اطلاعات سیستم ثبت شد |
| Crawl | ✅ | ۱۸ آیتم از سایت واقعی کراول شد |
| Visual Identity | ✅ | brand.yaml + ۵ قالب |
| Provider Benchmark | ✅ | deterministic + AI Horde + Ollama |
| Generation & QA | ✅ | pipeline کامل |
| Golden Set | ✅ | ۵۰ brief امنیتی |
| Risk Engine | ✅ | ESCALATE + امنیت محتوا |
| Playwright Render | ✅ | ۲۲۸ PNG رندر شد |
| Edge Case Tests | ✅ | prompt injection, duplicate, fallback, timeout |
| Snapshot Regression | ✅ | ۳ baseline + ۲۴ تست |
| Approval Gate | ✅ | ۱۹ تست + MockPublisher |
| Review Gallery | ✅ | تعاملی با PNG جاسازی‌شده |
| Scheduler | ✅ | ۴ cron entry نصب شد |
| Approval Workflow | ✅ | CLI approve/revoke/publish |
| گزارش‌ها | ✅ | ۵ گزارش بروزرسانی شد |
| Publish | ✅disabled | انتشار خودکار غیرفعال |

## آمار

| مورد | مقدار |
|------|-------|
| تست‌ها | ۱۱۵ سبز |
| Ruff | سبز |
| آیتم‌های کراول | ۱۸ |
| Brief تولید شده | ۱۸ |
| Golden Set | ۵۰ |
| Approvals | ۷۱ |
| ESCALATE | ۱۸ (۱۰۰٪) |
| Provider فعال | deterministic |
| قالب‌ها | ۵ |
| سایزها | ۳ |
| PNG رندر شده | ۲۲۸ |
| Snapshot Baselines | ۳ |
| Cron Entries | ۴ |

## CLI دستورات

```bash
# مدیریت scheduler
ptb-content schedule --dry-run    # بررسی بدون نصب
ptb-content schedule --install   # نصب cron
ptb-content schedule --uninstall # حذف cron

# مدیریت approval
ptb-content approve <brief_id>   # تأیید
ptb-content revoke <brief_id>    # لغو تأیید
ptb-content publish <brief_id>   # انتشار (mock)

# نمایش وضعیت
ptb-content status               # آمار کلی
```

## Rollback

```bash
# حذف scheduler
ptb-content schedule --uninstall

# حذف approvals
rm -rf data/approvals/

# حذف خروجی‌ها
rm -rf outputs/ data/catalog/

# برگشت به کد قبلی
git checkout main
```
