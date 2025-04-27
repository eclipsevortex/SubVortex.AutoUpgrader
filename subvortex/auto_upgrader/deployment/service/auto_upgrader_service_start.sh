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

# Build CLI args from SUBVORTEX_ environment variables
ARGS=()
PREFIX="SUBVORTEX_"

while IFS= read -r line; do
  key="${line%%=*}"
  value="${line#*=}"
  if [[ $key == ${PREFIX}* ]]; then
    key_suffix="${key#$PREFIX}"
    cli_key="--$(echo "$key_suffix" | tr '[:upper:]' '[:lower:]' | tr '_' '.')"
    value_lower="$(echo "$value" | tr '[:upper:]' '[:lower:]')"

    if [[ "$value_lower" == "true" ]]; then
      ARGS+=("$cli_key")
    elif [[ $value_lower == "false" ]]; then
      continue
    else
      ARGS+=("$cli_key" "$value")
    fi
  fi
done < <(env)

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
