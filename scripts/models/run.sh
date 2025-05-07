#!/bin/bash

set -euo pipefail

# Define paths
VENV_DIR=".venv"
MAIN_SCRIPT="main.py"
TORCH_FILE_PATH="$1"

# Step 1: Create virtual environment if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Step 2: Activate virtual environment
source "$VENV_DIR/bin/activate"

# Step 3: Upgrade pip and install torch
echo "📦 Installing torch..."
pip install --upgrade pip > /dev/null
pip install torch > /dev/null

# Step 4: Run the converter script
echo "🚀 Running model converter..."
python "$MAIN_SCRIPT" "$TORCH_FILE_PATH"

# Optional: deactivate
deactivate
