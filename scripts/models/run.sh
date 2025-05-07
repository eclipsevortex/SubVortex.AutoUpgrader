#!/bin/bash

set -e

# Determine script directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Define paths
VENV_DIR=".venv"
MAIN_SCRIPT="main.py"
TORCH_FILE_PATH="$1"
shift  # Remove torch file path from positional args

# Filter out --torch_model and its value from the remaining args
CLEANED_ARGS=()
SKIP_NEXT=false
for arg in "$@"; do
    if [ "$SKIP_NEXT" = true ]; then
        SKIP_NEXT=false
        continue
    fi
    if [ "$arg" == "--torch_model" ]; then
        SKIP_NEXT=true
        continue
    fi
    CLEANED_ARGS+=("$arg")
done

# Step 1: Create virtual environment if not exists
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Step 2: Activate virtual environment
source "$VENV_DIR/bin/activate"

# Step 3: Upgrade pip and install requirements
pip install --upgrade pip > /dev/null
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Step 4: Run the converter script
echo "🚀 Running model converter..."
python "$MAIN_SCRIPT" "$TORCH_FILE_PATH" "${CLEANED_ARGS[@]}"

# Step 5: Deactivate and clean up virtual environment
deactivate
echo "🧹 Cleaning up virtual environment..."
rm -rf "$VENV_DIR"

echo "✅ Done."
