# مشکلات باز — PersianToolbox Content Factory

**تاریخ:** 2026-07-31 (بازنگری شده)

## مشکلات حل‌شده

| # | مشکل | وضعیت | تاریخ حل |
|---|-------|-------|----------|
| 1 | Playwright نصب نبود | ✅ نصب شد | 2026-07-31 |
| 2 | Golden set ناقص بود | ✅ ۵۰ brief تکمیل شد | 2026-07-31 |
| 3 | Scheduler فعال نبود | ✅ dry-run موفق + آماده نصب | 2026-07-31 |
| 4 | Review Gallery ساخته نشده بود | ✅ تعاملی با PNG | 2026-07-31 |
| 5 | تست RTL و overflow نبود | ✅ ۲۴ تست snapshot اضافه شد | 2026-07-31 |
| 6 | Approval gate نبود | ✅ ۱۹ تست + MockPublisher | 2026-07-31 |
| 7 | گزارش‌ها stale بودند | ✅ همگام‌سازی شدند | 2026-07-31 |

## محدودیت‌های واقعی باقی‌مانده

| # | محدودیت | توضیح | اولویت |
|---|---------|-------|--------|
| 1 | AI Horde ممکن است از ایران قابل دسترسی نباشد | نیاز به تست واقعی با VPN | پایین |
| 2 | Blog post URLها timeout می‌خورند | بعضی URLهای طولانی ۶۰s timeout دارند | پایین |
| 3 | Scheduler هنوز نصب نشده | dry-run موفق، نیاز به تأیید کاربر برای crontab | متوسط |

## وضعیت فعلی

- ✅ ۱۱۵ تست سبز
- ✅ Ruff clean
- ✅ Playwright نصب و فعال
- ✅ ۸۱ PNG رندر شده
- ✅ ۵۰ Golden Set تکمیل
- ✅ Review Gallery تعاملی
- ✅ Approval Gate کامل
- ✅ Snapshot Regression Tests
- ✅ Scheduler Dry-Run موفق
