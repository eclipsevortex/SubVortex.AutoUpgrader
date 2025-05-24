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
- [Available Components](#available-components)
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

# 📦 Available Components <a id="available-components"></a>

Valid <component> values used across scripts and logs include:

- **redis** – Handles key-value data storage for the miner.
- **metagraph** – Maintains a local snapshot of the network graph.
- **neuron** – Executes the miner logic and interacts with the network.

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

### Data Dumps & Migrations <a id="dumpa-and-migrations"></a>

In addition to start/stop operations, Redis includes scripts to **create and restore a dump**, as well as to **rollout or rollback a migration** between versions or configurations.

- Dump Redis data:

  ```bash
  python3 ./scripts/redis/redis_dump.py --neuron miner --run_type create
  ```

- Restore Redis data:

  ```bash
  python3 ./scripts/redis/redis_dump.py --neuron miner --run_type restore
  ```

- Run a Redis migration (rollout):

  ```bash
  python3 ./scripts/redis/redis_migration.py --neuron miner --direction rollout
  ```

- Rollback a Redis migration:
  ```bash
  python3 ./scripts/redis/redis_migration.py --neuron miner --direction rollback
  ```

> ⚠️ These scripts must be used **at the correct point in your setup or upgrade process** to avoid **data loss** or **inconsistent state**. Always ensure other dependent components (like Metagraph and Neuron) are **stopped or aligned** when performing restore or migration steps.

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

### Consistency Check <a id="metagraph-consistency"></a>

You can run a consistency check between the Metagraph and Redis storage to ensure synchronization:

```bash
python3 /root/subvortex/subvortex/miner/metagraph/src/checker.py
```

This script will compare the current state of neurons in Redis with the active entries in the Metagraph and report any discrepancies (e.g., missing or outdated entries).

💡 Run this periodically or after major updates to verify data integrity.

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

### ✅ Connectivity Checklist <a id="neuron-connectivity-check"></a>

After installing and starting the Neuron, it's essential to verify that your Miner is **externally reachable**. Validators need to connect to both your **Miner** and your **Subtensor** node to send challenges and record results.

#### 🔌 1. Check Miner Port Accessibility

Verify that port `8091` (used for challenge handling) is accessible from the public internet.

From a **remote machine** (not the miner host), run:

```bash
nc -zv <YOUR_MINER_PUBLIC_IP> 8091
```

✅ Expected output:

```
Connection to <YOUR_MINER_PUBLIC_IP> port 8091 [tcp/*] succeeded!
```

> ⚠️ If this fails, check for:
>
> - Blocked ports in `ufw`, `iptables`, or cloud security groups
> - NAT/router not forwarding the port correctly
> - Misconfigured HAProxy or service not running

---

#### 🔌 2. Check Subtensor Node WebSocket Accessibility

Make sure your Subtensor node exposes a WebSocket at port `9944`.

Run this from an external machine:

```bash
wscat -c ws://<YOUR_SUBTENSOR_PUBLIC_IP>:9944
```

✅ Expected output:

```
Connected (press CTRL+C to quit)
>
```

> 📦 You can install `wscat` via:
>
> ```bash
> npm install -g wscat
> ```

---

#### 📡 3. Confirm the Neuron is Receiving Challenges

After startup, check your logs to confirm that scores are reaching your neuron:

- `service` (systemd)

```bash
tail -f /var/log/subvortex-miner/subvortex-miner-neuron.log | grep Score
```

- `process` (PM2)

```bash
pm2 log subvortex-miner-neuron | grep Score
```

- `container` (Docker)

```bash
docker logs subvortex-miner-neuron -f | grep Score
```

Look for lines like:

```
247|subvortex-miner-neuron  | 2025-05-24 21:36:12.185 |       INFO       | [20] Availability score 1.0
247|subvortex-miner-neuron  | 2025-05-24 21:36:12.185 |       INFO       | [20] Latency score 1.0
247|subvortex-miner-neuron  | 2025-05-24 21:36:12.185 |       INFO       | [20] Reliability score 0.8558733500690666
247|subvortex-miner-neuron  | 2025-05-24 21:36:12.185 |       INFO       | [20] Distribution score 1.0
247|subvortex-miner-neuron  | 2025-05-24 21:36:12.185 |     SUCCESS      | [20] Score 0.9711746700138133
```

---

If you're not receiving challenges:

- ✅ Double-check that Metagraph and Redis are correctly synced.
- ✅ Confirm your neuron is registered and emitting correctly on-chain.
- ✅ Verify your challenge port and WebSocket endpoint are **publicly reachable**.
