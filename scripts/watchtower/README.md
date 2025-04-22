[← Back to Main README](../../README.md)

# 🛠️ Watchtower Setup Guide

This guide explains how to **install** and **uninstall** Watchtower, the tool responsible for keeping your services up to date.

> ⚠️ **Important:** Only use Watchtower manually if you're facing issues that prevent the Auto Upgrader from running properly.  
> Under normal conditions, the **Auto Upgrader will handle upgrades automatically**, so there's no need to run this yourself.

<br />

## 📑 Contents

- [Installation](#installation)
- [Uninstallation](#uninstallation)

<br />
<br />

## 🛠️ Installation <a id="installation"></a>

To start Watchtower, run:

```bash
./scripts/watchtower/watchtower_start.sh
```

<br />

## 🧹 Uninstallation <a id="uninstallation"></a>

To stop Watchtower, run:

```bash
./scripts/watchtower/watchtower_stop.sh
```

Then to completely remove it:

```bash
./scripts/watchtower/watchtower_teardown.sh
```
