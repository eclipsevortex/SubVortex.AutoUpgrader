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
- [Log Locations](#log-locations)
- [Quick Setup](#quick-setup)
- [Quick Start](#quick-start)
- [Quick Stop](#quick-stop)
- [Quick Upgrade](#quick-upgrade)
- [Quick Restart](#quick-restart)
- [Quick Clean](#quick-clean)
- [Installation](#installation)
  - [Auto Upgrader](#installation-auto-upgrader)
  - [Miner](#installation-miner)
  - [Validator](#installation-validator)
  - [Other](#installation-other)
- [Tools](#tools)
  - [Wandb](#tool-wandb)
- [Good to Know](#good-to-know)
- [Troubleshooting](#troubleshooting)
- [License](#license)

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

1. Update the main Auto Upgrader `.env` file at:
   ```
   subvortex/auto_upgrader/.env
   ```

Here's a breakdown of the key variables:

- **SUBVORTEX_GITHUB_TOKEN**: GitHub token used to pull Docker images and download release assets from the GitHub registry. It is highly recommended to create a Personal Access Token (PAT) from your GitHub account for this purpose. See [Personal Access Token](#ipersonal-access-token) for instructions.

- **SUBVORTEX_PRERELEASE_ENABLED**:  
  Set to `true` if you want the Auto Upgrader to apply both releases and pre-releases. Default is `false`.

- **SUBVORTEX_EXECUTION_METHOD**:  
  Defines how the neuron and its components will be installed by the Auto Upgrader. Options are `process`, `service`, or `container`. Default is `service`.

- **SUBVORTEX_PRERELEASE_TYPE**:  
  Specifies a single prerelease identifier you want to be notified about. Options are `alpha` (**use ONLY in DEVNET**) or `rc` (**use ONLY in TESTNET**). Remove this variable to receive notifications from `latest` (**use in MAINNET**) prerelease types. Default is an empty string, which disables prerelease notifications.

- **SUBVORTEX_EXECUTION_ROLE**:  
  Specifies the type of neuron running on this machine. Options are `miner` and `validator`. Default value is `miner`. The Auto Upgrader uses this to decide how the machine should upgrade.

- **SUBVORTEX_WORKING_DIRECTORY**:  
  Working directory used by the Auto Upgrader. Recommended default: `/var/tmp/subvortex`

- **SUBVORTEX_CHECK_INTERVAL**:  
  Interval in seconds to check if new releases are available. Default 30 seconds.

- **SUBVORTEX_REDIS_HOST**:
  Host of the redis instance. Provide it ONLY if you are a validator. Default `localhost`

- **SUBVORTEX_REDIS_PORT**:
  Port of the redis instance. Provide it ONLY if you are a validator. Default `6379`.

- **SUBVORTEX_REDIS_INDEX**:
  Index of the redis database. Provide it ONLY if you are a validator. Default `0`

- **SUBVORTEX_REDIS_PASSWORD**:
  Password of the redis database. Provide it ONLY if you are a validator.

2. Update the environment variables inside the `subvortex/auto_upgrader/environment` folder.

   - For miners, edit files matching `env.subvortex.miner.*`
   - For validators, edit files matching `env.subvortex.validator.*`

3. Update the templates inside the `subvortex/auto_upgrader/template` folder. Recommended to keep as it is.

<br />

# 🔧 How It Works <a id="how-it-works"></a>

When setting up the Auto Upgrader, you can choose from three execution modes: `process`, `service`, or `container`. The default mode is `service`

🧩 Process & Service Modes

In these modes, the Auto Upgrader checks GitHub every **SUBVORTEX_CHECK_INTERVAL** seconds for new releases. When a new version is available, it:

1. Downloads and unzips the archive for your neuron type (**SUBVORTEX_EXECUTION_ROLE**) into **SUBVORTEX_WORKING_DIRECTORY**
2. Install the new version
3. Updates the symlink to point to the new version
4. Cleans up the previous version

➡️ The execution directory for SubVortex will now be located under `$HOME/subvortex`, with each version in its own subdirectory and a symlink pointing to the current version.
You no longer need to clone the SubVortex repository manually — and can safely remove any old local copies you previously cloned.

🐳 Docker Mode

Here, the Auto Upgrader also checks GitHub every **SUBVORTEX_CHECK_INTERVAL** seconds. When a new release is found:

1. It pulls the floating tag that matches your desired release type (**SUBVORTEX_PRERELEASE_TYPE**)
2. It starts the updated container

Note: In Docker mode, the Auto Upgrader only runs if the neuron isn’t installed or during rollback to version 2.3.3. Outside of that, upgrade responsibilities are delegated to Watchtower for seamless updates.

<br />

# 📁 Log Locations <a id="log-locations"></a>

You can monitor the Auto Upgrader using logs. Their location depends on the `SUBVORTEX_EXECUTION_METHOD`:

- **`service`**: logs are in `/var/log/subvortex-auto-upgrader/` and accessible via `tail -f <SERVICE_PATH>` e.v `tail -f /var/log/subvortex-auto-upgrader/subvortex-miner-neuron.log`
- **`process`**: logs are in `/root/.pm2/logs/` and accessible via `pm2 log <PROCESS_NAME>` e.g `pm2 log subvortex-miner-neuron`
- **`container`**: use `docker logs subvortex-auto-upgrader` (add `-f` to follow in real time) and accessible via `docker logs <CONTAINER_NAME>` e.g `docker logs subortex-miner-neuron`

<br />

# 🔑 Personal Access Token <a id="personal-access-token"></a>

To allow the system to pull Docker images and release assets from GitHub, you need to generate a GitHub Personal Access Token (PAT).

1. Go to [GitHub Settings → Developer Settings → Personal Access Tokens](https://github.com/settings/tokens).
2. Choose **Fine-grained tokens** (recommended) or **Classic** (still supported).
3. Create a new token with at least the following permissions:

   - **read:packages**
   - **read:org** (required if the repository is under an organization)
   - **public_repo** (sometimes required for public repositories)

4. Set the token to **read-only access** where possible.
5. Copy and save the token securely.

Then, copy that token as value of `SUBVORTEX_GITHUB_TOKEN` in the main Auto Upgrader `.env` file.

<br />

# 🚀 Quick Setup <a id="quick-setup"></a>

⚠️ Note: This step is usually not required. The Auto Upgrader automatically handles setup for you.
Use this only if you encounter issues or need to manually prepare a specific version.

To setup the Auto Upgrader in a quick way, you can run

```bash
./scripts/quick_setup.sh --neuron validator --release v3.0.1
```

It will download and unzip the neuron's assets of the SubVortex for the requested version.

Use `-h` to see the options

<br />

# 🚀 Quick Start <a id="quick-start"></a>

To install the Auto Upgrader in a quick way, you can run

```bash
./scripts/quick_start.sh --execution <EXECUTION_METHOD>
```

It will install and start the Auto Upgrader using the `EXECUTION_METHOD`, which defaults to `service`.

Use `-h` to see the options

<br />

# 🛑 Quick Stop <a id="quick-stop"></a>

To stop the Auto Upgrader in a quick way, you can run

```bash
./scripts/quick_stop.sh --execution <EXECUTION_METHOD>
```

It will stop and teardown the Auto Upgrader using the `EXECUTION_METHOD`, which defaults to `service`.

Use `-h` to see the options

<br />

# 🔄 Quick Upgrade <a id="quick-upgrade"></a>

To upgrade the Auto Upgrader when a new release has been deployed, you can run

```bash
./scripts/auto_upgrader/auto_upgrader_upgrade.sh --execution <EXECUTION_METHOD>
```

It will upgrade and restart the Auto Upgrader using the `EXECUTION_METHOD`, which defaults to `service`.

Use `-h` to see the options

<br />

# 🔄 Quick Restart <a id="quick-restart"></a>

To stop/start the Auto Upgrader workspace and/or dumps in a quick way. Optionally to remove the current version.

```bash
./scripts/quick_restart.sh --execution <EXECUTION_METHOD>
```

It will restart the Auto Upgrader using the `EXECUTION_METHOD`, which defaults to `service`.

Use `-h` to see the options

<br />

# 🧹 Quick Clean <a id="quick-clean"></a>

To clean the Auto Upgrader workspace and/or dumps. Optionally to remove the current version.

```bash
./scripts/quick_clean.sh
```

Use `-h` to see the options

<br />

# 🛠️ Installation <a id="installation"></a>

> ⚠️ **Important:** Use this section only if you’re experiencing issues with the quick setup.

## Auto Upgarder <a id="installation-auto-upgrader"></a>

To manage the Auto Upgrader, refer to the [user guide](./scripts/auto_upgrader/README.md)

## Miner <a id="installation-miner"></a>

> ⚠️ **Important:** It is highly recommended to install the Miner using the Auto Upgrader!

To manage the Miner manually and/or find out for the logs, refer to the [user guide](./scripts/miner/README.md)

## Validator <a id="installation-validator"></a>

> ⚠️ **Important:** It is highly recommended to install the Validator using the Auto Upgrader!

To manage the Validator manually and/or find out for the logs, refer to the [user guide](./scripts/validator/README.md)

## Other <a id="installation-other"></a>

To manage anything else, refer to the `scripts` folder and check each subdirectory—each one represents a different tool or service required for the Auto Upgrader.

For each of them, the same structure applies:

- **`<tool|service>_setup.sh`** – prepares and configures the tool or service
- **`<tool|service>_start.sh`** – launches the tool or service
- **`<tool|service>_stop.sh`** – stops the tool or service gracefully
- **`<tool|service>_teardown.sh`** – fully removes and cleans up the tool or service

<br />

# Tools <a id="tools"></a>

## Wandb <a id="tool-wandb"></a>

To login to wandb, run

```bash
./scripts/wandb/wandb_login.sh --api-key <WANDB_API_KEY>
```

To force relogin to wandb, run

```bash
./scripts/wandb/wandb_login.sh --api-key <WANDB_API_KEY> --relogin
```

# 💡 Good to Know <a id="good-to-know"></a>

After installing a version through the Auto Upgrader, you can directly run various management scripts for the Miner and/or Validator.
For detailed usage and available commands, refer to the [SubVortex](https://github.com/eclipsevortex/SubVortex) documentation

<br />

# 🔧 Troubleshooting <a id="troubleshooting"></a>

## 🐛 Issue: Auto Upgrader is mixing the versions or can not upgrade

**Cause:** The work directory may have some existing version causing an issue for the Auto Upgrader
**Solution:** Clean the working directory

```bash
./scripts/quick_clean.sh
```

The script will clean the Auto Upgrader workspace and/or dumps. Optionally removes the current version.

Use option `-h` to see the different options.

Once cleaned, restart the auto upgrader by running

```bash
./scripts/quick_restart.sh
```

Use `-h` to see the options

## 🐛 Issue: Environment variable changes aren't applied after upgrade/downgrade in miner container

**Cause:** Watchtower does not refresh the var env when upgrading/downgrading
**Solution:** Force to recreate (not rebuild) the image

```bash
./scripts/miner/quick_restart.sh
```

The script will restart all the miner's components in a way that environment variable will be reloaded

## 🐛 Issue: Environment variable changes aren't applied after upgrade/downgrade in validator container

**Cause:** Watchtower does not refresh the var env when upgrading/downgrading
**Solution:** Force to recreate (not rebuild) the image

```bash
./scripts/validator/quick_restart.sh
```

The script will restart all the validator's components in a way that environment variable will be reloaded

## 🐛 Issue: Working directory is not synched and I can not install any new version

**Cause:** This is likely caused by a manual change or a bug that needs fixing.
**Solution:** Clean your working directory entirely with the following command:

```bash
./scripts/quick_clean.sh --remove
```

Then, manually remove any miner and/or validator services based on the execution type you previously selected:

- service
- process
- container

To understand how each service is cleaned, set up, started, or stopped, refer to the relevant deployment folder for each neuron:

```bash
subvortex/
  └── [miner|validator]/
        └── [neuron|redis]/
              └── deployment/
                    └── [process|service|docker]
```

📘 You can find more details and actions in the [SubVortex Repo](https://github.com/eclipsevortex/SubVortex.git).

<br />

# 🪪 License

This repository is licensed under the MIT License.

```text
# The MIT License (MIT)
# Copyright © 2024 Eclipse Vortex

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
```
