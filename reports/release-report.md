# Release Report — PersianToolbox Content Factory

**تاریخ:** 2026-07-31
**نسخه:** 0.2.0
**وضعیت انتشار:** `disabled` (انتشار خودکار غیرفعال)
**Commit SHA:** `a87e54f`

## مشخصات

| مورد | مقدار |
|------|-------|
| Commit SHA | `a87e54f` |
| Python | 3.12.13 |
| Platform | Linux x86_64 |
| Playwright | Chromium 150 (`/snap/bin/chromium`) |

## دستورات اجراشده

```bash
# QA Gate
.venv/bin/ruff check src/ tests/         # All checks passed
.venv/bin/pytest -q                      # 115 passed

# Scheduler
.venv/bin/ptb-content schedule --dry-run # All 4 jobs valid
ptb-content schedule --install           # SUCCESS (4 cron entries)

# Pipeline
ptb-content crawl --pilot                # 18 items crawled
ptb-content generate --count 18          # 18 briefs
ptb-content qa                           # 18 ESCALATE
ptb-content render                       # 54 PNGs (18×3)
ptb-content approve <brief_id>           # Approval saved
ptb-content publish <brief_id>           # Mock publish (blocked/published)
```

## آمار نهایی

| مورد | مقدار |
|------|-------|
| تست‌ها | ۱۱۵ سبز |
| Ruff | سبز |
| PNG رندر شده | ۲۲۸ |
| Brief تولید شده | ۱۸ |
| Golden Set | ۵۰ |
| Approvals ذخیره شده | ۷۱ |
| ESCALATE | ۱۸ (۱۰۰٪) |
| Provider فعال | deterministic |
| قالب‌ها | ۵ |
| سایزها | ۳ (1080×1350, 1080×1080, 1080×1920) |
| Snapshot Baselines | ۳ |
| Cron Entries | ۴ |

## وضعیت انتشار

**`disabled`** — انتشار خودکار غیرفعال. تمام انتشارها نیاز به تأیید صریح انسانی دارند.

### Publish Gates

| Gate | وضعیت |
|------|-------|
| PTB_AUTO_PUBLISH | `false` |
| Approval Gate | فعال (fail-closed) |
| MockPublisher | فعال (تست‌ها) |
| Checksum Validation | فعال (file-based) |
| Expiry Check | فعال (۷ روز) |
| Version Check | فعال |
| Lockfile | فعال (/tmp/ptb-content-factory/) |

### فعال‌سازی انتشار

```bash
# ۱. تأیید brief
ptb-content approve brief-xxxxxxxxxxxx --reviewer admin

# ۲. انتشار (mock)
ptb-content publish brief-xxxxxxxxxxxx

# ۳. لغو تأیید
ptb-content revoke brief-xxxxxxxxxxxx

# ۴. غیرفعال کردن scheduler
ptb-content schedule --uninstall
```

## فایل‌های کلیدی

| فایل | مسیر |
|------|------|
| Release Report | `reports/release-report.md` |
| Test Report | `reports/test-report.txt` |
| Security Report | `reports/security-report.md` |
| Pilot Report | `reports/pilot-report.md` |
| Open Issues | `reports/open-issues.md` |
| Scheduler Dry-Run | `reports/scheduler-dry-run.json` |
| Review Gallery | `outputs/review-gallery.html` |
| Golden Set | `outputs/golden/` (۵۰ فایل) |
| Briefs | `outputs/briefs/` (۱۸ فایل) |
| PNGs | `outputs/*/feed-*.png` (۲۲۸ فایل) |
| Snapshots | `tests/baselines/snapshot-test/` (۳ فایل) |
| Approvals | `data/approvals/` (۷۱ فایل) |
| Cron Entries | system crontab (۴ entry) |
