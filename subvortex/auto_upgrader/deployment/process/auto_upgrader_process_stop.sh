#!/bin/bash

set -e

SERVICE_NAME=subvortex-auto-upgrader

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

if pm2 describe "$SERVICE_NAME" >/dev/null 2>&1; then
    echo "🛑 Stopping PM2 service: $SERVICE_NAME"
    pm2 stop "$SERVICE_NAME"
else
    echo "⚠️  PM2 service '$SERVICE_NAME' not found. Skipping stop."
fi

echo "✅ Auto Upgrader stopped successfully"
