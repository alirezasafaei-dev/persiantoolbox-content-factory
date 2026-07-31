#!/usr/bin/env bash
# Health check for PersianToolbox Content Factory
set -euo pipefail

echo "=== Content Factory Health Check ==="

# Check service
if systemctl is-active --quiet ptb-content.service; then
    echo "✅ ptb-content.service: running"
else
    echo "❌ ptb-content.service: NOT running"
fi

# Check queue DB
QUEUE_DB="${PTB_QUEUE_DB:-/var/lib/ptb-content/data/publish-queue.db}"
if [ -f "$QUEUE_DB" ]; then
    COUNT=$(sqlite3 "$QUEUE_DB" "SELECT COUNT(*) FROM publish_jobs;" 2>/dev/null || echo "0")
    PUBLISHED=$(sqlite3 "$QUEUE_DB" "SELECT COUNT(*) FROM publish_jobs WHERE state='PUBLISHED';" 2>/dev/null || echo "0")
    echo "✅ Queue DB: $COUNT jobs, $PUBLISHED published"
else
    echo "⚠️  Queue DB not found at $QUEUE_DB"
fi

# Check secrets file
SECRETS="/etc/ptb-content/production.env"
if [ -f "$SECRETS" ]; then
    echo "✅ Secrets file exists"
    if grep -q "META_INSTAGRAM_ACCESS_TOKEN=.[^ ].*" "$SECRETS" 2>/dev/null; then
        echo "✅ Meta credentials configured"
    else
        echo "⚠️  Meta credentials not yet configured"
    fi
else
    echo "❌ Secrets file missing"
fi

# Check disk space
DISK_USAGE=$(df -h / | awk 'NR==2 {print $5}' | tr -d '%')
echo "📊 Disk usage: ${DISK_USAGE}%"
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "❌ Disk usage critical!"
fi

# Check logs
echo ""
echo "=== Recent Logs ==="
sudo journalctl -u ptb-content.service -n 10 --no-pager 2>/dev/null || echo "No logs available"
