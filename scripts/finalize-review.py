import os

REVIEW_DIR = "outputs/canary-review/brief-1c6fd0618b67"

# Read existing files
b = __import__("json").load(open("%s/brief.json" % REVIEW_DIR))
qa_data = __import__("json").load(open("%s/qa-result.json" % REVIEW_DIR))
claims = __import__("json").load(open("%s/claims.json" % REVIEW_DIR))
cap = open("%s/caption.txt" % REVIEW_DIR).read()
import hashlib

cr = b["catalog_record"]

# PNG info
pngs = {
    "feed-1080x1350.png": (32902, "1080x1350", "86fe6133c953ecb8"),
    "square-1080x1080.png": (31485, "1080x1080", "93cfb66885c515b5"),
    "story-1080x1920.png": (36208, "1080x1920", "c2e3bb3fb23e4174"),
}

has_numbers = any(c.isdigit() for c in cap) or any(d in cap for d in "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9")
has_statistical = any(w in cap for w in ["\u0622\u0645\u0627\u0631", "\u062f\u0631\u0635\u062f", "\u066a", "\u0646\u0631\u062e", "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646"])
has_comparative = any(w in cap for w in ["\u0645\u0642\u0627\u06cc\u0633\u0647", "\u0628\u0647\u062a\u0631\u06cc\u0646", "\u0628\u062f\u062a\u0631\u06cc\u0646", "\u0628\u0631\u062a\u0631", "\u0631\u0642\u06cc\u0628", "\u0628\u06cc\u0634\u062a\u0631", "\u06a9\u0645\u062a\u0631", "\u0633\u0631\u06cc\u0639\u200c\u062a\u0631"])
has_security = any(w in cap for w in ["\u0627\u0645\u0646\u06cc\u062a", "\u0631\u0645\u0632", "\u06af\u0630\u0631\u0648\u0627\u0698\u0647", "\u0647\u06a9", "protect"])
has_privacy = any(w in cap for w in ["\u062d\u0631\u06cc\u0645 \u062e\u0635\u0648\u0635\u06cc", "Privacy", "\u0627\u0637\u0644\u0627\u0639\u0627\u062a \u0634\u062e\u0635\u06cc"])
has_free_claim = any(w in cap for w in ["\u0631\u0627\u06cc\u06af\u0627\u0646", "\u0628\u062f\u0648\u0646 \u0647\u0632\u06cc\u0646\u0647"])
has_guarantee = any(w in cap for w in ["\u062a\u0636\u0645\u06cc\u0646", "\u06af\u0627\u0631\u0627\u0646\u062a\u06cc", "\u0636\u0645\u0627\u0646\u062a"])

all_page_text = cr.get("summary", "") + " " + cr.get("title", "")
statistical_in_caption = has_statistical
statistical_in_page = any(w in all_page_text for w in ["\u0622\u0645\u0627\u0631", "\u062f\u0631\u0635\u062f", "\u066a", "\u0646\u0631\u062e", "\u0645\u06cc\u0627\u0646\u06af\u06cc\u0646"])

md = """# \u0628\u0633\u062a\u0647 \u0628\u0627\u0632\u0628\u06cc\u0646\u06cc \u0627\u0646\u0633\u0627\u0646\u06cc \u2014 brief-1c6fd0618b67

## \u0645\u0634\u062e\u0635\u0627\u062a \u06a9\u0644\u06cc

| \u0645\u0648\u0631\u062f | \u0645\u0642\u062f\u0627\u0631 |
|------|-------|
| Brief ID | brief-1c6fd0618b67 |
| \u0639\u0646\u0648\u0627\u0646 | %s |
| URL \u0645\u0646\u0628\u0639 | %s |
| \u062f\u0633\u062a\u0647\u200c\u0628\u0646\u062f\u06cc | %s |
| Risk Level | %s |
| Risk Decision | %s |
| Risk Tags | %s |
| Visible Text Length | %d |
| Content Hash | %s |

## Caption \u0645\u062a\u0646 \u06a9\u0627\u0645\u0644

%s

## CTA

%s

## Alt Text

%s

## Claims

""" % (
    cr["title"], cr["canonical_url"], cr["category"],
    b["risk_level"], b["risk_decision"], cr.get("risk_tags", []),
    cr.get("visible_text_length", 0), cr.get("content_hash", "N/A")[:16],
    cap, b["caption"].get("cta", ""), b["caption"].get("alt_text", ""),
)

if claims:
    for i, c in enumerate(claims, 1):
        md += "%d. %s\n   - verifiable: %s, confidence: %s\n" % (i, c["text"], c.get("verifiable"), c.get("confidence"))
else:
    md += "\u0628\u062f\u0648\u0646 claim\n"

md += """
## \u0646\u062a\u06cc\u062c\u0647 QA

| Check | Status | Score | Details |
|-------|--------|-------|---------|
"""
for k, v in qa_data["checks"].items():
    md += "| %s | %s | %.1f | %s |\n" % (k, v["status"], v["score"], v["details"][:100])

md += """
## PNG Files

| File | Size | Dimensions | SHA256 |
|------|------|------------|--------|
"""
for fname, (sz, dims, h) in sorted(pngs.items()):
    md += "| %s | %d bytes | %s | %s... |\n" % (fname, sz, dims, h)

md += """\n## \u062a\u062d\u0644\u06cc\u0644 Caption

- **\u0622\u06cc\u0627 Caption \u0634\u0627\u0645\u0644 \u0639\u062f\u062f \u06cc\u0627 \u062f\u0631\u0635\u062f \u0627\u0633\u062a\u061f** %s
- **\u0622\u06cc\u0627 \u0627\u062f\u0639\u0627\u06cc \u0622\u0645\u0627\u0631\u06cc \u062f\u0627\u0631\u062f\u061f** %s
- **\u0622\u06cc\u0627 \u0639\u0628\u0627\u0631\u062a \u0645\u0642\u0627\u06cc\u0633\u0647\u200c\u0627\u06cc (\u0628\u0647\u062a\u0631\u06cc\u0646\u060c \u0633\u0631\u06cc\u0639\u200c\u062a\u0631\u060c \u0628\u06cc\u0634\u062a\u0631) \u062f\u0627\u0631\u062f\u061f** %s
- **\u0622\u06cc\u0627 \u0627\u062f\u0639\u0627\u06cc \u0627\u0645\u0646\u06cc\u062a \u062f\u0627\u0631\u062f\u061f** %s
- **\u0622\u06cc\u0627 \u0627\u062f\u0639\u0627\u06cc \u062d\u0631\u06cc\u0645 \u062e\u0635\u0648\u0635\u06cc \u062f\u0627\u0631\u062f\u061f** %s
- **\u0622\u06cc\u0627 \u0627\u062f\u0639\u0627\u06cc \u0631\u0627\u06cc\u06af\u0627\u0646\u0628\u0648\u062f\u0646 \u062f\u0627\u0631\u062f\u061f** %s
- **\u0622\u06cc\u0627 \u0627\u062f\u0639\u0627\u06cc \u062a\u0636\u0645\u06cc\u0646 \u0646\u062a\u06cc\u062c\u0647 \u062f\u0627\u0631\u062f\u061f** %s

## \u0639\u0644\u062a RiskTag.STATISTICAL

Risk tag `statistical` \u0628\u0647 \u062f\u0644\u06cc\u0644 \u0648\u062c\u0648\u062f \u06a9\u0644\u0645\u0627\u062a \u06a9\u0644\u06cc\u062f\u06cc \u0622\u0645\u0627\u0631\u06cc \u062f\u0631 **\u0645\u062a\u0646 \u0635\u0641\u062d\u0647 \u0645\u0646\u0628\u0639** (%s) \u0641\u0639\u0627\u0644 \u0634\u062f\u0647 \u0627\u0633\u062a.

- \u06a9\u0644\u0645\u0627\u062a \u0622\u0645\u0627\u0631\u06cc \u062f\u0631 Caption: **%s**
- \u06a9\u0644\u0645\u0627\u062a \u0622\u0645\u0627\u0631\u06cc \u062f\u0631 \u0645\u062a\u0646 \u0635\u0641\u062d\u0647 \u0645\u0646\u0628\u0639: **%s**

## \u0646\u062a\u06cc\u062c\u0647\u200c\u06af\u06cc\u0631\u06cc

%s
""" % (
    "\u0628\u0644\u0647" if has_numbers else "\u062e\u06cc\u0631",
    "\u0628\u0644\u0647" if has_statistical else "\u062e\u06cc\u0631",
    "\u0628\u0644\u0647" if has_comparative else "\u062e\u06cc\u0631",
    "\u0628\u0644\u0647" if has_security else "\u062e\u06cc\u0631",
    "\u0628\u0644\u0647" if has_privacy else "\u062e\u06cc\u0631",
    "\u0628\u0644\u0647" if has_free_claim else "\u062e\u06cc\u0631",
    "\u0628\u0644\u0647" if has_guarantee else "\u062e\u06cc\u0631",
    cr["canonical_url"],
    "\u0628\u0644\u0647 \u2014 \u062f\u0631 \u0645\u062a\u0646 Caption" if statistical_in_caption else "\u062e\u06cc\u0631",
    "\u0628\u0644\u0647 \u2014 \u062f\u0631 \u0645\u062a\u0646 \u0635\u0641\u062d\u0647 \u0645\u0646\u0628\u0639" if statistical_in_page else "\u062e\u06cc\u0631",
    "\u0627\u06cc\u0646 brief \u0628\u0631\u0627\u06cc \u0627\u0648\u0644\u06cc\u0646 \u0627\u0646\u062a\u0634\u0627\u0631 \u0645\u0646\u0627\u0633\u0628 \u0627\u0633\u062a. Risk tag \u0641\u0642\u0637 \u0627\u0632 \u0645\u062a\u0646 \u0635\u0641\u062d\u0647 \u0645\u0646\u0628\u0639 \u0622\u0645\u062f\u0647 \u0648 Caption \u0641\u0627\u0642\u062f \u0627\u062f\u0639\u0627\u06cc \u0622\u0645\u0627\u0631\u06cc \u0635\u0631\u06cc\u062d \u0646\u062f\u0627\u0631\u062f." if not statistical_in_caption else "Caption \u0634\u0627\u0645\u0644 \u0627\u062f\u0639\u0627\u06cc \u0622\u0645\u0627\u0631\u06cc \u0627\u0633\u062a \u2014 \u0646\u06cc\u0627\u0632 \u0628\u0647 \u0628\u0627\u0632\u0628\u06cc\u0646\u06cc \u062f\u0642\u06cc\u0642\u200c\u062a\u0631 \u062f\u0627\u0631\u062f."
)

with open("%s/review-summary.md" % REVIEW_DIR, "w") as f:
    f.write(md)

# Rebuild tar
import subprocess
subprocess.run([
    "tar", "-czf",
    "%s/review.tar.gz" % os.path.dirname(REVIEW_DIR),
    "-C", os.path.dirname(REVIEW_DIR),
    os.path.basename(REVIEW_DIR)
], check=True)

print("Done. Files:")
for f in sorted(os.listdir(REVIEW_DIR)):
    print("  %s (%d bytes)" % (f, os.path.getsize(os.path.join(REVIEW_DIR, f))))
print("Tar: %s/review.tar.gz (%d bytes)" % (
    os.path.dirname(REVIEW_DIR),
    os.path.getsize("%s/review.tar.gz" % os.path.dirname(REVIEW_DIR))
))
