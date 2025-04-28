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
import os
import re
import time
import shutil
import tarfile
import requests
import subprocess
from packaging.version import Version, InvalidVersion

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.exception as saue
import subvortex.auto_upgrader.src.utils as sauu


class Github:
    def __init__(self, repo_owner="eclipsevortex", repo_name="SubVortex"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name

    def get_local_version(self):
        version = None

        if sauc.SV_EXECUTION_METHOD == "container":
            version = self._get_local_container_version()
        else:
            version = self._get_local_version()

        return version

    def get_latest_version(self):
        version = None
        if sauc.SV_EXECUTION_METHOD == "container":
            version = self._get_latest_container_version()
        else:
            version = self._get_latest_version()

        return version

    def get_latest_container_versions(self, name: str):
        # Get the default versions
        default_versions = self._get_default_versions(name=name)

        # Get the service versions
        versions = self.latest_versions.get(name, default_versions)

        return versions

    def get_local_container_versions(self, name: str):
        # Get the default versions
        default_versions = self._get_default_versions(name=name)

        # Get the service versions
        versions = self.local_versions.get(name, default_versions)

        return versions

    def download_and_unzip_assets(self, version: str, role: str):
        # Download the version
        archive_path = self._download_assets(role=role, version=version)
        if not archive_path:
            btul.logging.warning(
                f"No assets available for version {version}", prefix=sauc.SV_LOGGER_NAME
            )
            return None

        # Unzip the version
        asset_path = self._unzip_assets(archive_path=archive_path)

        # Remove the archive
        if os.path.isfile(archive_path):
            # Remove the archive
            os.remove(archive_path)

            # Log it
            archive_name = os.path.basename(archive_path)
            btul.logging.trace(
                f"Archive {archive_name} removed", prefix=sauc.SV_LOGGER_NAME
            )

        return asset_path

    def _is_valid_release_or_prerelease(self, tag_name: str) -> bool:
        try:
            version = Version(tag_name)
        except InvalidVersion:
            return False  # Reject malformed versions safely

        # Final release has no prerelease part
        if version.is_prerelease is False:
            return True

        # Accept all prereleases
        if "all" == sauc.SV_PRERELEASE_TYPE:
            return True

        prerelease_types = self._get_prerelease_types()

        # Check allowed prerelease types like "alpha", "rc", etc.
        prerelease = version.pre  # Tuple like ("rc", 1) or ("alpha", 2)
        if prerelease:
            pre_type = prerelease[0].lower()
            return pre_type in prerelease_types

        return False

    def _get_prerelease_types(self):
        if sauc.SV_PRERELEASE_TYPE == "alpha":
            return ["a", "rc"]

        if sauc.SV_PRERELEASE_TYPE == "rc":
            return ["rc"]

        return []

    def _download_assets(self, version: str, role: str):
        # Ensure the working directory exists
        os.makedirs(sauc.SV_ASSET_DIR, exist_ok=True)

        # Normalized the version
        normalized_version = sauv.normalize_version(version)

        # Build the archive name
        archive_name = f"subvortex_{role}-{normalized_version}.tar.gz"

        # Build the target path
        target_path = os.path.join(sauc.SV_ASSET_DIR, archive_name)
        if os.path.exists(target_path):
            # The asset has lready been downloaded
            return target_path

        url = f"https://github.com/eclipsevortex/SubVortex/releases/download/v{version}/{archive_name}"

        # Download the archive
        response = requests.get(url, stream=True)
        if response.status_code == 404:
            return None

        response.raise_for_status()

        # Save the archive on disk
        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

            f.flush()
            os.fsync(f.fileno())

        # Check with retry the file has been downloaded on the file system
        for _ in range(5):  # Try for ~500ms
            if os.path.exists(target_path):
                break
            time.sleep(0.5)
        else:
            raise saue.MissingFileError(
                file_path=target_path,
                message=f"Downloaded archive {target_path} does not exist after writing.",
            )

        btul.logging.trace(
            f"Archive {archive_name} downloaded into {target_path}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        return target_path

    def _unzip_assets(self, archive_path: str):
        if not os.path.isfile(archive_path):
            raise saue.MissingFileError(file_path=archive_path)

        # Ensure the directory exists
        os.makedirs(sauc.SV_ASSET_DIR, exist_ok=True)

        # Extract archive
        with tarfile.open(archive_path, "r:gz") as tar:
            # Get top-level directory from the first member
            top_level_dirs = {
                member.name.split("/")[0]
                for member in tar.getmembers()
                if member.name and "/" in member.name
            }

            if not top_level_dirs:
                raise ValueError(
                    "Could not determine top-level directory from archive."
                )

            top_level_dir = sorted(top_level_dirs)[0]

            # Build the target directory
            target_dir = os.path.join(sauc.SV_ASSET_DIR, top_level_dir)

            # If target directory exists, remove it to allow clean overwrite
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)

            # Extract archive
            tar.extractall(path=sauc.SV_ASSET_DIR)

        btul.logging.trace(
            f"Archive {archive_path} unzipped into {target_dir}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        if not os.path.exists(target_dir):
            raise saue.MissingDirectoryError(directory_path=target_dir)

        return target_dir

    def _get_latest_version(self):
        # Build the url to get the list of releases
        url = (
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases"
        )

        # Build the headers
        headers = (
            {"Authorization": f"token {sauc.SV_GITHUB_TOKEN}"}
            if sauc.SV_GITHUB_TOKEN
            else {}
        )

        # Send the request
        response = requests.get(url, headers=headers)

        # Check the the releases have not be found
        if response.status_code == 404:
            raise saue.ReleaseNotFoundError(url=url)

        # Raise any failed response
        response.raise_for_status()

        # Deseralized the resposne
        releases = response.json()

        if not releases:
            raise saue.NoReleaseAvailableError()

        # Sort releases by published_at descending (most recent first)
        releases = sorted(
            releases, key=lambda r: r.get("published_at", ""), reverse=True
        )

        # Get the first release/pre release
        last_release = next(
            (x for x in releases if self._is_valid_release_or_prerelease(x["tag_name"]))
        )

        # Optionally sort by semantic version if needed
        tag = last_release["tag_name"]
        version = tag[1:] if tag.startswith("v") else tag
        return version

    def _get_latest_container_version(self):
        """
        Get the latest container version from GitHub registry,
        inspecting the labels of the remote images.
        """
        # Build the URL to list packages in GitHub registry
        url = f"https://api.github.com/users/{self.repo_owner}/packages?package_type=container"

        # Build the header to use the GitHub token if available
        headers = (
            {"Authorization": f"token {sauc.SV_GITHUB_TOKEN}"}
            if sauc.SV_GITHUB_TOKEN
            else {}
        )

        # Send the request
        response = requests.get(url, headers=headers)

        if response.status_code == 404:
            raise saue.PackageNotFoundError(url=url)

        response.raise_for_status()

        # Deserialize the response
        packages = response.json()

        # Filter to only matching packages
        packages = [
            package
            for package in packages
            if package["name"].startswith(f"subvortex-{sauc.SV_EXECUTION_ROLE}")
        ]

        versions = {}
        for package in packages:
            package_name = package["name"]
            version_url = f"https://api.github.com/users/{self.repo_owner}/packages/container/{package_name}/versions"

            version_response = requests.get(version_url, headers=headers)
            if version_response.status_code != 200:
                continue

            package_versions = version_response.json()

            for v in package_versions:
                tags = v.get("metadata", {}).get("container", {}).get("tags", [])

                for tag in tags:
                    if tag in {"latest", "stable", "dev"}:
                        continue  # 🚫 Skip floating tags

                    # Build full image name
                    full_image = f"ghcr.io/{self.repo_owner}/{package_name}:{tag}"

                    # Pull the image quietly
                    pull_result = subprocess.run(
                        [
                            "docker",
                            "pull",
                            "--quiet",
                            full_image,
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    if pull_result.returncode != 0:
                        continue

                    # Inspect labels
                    inspect_result = subprocess.run(
                        [
                            "docker",
                            "inspect",
                            "--format",
                            "{{ json .Config.Labels }}",
                            full_image,
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                    if inspect_result.returncode != 0 or not inspect_result.stdout:
                        continue

                    try:
                        labels = eval(inspect_result.stdout)
                    except Exception:
                        continue

                    if not labels:
                        continue

                    # Collect service-specific versions
                    service_versions = {}
                    for key, value in labels.items():
                        if value:
                            service_versions[key] = value

                    # Extract service name from package
                    service_name = package_name.replace(
                        f"subvortex-{sauc.SV_EXECUTION_ROLE}-", ""
                    )

                    if service_versions:
                        versions[service_name] = service_versions

        # Determine the global version
        global_versions = list(
            {v.get("version") for v in versions.values() if v.get("version")}
        )

        versions["version"] = str(max(global_versions)) if global_versions else None

        # Store the versions
        self.latest_versions = versions
        btul.logging.trace(
            f"Latest container versions (from GitHub registry): {self.latest_versions}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        return versions.get("version")

    def _get_local_version(self):
        versions = []

        # Check if base_dir exists
        if not os.path.isdir(sauc.SV_ASSET_DIR):
            btul.logging.warning(
                f"Directory {sauc.SV_ASSET_DIR} does not exist",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return None

        # List all directories
        for entry in os.listdir(sauc.SV_ASSET_DIR):
            entry_path = os.path.join(sauc.SV_ASSET_DIR, entry)
            if not os.path.isdir(entry_path):
                continue

            # Match directory name pattern
            match = re.match(r"subvortex-(\d+\.\d+\.\d+(?:[ab]|rc)?\d*)", entry)
            if not match:
                continue

            version_str = match.group(1)

            # Try to parse version
            try:
                parsed_version = Version(version_str)
                versions.append(parsed_version)
            except InvalidVersion:
                continue

        # Check if there are versions or not
        if not versions:
            return None

        # Get the latest verison locally
        latest_version = str(max(versions))

        # Denormalize the version
        latest_version_denormalized = sauv.denormalize_version(latest_version)

        return latest_version_denormalized

    def _get_local_container_version(self):
        """
        Get the latest local version for container-based execution,
        inspecting the labels of the locally pulled images.
        """
        versions = {}

        try:
            # Get the floating tag (like dev/stable/latest)
            ftag = sauu.get_tag()

            # List all local images with their tags
            result = subprocess.run(
                ["docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            images = result.stdout.strip().split("\n")

            # Filter matching images
            for image in images:
                if ":" not in image:
                    continue

                repo, tag = image.rsplit(":", 1)

                # Build the prefix for GitHub registry
                prefix = (
                    f"ghcr.io/{self.repo_owner}/subvortex-{sauc.SV_EXECUTION_ROLE}-"
                )

                if not repo.startswith(prefix) or tag != ftag:
                    continue

                # Inspect labels of the local image
                container_versions = self._get_local_container_versions(
                    repo_name=repo, tag=ftag
                )

                # Extract service name from the repo name
                service_name = repo.replace(prefix, "")

                versions[service_name] = container_versions

        except subprocess.CalledProcessError as e:
            btul.logging.warning(
                f"Failed to list docker images: {e}", prefix=sauc.SV_LOGGER_NAME
            )

        # Determine the global "version"
        global_versions = list(
            {v.get("version") for v in versions.values() if v.get("version")}
        )

        versions["version"] = str(max(global_versions)) if global_versions else None

        # Store the versions
        self.local_versions = versions
        btul.logging.trace(
            f"Local versions: {self.local_versions}", prefix=sauc.SV_LOGGER_NAME
        )

        return versions["version"]

    def _get_local_container_versions(self, repo_name: str, tag: str) -> dict:
        """
        Inspect a local docker image and extract version labels.

        Args:
            repo_name (str): Full docker repository name (ex: ghcr.io/eclipsevortex/subvortex-miner-neuron)
            tag (str): Floating tag (ex: latest/stable/dev)

        Returns:
            dict: Dictionary of label key-values (like {"version": "1.2.3", "neuron.version": "1.2.3"})
        """
        try:
            inspect_cmd = [
                "docker",
                "inspect",
                "--format",
                "{{ json .Config.Labels }}",
                f"{repo_name}:{tag}",
            ]
            result = subprocess.run(
                inspect_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            labels_raw = result.stdout.strip()

            if not labels_raw or labels_raw == "null":
                return {}

            import json

            labels = json.loads(labels_raw)

            if not isinstance(labels, dict):
                return {}

            return labels

        except subprocess.CalledProcessError as e:
            btul.logging.warning(
                f"Failed to inspect image {repo_name}:{tag} - {e}",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return {}
        except json.JSONDecodeError as e:
            btul.logging.warning(
                f"Failed to parse JSON labels for image {repo_name}:{tag} - {e}",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return {}

    def _get_default_versions(self, name: str):
        component = sauc.SV_EXECUTION_ROLE
        service = f"{component}.{name}"
        return {
            "version": sauc.DEFAULT_LAST_RELEASE.get("global"),
            f"{component}.version": sauc.DEFAULT_LAST_RELEASE.get(component),
            service: sauc.DEFAULT_LAST_RELEASE.get(service),
        }
