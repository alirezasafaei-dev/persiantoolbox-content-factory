# گزارش Pilot — PersianToolbox Content Factory

**تاریخ:** 2026-07-31 (بازنگری شده)
**نسخه:** 0.2.0

## خلاصه اجرا

| مورد | مقدار |
|------|-------|
| آیتم‌های کراول‌شده | ۱۸ |
| Brief تولید شده | ۱۸ |
| QA PASS | ۰ |
| QA FAIL | ۰ |
| QA ESCALATE | ۱۸ (۱۰۰٪) |
| مدت کراول | ۱۷.۲۱s |
| Provider انتخابی | deterministic |
| PNG رندر شده | ۸۱ (۱۸ × ۳ سایز) |
| Golden Set | ۵۰ brief |
| تست‌ها | ۱۱۵ سبز |

## محتوای کراول شده

از سایت persiantoolbox.ir صفحات زیر کراول شدند:

- صفحه اصلی (/)
- بلاگ (/blog)
- درباره ما (/about)
- قیمت‌ها (/pricing)
- ابزارهای تخصصی (/tools/specialized)
- ابزارهای PDF (/pdf-tools/uses)
- ابزارهای کسب‌وکار (/business-tools)
- استودیو سند (/business-tools/document-studio)
- ابزارهای شغلی (/career-tools)
- سازنده رزومه (/career-tools/resume-builder)
- ابزارهای نگارش (/writing-tools)
- استودیو نگارش فارسی (/writing-tools/persian-writing-studio)
- موضوعات: اعتبارسنجی، قراردادها، کسب‌وکار، شغلی، نگارش، سئو

## نتایج Risk Engine

تمام ۱۸ آیتم ESCALATE شدند زیرا محتوای صفحات شامل کلمات کلیدی مالی/امنیتی/حقوقی است. این رفتار صحیح است — محتوای واقعی باید قبل از انتشار بازبینی شود.

## Playwright Rendering

- ۸۱ PNG با موفقیت رندر شد
- سایزها: 1080×1350, 1080×1080, 1080×1920
- RTL direction: ✓
- فونت Vazirmatn با fallback Tahoma: ✓
- Overflow handling (overflow:hidden): ✓
- CTA button placement: ✓

## Golden Set

- ۵۰ brief مرجع با ۵ دسته:
  - ۱۰ tool demos
  - ۱۰ PDF tutorials
  - ۱۰ Persian text
  - ۱۰ professional
  - ۵ privacy/financial/legal
- همه HIGH-risk briefs ESCALATE تأیید شدند

## Approval Gate

- ESCALATE بدون تأیید: مسدود ✓
- FAIL تحت هر شرایط: مسدود ✓
- Checksum نامعتبر: مسدود ✓
- Approval منقضی: مسدود ✓
- Version mismatch: مسدود ✓
- MockPublisher: هیچ انتشار خارجی انجام نمی‌دهد ✓

## Scheduler

- Dry-run موفق (۴ job)
- Lockfile برای جلوگیری از اجرای همزمان
- مسیرهای absolute برای Python, working dir, log dir
- آماده نصب (نیاز به تأیید کاربر)
