# جعبه‌ابزار محتوای فارسی — PersianToolbox Content Factory

**نسخه ۱.۱.۵** | AGPL-3.0-only

## خلاصه

سیستم تولید محتوای اجتماعی **کاملاً deterministic** برای سایت [persiantoolbox.ir](https://persiantoolbox.ir/).

بدون نیاز به API پولی، GPU، یا اینترنت دائمی.

## ویژگی‌ها

- کراولر با نرخ محدود از persiantoolbox.ir
- مولّد محتوای deterministic (بدون AI)
- رندر HTML/CSS/SVG → PNG با Playwright
- موتور ریسک سه‌سطحی (LOW/MEDIUM/HIGH)
- موتور QA خودکار (فارسی، ادعا، منبع، بصری)
- ۵ قالب اجتماعی برای ۳ سایز مختلف
- زمان‌بند محلی (cron/systemd)
- گزارش‌های کامل

## نصب

```bash
# نیازمندی‌ها
python3 --version  # ≥ 3.11
uv --version       # ≥ 0.10

# نصب پروژه
cd persiantoolbox-content-factory
uv venv
uv pip install -e ".[dev]"

# نصب Playwright
playwright install chromium
```

## استفاده

```bash
# کراول ابزارها
ptb-content crawl --pilot

# تولید محتوا
ptb-content generate --count 4

# رندر تصاویر
ptb-content render

# بررسی کیفیت
ptb-content qa

# بنچمارک provider
ptb-content benchmark

# نمایش زمان‌بندی
ptb-content schedule

# گزارش نهایی
ptb-content report
```

## ساختار پروژه

```
├── config/           # تنظیمات برند، کراولر، provider، ریسک
├── schemas/          # JSON Schema برای اعتبارسنجی
├── prompts/          # راهنمای اجرا (YOLO-AGENT-FA.md)
├── src/ptb_content/  # کد اصلی
│   ├── crawler/      # کراولر وب
│   ├── generator/    # مولّد محتوا
│   ├── renderer/     # رندر HTML/CSS → PNG
│   ├── qa/           # بررسی کیفیت
│   ├── risk/         # موتور ریسک
│   ├── providers/    # بنچمارک provider
│   ├── scheduler/    # زمان‌بند محلی
│   └── utils/        # ابزارهای متن فارسی
├── tests/            # تست‌ها
├── data/             # داده‌های کراول‌شده
├── outputs/          # خروجی‌های تولید شده
└── reports/          # گزارش‌ها
```

## محدودیت‌ها

- **بدون انتشار خودکار** — هر انتشار نیاز به تأیید صریح انسانی دارد
- **بدون محتوای مالی/حقوقی بدون بازبینی** — این محتواها همیشه ESCALATE می‌شوند
- **بدون testimonial ساختگی** — ادعاها باید source_id داشته باشند
- **بدون API پولی** — حالت اولیه همیشه deterministic کار می‌کند
- **اگر کامپیوتر خاموش باشد**، زمان‌بند اجرا نمی‌شود

## مجوز

AGPL-3.0-only — هرگونه استفاده باید متن‌باز باشد.
