# Meta Instagram Graph API Integration Report

**Branch:** `feat/instagram-real-publisher-v1`
**Date:** 2026-07-31
**Status:** Ready for VPS dry-run and canary

---

## What Was Built

### Publisher Protocol (`protocol.py`)
- `Publisher` Protocol with `validate()`, `publish()`, `get_status()`
- `PublishJob` dataclass with full state machine
- 14 states: DRAFT → QA_PASSED → ESCALATED → APPROVED → SCHEDULED → VALIDATING → MEDIA_EXPOSED → CONTAINER_CREATED → PROCESSING → PUBLISHED (or FAILED_RETRYABLE/FAILED_PERMANENT/REVOKED/CANCELLED)
- Idempotency key: `publish:<brief_id>:<content_checksum>:<instagram_account_id>`

### Meta Instagram Publisher (`meta_instagram.py`)
- Full container → poll → publish flow using `httpx`
- Image container creation via `POST /<IG_ID>/media`
- Status polling until FINISHED/EXPIRED/ERROR
- Media publish via `POST /<IG_ID>/media_publish`
- Error handling: TokenExpired, RateLimit, ContainerExpired, ContainerProcessing
- Retry logic: FAILED_RETRYABLE with max_retries=3

### Publish Queue (`queue.py`)
- SQLite WAL with idempotency key enforcement
- Thread-safe with `busy_timeout=5000`
- State transitions persisted to DB
- Recent post counting for rate limit enforcement

### Media Gateway (`media_gateway.py`)
- HMAC-SHA256 signed URLs
- Token expiry enforcement
- Path traversal protection
- Local path extraction from signed URLs

### OAuth CLI (`oauth.py`)
- `auth-url`: Generate Facebook OAuth URL
- `exchange-code`: Short-lived token exchange
- `exchange-long-lived`: 60-day token exchange
- `verify`: Validate token and show account info
- `token-status`: Check expiry and publishing limit
- `disconnect`: Revoke token

### Settings (`settings.py`)
- All from environment variables, never hardcoded
- Fail-closed defaults: `auto_publish=false`, `live_canary_approved=false`, `real_publish_enabled=false`
- `can_publish` property requires ALL flags true + valid credentials

### Custom Errors (`errors.py`)
- 13 specific error types for precise failure handling

---

## Security

- **Fail-closed defaults**: All publish flags default to false/NO
- **Secrets never committed**: `.env.example` has empty values
- **Idempotency enforced**: Duplicate publishes blocked at queue level
- **Rate limiting**: Max 50 posts/24h (Instagram limit: 100)
- **HMAC-signed media URLs**: Time-limited, path-traversal protected
- **Systemd hardening**: NoNewPrivileges, PrivateTmp, ProtectSystem=strict

---

## Test Coverage

- 40 new tests in `tests/test_publisher.py`
- 155 total tests passing
- Covers: state machine, queue, gateway, settings, publisher (mocked API), full flow

---

## VPS Deployment

- `deploy/vps/bootstrap-vps.sh`: System setup, systemd, firewall
- `deploy/vps/deploy-vps.sh`: Rsync + build + restart
- `deploy/vps/health-check.sh`: Service + queue + secrets check
- Secrets at `/etc/ptb-content/production.env` (root:ptbcontent, 640)

---

## Remaining Steps

1. **Meta App Setup**: Create App in Meta Developer Dashboard, add Instagram Login, configure redirect URI
2. **OAuth Exchange**: Get authorization code, exchange for long-lived token
3. **VPS Deploy**: Bootstrap, deploy, health check
4. **Dry-run**: Publish with `--dry-run` flag, verify all checks pass
5. **Canary**: Single real publish with explicit approval
6. **Post-canary**: Merge PR, tag v1.1.0, enable scheduler

---

## Blockers

- **Meta App credentials not yet created**: Need `META_INSTAGRAM_APP_ID`, `META_INSTAGRAM_APP_SECRET`, `META_INSTAGRAM_ACCESS_TOKEN`, `META_INSTAGRAM_ACCOUNT_ID`
- **Instagram account must be Professional** (Business or Creator)
- **App Review** may be required for `instagram_business_content_publish` permission
- **Media Gateway host** must be publicly accessible (Meta fetches images from URLs)
