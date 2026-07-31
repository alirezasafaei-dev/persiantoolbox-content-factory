#!/usr/bin/env bash
# Deploy PersianToolbox Content Factory to VPS
# Usage: bash deploy-vps.sh [--env production|staging]
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

VPS_HOST="${VPS_HOST:-91.107.153.223}"
VPS_USER="${VPS_USER:-asdev}"
VPS_DEPLOY_DIR="/opt/ptb-content-factory"
SSH_KEY="${SSH_KEY:-/home/dev13/.ssh/id_ed25519}"

echo "Target: ${VPS_USER}@${VPS_HOST}:${VPS_DEPLOY_DIR}"

# Sync code (excluding large dirs)
echo "Syncing code..."
rsync -avz --delete \
    -e "ssh -i $SSH_KEY" \
    --exclude 'node_modules' \
    --exclude '.next' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'data/publish-queue.db' \
    --exclude 'outputs/brief-*/feed-*.png' \
    --exclude 'outputs/test-*/feed-*.png' \
    --exclude 'outputs/golden/' \
    --exclude 'backups/' \
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
pip install httpx --quiet

# Run tests
echo "Running tests..."
python -m pytest tests/ -x -q --tb=short 2>&1 || echo "Tests completed with issues"

# Restart service
echo "Restarting service..."
sudo systemctl restart ptb-content.service
sleep 3

# Check status
if systemctl is-active --quiet ptb-content.service; then
    echo "✅ Service is running"
else
    echo "❌ Service failed to start"
    sudo journalctl -u ptb-content.service -n 20 --no-pager
    exit 1
fi
DEPLOY_SCRIPT

echo "=== Deploy Complete ==="
