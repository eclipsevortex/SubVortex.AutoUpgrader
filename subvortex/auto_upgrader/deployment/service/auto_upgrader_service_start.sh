#!/bin/bash

set -e

SERVICE_NAME=subvortex-auto-upgrader

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Install the service configuration
envsubst < "./deployment/templates/${SERVICE_NAME}.service" | tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null

# Prepare the log
sudo mkdir -p /var/log/$SERVICE_NAME
sudo chown root:root /var/log/$SERVICE_NAME

# Reload and (re)start the service
systemctl daemon-reexec
systemctl daemon-reload

if systemctl is-active --quiet $SERVICE_NAME; then
  systemctl restart $SERVICE_NAME
else
  systemctl start $SERVICE_NAME
fi

echo "✅ Auto Upgrader started successfully"
