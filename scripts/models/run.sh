#!/bin/bash

set -e

# Determine script directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Define paths
VENV_DIR=".venv"
MAIN_SCRIPT="main.py"
TORCH_FILE_PATH="$1"
shift  # Remove torch file path so "$@" holds only extra args

# Step 1: Create virtual environment if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Step 2: Activate virtual environment
source "$VENV_DIR/bin/activate"

# Step 3: Upgrade pip and install torch only if not already installed
echo "📦 Ensuring torch is installed..."
if ! python -c "import torch" &> /dev/null; then
    echo "📥 Installing torch..."
    pip install --upgrade pip > /dev/null
    pip install torch > /dev/null
else
    echo "✅ torch already installed"
fi

# Step 4: Run the converter script
echo "🚀 Running model converter..."
python "$MAIN_SCRIPT" "$TORCH_FILE_PATH" "$@"

# Step 5: Deactivate and clean up virtual environment
deactivate
echo "🧹 Cleaning up virtual environment..."
rm -rf "$VENV_DIR"

echo "✅ Done."
