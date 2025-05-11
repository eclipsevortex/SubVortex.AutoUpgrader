#!/bin/bash

set -e

# Ensure script run as root
if [[ "$EUID" -ne 0 ]]; then
    echo "🛑 This script must be run as root. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

SERVICE_NAME=subvortex-auto-upgrader

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ../../scripts/utils/utils.sh

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Build CLI args from SUBVORTEX_ environment variables
eval "ARGS=( $(convert_env_var_to_args) )"

# Build the full ExecStart line
PYTHON_EXEC="/root/SubVortex.AutoUpgrader/subvortex/auto_upgrader/venv/bin/python3"
MODULE="subvortex.auto_upgrader.src.main"
FULL_EXEC_START="$PYTHON_EXEC -m $MODULE ${ARGS[*]}"

# Path setup
TEMPLATE_PATH="./deployment/templates/${SERVICE_NAME}.service"
TEMP_TEMPLATE="/tmp/${SERVICE_NAME}.service.template"

# Replace ExecStart in template before envsubst
sed "s|^ExecStart=.*|ExecStart=$FULL_EXEC_START|" "$TEMPLATE_PATH" > "$TEMP_TEMPLATE"

# Install the service configuration
envsubst < "$TEMP_TEMPLATE" | tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null

# Prepare the log
mkdir -p /var/log/$SERVICE_NAME
chown root:root /var/log/$SERVICE_NAME

# Reload and (re)start the service
echo "📁 Preparing log directory for $NEURON_NAME..."
systemctl daemon-reexec
systemctl daemon-reload

# Check if the service is active
if systemctl list-unit-files | grep "$SERVICE_NAME.service"; then
  if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo "🔁 $SERVICE_NAME is already running — restarting..."
    systemctl restart "$SERVICE_NAME"
  else
    echo "🚀 Starting $SERVICE_NAME for the first time..."
    systemctl start "$SERVICE_NAME"
  fi
else
  echo "⚠️  Service $SERVICE_NAME is not installed or not recognized by systemd."
fi

echo "✅ Auto Upgrader started successfully"
