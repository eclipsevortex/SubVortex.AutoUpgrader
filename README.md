<div align="center">

# **SubVortex Auto Upgrader** <!-- omit in toc -->

[![Build & Push](https://github.com/eclipsevortex/SubVortex.AutoUpgrader/actions/workflows/docker-workflow.yml/badge.svg?branch=main)](https://github.com/eclipsevortex/SubVortex.AutoUpgrader/actions/workflows/docker-workflow.yml)
[![Discord Chat](https://img.shields.io/discord/308323056592486420.svg)](https://discord.gg/bittensor)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Effortless Updates for Your Miner & Validator <!-- omit in toc -->

[Github]() [Discord](https://discord.gg/bittensor) • [Network](https://taostats.io/) • [Research](https://bittensor.com/whitepaper)

---

<div>
  <img src="subvortex.png" alt="SubVortex" width="310" height="200">
</div>
<br />
<div style="font-size: 20px">Testnet: 92 • Mainnet: 7</div>

</div>

<br />
<br />

---

<br />

- [Introduction](#introduction)
- [Prerequisites](#prerequisites)
- [How It Works](#how-it-works)
- [Quick Start](#quick-start)
- [Quick Stop](#quick-stop)
- [Quick Upgrade](#quick-upgrade)
- [Installation](#installation)
  - [Auto Upgrader](#installation-auto-upgrader)
  - [Watchtower](#installation-watchtower)
  - [Other](#installation-other)
- [Troubleshooting](#troubleshooting)

<br />
<br />

# 🚀 Introduction <a id="introduction"></a>

Keeping your miner and validator up to date shouldn't be a chore.

The **SubVortex Auto Upgrader** automates upgrades for your SubVortex miner and validator. It ensures that your components are always running the latest version—without manual intervention.

Whether you're managing a single node or an entire fleet, the Auto Upgrader provides a reliable and flexible solution. Choose to run it as a standalone process, a system service, or in a ~~Docker container~~.

Simple to set up. Easy to monitor. Zero stress upgrades.

<br />

# ⚙️ Prerequisites <a id="prerequisites"></a>

> ⚠️ **Architecture Notice**  
> The SubVortex Auto Upgrader currently supports only **x86_64 (amd64)** servers.  
> `arm64` support is not yet available but is a work in progress.  
> We’re actively collaborating with OTF to bring full compatibility as soon as possible.

Before you begin, make sure you clone the Auto Upgrader repository:

```bash
git clone https://github.com/eclipsevortex/SubVortex.AutoUpgrader.git
```

Then, configure your environment:

1. Update the environment variables inside the `subvortex/auto_upgrader/environment/` folder.

   - For miners, edit files matching `env.subvortex.miner.*`
   - For validators, edit files matching `env.subvortex.validator.*`

2. Update the main Auto Upgrader `.env` file at:
   ```
   subvortex/auto_upgrader/.env
   ```

Here's a breakdown of the key variables:

- **SUBVORTEX_PRERELEASE_ENABLED**:  
  Set to `true` if you want the Auto Upgrader to apply both releases and pre-releases. Default is `false`.

- **SUBVORTEX_EXECUTION_METHOD**:  
  Defines how the Auto Upgrader runs. Options are `process`, `service`, or `docker`. Default is `service`.

- **SUBVORTEX_PRERELEASE_TYPE**:  
  Specifies a single prerelease identifier you want to be notified about. Options are `alpha` (**use ONLY in DEVNET**) or `rc` (**use ONLY in TESTNET**). Remove this variable to receive notifications from `latest` (**use in MAINNET**) prerelease types. Default is an empty string, which disables prerelease notifications.

- **SUBVORTEX_EXECUTION_ROLE**:  
  Specifies the type of neuron running on this machine. Options are `miner` and `validator`. Default value is `miner`. The Auto Upgrader uses this to decide how the machine should upgrade.

- **SUBVORTEX_WORKING_DIRECTORY**:  
  Working directory used by the Auto Upgrader. Recommended default: `/var/tmp/subvortex`

- **SUBVORTEX_CHECK_INTERVAL**:  
  Interval in seconds to check if new releases are available. Default 30 seconds.

<br />

# 🔧 How It Works <a id="how-it-works"></a>

When setting up the Auto Upgrader, you can choose from three execution modes: `process`, `service`, or `docker`. The default mode is `service`

🧩 Process & Service Modes

In these modes, the Auto Upgrader checks GitHub every **SUBVORTEX_CHECK_INTERVAL** seconds for new releases. When a new version is available, it:

1. Downloads and unzips the archive for your neuron type (**SUBVORTEX_EXECUTION_ROLE**) into **SUBVORTEX_WORKING_DIRECTORY**
2. Install the new version
3. Updates the symlink to point to the new version
4. Cleans up the previous version

🐳 Docker Mode

Here, the Auto Upgrader also checks GitHub every **SUBVORTEX_CHECK_INTERVAL** seconds. When a new release is found:

1. It pulls the floating tag that matches your desired release type (**SUBVORTEX_PRERELEASE_TYPE**)
2. It starts the updated container

Note: In Docker mode, the Auto Upgrader only runs if the neuron isn’t installed or during rollback to version 2.3.3. Outside of that, upgrade responsibilities are delegated to Watchtower for seamless updates.

<br />

# 🚀 Quick Start <a id="quick-start"></a>

To install the Auto Upgrader in a quick way, you can run

```bash
./scripts/quick_start.sh
```

It will install and start the Auto Upgrader as service which is the default mode.

Use `-h` to see the options

# 🛑 Quick Stop <a id="quick-stop"></a>

To stop the Auto Upgrader in a quick way, you can run

```bash
./scripts/quick_stop.sh
```

It will stop and teardown the Auto Upgrader.

Use `-h` to see the options

<br />

# 🔄 Quick Upgrade <a id="quick-upgrade"></a>

To upgrade the Auto Upgrader when a new release has been deployed, you can run

```bash
./scripts/auto_upgrader/auto_upgrader_upgrade.sh
```

Use `-h` to see the options

<br />

# 🛠️ Installation <a id="installation"></a>

> ⚠️ **Important:** Use this section only if you’re experiencing issues with the quick setup.

## Auto Upgarder <a id="installation-auto-upgrader"></a>

To manage the Auto Upgrader, refer to the [user guide](./scripts/auto_upgrader/README.md)

## Watchtower <a id="installation-watchtower"></a>

To manage the Watchtower, refer to the [user guide](./scripts/watchtower/README.md)

## Other <a id="installation-other"></a>

To manage anything else, refer to the `scripts` folder and check each subdirectory—each one represents a different tool or service required for the Auto Upgrader.

For each of them, the same structure applies:

- **`<tool|service>_setup.sh`** – prepares and configures the tool or service
- **`<tool|service>_start.sh`** – launches the tool or service
- **`<tool|service>_stop.sh`** – stops the tool or service gracefully
- **`<tool|service>_teardown.sh`** – fully removes and cleans up the tool or service

# 🔧 Troubleshooting <a id="troubleshooting"></a>

### 🐛 Issue: Auto Upgrader is mixing the versions or can not upgrade

**Cause:** The work directory may have some existing version causing an issue for the Auto Upgrader  
**Solution:** Clean the working directory

```bash
./scripts/quick_clean.sh
```

The script will clean all the existing version and keep only the last one which can be removed by adding `--remove`

Use option `-h` to see the different options.

Once clean, restart the auto upgrader by running

```bash
./scripts/auto_upgrader/auto_upgrader_restart.sh
```

Use `-h` to see the options
