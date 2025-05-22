#!/bin/bash

set -e

# Determine script directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0 [--force | --remove | --version <x.y.z>]"
    echo
    echo "Description:"
    echo "  Clean contents under /var/tmp/subvortex"
    echo
    echo "Options:"
    echo "  -v, --version      Remove a specific version (e.g x.x.x, x.x.x-alpha.x)"
    echo "  -r, --remove       Remove all versioned and non-versioned directories"
    echo "  -f, --force        Mark current version (symlink target) for reinstall"
    echo "  -d, --dry-run      Preview actions without executing"
    echo "  -h, --help         Show this help message"
    exit 0
}

version_sort() {
  awk '
  {
    orig = $0
    gsub(/^subvortex-/, "", orig)

    base = orig
    type = ""
    val = 0
    weight = 3

    if (index(orig, "a") > 0) {
      split(orig, parts, "a")
      base = parts[1]
      val = parts[2] + 0
      weight = 1
    } else if (index(orig, "rc") > 0) {
      split(orig, parts, "rc")
      base = parts[1]
      val = parts[2] + 0
      weight = 2
    } else if (match(orig, /^[0-9]+\.[0-9]+\.[0-9]+$/)) {
      base = orig
      weight = 3
    }

    printf "%s-%d-%02d %s\n", base, weight, val, $0
  }
  ' | sort | awk '{print $2}'
}

OPTIONS="v:rdhf"
LONGOPTIONS="version:,remove,dry-run,help,force"

REMOVE_LATEST=false
FORCE_REINSTALL=false
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
        -f|--force)
            FORCE_REINSTALL=true
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

# Load environment variables
echo "🔍 Loading environment variables from .env..."
export $(grep -v '^#' subvortex/auto_upgrader/.env | xargs)

TARGET_BASE=${SUBVORTEX_WORKING_DIRECTORY:-/var/tmp/subvortex}
SYMLINK_PATH="$HOME/subvortex"

echo "📁 Target base directory: $TARGET_BASE"
echo "🔗 Symlink path: $SYMLINK_PATH"

if [ ! -d "$TARGET_BASE" ]; then
    echo "❌ Directory '$TARGET_BASE' does not exist."
    exit 1
fi

# Handle --force case
if [ "$FORCE_REINSTALL" = true ]; then
    if [ -L "$SYMLINK_PATH" ]; then
        target_dir="$(readlink "$SYMLINK_PATH")"
        echo "📎 Marking current version for reinstall: $target_dir"
        touch "$target_dir/force_reinstall"
        echo "✅ Done. Restart auto-upgrader to reinstall current version."
        exit 0
    else
        echo "❌ No valid symlink found at $SYMLINK_PATH"
        exit 1
    fi
fi

cd "$TARGET_BASE"
echo "🔍 Searching for directories in $TARGET_BASE..."
all_dirs=($(find . -maxdepth 1 -mindepth 1 -type d -exec basename {} \;))

echo "🔎 Found directories: ${all_dirs[*]}"

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
    echo "🎯 Target version to remove: $target_normalized"
else
    if [ ${#versioned_dirs[@]} -gt 0 ]; then
        latest_version=$(printf "%s\n" "${versioned_dirs[@]}" | version_sort | tail -n 1)
        echo "🏷️ Latest version detected: $latest_version"
    fi
fi

# Get symlink target if it exists
echo "🔗 Checking symlink at: $SYMLINK_PATH"

symlink_target=""
if [ -L "$SYMLINK_PATH" ]; then
    resolved_target="$(readlink "$SYMLINK_PATH")"
    echo "📌 Resolved symlink target: $resolved_target"

    if [[ "$resolved_target" != /* ]]; then
        resolved_target="$(cd "$(dirname "$SYMLINK_PATH")" && cd "$(dirname "$resolved_target")" && pwd)/$(basename "$resolved_target")"
    fi

    symlink_target="$(basename "$resolved_target")"
    echo "🧭 Final resolved version dir: $symlink_target"
else
    echo "⚠️  No valid symlink found at $SYMLINK_PATH"
fi

echo "🧹 Starting cleanup in: $TARGET_BASE"

for dir in "${all_dirs[@]}"; do
    keep=false

    if [ -n "$VERSION" ]; then
        if [ "$dir" == "$target_normalized" ]; then
            if [[ "$DRY_RUN" == "false" ]]; then
                echo "🔥 Removing version: $dir"
                rm -rf "$dir" || true
                [ -d "$dir" ] && echo "⚠️  Still exists — retrying with sudo" && sudo rm -rf "$dir"

                if [ "$symlink_target" == "$dir" ]; then
                    echo "🔗 Removing symlink: $SYMLINK_PATH (targeted $dir)"
                    sudo rm -f "$SYMLINK_PATH"
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
            [ "$dir" == "$nvd" ] && keep=true && break
        done

        if [ -n "$symlink_target" ]; then
            [ "$dir" == "$symlink_target" ] && keep=true
        else
            [ "$dir" == "$latest_version" ] && keep=true
        fi
    fi

    if [ "$keep" = true ]; then
        echo "🛡️  Preserving: $dir"
    else
        if [[ "$DRY_RUN" == "false" ]]; then
            echo "🔥 Removing: $dir"
            rm -rf "$dir" || true
            [ -d "$dir" ] && echo "⚠️  Still exists — retrying with sudo" && sudo rm -rf "$dir"

            if [ "$symlink_target" == "$dir" ]; then
                echo "🔗 Removing symlink: $SYMLINK_PATH (targeted $dir)"
                sudo rm -f "$SYMLINK_PATH"
            fi
        else
            echo "💡 Simulating removal: $dir"
            [ "$symlink_target" == "$dir" ] && echo "💡 Simulating symlink removal: $SYMLINK_PATH"
        fi
    fi
done

# Final symlink cleanup check
if [ -L "$SYMLINK_PATH" ]; then
    resolved_target="$(readlink "$SYMLINK_PATH")"

    if [[ "$resolved_target" != /* ]]; then
        resolved_target="$(cd "$(dirname "$SYMLINK_PATH")" && cd "$(dirname "$resolved_target")" && pwd)/$(basename "$resolved_target")"
    fi

    if [ ! -d "$resolved_target" ]; then
        echo "🧨 Symlink target no longer exists. Removing broken symlink: $SYMLINK_PATH"
        sudo rm -f "$SYMLINK_PATH"
    fi
fi

echo "✅ Cleanup workspace complete."
