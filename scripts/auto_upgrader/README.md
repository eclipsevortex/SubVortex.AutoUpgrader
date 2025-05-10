[← Back to Main README](../../README.md)

# 🛠️ Auto Upgrader Setup Guide

This guide explains how to **install** and **uninstall** Auto Upgrader, the tool responsible for keeping your services up to date.

## 📑 Contents

- [Installation](#installation)
  - [Run as Process](#run-as-process)
  - [Run as Service](#run-as-service)
  - [Run as Container](#run-as-container)
- [Uninstallation](#uninstallation)
  - [Remove Process](#remove-process)
  - [Remove Service](#remove-service)
  - [Remove Container](#remove-container)

<br />
<br />

# 🛠️ Installation <a id="installation"></a>

You can install the Auto Upgrader in one of three ways:

- As a **process** (using PM2)
- As a **system service** (using systemd)
- ~~As a **container** (using Docker)~~

## ▶️ Run as Process <a id="run-as-process"></a>

1. Set the execution method in `.env`:

```env
SUBVORTEX_EXECUTION_METHOD=process
```

2. Run the setup script:

```bash
./subvortex/auto_upgrader/deployment/process/auto_upgrader_process_setup.sh
```

3. Start the Auto Upgrader:

```bash
./subvortex/auto_upgrader/deployment/process/auto_upgrader_process_start.sh
```

4. Verify it's running:

```bash
pm2 list
```

You should see a process named `subvortex-auto-upgrade`.

To check logs:

```bash
pm2 log subvortex-auto-upgrade
```

## 🛡️ Run as Service <a id="run-as-service"></a>

1. Set the execution method in `.env`:

```env
SUBVORTEX_EXECUTION_METHOD=service
```

2. Run the setup script:

```bash
./subvortex/auto_upgrader/deployment/service/auto_upgrader_service_setup.sh
```

3. Start the Auto Upgrader:

```bash
./subvortex/auto_upgrader/deployment/service/auto_upgrader_service_start.sh
```

4. Check the service status:

```bash
systemctl status subvortex-auto-upgrader
```

You should see something like

```bash
Loaded: loaded (/etc/systemd/user/subvortex-auto-upgrader.service; enabled; vendor preset: enabled)
     Active: active (running) since Thu 2025-04-10 11:51:27 BST; 6s ago
   Main PID: 2229560 (python3)
      Tasks: 10 (limit: 28765)
     Memory: 57.9M
        CPU: 1.592s
     CGroup: /system.slice/subvortex-auto-upgrader.service
             └─2229560 /root/SubVortex.AutoUpgrader/subvortex/auto_upgrader/venv/bin/python3 -m subvortex.auto_upgrader.src.main
```

To view logs:

```bash
tail -f /var/log/subvortex-auto-upgrader/subvortex-auto-upgrader.log
```

## 🐳 Run as Container <a id="run-as-container"></a>

> ⚠️ The Auto Upgrader is not yet available to run inside a Docker container. Please run it via `service` or `process`.

Before installing the Auto Upgrader as a container, be sure you have docker installed. If not, you can run

```bash
./scripts/docker/docker_setup.sh
```

1. Set the execution method in `.env`:

```env
SUBVORTEX_EXECUTION_METHOD=docker
```

2. Run the setup script:

```bash
./subvortex/auto_upgrader/deployment/docker/auto_upgrader_docker_setup.sh
```

3. Start the Auto Upgrader:

```bash
./subvortex/auto_upgrader/deployment/docker/auto_upgrader_docker_start.sh
```

4. Confirm it's running:

```bash
docker ps
```

Look for a container named `subvortex-auto-upgrade`.

To follow logs:

```bash
docker logs -f subvortex-auto-upgrade
```

<br />

# 🧹 Uninstallation <a id="uninstallation"></a>

## ❌ Remove Process <a id="remove-process"></a>

To stop and remove the Auto Upgrader running as a process:

```bash
./subvortex/auto_upgrader/deployment/process/auto_upgrader_process_teardown.sh
```

Confirm it's removed:

```bash
pm2 list
```

The `subvortex-auto-upgrade` process should no longer appear.

## ❌ Remove Service <a id="remove-service"></a>

To uninstall the Auto Upgrader running as a system service:

```bash
./subvortex/auto_upgrader/deployment/service/auto_upgrader_service_teardown.sh
```

Check that the service is removed:

```bash
systemctl status subvortex-auto-upgrader
```

You should see:

```
Unit subvortex-auto-upgrader.service could not be found.
```

## ❌ Remove Container <a id="remove-container"></a>

> ⚠️ The Auto Upgrader is not yet available to run inside a Docker container. Please run it via `service` or `process`.

To tear down the Auto Upgrader container:

```bash
./subvortex/auto_upgrader/deployment/docker/auto_upgrader_docker_teardown.sh
```

Verify it's gone:

```bash
docker ps
```

The `subvortex-auto-upgrade` container should no longer be listed.

---

Need help or want to chat with other SubVortex users?  
Join us on [Discord](https://discord.gg/bittensor)!
