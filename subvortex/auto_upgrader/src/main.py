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
import typing
import asyncio
import argparse
import traceback

import bittensor.core.config as btcc
import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc

import subvortex.auto_upgrader.src.upgraders.factory_uprader as sauufu
import subvortex.auto_upgrader.src.exception as saue


class AutoUpgrader:
    def __init__(self):
        parser = argparse.ArgumentParser()

        btul.logging.add_args(parser)
        self.config = btcc.Config(parser)

        btul.logging(config=self.config, debug=True)
        btul.logging.set_trace(self.config.logging.trace)
        btul.logging._stream_formatter.set_trace(self.config.logging.trace)

        # Create an instance of the upgrader
        self.upgrader = sauufu.create_upgrader(executor=sauc.SV_EXECUTION_METHOD)

        self.should_exit = asyncio.Event()
        self.finished = asyncio.Event()

    async def run(self):
        first_run = True
        while not self.should_exit.is_set():
            latest_version = None
            current_version = None
            is_upgrade = False
            success = False

            try:
                if not first_run:
                    await asyncio.sleep(sauc.SV_CHECK_INTERVAL)

                btul.logging.info(
                    f"Checking for new releases for {sauc.SV_EXECUTION_ROLE} running into {sauc.SV_EXECUTION_METHOD}",
                    prefix=sauc.SV_LOGGER_NAME,
                )

                # Get the latest version
                latest_version = await self.upgrader.get_latest_version()
                btul.logging.debug(
                    f"Latest version: {latest_version}",
                    prefix=sauc.SV_LOGGER_NAME,
                )

                # Get the current version
                current_version = self.upgrader.get_current_version()
                btul.logging.debug(
                    f"Current version: {current_version}",
                    prefix=sauc.SV_LOGGER_NAME,
                )

                # TODO: call a method that return true if you can start the upgrade/downgrade. True if all the version in the tag are built and available especially for docker!

                # Check if there is anew release
                if current_version == latest_version:
                    btul.logging.info(
                        f"No new version released",
                        prefix=sauc.SV_LOGGER_NAME,
                    )

                    # Mark the upgrade as success
                    success = True

                    continue

                # True if it is an upgrade, false if downgrade
                is_upgrade = self.upgrader.is_upgrade(
                    current_version=current_version, latest_version=latest_version
                )

                btul.logging.info(
                    f"{'Upgrading' if is_upgrade else 'Downgrading'} {current_version} -> {latest_version}",
                    prefix=sauc.SV_LOGGER_NAME,
                )

                # Rollout the update
                await self._execute_update_plan(
                    current_version=current_version,
                    latest_version=latest_version,
                    is_upgrade=is_upgrade,
                )

                # Mark the upgrade as success
                success = True

                btul.logging.success(
                    f"✅ Successfully {'upgraded' if is_upgrade else 'downgraded'} {current_version} -> {latest_version}",
                    prefix=sauc.SV_LOGGER_NAME,
                )

                # Complete the upgrader
                self.upgrader.post_upgrade(
                    previous_version=current_version,
                    version=latest_version,
                )

            except KeyboardInterrupt:
                btul.logging.debug("KeyboardInterrupt", prefix=sauc.SV_LOGGER_NAME)

            except saue.ComponentException as e:
                btul.logging.error(str(e))

            except Exception as e:
                btul.logging.error(
                    f"An error has been thrown: {e}", prefix=sauc.SV_LOGGER_NAME
                )
                btul.logging.debug(traceback.format_exc())

            finally:
                first_run = False

                if not success:
                    btul.logging.warning(
                        f"Rolling back {latest_version} -> {current_version}",
                        prefix=sauc.SV_LOGGER_NAME,
                    )

                    # Rollback the update
                    await self._execute_update_plan(
                        current_version=latest_version,
                        latest_version=current_version,
                        is_upgrade=not is_upgrade,
                    )

                    btul.logging.success(
                        f"✅ Successfully rollbacked {latest_version} -> {current_version}",
                        prefix=sauc.SV_LOGGER_NAME,
                    )

    async def shutdown(self):
        self.should_exit.set()
        await self.finished.wait()

    async def _execute_update_plan(
        self, current_version: str, latest_version: str, is_upgrade: bool
    ):
        # Get the components of the next version
        lastest_version_components = self.upgrader.get_latest_components(
            version=latest_version
        )
        btul.logging.debug(
            f"Latest version components: {list(lastest_version_components.keys())}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Get the components of the current version
        current_version_components = self.upgrader.get_current_components(
            version=current_version
        )
        btul.logging.debug(
            f"Current version components: {list(current_version_components.keys())}",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Teardown components that are in the current version but not in the latest one
        self._teardown_prune_components(
            current_components=current_version_components,
            latest_components=lastest_version_components,
        )

        # Install/Upgrade all the components that are in the next releases
        await self._update_components(
            current_components=current_version_components,
            latest_components=lastest_version_components,
            is_upgrade=is_upgrade,
        )

    def _teardown_prune_components(
        self,
        current_components: typing.Dict[str, str],
        latest_components: typing.Dict[str, str],
    ):
        for (
            component_name,
            component_path,
        ) in current_components.items():
            if component_name in latest_components:
                continue

            # Teardown the component
            self.upgrader.teardown(path=component_path, name=component_name)

    async def _update_components(
        self,
        current_components: typing.Dict[str, str],
        latest_components: typing.Dict[str, str],
        is_upgrade: bool,
    ):
        # Copy all the environment variables in the right place
        for (
            latest_component_name,
            latest_component_path,
        ) in latest_components.items():
            self.upgrader.copy_env_file(
                component_name=latest_component_name,
                component_path=latest_component_path,
            )
        btul.logging.info(f"Environement variables copied", prefix=sauc.SV_LOGGER_NAME)

        # Execute the upgrade/downgrade of each components
        for (
            latest_component_name,
            latest_component_path,
        ) in latest_components.items():
            # Get the component in the current release
            current_component_name = latest_component_name
            current_component_path = current_components.get(current_component_name)

            # Get the latest version of the component
            latest_component_version = self.upgrader.get_latest_component_version(
                name=current_component_name, path=latest_component_path
            )

            # Get the current version of the component
            current_component_version = self.upgrader.get_current_component_version(
                name=current_component_name, path=current_component_path
            )

            # Complete the upgrader
            self.upgrader.pre_upgrade(
                path=latest_component_path,
                name=latest_component_name,
            )

            if current_component_version == latest_component_version:
                btul.logging.info(
                    f"[{latest_component_name}] No new version released",
                    prefix=sauc.SV_LOGGER_NAME,
                )

                continue

            btul.logging.info(
                f"[{latest_component_name}] {'Upgrading' if is_upgrade else 'Downgrading'} {current_component_version} -> {latest_component_version}",
                prefix=sauc.SV_LOGGER_NAME,
            )

            # Upgrade or Downgrade the component
            if is_upgrade:
                await self.upgrader.upgrade(
                    path=latest_component_path,
                    name=latest_component_name,
                    previous_version=current_component_version,
                    version=latest_component_version,
                )
            else:
                await self.upgrader.downgrade(
                    path=latest_component_path,
                    name=latest_component_name,
                    previous_version=current_component_version,
                    version=latest_component_version,
                )


if __name__ == "__main__":
    asyncio.run(AutoUpgrader().run())
