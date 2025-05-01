#!/bin/bash

set -e

# Determine script directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0 [--execution=process|service]"
    echo
    echo "Description:"
    echo "  Clean all contents under /var/tmp/subvortex,"
    echo "  preserving only the latest versioned directory and all non-versioned ones."
    echo "  With --remove, remove everything including symlink and latest version."
    echo
    echo "Options:"
    echo "  -v, --version      Remove a specific version (e.g x.x.x, x.x.x-alpha.x)"
    echo "  -r, --remove       Remove all versioned and non-versioned directories"
    echo "  -d, --dry-run      Preview actions without executing"
    echo "  -h, --help         Show this help message and exit"
    exit 0
}

version_sort() {
    if command -v sort >/dev/null && sort -V </dev/null &>/dev/null; then
        sort -V
    elif command -v gsort >/dev/null; then
        gsort -V
    else
        echo "❌ Error: version sort (sort -V or gsort -V) not supported." >&2
        echo "👉 On macOS: brew install coreutils" >&2
        exit 1
    fi
}

OPTIONS="v:rdh"
LONGOPTIONS="version:,remove,dry-run,help"

REMOVE_LATEST=false
VERSION=""
DRY_RUN=false

# Parse args
while [ "$#" -ge 1 ]; do
    case "$1" in
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -r|--remove)
            REMOVE_LATEST=true
            shift
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "❌ Unexpected argument: $1"
            show_help
            ;;
    esac
done

TARGET_BASE="/var/tmp/subvortex"
SYMLINK_PATH="/root/subvortex"

if [ ! -d "$TARGET_BASE" ]; then
    echo "❌ Directory '$TARGET_BASE' does not exist."
    exit 1
fi

cd "$TARGET_BASE"
all_dirs=($(find . -maxdepth 1 -mindepth 1 -type d -exec basename {} \;))

versioned_dirs=()
non_versioned_dirs=()

# Classify directories
for dir in "${all_dirs[@]}"; do
    if [[ "$dir" =~ ^subvortex-[0-9]+\.[0-9]+\.[0-9]+.*$ ]]; then
        versioned_dirs+=("$dir")
    else
        non_versioned_dirs+=("$dir")
    fi
done

latest_version=""
target_normalized=""

if [ -n "$VERSION" ]; then
    target_normalized="subvortex-$(normalize_version "$VERSION")"
else
    if [ ${#versioned_dirs[@]} -gt 0 ]; then
        latest_version=$(printf "%s\n" "${versioned_dirs[@]}" | version_sort | tail -n 1)
    fi
fi

# Get symlink target if it exists
symlink_target=""
if [ -L "$SYMLINK_PATH" ]; then
    symlink_target="$(readlink "$SYMLINK_PATH")"
    symlink_target="$(basename "$symlink_target")"
fi

echo "🧹 Cleaning up: $TARGET_BASE"

for dir in "${all_dirs[@]}"; do
    keep=false

    if [ -n "$VERSION" ]; then
        if [ "$dir" == "$target_normalized" ]; then
            if [[ "$DRY_RUN" == "false" ]]; then
                echo "🔥 Removing: $dir"
                rm -rf "$dir" || true
                if [ -d "$dir" ]; then
                    echo "⚠️  Directory $dir still exists — retrying with sudo"
                    sudo rm -rf "$dir"
                fi

                if [ "$symlink_target" == "$dir" ]; then
                    echo "🔗 Removing symlink: $SYMLINK_PATH (targeted $dir)"
                    rm -f "$SYMLINK_PATH" || sudo rm -f "$SYMLINK_PATH"
                fi
            else
                echo "💡 Simulating removal: $dir"
                [ "$symlink_target" == "$dir" ] && echo "💡 Simulating symlink removal: $SYMLINK_PATH"
            fi
        else
            echo "🛡️  Preserving: $dir"
        fi
        continue
    fi

    if [ "$REMOVE_LATEST" = false ]; then
        for nvd in "${non_versioned_dirs[@]}"; do
            if [ "$dir" == "$nvd" ]; then
                keep=true
                break
            fi
        done

        [ "$dir" == "$latest_version" ] && keep=true
    fi

    if [ "$keep" = true ]; then
        echo "🛡️  Preserving: $dir"
    else
        if [[ "$DRY_RUN" == "false" ]]; then
            echo "🔥 Removing: $dir"
            rm -rf "$dir" || true
            if [ -d "$dir" ]; then
                echo "⚠️  Directory $dir still exists — retrying with sudo"
                sudo rm -rf "$dir"
            fi

            if [ "$symlink_target" == "$dir" ]; then
                echo "🔗 Removing symlink: $SYMLINK_PATH (targeted $dir)"
                rm -f "$SYMLINK_PATH" || sudo rm -f "$SYMLINK_PATH"
            fi
        else
            echo "💡 Simulating removal: $dir"
            [ "$symlink_target" == "$dir" ] && echo "💡 Simulating symlink removal: $SYMLINK_PATH"
        fi
    fi
done

echo "✅ Cleanup workspace complete."
