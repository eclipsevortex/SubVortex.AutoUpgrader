[← Back to Main README](../../README.md)

# 🛠️ Miner Setup Guide

This guide explains how to **install** and **uninstall** manually the Miner.

> ⚠️ **Manual installation is strongly discouraged.**  
> This setup guide is provided for **reference only**. The Miner is designed to be installed and managed using the **Auto Upgrader**, which ensures proper configuration, updates, and compatibility across components.
>
> If you choose to install components manually, **you are fully responsible for any issues** that arise. Community support may be **limited or unavailable** for manually configured environments.
>
> Proceed only if you understand the risks.

> ❗ **Before running any script:**  
> Make sure you've set up your environment with the version you intend to use.  
> If you're unsure, follow the [Quick Setup](../../README.md#quick-setup) guide first.

<br />

## 📑 Contents

- [About `--execution <EXECUTION_METHOD>`](#about-execution-method)
- [Quick Start](#quick-start)
- [Quick Stop](#quick-stop)
- [Monitoring & Logs](#monitoring-and-logs)
- [Quick Restart](#quick-restart)
- [Per-Component](#per-component)
  - [Redis](#redis)
  - [Metagraph](#metagraph)
  - [Neuron](#neuron)

<br />
<br />

# ⚙️ About `--execution <EXECUTION_METHOD>` <a id="about-execution-method"></a>

Most scripts require an `--execution` option to define how the Miner components should be managed:

- `process`: runs the component as a background process using **PM2**
- `service`: installs the component as a **systemd** service
- `container`: runs the component in a **Docker** container

If not specified, the default method is usually `service`.

<br />

# 🚀 Quick Start <a id="quick-start"></a>

To install the Miner in a quick way, you can run

```bash
./scripts/miner/quick_start.sh --execution <EXECUTION_METHOD>
```

It will install and start the Miner's components using the `EXECUTION_METHOD`, which defaults to `service`.

💡 Use `-h` with any script to see available options.

<br />

# 🛑 Quick Stop <a id="quick-stop"></a>

To stop the Miner in a quick way, you can run

```bash
./scripts/miner/quick_stop.sh --execution <EXECUTION_METHOD>
```

It will stop and teardown the Miner's components using the `EXECUTION_METHOD`, which defaults to `service`.

💡 Use `-h` with any script to see available options.

<br />

# 📈 Monitoring & Logs <a id="monitoring-and-logs"></a>

You can monitor the Miner and its components through logs. The log behavior depends on the `SUBVORTEX_EXECUTION_METHOD`.

Each component writes logs using the following filename format:

```bash
subvortex-miner-<component>.log
```

### 🔧 `service` mode

Logs are stored in:

```bash
/var/log/subvortex-miner/
```

Each log file inside that directory corresponds to a specific component. To view logs in real time, use:

```bash
tail -f /var/log/subvortex-miner/subvortex-miner-neuron.log
```

(Replace `neuron` with the actual component name such as `redis`, `scorer`, etc.)

---

### 🧩 `process` mode (PM2)

Logs are managed by PM2 and stored in:

```bash
/root/.pm2/logs/
```

To follow logs:

```bash
pm2 log subvortex-miner-<component>
```

---

### 🐳 `container` mode (Docker)

Logs are available via Docker:

```bash
docker logs subvortex-miner-<component> -f
```

Example:

```bash
docker logs subvortex-miner-neuron -f
```

---

### 🔍 Tips

- Add `| grep ERROR` or `| grep WARN` to quickly identify issues.
- For persistent monitoring, consider integrating with systemd journal, a log aggregator, or Prometheus log exporters.
- Always ensure your logs are rotated or cleared periodically to avoid storage bloat.

<br />

# 🔄 Quick Restart <a id="quick-restart"></a>

To stop/start the Miner in a quick way, you can run

```bash
./scripts/miner/quick_restart.sh --execution <EXECUTION_METHOD>
```

It will restart the Miner's components using the `EXECUTION_METHOD`, which defaults to `service`.

💡 Use `-h` with any script to see available options.

<br />

# Per-Component <a id="per-component"></a>

## Redis <a id="redis"></a>

### Installation <a id="redis-installation"></a>

To install Redis for the Miner:

1. Set it up:

```bash
./scripts/miner/redis/redis_setup.sh --execution <EXECUTION_METHOD>
```

2. Start it:

```bash
./scripts/miner/redis/redis_start.sh --execution <EXECUTION_METHOD>
```

💡 Use `-h` with any script to see available options.

### Uninstallation <a id="redis-uninstallation"></a>

⚠️ Note: Make sure Neuron and Metagraph are stopped before stopping Redis.

To uninstall Redis for the Miner:

1. Stop it:

```bash
./scripts/miner/redis/redis_stop.sh --execution <EXECUTION_METHOD>
```

2. Tear it down:

```bash
./scripts/miner/redis/redis_teardown.sh --execution <EXECUTION_METHOD>
```

💡 Use `-h` with any script to see available options.

## Metagraph <a id="metagraph"></a>

### Installation <a id="metagraph-installation"></a>

⚠️ Note: Make sure Redis and Metagraph are running before starting the Metagraph.

To install Metagraph for the Miner:

1. Set it up:

```bash
./scripts/miner/metagraph/metagraph_setup.sh --execution <EXECUTION_METHOD>
```

2. Start it:

```bash
./scripts/miner/metagraph/metagraph_start.sh --execution <EXECUTION_METHOD>
```

💡 Use `-h` with any script to see available options.

### Uninstallation <a id="metagraph-uninstallation"></a>

⚠️ Note: Make sure Neuron is stopped before stopping Metagraph.

To uninstall Metagraph for the Miner:

1. Stop it:

```bash
./scripts/miner/metagraph/metagraph_stop.sh --execution <EXECUTION_METHOD>
```

2. Tear it down:

```bash
./scripts/miner/metagraph/metagraph_teardown.sh --execution <EXECUTION_METHOD>
```

💡 Use `-h` with any script to see available options.

## Neuron <a id="neuron"></a>

### Installation <a id="neuron-installation"></a>

⚠️ Note: Make sure Redis and Metagraph are running before starting the Metagraph.

To install Neuron for the Miner:

1. Set it up:

```bash
./scripts/miner/neuron/neuron_setup.sh --execution <EXECUTION_METHOD>
```

2. Start it:

```bash
./scripts/miner/neuron/neuron_start.sh --execution <EXECUTION_METHOD>
```

💡 Use `-h` with any script to see available options.

### Uninstallation <a id="neuron-uninstallation"></a>

To uninstall Neuron for the Miner:

1. Stop it:

```bash
./scripts/miner/neuron/neuron_stop.sh --execution <EXECUTION_METHOD>
```

2. Tear it down:

```bash
./scripts/miner/neuron/neuron_teardown.sh --execution <EXECUTION_METHOD>
```

💡 Use `-h` with any script to see available options.

---

Need help or want to chat with other SubVortex users?  
Join us on [Discord](https://discord.gg/bittensor)!
