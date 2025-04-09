import os
import shutil
import asyncio
import argparse
import subprocess
from os import path

import bittensor.core.config as btcc
import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.github as saug
import subvortex.auto_upgrader.src.file_system as saufs
import subvortex.auto_upgrader.src.asset as saua
import subvortex.auto_upgrader.src.upgrade_executor as sauue


here = path.abspath(path.dirname(__file__))


class ServiceSentinel:
    def __init__(self):
        parser = argparse.ArgumentParser()

        parser.add_argument(
            "--role",
            type=str,
            default="miner",
            help="Role of the auto upgrader (miner or validator), default miner",
        )

        btul.logging.add_args(parser)
        self.config = btcc.Config(parser)

        btul.logging(config=self.config, debug=True)
        btul.logging.set_trace(self.config.logging.trace)
        btul.logging._stream_formatter.set_trace(self.config.logging.trace)

        self.should_exit = asyncio.Event()
        self.finished = asyncio.Event()

    async def run(self):
        # Initialize github
        github = saug.Github(repo_owner="eclipsevortex", repo_name="SubVortex")

        try:
            first_run = True
            while not self.should_exit.set():
                if not first_run:
                    # Wait a second
                    await asyncio.sleep(10)

                # Get the latest version
                latest_version = (
                    github.get_latest_tag_including_prereleases()
                    if sauc.SV_PRERELEASE_ENABLED
                    else github.get_latest_version()
                )
                btul.logging.info(
                    f"Remote version: {latest_version}", prefix=sauc.SV_LOGGER_NAME
                )

                # Get the current version
                current_version = github.get_version()
                btul.logging.info(
                    f"Current version: {current_version}", prefix=sauc.SV_LOGGER_NAME
                )

                if current_version == latest_version:
                    # No new version has been pushed
                    continue

                btul.logging.info(
                    f"Working directory: {sauc.SV_WORKING_DIRECTORY}",
                    prefix=sauc.SV_LOGGER_NAME,
                )

                # Download the new version
                asset_archive_path = github.download_neuron(
                    self.config.role, latest_version
                )
                btul.logging.debug(
                    f"Asset archive: {asset_archive_path}", prefix=sauc.SV_LOGGER_NAME
                )

                # Unzip the new version
                asset_path = saua.unzip_asset(path=asset_archive_path)
                btul.logging.debug(f"Asset: {asset_path}", prefix=sauc.SV_LOGGER_NAME)

                # Search for components that have changed
                components = saufs.get_components(
                    path=asset_path, role=self.config.role
                )
                for component_name, component_path in components:
                    # Build the path to the current component directory
                    current_component_path = os.path.expanduser(
                        f"~/subvortex/subvortex/{self.config.role}/{component_name}"
                    )

                    # Get the latest version
                    component_latest_version = saufs.get_version(
                        component_path=component_path
                    )
                    btul.logging.info(
                        f"[{component_name}] Remote version: {component_latest_version}",
                        prefix=sauc.SV_LOGGER_NAME,
                    )

                    # Get the current version
                    component_current_version = saufs.get_version(
                        component_path=current_component_path
                    )
                    btul.logging.info(
                        f"[{component_name}] Current version: {component_current_version}",
                        prefix=sauc.SV_LOGGER_NAME,
                    )

                    if component_current_version == component_latest_version:
                        # No new version for the component
                        continue

                    # Copy the env var file
                    self._copy_env_file(
                        component_name=component_name, component_path=component_path
                    )
                    btul.logging.info(
                        f"[{component_name}] Environment variables copied",
                        prefix=sauc.SV_LOGGER_NAME,
                    )

                    # Build the base script path
                    base_scripts = (
                        f"{component_path}/deployment/{sauc.SV_EXECUTION_METHOD}"
                    )

                    # Run the installation script
                    self._execute_setup(
                        base_scripts=base_scripts, component_name=component_name
                    )

                    # Run the starting script
                    self._execute_start(
                        base_scripts=base_scripts, component_name=component_name
                    )

                    btul.logging.success(
                        f"[{component_name}] Component has been migrated succesfully",
                        prefix=sauc.SV_LOGGER_NAME,
                    )

                first_run = False

        except KeyboardInterrupt:
            btul.logging.debug("KeyboardInterrupt", prefix=sauc.SV_LOGGER_NAME)

    async def shutdown(self):
        # Send the signal to stop the service
        self.should_exit.set()

        # Wait for the start method to finish
        await self.finished.wait()

    def _copy_env_file(self, component_name: str, component_path: str):
        # Build the source env file
        source_env_file = os.path.join(
            here,
            f"../environment/env.subvortex.{self.config.role}.{component_name}",
        )

        # Build the target env file
        target_env_file = f"{component_path}/.env"

        # Copy the source to the target
        shutil.copy2(source_env_file, target_env_file)

    def _execute_setup(self, base_scripts: str, component_name: str):
        # Build the name of the script
        script_name = f"{component_name}_{sauc.SV_EXECUTION_METHOD}_setup.sh"

        # Build the path of the script
        script_path = f"{base_scripts}/{script_name}"

        # Run the installation script
        subprocess.run(["bash", script_path], env=os.environ.copy(), check=True)

    def _execute_start(self, base_scripts: str, component_name: str):
        # Build the name of the script
        script_name = f"{component_name}_{sauc.SV_EXECUTION_METHOD}_start.sh"

        # Build the path of the script
        script_path = f"{base_scripts}/{script_name}"

        # Run the installation script
        subprocess.run(["bash", script_path], env=os.environ.copy(), check=True)


if __name__ == "__main__":
    asyncio.run(ServiceSentinel().run())
