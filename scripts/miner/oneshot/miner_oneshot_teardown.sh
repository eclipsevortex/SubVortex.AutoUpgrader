#!/bin/bash

set -euo pipefail

# 🧭 Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../.."

source ./scripts/utils/utils.sh

show_help() {
    echo
    echo "Description:"
    echo "  Stop and teardown the new miner and restart the old one"
    echo
    echo "Options:"
    echo "  --execution             Specify the execution method used from the auto upgrader r(default: service)"
    echo "  --skip-auto-upgrader    Skip stopping and tearing down the auto upgrader"
    echo "  --help                  Show this help message"
    exit 0
}

OPTIONS="e:ah"
LONGOPTIONS="execution:,:skip-auto-upgrader,help"

# Set defaults from env (can be overridden by arguments)
AU_EXECUTION="${SUBVORTEX_EXECUTION_METHOD:-service}"
SKIP_AUTO_UPGRADER=false

# Parse arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        -e |--execution)
            AU_EXECUTION="$2"
            shift 2
        ;;
        --skip-auto-upgrader)
            SKIP_AUTO_UPGRADER=true
            shift
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

echo "🔄 Starting rollback & restore..."

# --- STOP AUTO UPGRADER ---
echo "🛑 Stopping auto upgrader in $AU_EXECUTION..."
./scripts/auto_upgrader/auto_upgrader_stop.sh --execution "$AU_EXECUTION" || echo "⚠️ Stoppping Auto Upgrader failed"

# --- TEARDOWN NEW MINER ---
echo "🧨 Tearing down new miner neuron..."
NEURON_SCRIPT="/root/subvortex/subvortex/miner/neuron/scripts/neuron_teardown.sh"
if [[ -x "$NEURON_SCRIPT" ]]; then
    "$NEURON_SCRIPT" --execution "$SV_EXECUTION" || echo "⚠️ Teardown Neuron failed"
    echo "✅ Miner teardown complete."
else
    echo "⚠️ Neuron teardown script not found or not executable: $NEURON_SCRIPT"
fi

# --- WAIT NEW MINER STOP ---
sleep 5

# --- START OLD MINER ---
echo
echo "🧐 Choose how the old Miner should be started:"
echo "  1) systemd service"
echo "  2) background process (PM2)"
echo "  3) Docker container"
read -rp "⚙️  Enter option [1/2/3]: " val_mode

case "$val_mode" in
    1)
        read -rp "⚙️  Enter systemd service name: " val_svc
        echo "🔼 Starting systemd service '$val_svc'..."
        sudo systemctl start "$val_svc" || echo "⚠️ Failed to start systemd service"
    ;;
    2)
        read -rp "⚙️  Enter PM2 process name: " val_proc
        echo "🔼 Starting PM2 process '$val_proc'..."
        pm2 start "$val_proc" || echo "⚠️ Failed to start PM2 process"
    ;;
    3)
        read -rp "🐳 Enter Docker container name or ID: " val_container
        echo "🔼 Starting Docker container '$val_container'..."
        docker start "$val_container" || echo "⚠️ Failed to start container"
    ;;
    *)
        echo "⚠️ Invalid option. Skipping miner start."
    ;;
esac

# --- CLEAN WORKSPACE ---
echo "🧹 Cleaning auto upgrader workspace..."
./scripts/quick_clean.sh --workspace --remove || echo "⚠️ Cleaning failed"

# --- TEARDOWN AUTO UPGRADER ---
if [[ "$SKIP_AUTO_UPGRADER" == "false" ]]; then
    echo "🧨 Teardown the Auto Upgrader..."
    ./scripts/auto_upgrader/auto_upgrader_teardown.sh --execution "$AU_EXECUTION" || echo "⚠️ Teardown Auto Upgrader failed"
fi

echo "✅ Miner installed and started successfully."
