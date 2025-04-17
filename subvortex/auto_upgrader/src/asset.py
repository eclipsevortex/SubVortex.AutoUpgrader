# The MIT License (MIT)
# Copyright © 2025 Eclipse Vortex

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
import re
import os
import tarfile
import requests

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc


def download_and_unzip(version):
    # Download the version
    asset_archive_path, reason = download_asset(sauc.SV_EXECUTION_ROLE, version)
    if not asset_archive_path:
        return None, reason

    # Unzip the version
    asset_path = unzip_asset(path=asset_archive_path)

    return asset_path, None


def download_asset(role: str, version: str):
    # Ensure the download directory exists
    os.makedirs(sauc.SV_ASSET_DIR, exist_ok=True)

    # Normalized the version
    normalized_version = _normalize_version(version)

    # Build the archive name
    archive_name = f"subvortex_{role}-{normalized_version}.tar.gz"

    # Build the target path
    target_path = os.path.join(sauc.SV_ASSET_DIR, archive_name)
    if os.path.exists(target_path):
        # The asset has lready been downloaded
        return target_path, None

    url = f"https://github.com/eclipsevortex/SubVortex/releases/download/v{version}/{archive_name}"
    btul.logging.info(f"GITHUB URL: {url}")

    # Download the archive
    response = requests.get(url, stream=True)
    if response.status_code != 200:
        return None, response.reason

    # Save the archive on disk
    with open(target_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)

    return target_path, None


def unzip_asset(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Archive not found: {path}")

    # Ensure the directory exists
    os.makedirs(sauc.SV_ASSET_DIR, exist_ok=True)

    # Extract archive
    with tarfile.open(path, "r:gz") as tar:
        # Get top-level directory from the first member
        top_level_dirs = {
            member.name.split("/")[0]
            for member in tar.getmembers()
            if member.name and "/" in member.name
        }

        if not top_level_dirs:
            raise ValueError("Could not determine top-level directory from archive.")

        top_level_dir = sorted(top_level_dirs)[0]
        target_dir = os.path.join(sauc.SV_ASSET_DIR, top_level_dir)

        # If target directory exists, remove it to allow clean overwrite
        if os.path.exists(target_dir):
            return target_dir

        # Extract archive
        tar.extractall(path=sauc.SV_ASSET_DIR)

    return target_dir


def _normalize_version(self, version: str) -> str:
    # Remove leading "v" if present
    version = version.lstrip("v")

    # Replace pre-release suffix
    return re.sub(
        r"-(alpha|beta|rc)\.(\d+)",
        lambda m: {"alpha": "a", "beta": "b", "rc": "rc"}[m.group(1)] + m.group(2),
        version,
    )
