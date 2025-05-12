#!/bin/bash

set -e
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0 [--neuron=<neuron>] [--release=<tag>]"
    echo
    echo "Description:"
    echo "  Sets up the environment for the validator neuron,"
    echo "  downloading a specific release or prerelease if provided."
    echo
    echo "Options:"
    echo "  --neuron        Type of neuron to setup (options: miner|validator, default: miner)"
    echo "  --release       Tag of the official release/pre release to use (e.g. v3.0.0, v3.0.0-rc.1, v3.0.0-alpha.1)"
    echo "  --help          Show this help message"
    exit 0
}

NEURON="miner"
RELEASE=""

echo "🚀 Starting SubVortex environment setup for neuron: $NEURON"

while [ "$#" -ge 1 ]; do
    case "$1" in
        --neuron)
            NEURON="$2"
            shift 2
        ;;
        --release)
            RELEASE="$2"
            shift 2
        ;;
        -h|--help)
            show_help
        ;;
        *)
            echo "❌ Unrecognized option '$1'"
            exit 1
        ;;
    esac
done

REPO="eclipsevortex/SubVortex"
ASSET_DIR=${SUBVORTEX_ASSET_DIR:-/var/tmp/subvortex}
EXECUTION_DIR=${SUBVORTEX_EXECUTION_DIR:-$HOME/subvortex}

mkdir -p "$ASSET_DIR"

# Get release tag
TAG="${RELEASE}"
if [[ -z "$TAG" ]]; then
    echo "📦 Fetching latest release tag..."
    TAG=$(curl -s "https://api.github.com/repos/$REPO/releases/latest" | jq -r '.tag_name')
fi

echo "🔖 Using tag: $TAG"
RELEASE_JSON=$(curl -s "https://api.github.com/repos/$REPO/releases/tags/$TAG")

# Check for non-existent release
if echo "$RELEASE_JSON" | jq -e '.message? | test("Not Found")' >/dev/null; then
    echo "❌ Release tag '$TAG' does not exist in $REPO"
    exit 1
fi

ASSET_URL=$(echo "$RELEASE_JSON" | jq -r ".assets[]
    | select(.name | startswith(\"subvortex_$NEURON\") and endswith(\".tar.gz\"))
| .browser_download_url")

if [[ -z "$ASSET_URL" ]]; then
    echo "❌ No matching .tar.gz asset found for validator in release: $TAG"
    exit 1
fi

ARCHIVE_NAME=$(basename "$ASSET_URL")
ARCHIVE_PATH="$ASSET_DIR/$ARCHIVE_NAME"

echo "⬇️  Downloading archive from: $ASSET_URL"
curl -L "$ASSET_URL" -o "$ARCHIVE_PATH"
echo "✅ Download complete: $ARCHIVE_PATH"

echo "📂 Extracting archive into: $ASSET_DIR"
tar -xzf "$ARCHIVE_PATH" -C "$ASSET_DIR"

EXTRACTED_SUBDIR=$(tar -tzf "$ARCHIVE_PATH" | head -1 | cut -f1 -d"/")  # e.g. subvortex_validator-3.0.0
EXTRACTED_PATH="$ASSET_DIR/$EXTRACTED_SUBDIR"

# Normalize the name by removing _validator or _miner
RENAMED_SUBDIR="${EXTRACTED_SUBDIR/_validator/}"
RENAMED_SUBDIR="${RENAMED_SUBDIR/_miner/}"
RENAMED_PATH="$ASSET_DIR/$RENAMED_SUBDIR"

# Rename only if necessary
if [ "$EXTRACTED_PATH" != "$RENAMED_PATH" ]; then
    echo "📦 Renaming $EXTRACTED_PATH → $RENAMED_PATH"
    mv "$EXTRACTED_PATH" "$RENAMED_PATH"
fi

EXTRACT_DIR="$RENAMED_PATH"
echo "📁 Normalized extracted directory: $EXTRACT_DIR"

echo "🔗 Managing symlink at: $EXECUTION_DIR"
if [ -L "$EXECUTION_DIR" ]; then
    CURRENT_TARGET=$(readlink "$EXECUTION_DIR")
    if [ "$CURRENT_TARGET" == "$EXTRACT_DIR" ]; then
        echo "✅ Symlink already correct: $EXECUTION_DIR → $CURRENT_TARGET"
    else
        echo "🔁 Updating symlink to point to: $EXTRACT_DIR"
        ln -sfn "$EXTRACT_DIR" "$EXECUTION_DIR"
    fi
    elif [ -e "$EXECUTION_DIR" ]; then
    echo "❌ $EXECUTION_DIR exists and is not a symlink. Refusing to overwrite."
    exit 1
else
    echo "➕ Creating symlink: $EXECUTION_DIR → $EXTRACT_DIR"
    ln -s "$EXTRACT_DIR" "$EXECUTION_DIR"
fi

echo "🛠️  Processing environment files..."
for ENV_SRC in ./subvortex/auto_upgrader/environment/env.subvortex.$NEURON.*; do
    [ -f "$ENV_SRC" ] || continue
    COMPONENT=$(basename "$ENV_SRC" | cut -d'.' -f4)
    DEST_DIR="$EXTRACT_DIR/subvortex/$NEURON/$COMPONENT"
    
    if [ ! -d "$DEST_DIR" ]; then
        echo "⚠️ Skipping env copy for $COMPONENT: $DEST_DIR does not exist"
        continue
    fi
    
    echo "📄 Copying env file → $DEST_DIR/.env"
    cp "$ENV_SRC" "$DEST_DIR/.env"
done

echo "🛠️  Processing template files..."
for TEMPLATE_SRC in ./subvortex/auto_upgrader/template/template-subvortex-$NEURON-*.*; do
    [ -f "$TEMPLATE_SRC" ] || continue
    
    FILENAME=$(basename "$TEMPLATE_SRC")
    NAME_PART="${FILENAME#template-subvortex-validator-}"  # e.g. redis.conf
    COMPONENT="${NAME_PART%%.*}"                           # e.g. redis
    
    DEST_DIR="$EXTRACT_DIR/subvortex/$NEURON/$COMPONENT/deployment/templates"
    DEST_FILE="$DEST_DIR/subvortex-$NEURON-$NAME_PART"
    
    if [ ! -d "$DEST_DIR" ]; then
        echo "⚠️ Skipping template for $COMPONENT: $DEST_DIR does not exist"
        continue
    fi
    
    echo "📄 Copying template → $DEST_FILE"
    cp "$TEMPLATE_SRC" "$DEST_FILE"
done

echo "🧹 Cleaning up downloaded archive: $ARCHIVE_PATH"
rm -f "$ARCHIVE_PATH"

echo "🎉 SubVortex environment setup complete for $NEURON using release: ${RELEASE:-${PRERELEASE:-latest}}"
