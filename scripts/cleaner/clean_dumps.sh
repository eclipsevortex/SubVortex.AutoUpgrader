#!/bin/bash

set -e

# Determine script directory dynamically to ensure everything runs in ./scripts/api/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."

source ./scripts/utils/utils.sh

show_help() {
    echo "Usage: $0"
    echo
    echo "Description:"
    echo "  Clean all contents under the dump directory"
    echo
    echo "Options:"
    echo "  -d, --dump-path         Path of the dumps and cheksum directory. Reflect `dir` in redis.config". Default /var/tmp/dumps/redis
    exit 0
}

OPTIONS="d:h"
LONGOPTIONS="dump-path:,help"

DUMP_DIR=/var/tmp/dumps/redis

# Parse arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        -d|--dump-path)
            DUMP_DIR="$2"
            shift 2
        ;;
        -h|--help)
            show_help
            exit 0
        ;;
        --)
            shift
            break
        ;;
        *)
            echo "❌ Unexpected argument: $1"
            show_help
            exit 1
        ;;
    esac
done

echo "🧹 Checking for dump directory at: $DUMP_DIR"
if [[ -d "$DUMP_DIR" ]]; then
    echo "🔥 Removing dump directory and contents: $DUMP_DIR"
    sudo rm -rf "$DUMP_DIR"
else
    echo "ℹ️ Dump directory not found: $DUMP_DIR — nothing to clean."
fi

echo "✅ Cleanup dumps complete."
