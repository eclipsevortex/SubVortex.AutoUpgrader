#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0 [--api-key <WANDB_API_KEY>] [--relogin]"
    echo
    echo "Description:"
    echo "  This script activates a virtual environment and logs into Weights & Biases."
    echo
    echo "Options:"
    echo "  --api-key   Wandb API key"
    echo "  --relogin   Force a re-login to Wandb"
    echo "  --help      Show this help message"
    exit 0
}

API_KEY=""
FORCE_RELOGIN=false

# Parse arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        -k | --api-key)
            API_KEY="$2"
            shift 2
        ;;
        --relogin)
            FORCE_RELOGIN=true
            shift
        ;;
        -h | --help)
            show_help
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

# Check mandatory args
check_required_args API_KEY

# --- Subvortex structure checks ---
if [[ ! -L "/root/subvortex" ]]; then
    echo "❌ /root/subvortex is not a symbolic link. Aborting."
    exit 1
fi

if [[ ! -d "/root/subvortex/subvortex/validator/neuron" ]]; then
    echo "❌ Expected directory /root/subvortex/subvortex/validator/neuron does not exist. Aborting."
    exit 1
fi

# --- Activate virtual environment ---
VENV_PATH="/root/subvortex/subvortex/validator/neuron/venv/bin/activate"
if [[ -f "$VENV_PATH" ]]; then
    echo "[INFO] Activating virtual environment..."
    source "$VENV_PATH"
else
    echo "❌ Virtual environment not found at $VENV_PATH"
    exit 1
fi

# --- W&B login ---
if command -v wandb &> /dev/null; then
    echo "[INFO] Logging into Weights & Biases..."
    if [[ "$FORCE_RELOGIN" == true ]]; then
        wandb login "$API_KEY" --relogin
    else
        wandb login "$API_KEY"
    fi
else
    echo "❌ 'wandb' is not installed in the virtual environment."
    exit 1
fi
