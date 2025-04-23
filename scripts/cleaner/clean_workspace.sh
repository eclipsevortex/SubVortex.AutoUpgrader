#!/bin/bash

set -e

REMOVE_LATEST=false

usage() {
cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Clean all contents under /var/tmp/subvortex,
preserving only the latest versioned directory and all non-versioned ones.
With --remove, remove everything.

Options:
  -r, --remove       Remove all versioned and non-versioned directories
  -h, --help         Show this help message and exit

Examples:
  $(basename "$0")
  $(basename "$0") --remove
EOF
}

# Determine compatible version sort command
version_sort() {
  if command -v sort >/dev/null && sort -V </dev/null &>/dev/null; then
    sort -V
  elif command -v gsort >/dev/null; then
    gsort -V
  else
    echo "❌ Error: version sort (sort -V or gsort -V) not supported on this system." >&2
    echo "👉 On macOS, run: brew install coreutils" >&2
    exit 1
  fi
}

OPTIONS="e:rh"
LONGOPTIONS="execute:,remove,help"

# Parse the options and their arguments
PARSED="$(getopt -o $OPTIONS -l $LONGOPTIONS: --name "$0" -- "$@")"
# PARSED=$(getopt -o "$OPTIONS" -l "$LONGOPTIONS" --name "$0" -- "$@")
if [ $? -ne 0 ]; then
    exit 1
fi

# Evaluate the parsed result to reset positional parameters
eval set -- "$PARSED"

# Parse arguments
while true; do
echo "ARG $1"
  case "$1" in
    -r|--remove)
      REMOVE_LATEST=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "❌ Unknown option: $1"
      usage
      exit 1
      ;;
    *)
      echo "❌ Unexpected argument: $1"
      usage
      exit 1
      ;;
  esac
done

echo "REMOVE $REMOVE_LATEST"

TARGET_BASE="/var/tmp/subvortex"

if [ ! -d "$TARGET_BASE" ]; then
  echo "❌ Error: Directory '$TARGET_BASE' does not exist."
  exit 1
fi

cd "$TARGET_BASE"
all_dirs=($(find . -maxdepth 1 -mindepth 1 -type d -exec basename {} \;))

versioned_dirs=()
non_versioned_dirs=()

# Classify directories
for dir in "${all_dirs[@]}"; do
  if [[ "$dir" =~ ^subvortex-[0-9]+\.[0-9]+\.[0-9]+([^/]+)?$ ]]; then
    versioned_dirs+=("$dir")
  else
    non_versioned_dirs+=("$dir")
  fi
done

# Identify latest versioned directory
latest_version=""
if [ ${#versioned_dirs[@]} -gt 0 ]; then
  latest_version=$(printf "%s\n" "${versioned_dirs[@]}" | version_sort | tail -n 1)
fi

echo "🧹 Cleaning up: $TARGET_BASE"

for dir in "${all_dirs[@]}"; do
  keep=false

  if [ "$REMOVE_LATEST" = false ]; then
    for nvd in "${non_versioned_dirs[@]}"; do
      if [ "$dir" == "$nvd" ]; then
        keep=true
        break
      fi
    done

    if [ "$dir" == "$latest_version" ]; then
      keep=true
    fi
  fi

  if [ "$keep" = true ]; then
    echo "🛡️  Preserving: $dir"
  else
    echo "🔥 Removing: $dir"
    # rm -rf "$dir"
  fi
done

echo "✅ Cleanup complete."
