#!/bin/bash

set -e

# Determine script directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../.."

source ./scripts/utils/utils.sh

show_help() {
    echo
    echo "Description:"
    echo "  Setup and start the new miner and stop the old one"
    echo
    echo "Options:"
    echo "  --execution   Specify the execution method used from the auto upgrader r(default: service)"
    echo "  --help        Show this help message"
    exit 0
}

OPTIONS="e:h"
LONGOPTIONS="execution:,help"

# Set defaults from env (can be overridden by arguments)
AU_EXECUTION="${SUBVORTEX_EXECUTION_METHOD:-service}"

# Parse arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        -e |--execution)
            AU_EXECUTION="$2"
            shift 2
        ;;
        -h | --help)
            show_help
            exit 0
        ;;
        --)
            shift
            break
        ;;
        *)
            echo "❌ Unrecognized option '$1'"
            exit 1
        ;;
    esac
done

# Check maandatory args
check_required_args AU_EXECUTION

# Redis backup
REDIS_BACKUP="/var/tmp/backup"
mkdir -p "$REDIS_BACKUP"

# Execution for the service of SubVortex
source subvortex/auto_upgrader/.env
SV_EXECUTION=${SUBVORTEX_EXECUTION_METHOD:-service}
NEW_REDIS_HOST=${SUBVORTEX_REDIS_HOST:-127.0.0.1}
NEW_REDIS_PORT=${SUBVORTEX_REDIS_PORT:-6379}
NEW_REDIS_PASSWORD=${SUBVORTEX_REDIS_PASSWORD:-}
NEW_REDIS_DB=${SUBVORTEX_REDIS_INDEX:-0}

# ✅ Export SUBVORTEX_FLOATTING_FLAG if it exists (without error if not set)
export SUBVORTEX_FLOATTING_FLAG="${SUBVORTEX_FLOATTING_FLAG:-}"

echo "🔧 Installing the Auto Upgrader..."
./scripts/auto_upgrader/auto_upgrader_setup.sh --execution "$AU_EXECUTION"

# --- DUMP OLD REDIS ---
echo "🧠 Configuring Redis connection..."
read -p "📡 Old Redis Host [127.0.0.1]: " host
host=${host:-127.0.0.1}

read -p "🔌 Old Redis Port [6379]: " port
port=${port:-6379}

read -s -p "🔐 Old Redis Password (leave empty if none): " password
echo

read -p "📦 Old Redis DB Index to dump [1]: " dbindex
dbindex=${dbindex:-1}

read -p "📦 Old Redis config [/etc/redis/redis.conf]: " config_path
config_path=${config_path:-/etc/redis/redis.conf}

# --- TEST CONNECTION ---
echo "🔄 Connecting to the Old Redis DB $dbindex on $host:$port..."
if [[ -n "$password" ]]; then
    ping_output=$(redis-cli -h "$host" -p "$port" -a "$password" -n "$dbindex" PING 2>&1)
else
    ping_output=$(redis-cli -h "$host" -p "$port" -n "$dbindex" PING 2>&1)
fi

if ! echo "$ping_output" | grep -q "PONG"; then
    echo "❌ Connection failed: $ping_output"
    exit 1
fi

echo "✅ Connected to the Old Redis @ $host:$port (DB $dbindex)"

# Timestamp and base backup directory
timestamp=$(date +%Y%m%d%H%M%S)

# Get Redis user (from ps)
redis_user=$(ps -eo user,cmd | grep '[r]edis-server' | awk '{print $1}' | head -n1)
echo "👤 Detected Redis user: $redis_user"

# --- BACKUP Config ---
config_dir="$(dirname "$config_path")"
conf_backup="$REDIS_BACKUP/redis.conf.backup.$timestamp"
sudo cp "$config_path" "$conf_backup"
sudo chown "$new_redis_user":"$new_redis_user" "$conf_backup"
echo "✅ Backed up redis.conf to: $conf_backup"

# --- BACKUP KEYS ---
echo "🔹 Dumping keys from old Redis..."
python3 ./scripts/redis/redis_dump.py \
    --run_type create \
    --redis_host $host \
    --redis_port $port \
    --redis_index $dbindex \
    --redis_password $password \
    --redis_dump_path "$REDIS_BACKUP/redis.dump"
echo "✅ Redis dumped succesfully"

# --- SAVE METADATA ---
echo "🧾 Writing metadata.json for rollback..."
METADATA_FILE="$REDIS_BACKUP/metadata.json"
cat <<EOF > "$METADATA_FILE"
{
  "timestamp": "$timestamp",
  "old_redis_host": "$host",
  "old_redis_port": "$port",
  "old_redis_dbindex": "$dbindex",
  "old_redis_password": "${password}",
  "config_path": "$config_path",
  "config_dir": "$config_dir",
  "dump_file": "$REDIS_BACKUP/redis.dump",
  "user": "$redis_user"
}
EOF

echo "✅ Metadata stored in $METADATA_FILE"

# --- STOP OLD VALIDATOR NEURON ---
echo
read -p "🛠️ How is the Validator running? [1=systemd, 2=pm2, 3=docker]: " val_mode
case "$val_mode" in
    1) read -p "Validator service name: " val_svc; sudo systemctl stop "$val_svc";;
    2) read -p "Validator process name: " val_proc; sudo pm2 stop "$val_proc";;
    3) read -p "Validator container name/ID: " val_container; docker stop "$val_container";;
    *) echo "⚠️ Skipping validator stop.";;
esac

# --- STOP OLD VALIDATOR REDIS ---
echo
read -p "🛠️ How is the Old Redis running? [1=systemd, 2=pm2, 3=docker]: " mode

case "$mode" in
    1)
        read -p "⚙️  Enter systemd service name [redis-server]: " svc
        svc=${svc:-redis-server}
        echo "🔼 Stopping systemd service '$svc'..."
        sudo systemctl stop "$svc" || echo "⚠️ Failed to stop systemd service $svc"
    ;;
    2)
        read -p "⚙️  Enter Redis process (PM2) name: " proc
        proc=${proc:-redis-server}
        echo "🔼 Stopping PM2 process '$proc'..."
        pm2 stop "$proc" || echo "⚠️ Failed to stop PM2 process $proc"
    ;;
    3)
        read -p "🐳 Enter Redis Docker container name or ID: " container
        echo "🔼 Stopping Docker container '$container'..."
        docker stop "$container" || echo "⚠️ Failed to stop container $container"
    ;;
    *)
        echo "⚠️ Invalid option. Skipping Redis stop."
    ;;
esac

sleep 3

# If Redis still running on port 6379, kill it
if lsof -iTCP:6379 -sTCP:LISTEN >/dev/null; then
    echo "⚠️ Redis still listening on port 6379. Killing manually..."
    pid=$(lsof -tiTCP:6379 -sTCP:LISTEN)
    if [[ -n "$pid" ]]; then
        sudo kill -9 "$pid"
        echo "✅ Redis process (PID $pid) killed"
    else
        echo "❌ Could not identify Redis process. Check manually."
    fi
else
    echo "✅ Redis is fully stopped"
fi

# --- START AUTO UPGRADER ---
echo "🚀 Starting Auto Upgrader..."
./scripts/auto_upgrader/auto_upgrader_start.sh --execution "$AU_EXECUTION"

# --- WAIT FOR NEW VALIDATOR NEURON ---
echo "⏳ Waiting for validator neuron to be up via $SV_EXECUTION..."
NEURON_NAME="subvortex-validator-neuron"
MAX_WAIT=300; WAIT_INTERVAL=3; elapsed=0; ready=0

while [[ $elapsed -lt $MAX_WAIT ]]; do
    case "$SV_EXECUTION" in
        service) systemctl is-active --quiet "$NEURON_NAME" && ready=1 && break;;
        process) pm2 list | grep "$NEURON_NAME" | grep -q online && ready=1 && break;;
        container) docker ps --format '{{.Names}}' | grep -q "^$NEURON_NAME$" && ready=1 && break;;
        *) echo "⚠️ Unknown execution method."; break;;
    esac
    echo "🕒 Waiting... ($elapsed/$MAX_WAIT)"
    sleep "$WAIT_INTERVAL"
    elapsed=$((elapsed + WAIT_INTERVAL))
done

[[ $ready -eq 0 ]] && echo "❌ Timeout. Proceeding anyway."

# --- STOP VALIDATOR NEURON TO RESTORE KEYS ---
echo "🔚 Stopping validator neuron..."
/root/subvortex/subvortex/validator/neuron/scripts/neuron_stop.sh --execution "$SV_EXECUTION"

# --- WAIT FOR NEW VALIDATOR REDIS ---
echo "⏳ Waiting for validator redis to be up via $SV_EXECUTION..."
REDIS_NAME="subvortex-validator-redis"
MAX_WAIT=300; WAIT_INTERVAL=3; elapsed=0; ready=0

while [[ $elapsed -lt $MAX_WAIT ]]; do
    case "$SV_EXECUTION" in
        service) systemctl is-active --quiet "$REDIS_NAME" && ready=1 && break;;
        process) pm2 list | grep "$REDIS_NAME" | grep -q online && ready=1 && break;;
        container) docker ps --format '{{.Names}}' | grep -q "^$REDIS_NAME$" && ready=1 && break;;
        *) echo "⚠️ Unknown execution method."; break;;
    esac
    echo "🕒 Waiting... ($elapsed/$MAX_WAIT)"
    sleep "$WAIT_INTERVAL"
    elapsed=$((elapsed + WAIT_INTERVAL))
done

# --- RESTORE KEYS TO NEW REDIS ---
echo "🚧 Restoring keys to new Redis..."
python3 ./scripts/redis/redis_dump.py \
    --run_type restore \
    --redis_host $NEW_REDIS_HOST \
    --redis_port $NEW_REDIS_PORT \
    --redis_index $NEW_REDIS_DB \
    --redis_password $NEW_REDIS_PASSWORD \
    --redis_dump_path "$REDIS_BACKUP/redis.dump"
echo "✅ Restored keys to new Redis."

# --- START VALIDATOR NEURON ---
echo "🚀 Starting validator neuron..."
/root/subvortex/subvortex/validator/neuron/scripts/neuron_start.sh --execution "$SV_EXECUTION"

echo "✅ Validator installed and started successfully."
