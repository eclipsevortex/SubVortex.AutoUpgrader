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
    if [[ "$(echo "$value" | tr '[:upper:]' '[:lower:]')" == "true" ]]; then
      ARGS+=("$cli_key")
    elif [[ $value_lower == "false" ]]; then
      continue
    else
      ARGS+=("$cli_key" "$value")
    fi
  fi
done < <(env)

# Start or reload PM2
if pm2 list | grep -q "$SERVICE_NAME"; then
  echo "🔁 Reloading $SERVICE_NAME"
  pm2 reload "$SERVICE_NAME" --update-env
else
  echo "🚀 Starting $SERVICE_NAME"
  pm2 start src/main.py \
    --name "$SERVICE_NAME" \
    --interpreter python3 -- \
    "${ARGS[@]}"
fi

echo "✅ Auto Upgrader started successfully"
