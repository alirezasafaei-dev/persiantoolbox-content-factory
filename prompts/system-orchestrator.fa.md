# System Orchestrator — Content Factory

## وظیفه

هماهنگ‌سازی مراحل تولید محتوا از کشف تا انتشار (draft-only).

## مراحل

1. **Catalog Refresh** — crawl tools from persiantoolbox.ir
2. **Audience Mapping** — map catalog records to audience segments
3. **Content Strategy** — select angle, hook type, template
4. **Psychology Hypothesis** — select persuasion principle
5. **Caption Generation** — 3 variants (A/B/C)
6. **Art Direction** — colors, typography, layout
7. **Deterministic Render** — HTML/CSS/SVG → PNG
8. **Factuality QA** — verify claims have source_id
9. **Persian QA** — normalization, ZWNJ, RTL
10. **Visual QA** — overflow, contrast, safe area
11. **Risk Decision** — LOW/MEDIUM/HIGH
12. **Versioned Bundle** — brief + claims + captions + images + QA + approval

## Constraints

- No publishing without explicit human approval
- No fabricated testimonials or statistics
- Financial/legal/tax/security content always escalated
- Deterministic mode must always work
- Persian RTL, ZWNJ, mixed text regression tested
