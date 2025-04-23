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
import base64
import requests
from packaging.version import Version, InvalidVersion

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.asset as saua


class Github:
    def __init__(self, repo_owner="eclipsevortex", repo_name="SubVortex"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.latest_version = None
        self.published_at = None

    def get_version(self) -> str:
        # Build the path to the current component directory
        version_path = os.path.expanduser(f"{sauc.SV_EXECUTION_DIR}/VERSION")

        if not os.path.exists(version_path):
            return None

        with open(version_path, encoding="utf-8") as version_file:
            version_string = version_file.read().strip()
            if re.match(r"^\d+\.\d+\.\d+(?:-(alpha|rc)\.\d+)?$", version_string):
                return version_string
            raise ValueError(f"Invalid version format: {version_string}")

    def get_latest_tag_including_prereleases(self):
        url = (
            f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases"
        )
        headers = (
            {"Authorization": f"token {sauc.SV_GITHUB_TOKEN}"}
            if sauc.SV_GITHUB_TOKEN
            else {}
        )

        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return self.latest_version

        releases = response.json()

        if not releases:
            return self.latest_version, self.published_at

        # Get the first release/pre release
        last_release = next(
            (x for x in releases if self._is_valid_release_or_prerelease(x["tag_name"]))
        )
        if not last_release:
            return self.latest_version, self.published_at

        # Optionally sort by semantic version if needed
        self.published_at = last_release["published_at"]

        # Optionally sort by semantic version if needed
        tag = last_release["tag_name"]
        self.latest_version = tag[1:] if tag.startswith("v") else tag
        return self.latest_version, self.published_at

    def get_latest_version(self) -> str:
        """
        Get the latest release on github
        Return the cached value if any errors
        """
        try:
            url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
            headers = (
                {"Authorization": f"token {sauc.SV_GITHUB_TOKEN}"}
                if sauc.SV_GITHUB_TOKEN
                else {}
            )

            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                return self.latest_version, None

            releases = response.json()
            if not releases:
                return self.latest_version, self.published_at

            # Optionally sort by semantic version if needed
            self.published_at = releases[0]["published_at"]

            tag = releases[0]["tag_name"]
            self.latest_version = tag[1:] if tag.startswith("v") else tag
            return self.latest_version, self.published_at
        except Exception:
            return self.latest_version, self.published_at

    def download_and_unzip(self, version):
        # Normalized the version
        normalized_version = sauv.normalize_version(version=version)

        # Build the archive name
        asset_path = os.path.join(sauc.SV_ASSET_DIR, f"subvortex-{normalized_version}")
        if os.path.exists(asset_path):
            return asset_path, None

        # Download the version
        asset_archive_path, reason = self._download_asset(
            sauc.SV_EXECUTION_ROLE, version
        )

        if not asset_archive_path:
            return None, reason

        # Unzip the version
        asset_path = saua.unzip_asset(path=asset_archive_path)

        # Remove the archive
        os.remove(path=asset_archive_path)

        return asset_path, None

    def get_docker_versions(self, tag: str):
        versions = {}

        # Get all the remote images with their digests
        latest_version, _ = self.get_latest_tag_including_prereleases()

        # If it is the last tag before releasing Auto Upgrader we do nothing
        if latest_version == sauc.DEFAULT_LAST_RELEASE["global"]:
            return versions

        # Download the version
        target_path, _ = self.download_and_unzip(version=latest_version)
        if not target_path:
            raise Exception(
                f"Could not download the assets for the version {latest_version}: {target_path}"
            )

        # Get the subvortex version
        versions["version"] = self._find_version(target_path)

        # Build the component directory
        component_directory = f"{target_path}/subvortex/{sauc.SV_EXECUTION_ROLE}"

        # Get the component version
        component_version = self._find_version(component_directory)

        for service in os.listdir(component_directory):
            service_path = os.path.join(component_directory, service)
            if not os.path.isdir(service_path):
                continue

            service_version = self._find_version(service_path)
            if not service_version:
                # Not a service, it can be share directory for example
                continue

            versions[service] = {
                "version": service_version,
                f"{sauc.SV_EXECUTION_ROLE}.version": component_version,
            }

        return versions

    def download_docker_compose_from_tag(self, version: str, source_version: str):
        if version is None:
            return None, "Version is empty"

        # Normalized the version
        normalized_version = sauv.normalize_version(version=version)

        # Build the archive name
        name = f"subvortex-{normalized_version}"

        # Build the target path
        target_path = os.path.join(sauc.SV_ASSET_DIR, name)

        # Build the file path
        file_path = f"{target_path}/docker-compose.yml"

        # Ensure the download directory exists
        os.makedirs(target_path, exist_ok=True)

        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/contents/subvortex/{sauc.SV_EXECUTION_ROLE}/docker-compose.yml?ref=v{source_version}"
        headers = (
            {"Authorization": f"token {sauc.SV_GITHUB_TOKEN}"}
            if sauc.SV_GITHUB_TOKEN
            else {}
        )

        # Download the file
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return None, response.reason

        data = response.json()
        if data.get("encoding") == "base64":
            content = base64.b64decode(data["content"]).decode("utf-8")

        # Save the archive on disk
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path, None

    def _download_asset(self, role: str, version: str):
        # Ensure the download directory exists
        os.makedirs(sauc.SV_ASSET_DIR, exist_ok=True)

        # Normalized the version
        normalized_version = sauv.normalize_version(version=version)

        # Build the archive name
        archive_name = f"subvortex_{role}-{normalized_version}.tar.gz"

        # Build the target path
        target_path = os.path.join(sauc.SV_ASSET_DIR, archive_name)
        if os.path.exists(target_path):
            # The asset has lready been downloaded
            return target_path, None

        url = f"https://github.com/eclipsevortex/SubVortex/releases/download/v{version}/{archive_name}"
        headers = (
            {"Authorization": f"token {sauc.SV_GITHUB_TOKEN}"}
            if sauc.SV_GITHUB_TOKEN
            else {}
        )

        # Download the archive
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code != 200:
            return None, response.reason

        # Save the archive on disk
        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return target_path, None

    def get_latest_versions2(self):
        latest_version, _ = (
            self.get_latest_tag_including_prereleases()
            if sauc.SV_PRERELEASE_ENABLED
            else self.get_latest_version()
        )

        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/trees/v{latest_version}?recursive=1"
        resp = requests.get(url)
        resp.raise_for_status()
        items = resp.json().get("tree", [])

        return sorted(
            {
                path.split("/")[1]
                for path in [i["path"] for i in items if i["type"] == "tree"]
                if path.startswith("subvortex/") and len(path.split("/")) > 1
            }
        )

    # TODO: make some unit tests to validator the set of logic here!
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

    def _find_version(self, path: str):
        pyproject = os.path.join(path, "pyproject.toml")
        version_py = os.path.join(path, "version.py")
        version_txt = os.path.join(path, "VERSION")

        if os.path.isfile(version_py):
            with open(version_py) as f:
                content = f.read()
                match = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                if match:
                    return match.group(1)
        elif os.path.isfile(version_txt):
            with open(version_txt) as f:
                return f.read().strip()
        elif os.path.isfile(pyproject):
            with open(pyproject) as f:
                for line in f:
                    match = re.match(r'^version\s*=\s*"([^"]+)"', line)
                    if match:
                        return match.group(1)
        else:
            return None

    def _get_release_tree_sha(self, tag):
        components = []

        url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/trees/{tag}?recursive=1"

        resp = requests.get(url)
        if resp.status_code != 200:
            return components

        base_path = f"subvortex/{sauc.SV_EXECUTION_ROLE}"

        seen = set()
        for item in resp.json()["tree"]:
            if item["type"] == "tree" and item["path"].startswith(base_path + "/"):
                parts = item["path"].split("/")
                if len(parts) == 3:
                    component_name = parts[2]
                    if component_name not in seen:
                        components.append(component_name)
                        seen.add(component_name)

        return components

    def get_components(self):
        components = []

        # Get the latest version
        latest_version, _ = (
            self.get_latest_tag_including_prereleases()
            if sauc.SV_PRERELEASE_ENABLED
            else self.get_latest_version()
        )

        # If it is the last tag before releasing Auto Upgrader we do nothing
        if latest_version == sauc.DEFAULT_LAST_RELEASE["global"]:
            return components

        # Download the version
        target_path, _ = self.download_and_unzip(version=latest_version)
        if not target_path:
            raise Exception(
                f"Could not download the assets for the version {latest_version}: {target_path}"
            )
        btul.logging.debug(
            f"Version {latest_version} has been downloaded and unzipped",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Build the component directory
        component_directory = f"{target_path}/subvortex/{sauc.SV_EXECUTION_ROLE}"

        for service in os.listdir(component_directory):
            service_path = os.path.join(component_directory, service)
            if not os.path.isdir(service_path):
                continue

            if not self._find_version(service_path):
                continue

            components.append(service)

        return components

        # # Build the tag version of it
        # tag = f"v{latest_version}"

        # # Get the sha for the subvortex directory
        # components = self._get_release_tree_sha(tag)

        # return components
        # if not sha:
        #     return versions

        # Build the url to get the tree of subvortex
        # url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/git/trees/{sha}"

        # resp = requests.get(url)
        # if resp.status_code != 200:
        #     return versions

        # data = resp.json()
        # print(data)

        # components = []

        # return components

        # components = []
        # for item in resp.json()["tree"]:
        #     if item["type"] != "tree":
        #         continue

        #     sub_url = item["url"]
        #     sub_resp = requests.get(sub_url)
        #     if sub_resp.status_code != 200:
        #         continue

        #     # files = {
        #     #     f["path"]: f["url"]
        #     #     for f in sub_resp.json()["tree"]
        #     #     if f["type"] == "blob"
        #     # }

        #     # version = None
        #     # if "version.py" in files:
        #     #     content = requests.get(files["version.py"]).json()["content"]
        #     #     content_decoded = base64.b64decode(content).decode()
        #     #     match = re.search(
        #     #         r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', content_decoded
        #     #     )
        #     #     if match:
        #     #         version = match.group(1)
        #     # elif "VERSION" in files:
        #     #     content = requests.get(files["VERSION"]).json()["content"]
        #     #     version = base64.b64decode(content).decode().strip()
        #     # elif "pyproject.toml" in files:
        #     #     content = requests.get(files["pyproject.toml"]).json()["content"]
        #     #     content_decoded = base64.b64decode(content).decode()
        #     #     for line in content_decoded.splitlines():
        #     #         match = re.match(r'^version\s*=\s*"([^"]+)"', line)
        #     #         if match:
        #     #             version = match.group(1)
        #     #             break

        #     # if not version:
        #     #     continue

        #     # versions[item] = {"version": version, "": None}

        # print(components)
        # return components
