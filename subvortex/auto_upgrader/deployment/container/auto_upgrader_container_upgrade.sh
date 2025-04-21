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

# Install watchtower
./../../scripts/watchtower/watchtower_start.sh

echo "📥 Pulling latest image for $SERVICE_NAME..."
docker compose pull "$SERVICE_NAME"

echo "🔄 Recreating container with updated image..."
$DOCKER_CMD -f ../../docker-compose.yml up auto_upgrader -d --no-deps --force-recreate

echo "✅ Auto Upgrader upgraded successfully"
