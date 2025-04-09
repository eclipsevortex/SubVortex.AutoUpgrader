import os
import re
import requests
import subprocess
from os import path

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc

here = path.abspath(path.dirname(__file__))


class Github:
    def __init__(self, repo_owner="eclipsevortex", repo_name="SubVortex"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.latest_version = None

    def get_version(self) -> str:
        version_path = os.path.join(here, "../../../VERSION")

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
        response.raise_for_status()

        releases = response.json()

        if not releases:
            return None  # No releases yet

        # Optionally sort by semantic version if needed
        return releases[0]["tag_name"]

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
            print(response)
            if response.status_code != 200:
                return self.latest_version

            latest_version = response.json()["tag_name"]
            self.latest_version = latest_version[1:]
            return self.latest_version
        except Exception:
            return self.latest_version

    def get_branch(self, branch_name="main"):
        """
        Get the expected branch
        """
        # Stash if there is any local changes just in case
        subprocess.run(["git", "stash"], check=True)

        # Checkout branch
        subprocess.run(["git", "checkout", "-B", branch_name], check=True)

        # Set tracking
        subprocess.run(
            ["git", "branch", f"--set-upstream-to=origin/{branch_name}", branch_name],
            check=True,
        )

        # Pull branch
        subprocess.run(["git", "reset", "--hard", f"origin/{branch_name}"], check=True)

        # Pull the branch
        subprocess.run(["git", "pull"], check=True)

        # Stash if there is any local changes just in case
        subprocess.run(["git", "stash"], check=True)

        btul.logging.info(
            f"Successfully pulled source code for branch '{branch_name}'."
        )

    def get_tag(self, tag):
        """
        Get the expected tag
        """
        # Stash if there is any local changes just in case
        subprocess.run(["git", "stash"], check=True)

        # Fetch tags
        subprocess.run(["git", "fetch", "--tags", "--force"], check=True)
        btul.logging.info(f"Fetch tags.")

        # Checkout tags
        subprocess.run(["git", "checkout", f"tags/{tag}"], check=True)
        btul.logging.info(f"Successfully pulled source code for tag '{tag}'.")

    def download_neuron(self, role: str, version: str):
        # Ensure the download directory exists
        os.makedirs(sauc.SV_ASSET_DIR, exist_ok=True)

        # Normalized the version
        normalized_version = self._normalize_version(version)

        archive_name = f"subvortex_{role}-{normalized_version}.tar.gz"
        url = f"https://github.com/eclipsevortex/SubVortex/releases/download/{version}/{archive_name}"
        target_path = os.path.join(sauc.SV_ASSET_DIR, archive_name)

        # Download the archive
        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Save the archive on disk
        with open(target_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        return target_path

    def _normalize_version(self, version: str) -> str:
        # Remove leading "v" if present
        version = version.lstrip("v")

        # Replace pre-release suffix
        return re.sub(
            r"-(alpha|beta|rc)\.(\d+)",
            lambda m: {"alpha": "a", "beta": "b", "rc": "rc"}[m.group(1)] + m.group(2),
            version,
        )
