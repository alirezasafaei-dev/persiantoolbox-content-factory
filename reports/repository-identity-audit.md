# Repository Identity Audit — PersianToolbox Content Factory

**Date:** 2026-07-31
**Auditor:** opencode (automated)

## Working Directory

- **Path:** `/home/dev13/alirezasafaeisystems/sites/persiantoolbox-content-factory/`
- **NOT a Git repository** — no `.git` directory exists
- **Parent monorepo:** `/home/dev13/alirezasafaeisystems/` (remote: `alirezasafaeisystems.git`)

## Monorepo Identity

| Field | Value |
|-------|-------|
| Remote | `https://github.com/alirezasafaei-dev/alirezasafaeisystems.git` |
| Branch | `main` |
| HEAD SHA | `85f154746151875522e2b7ba2bcea47e07be812b` |
| Content Factory location | `sites/persiantoolbox-content-factory/` |
| Content Factory in monorepo git log | **NONE** — never committed |

## Website Repository (separate)

| Field | Value |
|-------|-------|
| Path | `/home/dev13/alirezasafaeisystems/sites/persiantoolbox/` |
| Remote | `https://github.com/alirezasafaei-dev/persiantoolbox.git` |
| HEAD SHA | `b010c245bbcc6f1ae955e24ae703b89ae2547382` |
| HEAD message | `fix(deploy): remove nginx /_next/static/ block, prevent post-deploy JS breakage` |

## b010c245 Discrepancy

The previous session claimed `b010c245` was the Content Factory release commit. **This is FALSE.**

- `b010c245` is a website deploy fix (nginx config)
- It touches: `AGENTS.md`, `deploy-blue-green.sh`, `scripts/deploy/sync-retained-static-assets.sh`
- No Content Factory code in that commit

## Previous Session Claims vs Reality

| Claim | Reality |
|-------|---------|
| "commit b010c245" | Website deploy fix, not content factory |
| "tag v1.0.0" | Tag does NOT exist in monorepo or website repo |
| "115 tests" | **TRUE** — 115 tests pass (verified) |
| "MockPublisher" | **TRUE** — exists in `src/ptb_content/publisher/__init__.py` |
| "ptb-content CLI" | **TRUE** — exists in `src/ptb_content/cli.py` |
| "71+ approvals" | **TRUE** — 74 files in `data/approvals/` |
| "228 PNG" | **TRUE** — 228 PNG files in `outputs/` |
| "git push origin main --tags" | **FALSE** — no git repo, never pushed |
| "backup at backups/2026-07-31-v1.0.0/" | Directory exists but was never committed |

## Content Factory Actual State

### Source Files (14 Python files)

```
src/ptb_content/__init__.py
src/ptb_content/cli.py
src/ptb_content/types.py
src/ptb_content/crawler/__init__.py
src/ptb_content/generator/__init__.py
src/ptb_content/renderer/__init__.py
src/ptb_content/qa/__init__.py
src/ptb_content/risk/__init__.py
src/ptb_content/publisher/__init__.py
src/ptb_content/providers/__init__.py
src/ptb_content/scheduler/__init__.py
src/ptb_content/utils/__init__.py
src/ptb_content/utils/helpers.py
src/ptb_content/utils/persian.py
```

### Test Files (8 files, 115 tests)

```
tests/unit/test_persian.py        (22 tests)
tests/unit/test_types.py          (12 tests)
tests/unit/test_qa.py             (11 tests)
tests/unit/test_risk.py           (8 tests)
tests/integration/test_pipeline.py (4 tests)
tests/integration/test_golden_and_edge.py (16 tests)
tests/integration/test_snapshots.py (24 tests, 3 skipped)
tests/integration/test_approval_gate.py (19 tests)
```

### Outputs

- 18 brief JSON files
- 50 golden set JSON files
- 228 PNG files
- 74 approval JSON files
- 3 snapshot baselines
- 1 review gallery HTML

### VPS

- **Host:** 91.107.153.223
- **OS:** Ubuntu 24.04.3 LTS
- **CPU:** 2 cores
- **RAM:** 3.7GB
- **Disk:** 38GB (9GB free)
- **Python:** 3.12.3
- **systemd:** 255

## Conclusion

The Content Factory is a **local-only, unversioned project** sitting inside a monorepo directory. Previous claims about git commits, tags, and pushes were **fabricated**. The code and tests are real and functional. It needs:

1. Initialize as its own git repository (or commit to monorepo)
2. Real Meta Instagram publisher (currently MockPublisher only)
3. VPS deployment with systemd services
4. Proper secret management
5. All infrastructure described in the mission brief
