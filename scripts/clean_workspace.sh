#!/bin/bash

set -e

SHOW_HELP=false
REMOVE_LATEST=false

# --- Usage function ---
usage() {
cat <<EOF
Usage: $(basename "$0") [OPTIONS] <directory>

Clean all contents of a directory except the latest versioned "subvortex-X.Y.Z-[alpha|rc].W" subdirectory.

Options:
  -r, --remove       Remove the latest version directory as well
  -h, --help         Show this help message and exit

Examples:
  $(basename "$0")
  $(basename "$0") --remove
EOF
}

# --- Parse arguments ---
ARGS=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -r|--remove)
      REMOVE_LATEST=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    -*)
      echo "❌ Unknown option: $1"
      usage
      exit 1
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

# Restore positional parameters
set -- "${POSITIONAL[@]}"

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
  exit 0
fi

# Check directory argument
TARGET_DIR=/var/tmp/subvortex

if [ -z "$TARGET_DIR" ]; then
  echo "❌ Error: No directory provided."
  exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
  echo "❌ Error: Directory '$TARGET_DIR' does not exist."
  exit 1
fi

# --- Find and preserve the latest subvortex version ---
cd "$TARGET_DIR"
version_dirs=($(find . -maxdepth 1 -type d -name "subvortex-*" -exec basename {} \; | grep -E '^subvortex-[0-9]+\.[0-9]+\.[0-9]+([a-z]+\d+)?$'))

if [ ${#version_dirs[@]} -eq 0 ]; then
  echo "⚠️ No matching subvortex version directories found."
  exit 0
fi

latest_version=$(printf "%s\n" "${version_dirs[@]}" | sort -V | tail -n 1)

if [ "$REMOVE_LATEST" = false ]; then
  echo "🛡️ Preserving latest version: $latest_version"
else
  echo "🧨 '--remove' provided — deleting everything, including: $latest_version"
fi

# --- Remove content ---
for entry in "$TARGET_DIR"/* "$TARGET_DIR"/.*; do
  base=$(basename "$entry")

  if [ "$base" == "." ] || [ "$base" == ".." ]; then
    continue
  fi

  if [ "$REMOVE_LATEST" = false ] && [ "$base" == "$latest_version" ]; then
    continue
  fi

  echo "🧹 Removing: $entry"
  rm -rf "$entry"
done

echo "✅ Cleanup complete."
