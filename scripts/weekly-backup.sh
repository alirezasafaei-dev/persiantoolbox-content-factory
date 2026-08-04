#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PTB_PROJECT_DIR:-/opt/ptb-content-factory}"
BACKUP_DIR="${PTB_BACKUP_DIR:-${PROJECT_DIR}/backups}"
TIMESTAMP=$(date +%Y-%m-%d-%H%M%S)
BACKUP_NAME="weekly-backup-${TIMESTAMP}"

mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

# Backup runtime data (briefs, approvals, queue, logs)
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}/runtime.tar.gz" \
    -C "${PROJECT_DIR}" \
    data/ \
    outputs/briefs/ \
    outputs/bundles/ \
    outputs/renders/ \
    logs/ 2>/dev/null || true

# Backup environment
cp /etc/ptb-content/production.env "${BACKUP_DIR}/${BACKUP_NAME}/production.env" 2>/dev/null || true
chmod 600 "${BACKUP_DIR}/${BACKUP_NAME}/production.env" 2>/dev/null || true

# Keep only last 8 weekly backups
cd "${BACKUP_DIR}"
ls -dt weekly-backup-* 2>/dev/null | tail -n +9 | xargs rm -rf 2>/dev/null || true

echo "Backup complete: ${BACKUP_DIR}/${BACKUP_NAME}"
du -sh "${BACKUP_DIR}/${BACKUP_NAME}"
