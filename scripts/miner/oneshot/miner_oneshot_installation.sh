#!/bin/bash

set -euo pipefail

# Ensure script run as root
if [[ "$EUID" -ne 0 ]]; then
    echo "🛑 This script must be run as root. Re-running with sudo..."
    exec sudo "$0" "$@"
fi

# 🧭 Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../.."

source ./scripts/utils/utils.sh

show_help() {
    echo
    echo "Description:"
    echo "  Setup and start the new miner and stop the old one"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method used from the auto upgrader r(default: service)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:h"
LONGOPTIONS="execution:,help"

# Set defaults from env (can be overridden by arguments)
AU_EXECUTION="${SUBVORTEX_EXECUTION_METHOD:-service}"

# Parse arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        -e |--execution)
            AU_EXECUTION="$2"
            shift 2
        ;;
        -h | --help)
            show_help
            exit 0
        ;;
        --)
            shift
            break
        ;;
        *)
            echo "❌ Unrecognized option '$1'"
            exit 1
        ;;
    esac
done

# Check maandatory args
check_required_args AU_EXECUTION

# Set execution methods
source subvortex/auto_upgrader/.env
SV_EXECUTION="${SUBVORTEX_EXECUTION_METHOD:-service}"

# ✅ Export SUBVORTEX_FLOATTING_FLAG if it exists (without error if not set)
export SUBVORTEX_FLOATTING_FLAG="${SUBVORTEX_FLOATTING_FLAG:-}"

echo "🔧 Installing the Auto Upgrader in $AU_EXECUTION..."
./scripts/auto_upgrader/auto_upgrader_setup.sh --execution "$AU_EXECUTION"

# --- STOP OLD MINER ---
echo
echo "🛠️ How is the old Miner currently running?"
echo "  1) systemd service"
echo "  2) background process (PM2)"
echo "  3) Docker container"
read -rp "⚙️  Enter option [1/2/3]: " val_mode

case "$val_mode" in
    1)
        read -rp "⚙️  Enter systemd service name: " val_svc
        echo "⛔ Stopping systemd service '$val_svc'..."
        systemctl stop "$val_svc" || echo "⚠️ Failed to stop systemd service"
    ;;
    2)
        read -rp "⚙️  Enter PM2 process name: " val_proc
        echo "⛔ Stopping PM2 process '$val_proc'..."
        pm2 stop "$val_proc" || echo "⚠️ Failed to stop PM2 process"
    ;;
    3)
        read -rp "🐳 Enter Docker container name or ID: " val_container
        echo "⛔ Stopping Docker container '$val_container'..."
        docker stop "$val_container" || echo "⚠️ Failed to stop container"
    ;;
    *)
        echo "⚠️ Invalid option. Skipping old miner stop."
    ;;
esac

# --- WAIT OLD MINER STOP ---
if [[ "$val_mode" == "3" ]]; then
    echo "⏳ Waiting for Docker container '$val_container' to stop..."
    MAX_WAIT=60; WAIT_INTERVAL=2; elapsed=0
    while docker ps --format '{{.Names}}' | grep -q "^$val_container$"; do
        if [[ $elapsed -ge $MAX_WAIT ]]; then
            echo "⚠️ Docker container did not stop within timeout. Forcing stop"
            docker kill "$val_container" || echo "⚠️ Failed to kill container"
            break
        fi
        sleep "$WAIT_INTERVAL"
        elapsed=$((elapsed + WAIT_INTERVAL))
    done
    echo "✅ Docker container '$val_container' has stopped."
else
    sleep 5
fi

# --- START AUTO UPGRADER ---
echo "🚀 Starting Auto Upgrader..."
./scripts/auto_upgrader/auto_upgrader_start.sh --execution "$AU_EXECUTION"

# --- WAIT FOR NEW MINER ---
echo "⏳ Waiting for Miner neuron to be up via '$SV_EXECUTION'..."
NEURON_NAME="subvortex-miner-neuron"
MAX_WAIT=300; WAIT_INTERVAL=3; elapsed=0; ready=0

while [[ $elapsed -lt $MAX_WAIT ]]; do
    case "$SV_EXECUTION" in
        service)
            systemctl is-active --quiet "$NEURON_NAME" && ready=1 && break
        ;;
        process)
            pm2 list | grep -qE "$NEURON_NAME.*online" && ready=1 && break
        ;;
        container)
            docker ps --format '{{.Names}}' | grep -q "^$NEURON_NAME$" && ready=1 && break
        ;;
        *)
            echo "⚠️ Unknown execution method: $SV_EXECUTION"
            break
        ;;
    esac
    echo "🕒 Waiting... ($elapsed/$MAX_WAIT)"
    sleep "$WAIT_INTERVAL"
    elapsed=$((elapsed + WAIT_INTERVAL))
done

[[ $ready -eq 0 ]] && echo "❌ Timeout reached. Proceeding anyway."


# --- START MINER NEURON ---
echo "🚀 Starting miner neuron..."
/root/subvortex/subvortex/miner/neuron/scripts/neuron_start.sh --execution "$SV_EXECUTION"


echo "✅ Miner installed and started successfully."
