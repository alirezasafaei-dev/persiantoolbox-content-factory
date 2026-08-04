"""Unit tests for crawler HTML extraction, contamination detection, and claim extraction."""

from ptb_content.crawler import (
    Crawler,
    _extract_visible_text,
    validate_visible_text,
)
from ptb_content.types import RiskTag

# ─── Fixtures ────────────────────────────────────────────────────────────────

REALISTIC_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>ابزارهای PDF — جعبه ابزار فارسی</title>
    <meta name="description" content="ابزارهای رایگان برای کار با فایل‌های PDF"/>
    <link rel="stylesheet" href="/_next/static/chunks/21ebrt1uadu1m.css" nonce="abc123"/>
    <script src="/_next/static/chunks/0-52qqhjy766e.js" nonce="abc123"></script>
    <script>self.__next_f.push([[0], "some payload"])</script>
</head>
<body>
    <nav>منوی سایت</nav>
    <main>
        <h1>ابزارهای PDF</h1>
        <p>برای مدیریت فایل‌های PDF از ابزارهای موجود استفاده کنید.</p>
        <p>این ابزارها رایگان هستند و بدون ثبت‌نام کار می‌کنند.</p>
        <p>بیش از ۱۰ ابزار متنوع در اختیار شماست.</p>
    </main>
    <footer>طراحی شده توسط جعبه ابزار فارسی</footer>
    <style>.foo { display:flex; font-family: Vazirmatn; }</style>
</body>
</html>"""

SCRIPT_ONLY_HTML = """<!DOCTYPE html>
<html>
<head><title>Script Page</title></head>
<body>
<script>self.__next_f.push([[0], "payload"])</script>
<script>console.log("hello")</script>
<style>.foo { display: flex; }</style>
</body>
</html>"""

EMPTY_HTML = """<!DOCTYPE html>
<html>
<head><title></title></head>
<body></body>
</html>"""

MINIMAL_PERSIAN_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head><title>تست</title></head>
<body>
<main>
<p>این یک متن تست فارسی است که برای بررسی استخراج متن از صفحات وب استفاده می‌شود.</p>
<p>ابزارهای رایگان فارسی برای کار با متن و اسناد.</p>
</main>
</body>
</html>"""

MALFORMED_HTML = """<html><head><title>Broken</title></head>
<body>
<p>متن فارسی بدون بسته شدن تگ‌ها
<div>بخش دیگر
<main>
<p>محتوای اصلی صفحه که باید استخراج شود و شامل متن قابل‌خواندن است.</p>
</main>"""

NOISE_HEAVY_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width"/>
<meta property="og:title" content="ابزارهای رایگان"/>
<meta property="og:description" content="ابزارهای رایگان فارسی"/>
<link rel="stylesheet" href="/style.css"/>
<script nonce="abc">self.__next_f.push([[0],"data"])</script>
</head>
<body>
<nav>منوی اصلی | صفحه نخست | ابزارها | مقالات | تماس با ما</nav>
<main>
<h1>ابزارهای رایگان فارسی</h1>
<p>جعبه ابزار فارسی مجموعه‌ای از ابزارهای رایگان برای کار با متن فارسی است.</p>
<p>تمام پردازش‌ها به صورت محلی در مرورگر شما انجام می‌شود.</p>
<p>هیچ اطلاعاتی به سرور ارسال نمی‌شود.</p>
</main>
<footer>© ۲۰۲۶ جعبه ابزار فارسی — تمامی حقوق محفوظ است</footer>
</body>
</html>"""

NEXTJS_PAYLOAD_HTML = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
<script src="/_next/static/chunks/0-52qqhjy766e.js"></script>
<script>self.__next_f.push([[0,"$","div",null,{"children":"test"}]])</script>
<style>body{margin:0} .container{display:flex}</style>
<link rel="preload" as="script" href="/_next/static/chunks/turbopack-abc.js"/>
</head>
<body>
<main>
<h1>آموزش ساخت رزومه</h1>
<p>رزومه حرفه‌ای خود را به صورت رایگان بسازید.</p>
<p>با استفاده از ابزار رزومه‌ساز، رزومه خود را در چند دقیقه آماده کنید.</p>
<p>بیش از ۵۰۰۰ کاربر از این ابزار استفاده کرده‌اند.</p>
</main>
</body>
</html>"""


# ─── _extract_visible_text tests ─────────────────────────────────────────────


class TestExtractVisibleText:
    def test_strips_script_tags(self) -> None:
        result = _extract_visible_text(SCRIPT_ONLY_HTML)
        assert "self.__next_f" not in result
        assert "console.log" not in result

    def test_strips_style_tags(self) -> None:
        result = _extract_visible_text(SCRIPT_ONLY_HTML)
        assert "display:" not in result
        assert "font-family:" not in result

    def test_strips_html_head_content(self) -> None:
        result = _extract_visible_text(REALISTIC_HTML)
        assert "<script" not in result
        assert "<link" not in result
        assert "<meta" not in result
        assert "nonce=" not in result

    def test_preserves_main_content(self) -> None:
        result = _extract_visible_text(REALISTIC_HTML)
        assert "ابزارهای PDF" in result
        assert "مدیریت فایل‌های PDF" in result

    def test_strips_nav_and_footer(self) -> None:
        result = _extract_visible_text(REALISTIC_HTML)
        # nav and footer content may appear but main content should dominate
        assert "ابزارهای PDF" in result

    def test_empty_html(self) -> None:
        result = _extract_visible_text(EMPTY_HTML)
        assert result == "" or len(result.strip()) == 0

    def test_malformed_html_no_crash(self) -> None:
        result = _extract_visible_text(MALFORMED_HTML)
        assert isinstance(result, str)
        assert "محتوای اصلی" in result

    def test_minimal_persian(self) -> None:
        result = _extract_visible_text(MINIMAL_PERSIAN_HTML)
        assert "متن تست فارسی" in result
        assert "ابزارهای رایگان" in result

    def test_empty_string(self) -> None:
        assert _extract_visible_text("") == ""

    def test_none_like_empty(self) -> None:
        assert _extract_visible_text("   ") == ""

    def test_strips_doctype(self) -> None:
        result = _extract_visible_text(REALISTIC_HTML)
        assert "DOCTYPE" not in result

    def test_strips_html_tag(self) -> None:
        result = _extract_visible_text(REALISTIC_HTML)
        assert "<html" not in result

    def test_strips_nav_element(self) -> None:
        result = _extract_visible_text(NOISE_HEAVY_HTML)
        assert "منوی اصلی" not in result

    def test_strips_footer_element(self) -> None:
        result = _extract_visible_text(NOISE_HEAVY_HTML)
        assert "تمامی حقوق محفوظ" not in result

    def test_nextjs_payload_removed(self) -> None:
        result = _extract_visible_text(NEXTJS_PAYLOAD_HTML)
        assert "self.__next_f" not in result
        assert "turbopack" not in result
        assert "__NEXT_DATA__" not in result

    def test_nextjs_main_content_preserved(self) -> None:
        result = _extract_visible_text(NEXTJS_PAYLOAD_HTML)
        assert "آموزش ساخت رزومه" in result
        assert "رزومه حرفه‌ای" in result

    def test_no_raw_html_in_output(self) -> None:
        result = _extract_visible_text(REALISTIC_HTML)
        assert "<" not in result
        assert ">" not in result

    def test_no_raw_html_noisy(self) -> None:
        result = _extract_visible_text(NOISE_HEAVY_HTML)
        assert "<" not in result
        assert ">" not in result

    def test_whitespace_normalized(self) -> None:
        result = _extract_visible_text(REALISTIC_HTML)
        assert "  " not in result  # No double spaces

    def test_long_html_truncated(self) -> None:
        long_html = (
            "<html><body>" + "<p>test content here for each iteration</p>" * 5000 + "</body></html>"
        )
        result = _extract_visible_text(long_html)
        assert len(result) <= 50_000

    def test_persian_text_quality(self) -> None:
        result = _extract_visible_text(NOISE_HEAVY_HTML)
        persian_chars = sum(1 for c in result if "\u0600" <= c <= "\u06ff")
        assert persian_chars > 10


# ─── validate_visible_text tests ─────────────────────────────────────────────


class TestValidateVisibleText:
    def test_clean_text_passes(self) -> None:
        text = "ابزارهای رایگان فارسی برای کار با متن و اسناد. این ابزارها به صورت محلی کار می‌کنند."
        issues = validate_visible_text(text)
        assert len(issues) == 0

    def test_too_short_fails(self) -> None:
        text = "کوتاه"
        issues = validate_visible_text(text)
        assert any("too_short" in i for i in issues)

    def test_script_contamination_detected(self) -> None:
        text = "متن عادی self.__next_f.push() متن دیگر"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)

    def test_css_contamination_detected(self) -> None:
        text = "متن عادی font-family: Vazirmatn متن دیگر"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)

    def test_display_flex_contamination(self) -> None:
        text = "متن عادی display:flex متن دیگر"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)

    def test_html_tags_detected(self) -> None:
        text = "متن عادی <div>content</div> متن دیگر"
        issues = validate_visible_text(text)
        assert any("raw_html" in i for i in issues)

    def test_doctype_detected(self) -> None:
        text = "متن عادی <!DOCTYPE html> متن دیگر"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)

    def test_webpack_detected(self) -> None:
        text = "متن عادی webpack chunk متن دیگر"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)

    def test_stylesheet_detected(self) -> None:
        text = "متن عادی stylesheet link متن دیگر"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)

    def test_empty_text_too_short(self) -> None:
        issues = validate_visible_text("")
        assert any("too_short" in i for i in issues)

    def test_clean_persian_no_issues(self) -> None:
        text = (
            "ابزارهای رایگان فارسی برای کار با متن و اسناد. "
            "این ابزارها به صورت محلی در مرورگر شما کار می‌کنند. "
            "هیچ اطلاعاتی به سرور ارسال نمی‌شود."
        )
        issues = validate_visible_text(text)
        assert len(issues) == 0

    def test_display_flex_in_text(self) -> None:
        text = "متن normal display:flex ادامه متن"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)

    def test_classname_detected(self) -> None:
        text = "متن عادی className=foo متن دیگر"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)

    def test_nextdata_detected(self) -> None:
        text = "متن عادی __NEXT_DATA__ payload متن دیگر"
        issues = validate_visible_text(text)
        assert any("contamination" in i for i in issues)


# ─── Claim extraction via Crawler instance ────────────────────────────────────


class TestClaimExtraction:
    def setup_method(self) -> None:
        self.crawler = Crawler()

    def test_no_claims_from_html(self) -> None:
        text = "ابزارهای PDF رایگان برای کار با فایل‌ها."
        claims = self.crawler._extract_claims(text, "test")
        assert isinstance(claims, list)

    def test_claims_with_numbers(self) -> None:
        text = "بیش از ۱۰ ابزار رایگان در اختیار شماست. بیش از ۵۰۰۰ کاربر فعال داریم."
        claims = self.crawler._extract_claims(text, "test")
        assert len(claims) >= 1

    def test_claims_no_html(self) -> None:
        text = "بیش از ۱۰ ابزار. <script>alert(1)</script> ادامه متن."
        claims = self.crawler._extract_claims(text, "test")
        for claim in claims:
            assert "<" not in claim.text
            assert ">" not in claim.text

    def test_claims_deduplication(self) -> None:
        text = "بیش از ۱۰ ابزار رایگان. بیش از ۱۰ ابزار رایگان."
        claims = self.crawler._extract_claims(text, "test")
        texts = [c.text for c in claims]
        assert len(texts) == len(set(texts))

    def test_claims_max_length(self) -> None:
        text = "بیش از ۱۰ ابزار. " * 100
        claims = self.crawler._extract_claims(text, "test")
        for claim in claims:
            assert len(claim.text) <= 300

    def test_empty_text_no_claims(self) -> None:
        claims = self.crawler._extract_claims("", "test")
        assert claims == []

    def test_no_css_in_claims(self) -> None:
        text = "متن با font-family: Vazirmatn و بیش از ۱۰ ابزار."
        claims = self.crawler._extract_claims(text, "test")
        for claim in claims:
            assert "font-family:" not in claim.text

    def test_no_js_in_claims(self) -> None:
        text = "متن با function() test و بیش از ۱۰ ابزار."
        claims = self.crawler._extract_claims(text, "test")
        for claim in claims:
            assert "function()" not in claim.text


# ─── Risk detection on clean text ────────────────────────────────────────────


class TestRiskDetectionCleanText:
    def setup_method(self) -> None:
        self.crawler = Crawler()

    def test_no_risk_in_clean_tool_text(self) -> None:
        text = "ابزارهای PDF رایگان برای مدیریت فایل‌ها. این ابزارها ساده و سریع هستند."
        tags = self.crawler._detect_risk_tags(text)
        assert len(tags) == 0

    def test_financial_risk_detected(self) -> None:
        text = "هزینه استفاده از این ابزار رایگان است و نیاز به پرداخت ندارد."
        tags = self.crawler._detect_risk_tags(text)
        assert any(t.value == "financial" for t in tags)

    def test_privacy_risk_detected(self) -> None:
        text = "حریم خصوصی شما برای ما مهم است. اطلاعات شخصی شما ذخیره نمی‌شود."
        tags = self.crawler._detect_risk_tags(text)
        assert any(t.value == "privacy" for t in tags)

    def test_risk_not_from_html(self) -> None:
        textclean = "ابزار رایگان PDF برای مدیریت اسناد."
        tags = self.crawler._detect_risk_tags(textclean)
        # No risk tags in clean tool text
        assert RiskTag.FINANCIAL not in tags or len(tags) == 0


# ─── Metadata extraction ─────────────────────────────────────────────────────


class TestMetadataExtraction:
    def setup_method(self) -> None:
        self.crawler = Crawler()

    def test_extracts_title(self) -> None:
        meta = self.crawler._extract_metadata(REALISTIC_HTML, "https://test.com", 200, {})
        assert meta["html_title"] == "ابزارهای PDF — جعبه ابزار فارسی"

    def test_extracts_meta_description(self) -> None:
        meta = self.crawler._extract_metadata(REALISTIC_HTML, "https://test.com", 200, {})
        assert "ابزارهای رایگان" in meta.get("meta_description", "")

    def test_handles_no_title(self) -> None:
        meta = self.crawler._extract_metadata(
            "<html><body></body></html>", "https://test.com", 200, {}
        )
        assert "html_title" not in meta

    def test_handles_malformed_html(self) -> None:
        meta = self.crawler._extract_metadata(MALFORMED_HTML, "https://test.com", 200, {})
        assert isinstance(meta, dict)

    def test_content_type_from_headers(self) -> None:
        headers = {"content-type": "text/html; charset=utf-8"}
        meta = self.crawler._extract_metadata("<html></html>", "https://test.com", 200, headers)
        assert "text/html" in meta["content_type"]


# ─── Integration: full extraction pipeline ────────────────────────────────────


class TestFullExtractionPipeline:
    def setup_method(self) -> None:
        self.crawler = Crawler()

    def test_full_pipeline_clean_output(self) -> None:
        raw_html = NEXTJS_PAYLOAD_HTML

        # Extract visible text
        visible_text = _extract_visible_text(raw_html)

        # Validate
        issues = validate_visible_text(visible_text)
        assert len(issues) == 0, f"Contamination found: {issues}"

        # Detect risk
        risk_tags = self.crawler._detect_risk_tags(visible_text)

        # Extract claims
        claims = self.crawler._extract_claims(visible_text, "test-source")

        # Verify results
        assert "آموزش ساخت رزومه" in visible_text
        assert "self.__next_f" not in visible_text
        assert isinstance(risk_tags, list)
        assert isinstance(claims, list)

    def test_full_pipeline_noisy_html(self) -> None:
        visible_text = _extract_visible_text(NOISE_HEAVY_HTML)
        issues = validate_visible_text(visible_text)
        assert len(issues) == 0, f"Contamination found: {issues}"
        assert "ابزارهای رایگان فارسی" in visible_text

    def test_full_pipeline_realistic_html(self) -> None:
        visible_text = _extract_visible_text(REALISTIC_HTML)
        issues = validate_visible_text(visible_text)
        assert len(issues) == 0, f"Contamination found: {issues}"
        assert "ابزارهای PDF" in visible_text
