#!/bin/bash

set +e

# 🧭 Navigate to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../../.."

source ./scripts/utils/utils.sh

show_help() {
    echo
    echo "Description:"
    echo "  Stop and teardown the new miner and restart the old one"
    echo
    echo "Options:"
    echo "  --execution             Specify the execution method used from the auto upgrader r(default: service)"
    echo "  --skip-auto-upgrader    Skip stopping and tearing down the auto upgrader"
    echo "  --help                  Show this help message"
    exit 0
}

OPTIONS="e:ah"
LONGOPTIONS="execution:,:skip-auto-upgrader,help"

# Set defaults from env (can be overridden by arguments)
AU_EXECUTION="${SUBVORTEX_EXECUTION_METHOD:-service}"
SKIP_AUTO_UPGRADER=false

# Parse arguments
while [ "$#" -ge 1 ]; do
    case "$1" in
        -e |--execution)
            AU_EXECUTION="$2"
            shift 2
        ;;
        --skip-auto-upgrader)
            SKIP_AUTO_UPGRADER=true
            shift
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

# Execution for the service of SubVortex
source subvortex/auto_upgrader/.env
SV_EXECUTION=${SUBVORTEX_EXECUTION_METHOD:-service}

# ✅ Export SUBVORTEX_FLOATTING_FLAG if it exists (without error if not set)
export SUBVORTEX_FLOATTING_FLAG="${SUBVORTEX_FLOATTING_FLAG:-}"

echo "🔄 Starting rollback & restore..."

# --- STOP THE AUTO UPGRADER ---
echo "🚀 Attempting to stop new auto upgrader..."
./scripts/auto_upgrader/auto_upgrader_stop.sh --execution "$AU_EXECUTION" || echo "⚠️ Stoppping Auto Upgrader failed"

# --- TEARDOWN NEW VALIDATOR ---
echo "🧨 Attempting to teardown new validator neuron..."
NEURON_SCRIPT="/root/subvortex/subvortex/validator/neuron/scripts/neuron_teardown.sh"
if [[ -f "$NEURON_SCRIPT" ]]; then
    "$NEURON_SCRIPT" --execution "$SV_EXECUTION" || echo "⚠️ Teardown Neuron failed"
fi
echo "✅ New Validator teardown successfully."

# --- STOP NEW REDIS
echo "🛑 Attempting to stop new validator redis..."
REDIS_SCRIPT="/root/subvortex/subvortex/validator/redis/scripts/redis_stop.sh"
if [[ -f "$REDIS_SCRIPT" ]]; then
    "$REDIS_SCRIPT" --execution "$SV_EXECUTION" || echo "⚠️ Stopping Reids failed"
fi
echo "✅ New Redis teardown successfully."

# --- DELETE NEW REDIS WITHOUT REMOVINS REDIS SERVER THAT WAS USED BEFORE ---
echo "🧹 Attempting to clean new validator Redis..."
SERVICE_NAME="subvortex-validator-redis"

if [[ "$SV_EXECUTION" == "service" ]]; then
    if systemctl list-units --type=service --all | grep -q "${SERVICE_NAME}.service"; then
        echo "🛑 Disabling systemd service: $SERVICE_NAME..."
        sudo systemctl disable "${SERVICE_NAME}.service"

        echo "🧽 Removing systemd service file..."
        sudo rm -f "/etc/systemd/user/${SERVICE_NAME}.service"

        echo "🔄 Reloading systemd daemon..."
        sudo systemctl daemon-reexec
        sudo systemctl daemon-reload
    else
        echo "ℹ️ Systemd service ${SERVICE_NAME}.service not found. Skipping."
    fi

elif [[ "$SV_EXECUTION" == "process" ]]; then
    echo "🛑 Stopping PM2 process: $SERVICE_NAME"
    pm2 delete "$SERVICE_NAME" || echo "⚠️ PM2 process $SERVICE_NAME not found. Skipping."

elif [[ "$SV_EXECUTION" == "container" ]]; then
    echo "🐳 Removing Docker container: $SERVICE_NAME"
    
    # Removing the container
    docker rm "$SERVICE_NAME" -f || echo "⚠️ Failed to remove Docker container: $SERVICE_NAME"

    # Removing the image
    IMAGE_NAME=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep "$SERVICE_NAME" | head -n1)
    if [[ -n "$IMAGE_NAME" ]]; then
    echo "🐳 Removing Docker image: $IMAGE_NAME"
        docker rmi "$IMAGE_NAME" -f || echo "⚠️ Failed to remove Docker image: $IMAGE_NAME"
    else
        echo "ℹ️ No matching Docker image found for pattern: $SERVICE_NAME"
    fi
fi

echo "✅ New Redis teardown completed."

# If Redis still running on port 6379, kill it
if lsof -iTCP:6379 -sTCP:LISTEN >/dev/null; then
    echo "⚠️ Redis still listening on port 6379. Killing manually..."
    pid=$(lsof -tiTCP:6379 -sTCP:LISTEN)
    if [[ -n "$pid" ]]; then
        sudo kill -9 "$pid" || echo "⚠️ Failed to kill Redis process PID $pid"
        echo "✅ Redis process (PID $pid) killed"
    else
        echo "❌ Could not identify Redis process. Check manually."
    fi
else
    echo "✅ Redis is fully stopped"
fi

# --- RESTORE Redis config and data ---
metadata_file="$REDIS_BACKUP/metadata.json"

if [[ -f "$metadata_file" ]]; then
    echo "📖 Found metadata file: $metadata_file"

    # Load metadata
    config_path=$(jq -r .config_path "$metadata_file")
    config_dir=$(jq -r .config_dir "$metadata_file")
    persistence_type=$(jq -r .persistence_type "$metadata_file")
    redis_dir=$(jq -r .redis_dir "$metadata_file")
    dbfilename=$(jq -r .dbfilename "$metadata_file")
    redis_user=$(jq -r .user "$metadata_file")

    # --- Restore redis.conf ---
    conf_backup=$(ls -t "$REDIS_BACKUP"/redis.conf.backup.* 2>/dev/null | head -n1 || true)
    if [[ -n "$conf_backup" && -f "$conf_backup" ]]; then
        echo "📄 Restoring redis.conf to $config_path..."
        sudo cp "$conf_backup" "$config_path" || echo "⚠️ Failed to restore redis.conf"
        sudo chown "$redis_user:$redis_user" "$config_path" || echo "⚠️ Failed to set ownership on redis.conf"
        echo "✅ redis.conf restored and ownership set to $redis_user."

        # Extract password (optional)
        password=$(grep -E '^requirepass ' "$config_path" | awk '{print $2}' || true)
        [[ -n "$password" ]] && echo "🔐 Loaded Redis password from config."
    else
        echo "⚠️ redis.conf not restored — backup not found."
    fi
    echo "✅ Redis config restored."

else
    echo "⚠️ No redis.json metadata found in $REDIS_BACKUP. Skipping restore."
fi

# --- START OLD REDIS ---
echo "🧠 Configuring Redis connection..."
read -p "📡 Old Redis Host [127.0.0.1]: " host
host=${host:-127.0.0.1}

read -p "🔌 Old Redis Port [6379]: " port
port=${port:-6379}

read -p "📦 Old Redis DB Index to dump [1]: " dbindex
dbindex=${dbindex:-1}

# Mask default redis-server systemd service
echo "🚫 Unmasking default redis-server systemd service..."
sudo systemctl unmask redis-server || true

echo
echo "🧐 Choose how the old Redis should be started:"
echo "  1) systemd service"
echo "  2) background process"
echo "  3) docker container"
read -p "⚙️  Enter option [1/2/3]: " mode

case "$mode" in
    1)
        read -p "⚙️  Enter systemd service name [redis-server]: " svc
        svc=${svc:-redis-server}
        echo "🔼 Starting systemd service '$svc'..."
        sudo systemctl start "$svc" || echo "⚠️ Failed to start systemd service $svc"
    ;;
    2)
        read -p "⚙️  Enter Redis process (PM2) name: " proc
        proc=${proc:-redis-server}
        echo "🔼 Starting PM2 process '$proc'..."
        pm2 start "$proc" || echo "⚠️ Failed to start PM2 process $proc"
    ;;
    3)
        read -p "🐳 Enter Redis Docker container name or ID: " container
        echo "🔼 Starting Docker container '$container'..."
        docker start "$container" || echo "⚠️ Failed to start container $container"
    ;;
    *)
        echo "⚠️ Invalid option. Skipping Redis start."
    ;;
esac

echo "⏳ Waiting for Redis to respond..."
sleep 3

if [[ -n "$password" ]]; then
    ping_restore=$(redis-cli -h "$host" -p "$port" -a "$password" -n "$dbindex" PING 2>&1 || true)
else
    ping_restore=$(redis-cli -h "$host" -p "$port" -n "$dbindex" PING 2>&1 || true)
fi

if echo "$ping_restore" | grep -q "PONG"; then
    echo "✅ Redis is up."
else
    echo "⚠️ Redis did not respond. Continuing anyway."
fi

# --- RESTORE KEYS TO NEW REDIS ---
echo "🚧 Restoring keys to new Redis..."
python3 ./scripts/redis/redis_dump.py \
    --run_type restore \
    --redis_host $host \
    --redis_port $port \
    --redis_index $dbindex \
    --redis_password $password \
    --redis_dump_path "$REDIS_BACKUP/redis.dump"
echo "✅ Restored keys to new Redis."

# --- START OLD VALIDATOR ---
echo
echo "🧐 Choose how the old Validator should be started:"
echo "  1) systemd service"
echo "  2) background process"
echo "  3) docker container"
read -p "⚙️  Enter option [1/2/3]: " val_mode

case "$val_mode" in
    1)
        read -p "⚙️  Enter validator systemd service name: " val_svc
        echo "🔼 Starting validator systemd service '$val_svc'..."
        sudo systemctl start "$val_svc" || echo "⚠️ Failed to start validator systemd service"
    ;;
    2)
        read -p "⚙️  Enter validator process (PM2) name: " val_proc
        echo "🔼 Starting validator PM2 process '$val_proc'..."
        pm2 start "$val_proc" || echo "⚠️ Failed to start validator PM2 process"
    ;;
    3)
        read -p "🐳 Enter validator container name or ID: " val_container
        echo "🔼 Starting validator Docker container '$val_container'..."
        docker start "$val_container" || echo "⚠️ Failed to start validator container"
    ;;
    *)
        echo "⚠️ Invalid option. Skipping validator start."
    ;;
esac

# --- CLEAN BACKUP ---
echo "🧹 Cleaning previous Redis backup contents in $REDIS_BACKUP..."
sudo find "$REDIS_BACKUP" -mindepth 1 -delete

# --- CLEAN WORKSPACE ---
echo "🧹 Cleaning auto upgrader workspace..."
./scripts/quick_clean.sh --workspace --remove --dumps || echo "⚠️ Cleaning failed"

# --- TEARDOWN AUTO UPGRADER ---
if [[ "$SKIP_AUTO_UPGRADER" == "false" ]]; then
    echo "🧨 Teardown the Auto Upgrader..."
    ./scripts/auto_upgrader/auto_upgrader_teardown.sh --execution "$AU_EXECUTION" || echo "⚠️ Auto Upgrade teardown failed"
fi

echo "✅ Validator installed and started successfully."
