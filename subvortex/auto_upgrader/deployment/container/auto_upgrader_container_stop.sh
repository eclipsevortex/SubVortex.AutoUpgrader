#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check which command is available
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    DOCKER_CMD="docker compose"
    elif command -v docker-compose &> /dev/null; then
    DOCKER_CMD="docker-compose"
else
    echo "❌ Neither 'docker compose' nor 'docker-compose' is installed. Please install Docker Compose."
    exit 1
fi

# Stop watchtower
./../../scripts/watchtower/watchtower_stop.sh

if [ -n "$SUBVORTEX_LOCAL" ]; then
    $DOCKER_CMD -f ../../docker-compose.local.yml stop auto_upgrader
else
    $DOCKER_CMD -f ../../docker-compose.yml stop auto_upgrader
fi

echo "✅ Auto Upgrader stopped successfully"
