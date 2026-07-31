#!/usr/bin/env bash
# Deploy PersianToolbox Content Factory to VPS
# Usage: VPS_HOST=... VPS_USER=... SSH_KEY=... bash deploy-vps.sh [--env production|staging]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
DEPLOY_ENV="${1:-production}"

echo "=== Deploying PersianToolbox Content Factory ($DEPLOY_ENV) ==="

# Load environment
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Fail-fast: require VPS connection vars
: "${VPS_HOST:?VPS_HOST is required (set in .env or export)}"
: "${VPS_USER:?VPS_USER is required (set in .env or export)}"
: "${SSH_KEY:?SSH_KEY is required (set in .env or export)}"

VPS_DEPLOY_DIR="${VPS_DEPLOY_DIR:-/opt/ptb-content-factory}"

[[ -f "$SSH_KEY" ]] || {
    echo "SSH key not found: $SSH_KEY" >&2
    exit 1
}

echo "Target: ${VPS_USER}@${VPS_HOST}:${VPS_DEPLOY_DIR}"

# Sync code (excluding large dirs)
echo "Syncing code..."
rsync -avz --delete \
    -e "ssh -i $SSH_KEY" \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude '.ruff_cache' \
    --exclude '.pytest_cache' \
    --exclude 'data/publish-queue.db' \
    --exclude 'data/manual-queue.db' \
    --exclude 'data/approvals/' \
    --exclude 'outputs/bundles/' \
    --exclude 'outputs/brief-*/feed-*.png' \
    --exclude 'outputs/test-*/feed-*.png' \
    --exclude 'outputs/golden/' \
    --exclude 'backups/' \
    --exclude 'reports/' \
    "$PROJECT_DIR/" "${VPS_USER}@${VPS_HOST}:${VPS_DEPLOY_DIR}/"

# Build on VPS
echo "Building on VPS..."
ssh -i "$SSH_KEY" "${VPS_USER}@${VPS_HOST}" << 'DEPLOY_SCRIPT'
set -euo pipefail
cd /opt/ptb-content-factory

# Create venv if not exists
if [ ! -d .venv ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -e ".[dev]" --quiet

# Run tests — fail deploy on test failure
echo "Running tests..."
python -m pytest tests/ -x -q --tb=short

# Restart service
echo "Restarting service..."
sudo systemctl restart ptb-content.service || true
sleep 3

# Check status
if systemctl is-active --quiet ptb-content.service; then
    echo "Service is running"
else
    echo "Service not running (may be expected for cron-only mode)"
fi
DEPLOY_SCRIPT

echo "=== Deploy Complete ==="
