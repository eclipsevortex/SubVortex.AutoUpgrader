#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Start with PM2
pm2 stop --name subvortex-auto-upgrader

echo "✅ Auto Upgrader stopped successfully"
