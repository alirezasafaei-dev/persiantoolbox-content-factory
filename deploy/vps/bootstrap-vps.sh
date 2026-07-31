#!/usr/bin/env bash
# VPS bootstrap for PersianToolbox Content Factory
# Run once on a fresh VPS: bash bootstrap-vps.sh
set -euo pipefail

echo "=== PersianToolbox Content Factory — VPS Bootstrap ==="

# System packages (DEBIAN_FRONTEND for non-interactive)
sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    python3 python3.12-dev python3.12-venv python3-pip \
    ufw

# Create ptbcontent user (if not exists)
if ! id -u ptbcontent &>/dev/null; then
    sudo useradd -m -s /bin/bash ptbcontent
    echo "Created user: ptbcontent"
fi

# Create directories
sudo mkdir -p /opt/ptb-content-factory
sudo mkdir -p /var/log/ptb-content
sudo mkdir -p /etc/ptb-content
sudo mkdir -p /var/lib/ptb-content/data
sudo mkdir -p /opt/ptb-content-factory/{logs,outputs,data,backups}

# Set ownership
sudo chown -R ptbcontent:ptbcontent /opt/ptb-content-factory
sudo chown -R ptbcontent:ptbcontent /var/log/ptb-content
sudo chown -R ptbcontent:ptbcontent /var/lib/ptb-content

# Create secrets template (only if not exists)
if [ ! -f /etc/ptb-content/production.env ]; then
    sudo tee /etc/ptb-content/production.env > /dev/null <<'EOF'
# PersianToolbox Content Factory — Production Secrets
# NEVER commit this file to Git.

# Meta Instagram API
# BLOCKED: Semi-automated mode does NOT require these.
META_INSTAGRAM_APP_ID=
META_INSTAGRAM_APP_SECRET=
META_INSTAGRAM_ACCESS_TOKEN=
META_INSTAGRAM_ACCOUNT_ID=
META_API_VERSION=
META_HOST_URL=

# Publish Controls (FAIL-CLOSED defaults)
PTB_AUTO_PUBLISH=false
PTB_LIVE_CANARY_APPROVED=false
PTB_GENERATION_ENABLED=true
PTB_SCHEDULER_ENABLED=true
PTB_REAL_PUBLISH_ENABLED=false
PTB_PUBLISHER=mock

# Rate Limiting
PTB_MAX_POSTS_PER_24H=50
PTB_CONTAINER_TIMEOUT=600
PTB_POLL_INTERVAL=10

# Media Gateway
PTB_MEDIA_GATEWAY_SECRET=
PTB_MEDIA_GATEWAY_TTL_HOURS=24
PTB_MEDIA_GATEWAY_HOST=

# Queue
PTB_QUEUE_DB=/var/lib/ptb-content/data/publish-queue.db

# OAuth
PTB_OAUTH_REDIRECT_URI=http://localhost:8080/callback
EOF
    sudo chmod 640 /etc/ptb-content/production.env
    sudo chown root:ptbcontent /etc/ptb-content/production.env
    echo "Created secrets template at /etc/ptb-content/production.env"
else
    echo "Secrets file exists, skipping"
fi

# Firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

echo ""
echo "=== Bootstrap Complete ==="
echo "Next steps:"
echo "1. Edit /etc/ptb-content/production.env with real credentials"
echo "2. Deploy code: bash deploy-vps.sh"
echo "3. Setup venv: cd /opt/ptb-content-factory && python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'"
echo "4. Install cron: .venv/bin/ptb-content schedule --install"
