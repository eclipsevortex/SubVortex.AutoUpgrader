#!/bin/bash

set -e

SERVICE_NAME=subvortex-auto-upgrader

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ../scripts/utils/utils.sh

# Activate virtual environment
source venv/bin/activate

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Build CLI args from SUBVORTEX_ environment variables
ARGS=$(convert_env_var_to_args)

# Start or reload PM2
if pm2 list | grep -q "$SERVICE_NAME"; then
    if [[ ${#ARGS[@]} -eq 0 ]]; then
        echo "🔁  No additional CLI args, reloading service normally..."
        pm2 reload "$SERVICE_NAME" --update-env
    else
        echo "🔁  Restarting $SERVICE_NAME with updated CLI args: ${ARGS[*]}"
        pm2 restart "$SERVICE_NAME" --update-env -- "${ARGS[@]}"
    fi
else
    echo "🚀 Starting $SERVICE_NAME"
    pm2 start src/main.py \
    --name "$SERVICE_NAME" \
    --interpreter venv/bin/python3 -- \
    "${ARGS[@]}"
fi

echo "✅ Auto Upgrader started successfully"
