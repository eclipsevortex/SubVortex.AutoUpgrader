#!/bin/bash

set -e

# Check if Redis is managed by systemd
if systemctl list-units --type=service --all | grep -qE '^redis\.service|^redis-server\.service'; then
    echo "Stopping and disabling Redis via systemd..."
    sudo systemctl stop redis-server || true
    sudo systemctl disable redis-server || true
    sudo rm -f /etc/systemd/system/redis.service
    sudo systemctl daemon-reload
else
    # Check if Redis is managed by PM2 with pattern subvortex-*-redis
    if command -v pm2 &>/dev/null && pm2 list | grep -q 'subvortex-.*-redis'; then
        echo "Stopping and deleting Redis processes via PM2..."
        pm2 list | grep 'subvortex-.*-redis' | awk '{print $2}' | while read -r proc_name; do
            pm2 stop "$proc_name" || true
            pm2 delete "$proc_name" || true
        done
    else
        echo "No Redis process detected via systemd or PM2. Skipping service stop."
    fi
fi

# Purge Redis packages if installed
echo "Purging Redis packages..."
sudo apt purge redis-server redis -y || true
sudo apt autoremove --purge -y || true

# Remove Redis-related files and directories
echo "Removing Redis files..."
sudo rm -rf /etc/redis/
sudo rm -rf /var/lib/redis/
sudo rm -rf /var/log/redis/
sudo rm -f /usr/local/bin/redis-server
sudo rm -f /usr/local/bin/redis-cli

# Vacuum journal logs to reclaim space
echo "Vacuuming journal logs..."
sudo journalctl --vacuum-time=1s || true

echo "Redis cleanup complete."
