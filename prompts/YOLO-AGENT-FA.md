# PersianToolbox Content Factory — YOLO Agent Guide

## دستور اجرا

این فایل مرجع اصلی اجرای پروژه است. تمام مراحل را به‌ترتیب اجرا کن.

## Phase 1: Preflight

- [x] System discovery (OS, Python, CPU, RAM, GPU, disk, Docker, Chromium, Playwright, Git, network)
- [x] Create `reports/preflight.json`
- [x] Create git branch `feat/production-content-factory`
- [x] Compile all source with `python -m compileall`
- [x] Run pytest
- [x] Run ruff check
- [x] Test CLI `ptb-content --help`

## Phase 2: Crawl

- [x] Check robots.txt and sitemap
- [x] Implement rate-limited crawler (concurrency ≤ 2, rate ≤ 1 rps, timeout ≤ 30s)
- [x] Crawl 20-30 low-risk tools for pilot
- [x] Output: `data/catalog/tools.jsonl`, `claims.jsonl`, `crawl-report.json`, `manual-review.csv`
- [x] Each record: canonical_url, title, summary, category, source_id, source_hash, crawled_at, verified_at, expires_at, claims, risk_tags, HTTP metadata

## Phase 3: Visual Identity

- [x] Extract brand tokens from persiantoolbox.ir
- [x] Create `config/brand.yaml` with colors, spacing, typography, shadows, icon style, logo safe area
- [x] Build 5 templates: tool-demo, step-by-step, common-mistake, privacy-trust, professional-seasonal
- [x] Each template: 1080x1350, 1080x1080, 1080x1920

## Phase 4: Provider Benchmark

- [x] Probe: deterministic, AI Horde, Ollama local, llama.cpp
- [x] Record: reachable, auth_ok, free, open_weight, persian_score, json_score, latency, failure_rate
- [x] Run 30+ Persian tests (natural Persian, ZWNJ, valid JSON, no fabricated claims, hooks, CTA, risk detection, non-literal rewrite)
- [x] Save `reports/provider-benchmark.json`
- [x] Deterministic mode as fallback

## Phase 5: Generation & QA

- [x] Pipeline: catalog → audience → strategy → psychology → caption → art direction → render → factuality QA → Persian QA → visual QA → risk decision → bundle
- [x] 3 caption variants: A (direct), B (educational), C (curiosity)
- [x] Rubric scoring: traceability 30, natural Persian 20, clarity 15, brand 15, save/share 10, safety 10
- [x] Risk engine: LOW/MEDIUM/HIGH with ESCALATE for HIGH

## Phase 6: Golden Set

- [ ] 50 reference briefs (10 tool demos, 10 PDF tutorials, 10 Persian text, 10 professional, 5 privacy, 5 financial/legal)
- [ ] Schema validation, Persian normalization, mixed RTL/LTR, long headline, overflow, missing source, prompt injection, provider timeout, fallback, duplicate publish, approval gate, render snapshots

## Phase 7: Pilot

- [ ] 8 posts, 2-week schedule
- [ ] Min 3 pillars, min 3 templates, category diversity
- [ ] Max 1 financial/week
- [ ] Unique UTM per post
- [ ] Full bundle per post
- [ ] `outputs/review-gallery.html`
- [ ] No publishing

## Phase 8: Local Scheduler

- [ ] cron/systemd timer for: catalog refresh, weekly generation, metrics import, weekly QA report
- [ ] Lock, idempotency, log rotation, limited retry

## Phase 9: Postiz & Meta (only on user request)

- [ ] Not activated — awaiting user confirmation

## Final Reports

- [ ] `reports/preflight.json`
- [ ] `reports/provider-benchmark.json`
- [ ] `reports/catalog-report.json`
- [ ] `reports/pilot-report.md`
- [ ] `reports/security-report.md`
- [ ] `reports/test-report.txt`
- [ ] `reports/open-issues.md`
- [ ] `STATUS.md`
- [ ] `CHANGELOG.md`
