#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Load environment variables
echo "🔍 Loading environment variables from .env..."
export $(grep -v '^#' subvortex/auto_upgrader/.env | xargs)

# Extract default DUMP_DIR from Redis config
REDIS_CONF_PATH="./subvortex/auto_upgrader/template/template-subvortex-$SUBVORTEX_EXECUTION_ROLE-redis.conf"
DUMP_DIR=$(grep -E '^\s*dir\s+' "$REDIS_CONF_PATH" | awk '{print $2}')

# Fallback if not found
DUMP_DIR=${DUMP_DIR:-/var/tmp/dumps/redis}

echo "🧹 Checking for dump directory at: $DUMP_DIR"
if [[ -d "$DUMP_DIR" ]]; then
    echo "🔥 Removing dump directory and contents: $DUMP_DIR"
    sudo rm -rf "$DUMP_DIR"
else
    echo "ℹ️ Dump directory not found: $DUMP_DIR — nothing to clean."
fi

echo "✅ Cleanup dumps complete."
