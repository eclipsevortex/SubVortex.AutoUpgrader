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
import typing
import shutil
import subprocess
from os import path
from packaging.version import Version

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.github as saug
import subvortex.auto_upgrader.src.asset as saua
import subvortex.auto_upgrader.src.file_system as saufs
import subvortex.auto_upgrader.src.upgraders.base_upgrader as sauubu
import subvortex.auto_upgrader.src.migrator as saum
import subvortex.auto_upgrader.src.exception as saue
import subvortex.auto_upgrader.src.link as saul
import subvortex.auto_upgrader.src.version as sauv

here = path.abspath(path.dirname(__file__))


class AssetUpgrader(sauubu.BaseUpgrader):
    def __init__(self):
        self.github = saug.Github(repo_owner="eclipsevortex", repo_name="SubVortex")
        self.migrator = saum.Migrator()

    def can_upgrade():
        return True

    def should_skip(self):
        return False

    def is_upgrade(self, current_version: str, latest_version: str):
        return Version(current_version) < Version(latest_version)

    async def get_latest_version(self):
        version, release_time = (
            self.github.get_latest_tag_including_prereleases()
            if sauc.SV_PRERELEASE_ENABLED
            else self.github.get_latest_version()
        )

        return version

    def get_current_version(self):
        return self.github.get_version() or sauc.DEFAULT_LAST_RELEASE["global"]

    def get_latest_components(self, version: str) -> typing.Dict[str, str]:
        return self._get_components(version=version)

    def get_current_components(self, version: str) -> typing.Dict[str, str]:
        return self._get_components(version=version)

    def get_latest_component_version(self, name: str, path: str):
        return saufs.get_version(path=path)

    def get_current_component_version(self, name: str, path: str):
        return (
            saufs.get_version(path=path)
            or sauc.DEFAULT_LAST_RELEASE[f"{sauc.SV_EXECUTION_ROLE}.{name}"]
        )

    async def upgrade(self, path: str, name: str, previous_version: str, version: str):
        # Setup the component
        result, reason = self._setup_component(path=path, name=name)
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not setup the component {version}: {reason}",
            )

        # Rollout the migration
        result, reason = (
            await self.migrator.rollout(
                component_name=name,
                component_path=path,
                version=version,
                previous_version=previous_version,
            )
            if result
            else (result, reason)
        )
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not migrate the component {version}: {reason}",
            )

        # Start the component
        result, reason = self._start_component(path=path, name=name)
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not start the component {version}: {reason}",
            )

    async def downgrade(
        self, path: str, name: str, previous_version: str, version: str
    ):
        # Setup the component
        result, reason = self._setup_component(path=path, name=name)
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not setup the component {version}: {reason}",
            )

        # Get the previous version path
        normalized_version = sauv.normalize_version(version)
        normalized_previous_version = sauv.normalize_version(previous_version)
        previous_path = path.replace(normalized_version, normalized_previous_version)

        # Rollout the migration
        result, reason = (
            await self.migrator.rollback(
                component_name=name,
                component_path=previous_path,
                version=version,
                previous_version=previous_version,
            )
            if result
            else (result, reason)
        )
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not migrate the component {version}: {reason}",
            )

        # Start the component
        result, reason = self._start_component(path=path, name=name)
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not start the component {version}: {reason}",
            )

    def teardown(self, path: str, name: str):
        try:
            # Get the script path
            script_path = self._get_script_path(path=path, name=name, action="teardown")

            # Execute the script
            subprocess.run(
                ["bash", script_path],
                env=os.environ.copy(),
                check=True,
                text=True,
            )

        except subprocess.CalledProcessError as e:
            btul.logging.warning(
                f"[{name}] Could not teardown the service: {e}. Please manuually stop it.",
                prefix=sauc.SV_LOGGER_NAME,
            )

    def start(self):
        pass

    def pre_upgrade(self, path: str, name: str):
        pass

    def post_upgrade(self, previous_version: str, version: str):
        if version == sauc.DEFAULT_LAST_RELEASE.get("global"):
            # Remove the previous version sym link
            self._remove_symlink()
        else:
            # Update the link to the new version
            self._update_symlink(version=version)

        # Remove the previous version
        self._remove_version(version=previous_version)

    def copy_env_file(self, component_name: str, component_path: str):
        source_env_file = os.path.join(
            here,
            f"../../environment/env.subvortex.{sauc.SV_EXECUTION_ROLE}.{component_name}",
        )
        target_env_file = f"{component_path}/.env"
        shutil.copy2(source_env_file, target_env_file)

    def _setup_component(self, path: str, name: str):
        try:
            # Get the script path
            script_path = self._get_script_path(path=path, name=name, action="setup")

            # Execute the script
            subprocess.run(
                ["bash", script_path],
                env=os.environ.copy(),
                check=True,
                text=True,
            )

            return True, None

        except subprocess.CalledProcessError as e:
            return False, str(e)

    def _start_component(self, path: str, name: str):
        try:
            # Get the script path
            script_path = self._get_script_path(path=path, name=name, action="start")

            # Execute the script
            subprocess.run(
                ["bash", script_path],
                env=os.environ.copy(),
                check=True,
                text=True,
            )

            return True, None

        except subprocess.CalledProcessError as e:
            return False, str(e)

    def _get_components(self, version: str) -> typing.Dict[str, str]:
        components = {}

        if version == sauc.DEFAULT_LAST_RELEASE["global"]:
            return components

        # Download assets
        path, reason = self.github.download_and_unzip(version=version)
        if not path:
            raise Exception(
                f"Could not download the assets for the version {version}: {reason}"
            )
        
        btul.logging.debug(
            f"Version {version} has been downloaded and unzipped",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Build the list of components
        components = saufs.get_components(path=path, role=sauc.SV_EXECUTION_ROLE)

        return components

    def _get_deployment_dir(self, component_path: str):
        # Build the base script path
        return f"{component_path}/deployment/{sauc.SV_EXECUTION_METHOD}"

    def _update_symlink(self, version: str):
        # Normalized the version
        normalized_version = sauv.normalize_version(version=version)

        # Build the path where to find the new version
        path = f"{sauc.SV_ASSET_DIR}/subvortex-{normalized_version}"

        # Change the sym link
        saul.update_symlink(
            f"{path}",
            f"{sauc.SV_EXECUTION_DIR}",
        )

        btul.logging.info(
            f"🔗 Symlink set: {path} → {sauc.SV_EXECUTION_DIR}",
            prefix=sauc.SV_LOGGER_NAME,
        )

    def _remove_symlink(self):
        # Remove the link
        saul.remove_symlink(sauc.SV_EXECUTION_DIR)

        btul.logging.info(
            f"🔗 Symlink removed: {sauc.SV_EXECUTION_DIR}",
            prefix=sauc.SV_LOGGER_NAME,
        )

    def _remove_version(self, version: str):
        # Normalized the version
        normalized_version = sauv.normalize_version(version=version)

        # Build the path where to find the new version
        path = f"{sauc.SV_ASSET_DIR}/subvortex-{normalized_version}"

        # Remove the old version
        if os.path.exists(path):
            shutil.rmtree(path)

        success = not os.path.exists(path)

        if success:
            btul.logging.info(
                f"🧹 Previous version {version} removed",
                prefix=sauc.SV_LOGGER_NAME,
            )
        else:
            btul.logging.warning(
                f"⚠️ Previous version {version} could not be removed",
                prefix=sauc.SV_LOGGER_NAME,
            )

    def _get_script_path(self, path: str, name: str, action: str):
        # Get the deployment path
        deployment_path = self._get_deployment_dir(component_path=path)

        # Get the script name
        script_name = f"{name}_{sauc.SV_EXECUTION_METHOD}_{action}.sh"

        # If the method does not exist, we default to service which always exist
        script_name = (
            script_name
            if os.path.exists(f"{deployment_path}/{script_name}")
            else f"{name}_{sauc.SV_EXECUTION_METHOD}_service.sh"
        )

        # Get the script path
        script_path = f"{deployment_path}/{script_name}"

        return script_path
