#!/usr/bin/env bash
# VPS bootstrap for PersianToolbox Content Factory
# Run once on a fresh VPS: bash bootstrap-vps.sh
set -euo pipefail

echo "=== PersianToolbox Content Factory — VPS Bootstrap ==="

# System packages
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx ufw fail2ban

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

# Set ownership
sudo chown -R ptbcontent:ptbcontent /opt/ptb-content-factory
sudo chown -R ptbcontent:ptbcontent /var/log/ptb-content
sudo chown -R ptbcontent:ptbcontent /var/lib/ptb-content

# Create systemd service
sudo tee /etc/systemd/system/ptb-content.service > /dev/null <<'EOF'
[Unit]
Description=PersianToolbox Content Factory
After=network.target

[Service]
Type=simple
User=ptbcontent
Group=ptbcontent
WorkingDirectory=/opt/ptb-content-factory
ExecStart=/opt/ptb-content-factory/.venv/bin/ptb-content schedule
Restart=on-failure
RestartSec=10
TimeoutStopSec=30

# Secrets
EnvironmentFile=/etc/ptb-content/production.env

# Hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
PrivateTmp=true
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictNamespaces=true
LockPersonality=true
MemoryDenyWriteExecute=false
RestrictRealtime=true
RestrictFileSystems=ptb-content-factory:ro
ReadWritePaths=/var/lib/ptb-content/data
ReadWritePaths=/var/log/ptb-content

[Install]
WantedBy=multi-user.target
EOF

# Create timer for scheduled publishes
sudo tee /etc/systemd/system/ptb-publish.timer > /dev/null <<'EOF'
[Unit]
Description=PersianToolbox Content Factory — Publish Timer

[Timer]
OnCalendar=*-*-* 06,12,18,21:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo tee /etc/systemd/system/ptb-publish.service > /dev/null <<'EOF'
[Unit]
Description=PersianToolbox Content Factory — Scheduled Publish
After=network.target ptb-content.service

[Service]
Type=oneshot
User=ptbcontent
Group=ptbcontent
WorkingDirectory=/opt/ptb-content-factory
ExecStart=/opt/ptb-content-factory/.venv/bin/ptb-content publish-scheduled
EnvironmentFile=/etc/ptb-content/production.env
NoNewPrivileges=true
ProtectSystem=strict
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Create secrets template
sudo tee /etc/ptb-content/production.env > /dev/null <<'EOF'
# PersianToolbox Content Factory — Production Secrets
# NEVER commit this file to Git.

# Meta Instagram API
META_INSTAGRAM_APP_ID=
META_INSTAGRAM_APP_SECRET=
META_INSTAGRAM_ACCESS_TOKEN=
META_INSTAGRAM_ACCOUNT_ID=
META_API_VERSION=v21.0
META_HOST_URL=https://graph.facebook.com

# Publish Controls
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

# Firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Enable services
sudo systemctl daemon-reload
sudo systemctl enable ptb-content.service
sudo systemctl enable ptb-publish.timer

echo ""
echo "=== Bootstrap Complete ==="
echo "Next steps:"
echo "1. Edit /etc/ptb-content/production.env with real credentials"
echo "2. Deploy code: bash deploy-vps.sh"
echo "3. Start service: sudo systemctl start ptb-content"
echo "4. Enable timer: sudo systemctl start ptb-publish.timer"
