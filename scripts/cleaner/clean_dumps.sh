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
DB_FILENAME=$(grep -E '^\s*dbfilename\s+' "$REDIS_CONF_PATH" | awk '{print $2}')
CHECKSUM_DIR="/var/tmp/subvortex.checksums"

# Fallbacks if not found
DUMP_DIR=${DUMP_DIR:-/var/tmp/dumps/redis}
DB_FILENAME=${DB_FILENAME:-dump.rdb}

DUMP_PATH="$DUMP_DIR/$DB_FILENAME"

echo "🧹 Checking for Redis dump file: $DUMP_PATH"
if [[ -f "$DUMP_PATH" ]]; then
    echo "🔥 Removing Redis dump file: $DUMP_PATH"
    sudo rm -f "$DUMP_PATH"
else
    echo "ℹ️ Redis dump file not found: $DUMP_PATH — nothing to clean."
fi

echo "🧹 Checking for checksum directory at: $CHECKSUM_DIR"
if [[ -d "$CHECKSUM_DIR" ]]; then
    echo "🔥 Removing checksum directory and contents: $CHECKSUM_DIR"
    sudo rm -rf "$CHECKSUM_DIR"
else
    echo "ℹ️ Checksum directory not found: $CHECKSUM_DIR — nothing to clean."
fi

echo "✅ Cleanup dumps ahd checksums complete."
