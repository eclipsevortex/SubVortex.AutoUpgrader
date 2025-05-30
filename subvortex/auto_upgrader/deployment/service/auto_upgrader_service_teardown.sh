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

# Stop and disable the systemd service
if systemctl list-units --type=service --all | grep -q "${SERVICE_NAME}.service"; then
    echo "Stopping systemd service $SERVICE_NAME..."
    systemctl stop "${SERVICE_NAME}.service"

    echo "Disabling systemd service $SERVICE_NAME..."
    systemctl disable "${SERVICE_NAME}.service"

    echo "Removing systemd service file..."
    rm -f "/etc/systemd/system/${SERVICE_NAME}.service"

    echo "Reloading systemd daemon..."
    systemctl daemon-reload
else
    echo "Systemd service ${SERVICE_NAME}.service not found. Skipping stop/disable."
fi

# Remove log directory
LOG_DIR="/var/log/$SERVICE_NAME"
if [[ -d "$LOG_DIR" ]]; then
    echo "Removing log directory: $LOG_DIR"
    rm -rf "$LOG_DIR"
else
    echo "Log directory $LOG_DIR does not exist. Skipping."
fi

# Uninstall dependencies if virtual environment exists
if [[ -d "venv" ]]; then
    echo "Activating virtual environment to uninstall dependencies..."
    source "venv/bin/activate"

    if pip list | grep -q "$SERVICE_NAME"; then
        echo "Uninstalling editable package: $SERVICE_NAME..."
        pip uninstall -y "$SERVICE_NAME"
    else
        echo "Editable package $SERVICE_NAME not found. Skipping."
    fi

    # Uninstall dependencies
    if [[ -f "requirements.txt" ]]; then
        echo "Uninstalling dependencies..."
        pip uninstall -y -r "requirements.txt"
    else
        echo "requirements.txt not found. Skipping dependency uninstallation."
    fi

    # Deactivate virtual environment
    deactivate

    echo "Removing virtual environment..."
    rm -rf "venv"
else
    echo "Virtual environment not found. Skipping removal."
fi

# Ensure egg-info is removed
EGG_INFO_DIR=$(find . -name "*.egg-info" -type d)
if [[ -n "$EGG_INFO_DIR" ]]; then
    echo "Removing egg-info directory: $EGG_INFO_DIR..."
    rm -rf "$EGG_INFO_DIR"
else
    echo "No egg-info directory found."
fi

echo "✅ Auto Upgrader teardown completed successfully."
