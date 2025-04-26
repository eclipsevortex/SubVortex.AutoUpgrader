import os
import time
import shutil
import tarfile
import requests
from packaging.version import Version, InvalidVersion

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.exception as saue


class Github:
    def __init__(self, repo_owner="eclipsevortex", repo_name="SubVortex"):
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.latest_version = None
        self.published_at = None

    def get_latest_version(self):
        version, _ = self._get_latest_tag_including_prereleases()
        return version

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

        return asset_path

    def _get_latest_tag_including_prereleases(self):
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
            return self.latest_version, None

        releases = response.json()

        if not releases:
            return self.latest_version, self.published_at

        # Sort releases by published_at descending (most recent first)
        releases = sorted(
            releases, key=lambda r: r.get("published_at", ""), reverse=True
        )

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

        btul.logging.debug(
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

        btul.logging.debug(
            f"Archive {archive_path} unzipped into {target_dir}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        if not os.path.exists(target_dir):
            raise saue.MissingDirectoryError(directory_path=target_dir)

        return target_dir
