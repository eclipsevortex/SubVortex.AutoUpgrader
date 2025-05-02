#!/bin/bash

set -e

# Determine script directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0 [--version=<x.x.x>] [--remove] [--force]"
    echo
    echo "Description:"
    echo "  Clean all contents under /var/tmp/subvortex,"
    echo "  preserving only the latest versioned directory and all non-versioned ones."
    echo "  Use --remove to delete everything including the latest and symlink. To be used when services are stopped"
    echo "  Use --force to mark current version for reinstall (touches force_reinstall file)."
    echo
    echo "Options:"
    echo "  -v, --version      Remove a specific version (e.g. 1.0.0 or 1.0.0-alpha.1)"
    echo "  -r, --remove       Remove all versioned and non-versioned directories"
    echo "  -f, --force        Mark current version (symlink target) for reinstall"
    echo "  -d, --dry-run      Simulate without making any changes"
    echo "  -h, --help         Show this help message"
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

symlink_target=""
if [ -L "$SYMLINK_PATH" ]; then
    symlink_target="$(readlink "$SYMLINK_PATH")"
    symlink_target="$(basename "$symlink_target")"
fi

# Handle --force separately
if [[ "$FORCE_REINSTALL" == "true" && -n "$symlink_target" && -d "$symlink_target" ]]; then
    echo "📎 Marking symlink target $symlink_target for reinstall..."
    [ "$DRY_RUN" == "false" ] && touch "$symlink_target/force_reinstall" || echo "💡 Simulating: touch $symlink_target/force_reinstall"
    echo "✅ Force reinstall flag added."
    exit 0
fi

echo "🧹 Cleaning up: $TARGET_BASE"

for dir in "${all_dirs[@]}"; do
    keep=false

    if [ -n "$VERSION" ]; then
        if [ "$dir" == "$target_normalized" ]; then
            if [[ "$DRY_RUN" == "false" ]]; then
                echo "📎 Marking for reinstall: $dir"
                touch "$dir/force_reinstall"

                if [ "$symlink_target" != "$dir" ]; then
                    echo "🔥 Removing version $dir (not current symlink)"
                    rm -rf "$dir" || true
                    [ -d "$dir" ] && echo "⚠️  Directory still exists — retrying with sudo" && sudo rm -rf "$dir"
                else
                    echo "🛡️  Preserving current symlink target $dir (marked for reinstall only)"
                fi
            else
                echo "💡 Simulating: mark $dir with force_reinstall"
                [ "$symlink_target" != "$dir" ] && echo "💡 Simulating removal of $dir"
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
        [ "$dir" == "$latest_version" ] && keep=true
    fi

    if [ "$keep" = true ]; then
        echo "🛡️  Preserving: $dir"
    else
        if [[ "$DRY_RUN" == "false" ]]; then
            echo "📎 Marking for reinstall: $dir"
            touch "$dir/force_reinstall"

            if [ "$symlink_target" != "$dir" ]; then
                echo "🔥 Removing: $dir"
                rm -rf "$dir" || true
                [ -d "$dir" ] && echo "⚠️  Directory still exists — retrying with sudo" && sudo rm -rf "$dir"
            else
                echo "🛡️  Preserving current symlink target $dir (marked for reinstall only)"
            fi
        else
            echo "💡 Simulating: mark $dir with force_reinstall"
            [ "$symlink_target" != "$dir" ] && echo "💡 Simulating removal of $dir"
        fi
    fi
done

echo "✅ Cleanup workspace complete."
