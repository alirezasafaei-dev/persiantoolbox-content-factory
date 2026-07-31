# گزارش امنیت — PersianToolbox Content Factory

**تاریخ:** 2026-07-31 (بازنگری شده)
**نسخه:** 0.2.0

## بررسی امنیتی

### ۱. Credential و Secret

- ✅ هیچ secret یا credential در کد، log یا prompt قرار ندارد
- ✅ متغیرهای محیطی برای auth استفاده می‌شوند (AI_HORDE_API_KEY)
- ✅ tokenها در کد hardcode نشده‌اند

### ۲. Prompt Injection

- ✅ HTML سایت به‌عنوان untrusted data رفتار می‌شود
- ✅ هیچ دستوری از HTML اجرا نمی‌شود
- ✅ metadata extraction فقط regex ساده است (نه eval/exec)
- ✅ تست‌های prompt injection اضافه شد (title, meta, OG tags)

### ۳. Rate Limiting

- ✅ کراولر: concurrency ≤ 2, rate ≤ 1 rps
- ✅ timeout ≤ 60s
- ✅ bounded retries (3 بار)

### ۴. Data Handling

- ✅ اطلاعات کاربر ذخیره نمی‌شود
- ✅ فایل‌های مالی/حقوقی همیشه ESCALATE می‌شوند
- ✅ testimonial ساختگی ممنوع است
- ✅ هر claim باید source_id داشته باشد

### ۵. Publishing Safety

- ✅ انتشار خودکار غیرفعال (fail-closed)
- ✅ نیاز به approval صریح انسانی
- ✅ PTB_AUTO_PUBLISH پیش‌فرض false
- ✅ checksums قبل از انتشار اعتبارسنجی می‌شوند
- ✅ Approval Gate: ESCALATE/FAIL/checksum/expiry/version همه تست شد
- ✅ MockPublisher: هیچ انتشار خارجی در تست‌ها انجام نمی‌شود
- ✅ Brief تغییر یافته پس از approval → approval باطل می‌شود

### ۶. Dependency Safety

- ✅ تمام وابستگی‌ها open-source و AGPL-compatible
- ✅ بدون API پولی اجباری
- ✅ Playwright فقط برای رندر local استفاده می‌شود

### ۷. File System

- ✅ فایل‌ها فقط در پروژه محلی ذخیره می‌شوند
- ✅ تصاویر رندر شده local هستند
- ✅ هیچ فایلی به سرور خارجی ارسال نمی‌شود

### ۸. Scheduler Safety

- ✅ Lockfile برای جلوگیری از اجرای همزمان
- ✅ Dry-run قبل از نصب
- ✅ PTB_AUTO_PUBLISH=false باقی می‌ماند
- ✅ هیچ محتوایی بدون approval صریح منتشر نمی‌شود
- ✅ Exit code غیرصفر در صورت خطا

### ۹. Snapshot Regression

- ✅ Baseline PNGها ذخیره شدند
- ✅ تغییرات ناخواسته در RTL، overflow، clipping، CTA، فونت تشخیص داده می‌شود
- ✅ Baseline فقط با دستور صریح به‌روزرسانی می‌شود

### نتیجه‌گیری

سیستم از نظر امنیتی در وضعیت قابل قبولی قرار دارد. نقاط قوت:
- Privacy-first architecture
- Deterministic fallback
- Human-in-the-loop for publishing
- No hardcoded secrets
- Approval Gate کامل (checksum, expiry, version, fail-closed)
- Snapshot regression detection

نقطه ضعف شناخته‌شده:
- AI Horde ممکن است از ایران قابل دسترسی نباشد
