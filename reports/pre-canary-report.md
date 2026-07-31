# Pre-Canary Report — PersianToolbox Content Factory

**Date:** 2026-07-31
**Status:** BLOCKED — awaiting credentials and canary approval

---

## Repository & Branch

- **Repository:** https://github.com/alirezasafaei-dev/persiantoolbox-content-factory
- **Branch:** `feat/instagram-real-publisher-v1`
- **Base:** `main`
- **Commit SHA:** `9953968d61198347dab72f5f88edba1eee0bca2f`
- **PR:** https://github.com/alirezasafaei-dev/persiantoolbox-content-factory/pull/1
- **CI Status:** No workflow configured (expected — Python project)

---

## VPS Information

- **OS:** Ubuntu 24.04.3 (Linux 6.8.0-136-generic)
- **RAM:** 3.7GB total, 2.1GB available
- **Disk:** 38GB total, 9GB free (75% used)
- **Python:** 3.12.3
- **IP:** 91.107.153.223
- **SSH:** asdev@91.107.153.223 (key: /home/dev13/.ssh/id_ed25519)

---

## Meta App Credentials

- **Instagram Username:** NOT YET CONFIGURED
- **Token Expiry:** N/A
- **Token Fingerprint:** N/A
- **Confirmed Permissions:** N/A
- **App ID:** NOT YET CONFIGURED
- **App Secret:** NOT YET CONFIGURED
- **Access Token:** NOT YET CONFIGURED
- **Account ID:** NOT YET CONFIGURED

---

## Canary Brief

- **Brief ID:** BLOCKED — no LOW risk brief with rendered PNG available
- **All briefs in `outputs/briefs/` are HIGH risk / ESCALATE**
- **Golden set has LOW risk briefs but no rendered PNGs**
- **Approval ID:** N/A
- **Risk Status:** N/A
- **Caption:** N/A
- **PNG Path:** N/A
- **PNG Checksum:** N/A

---

## Dry-Run Result

NOT YET EXECUTED — blocked by missing credentials.

---

## Blockers

1. **Meta App not created** — Need to create App in Meta Developer Dashboard
2. **Instagram Professional account not connected** — Must be Business or Creator
3. **No LOW risk brief with rendered PNG** — All briefs in `outputs/briefs/` are HIGH/ESCALATE
4. **Media Gateway host not configured** — Need publicly accessible URL for image delivery
5. **VPS deploy not yet executed** — Scripts audited, ready to deploy

---

## Next Steps (Ordered)

1. Create Meta App in Developer Dashboard
2. Add Instagram Login product
3. Connect Instagram Professional account
4. Configure redirect URI
5. Enable `instagram_business_basic` and `instagram_business_content_publish` permissions
6. Run OAuth flow to get access token
7. Deploy to VPS with `bootstrap-vps.sh` then `deploy-vps.sh`
8. Configure secrets in `/etc/ptb-content/production.env`
9. Run `instagram verify` and `token-status`
10. Set up Media Gateway with publicly accessible host
11. Generate or approve a LOW risk brief with rendered PNG
12. Run dry-run publish
13. Await explicit canary approval
14. Execute single canary publish
15. Verify post on Instagram
16. Disable kill switches
17. Merge PR, tag v1.1.0
