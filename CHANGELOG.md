# CHANGELOG

## [0.2.0] - 2026-07-31

### Added
- Playwright PNG rendering (3 sizes: 1080×1350, 1080×1080, 1080×1920)
- 228 PNGs rendered from 18 generated briefs
- Golden set: 50 security edge-case briefs
- Prompt injection detection tests (title, meta, OG tags)
- Duplicate publish detection (caption hash comparison)
- Provider fallback test (deterministic always selected)
- Provider timeout test (graceful failure handling)
- Risk escalation tests (financial, privacy, comparative tags)
- Golden set validation tests (schema, Persian normalization, completeness)
- Interactive review gallery with embedded PNG previews
- **Snapshot regression tests**: 3 baselines, 24 tests (RTL, overflow, clipping, CTA, font, dimensions)
- **Approval gate**: 19 tests (ESCALATE, FAIL, checksum, expiry, version, fail-closed, mock publishers)
- **Approval workflow CLI**: `approve`, `revoke`, `publish` commands
- **Scheduler CLI**: `--install`, `--uninstall`, `--dry-run` options
- **Scheduler lockfile**: prevents overlapping runs (/tmp/ptb-content-factory/)
- **File-based checksum**: avoids reconstruction drift between approve and publish
- 16 new tests (115 total, all passing)
- Cron schedule saved to reports/schedule.json + reports/scheduler-dry-run.json
- Release report with commit SHA, commands, and publish status

### Fixed
- Prompt injection test assertion (safe extraction behavior)
- Import sorting (ruff auto-fix)
- Unused import cleanup
- Approval checksum mismatch (file-based vs reconstruction-based)
- Version field added to Approval dataclass

### Changed
- Scheduler: absolute paths for Python, working dir, log dir
- Scheduler: lockfile-based job deduplication
- Scheduler: 4 jobs (catalog-refresh, weekly-generation, weekly-render, weekly-qa-report)
- Reports: all 4 stale reports updated with final numbers
- CLI version bumped to 0.2.0

## [0.1.0] - 2026-07-31

### Added
- Initial project structure and configuration
- Core type system (CatalogRecord, Brief, QA, Risk, etc.)
- Persian text normalization (Arabic→Persian, ZWNJ, whitespace)
- Web crawler with rate limiting (1 rps, concurrency 2)
- Deterministic content generator (no AI needed)
- HTML/CSS/SVG renderer for 3 social media sizes
- Risk engine (LOW/MEDIUM/HIGH with ESCALATE)
- QA engine (factuality, Persian, RTL, visual, source, duplicate)
- Provider benchmark (deterministic, AI Horde, Ollama, llama.cpp)
- CLI with click (crawl, generate, render, qa, benchmark, schedule, report)
- 5 templates: tool-demo, step-by-step, common-mistake, privacy-trust, professional-seasonal
- 57 unit and integration tests
- JSON schemas for catalog, brief, claims, QA, approval, publish
- Brand configuration (colors, typography, spacing, tone)
- Crawler configuration (rate limits, timeouts, retries)
- Risk engine configuration (escalate tags, always-review)
- Provider configuration (fallback order, selection rules)
- Local scheduler (cron entries for 4 jobs)
- Reports: preflight, provider-benchmark, catalog-report, pilot-report, security-report, test-report, open-issues

### Fixed
- project_root() path resolution
- ZWNJ heuristic over-aggressiveness
- Duplicate dictionary key in persian.py
- httpx proxy environment variable issue (trust_env=False)
- Risk engine escalate_tags missing comparative
