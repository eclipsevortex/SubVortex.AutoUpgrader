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
import shutil
import asyncio
import traceback
import subprocess
from os import path
from typing import List, Tuple, Callable
from packaging.version import Version

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.service as saus
import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.path as saup
import subvortex.auto_upgrader.src.utils as sauu
import subvortex.auto_upgrader.src.exception as saue
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.resolvers.dependency_resolver as saudr
import subvortex.auto_upgrader.src.github as saug
import subvortex.auto_upgrader.src.resolvers.metadata_resolver as saumr
from subvortex.auto_upgrader.src.migration_manager import MigrationManager

here = path.abspath(path.dirname(__file__))


class Orchestrator:
    def __init__(self):
        self.rollback_steps: List[Tuple[str, callable]] = []
        self.previously_started_services: List[str] = []

        self.services: List[saus.Service] = []
        self.current_services: List[saus.Service] = []
        self.latest_services: List[saus.Service] = []

        self.github = saug.Github()
        self.metadata_resolver = saumr.MetadataResolver()

        self.has_changed = True

    async def run_plan(self):
        btul.logging.info("Running the plan...", prefix=sauc.SV_LOGGER_NAME)

        # Get version before auto upgrader
        last_version_before_auto_upgrader = sauc.DEFAULT_LAST_RELEASE.get("global")

        # Get the current version
        await self._step(
            "Get current version",
            self._rollback_nop,
            self._get_current_version,
        )

        # Get the latest version
        await self._step(
            "Get latest version",
            self._rollback_nop,
            self._get_latest_version,
        )

        # Pull the assets of the current version for the neuron
        await self._step(
            "Pull current version",
            self._rollback_nop,
            self._pull_current_assets,
            condition=lambda: self.current_version != last_version_before_auto_upgrader,
        )

        # Pull the assets of the latest version for the neuron
        await self._step(
            "Pull latest version",
            self._rollback_pull_latest_assets,
            self._pull_latest_assets,
        )

        if (
            sauc.SV_EXECUTION_METHOD != "container"
            and self.current_version == self.latest_version
        ):
            btul.logging.debug(
                "🟢 No new release available. All services are up-to-date.",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return True

        # Set the action
        action = (
            "upgrade" if self.current_version < self.latest_version else "downgrade"
        )
        emoji = "⬆️" if self.current_version < self.latest_version else "⬇️"

        # Load the services of the current version
        await self._step(
            "Load current services",
            self._rollback_nop,
            self._load_current_services,
            condition=lambda: self.current_version != last_version_before_auto_upgrader,
        )

        # Load the services of the latest version
        await self._step(
            "Load latest services", self._rollback_nop, self._load_latest_services
        )

        # Check the latest version and the current one
        await self._step("Check versions", self._rollback_nop, self._check_versions)

        # Stop if no services have changed
        if not self.has_changed:
            btul.logging.success(
                f"🟢 No service changes detected. All services are up-to-date.",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return True

        # Copy the env var file in the latest version services
        await self._step(
            "Copying environement variables",
            self._rollback_nop,
            self._copy_env_files,
        )

        # Upgrade the services that have changed
        await self._step(
            f"{action} services".capitalize(),
            self._rollback_services,
            self._rollout_service,
        )

        # Rollout migrations
        await self._step(
            "Run migrations", self._rollback_migrations, self._rollout_migrations
        )

        # Stop previous services
        await self._step(
            "Stop previous services",
            self._rollback_stop_current_services,
            self._stop_current_services,
        )

        # Switch services to new version
        await self._step(
            "Switching to new version",
            self._rollback_switch_services,
            self._switch_services,
        )

        # Start latest services
        await self._step(
            "Start new services",
            self._rollback_start_latest_services,
            self._start_latest_services,
        )

        # Remove prune services
        await self._step(
            "Remove prune services",
            self._rollback_prune_services,
            self._prune_services,
        )

        # Remove previous services
        await self._step(
            "Remove previous version",
            self._rollback_remove_services,
            self._remove_services,
        )

        # Finalize service versions
        await self._step(
            "Finalize service versions",
            self._rollback_nop,
            self._finalize_versions,
        )

        btul.logging.success(
            f"{emoji} {action} {self.current_version} -> {self.latest_version} completed succesfully".capitalize(),
            prefix=sauc.SV_LOGGER_NAME,
        )

        return True

    async def run_rollback_plan(self):
        btul.logging.info("Rolling back the plan...", prefix=sauc.SV_LOGGER_NAME)

        success = True
        for description, rollback_func in reversed(self.rollback_steps):
            btul.logging.info(
                f"▶️ \033[35mRolling back: {description}\033[0m",
                prefix=sauc.SV_LOGGER_NAME,
            )
            try:
                if asyncio.iscoroutinefunction(rollback_func):
                    await rollback_func()
                else:
                    rollback_func()

                btul.logging.info(
                    f"✅ \033[32mCompleted: {description}\033[0m",
                    prefix=sauc.SV_LOGGER_NAME,
                )
            except Exception as e:
                success = False
                btul.logging.error(
                    f"❌ Failed to rollback {description}: {e}",
                    prefix=sauc.SV_LOGGER_NAME,
                )
                btul.logging.debug(traceback.format_exc())

        if success:
            btul.logging.success(
                "Rollback completed succesfully",
                prefix=sauc.SV_LOGGER_NAME,
            )

    def reset(self):
        self.rollback_steps.clear()
        self.previously_started_services.clear()
        self.current_services.clear()
        self.latest_services.clear()
        self.current_version = None
        self.latest_version = None

    async def _step(
        self,
        description: str,
        rollback_func: callable,
        action_func: callable,
        service_filter: callable = None,
        condition: Callable[[], bool] = None,
    ):
        if condition and not condition():
            btul.logging.debug(
                f"⏩ Skipping: {description} (condition not met)",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return

        btul.logging.info(
            f"▶️ \033[34mStarting: {description}\033[0m", prefix=sauc.SV_LOGGER_NAME
        )
        self.rollback_steps.append((description, rollback_func))

        if service_filter:
            if asyncio.iscoroutinefunction(action_func):
                await action_func(service_filter=service_filter)
            else:
                action_func(service_filter=service_filter)
        else:
            if asyncio.iscoroutinefunction(action_func):
                await action_func()
            else:
                action_func()

        btul.logging.info(
            f"✅ \033[32mCompleted: {description}\033[0m", prefix=sauc.SV_LOGGER_NAME
        )

    def _rollback_nop(self):
        pass  # For steps that don't change state

    async def _get_current_version(self):
        # Get the latest version
        version = self.github.get_local_version()

        # Store the current version
        self.current_version = version or sauc.DEFAULT_LAST_RELEASE.get("global")

        btul.logging.debug(
            f"Current version: {self.current_version}", prefix=sauc.SV_LOGGER_NAME
        )

    async def _get_latest_version(self):
        # Get the latest version
        version = self.github.get_latest_version()

        if version is None:
            raise saue.MissingVersionError(name="global", type="latest")

        # Store the latest version
        self.latest_version = version

        btul.logging.debug(
            f"Latest version: {self.latest_version}", prefix=sauc.SV_LOGGER_NAME
        )

    def _pull_current_assets(self):
        # Normalized the current version
        denormalized_version = sauv.normalize_version(version=self.current_version)

        # Check if the current assets have already been download and unzipped
        version_path = os.path.join(
            sauc.SV_ASSET_DIR, f"subvortex-{denormalized_version}"
        )
        is_exist = os.path.exists(version_path)
        if is_exist:
            btul.logging.debug(
                f"Version {self.current_version} already pulled in {version_path}",
                prefix=sauc.SV_LOGGER_NAME,
            )

            return

        # Download and unzip the latest version
        self._pull_assets(version=self.current_version)

    def _pull_latest_assets(self):
        # Download and unzip the latest version
        self._pull_assets(version=self.latest_version)

        # Buid the path of the the version directory
        path = saup.get_version_directory(version=self.latest_version)
        if not os.path.exists(path):
            raise saue.MissingDirectoryError(directory_path=path)

    def _copy_env_files(self):
        for service in self.latest_services:
            # Create the env file path
            source_file = saup.get_au_environment_file(service=service)
            if not os.path.exists(source_file):
                raise saue.MissingFileError(file_path=source_file)

            # Build the target env file
            target_dir = saup.get_service_directory(service=service)
            if not os.path.isdir(target_dir):
                raise saue.MissingDirectoryError(directory_path=target_dir)

            # Create the env file
            env_file = f"{target_dir}/.env"

            # Copy the env file to the service directory
            shutil.copy2(source_file, env_file)

            # Check if the file is there
            if not os.path.isfile(env_file):
                raise saue.MissingFileError(file_path=env_file)

            btul.logging.trace(
                f"Env file {source_file} copied to {env_file}",
                prefix=sauc.SV_LOGGER_NAME,
            )

    def _rollback_pull_latest_assets(self):
        # Remove the latest version
        self._remove_assets(version=self.latest_version)

        btul.logging.debug("Latest assets removed", prefix=sauc.SV_LOGGER_NAME)

    def _load_current_services(self):
        # Get the version of all services for container, for the other it will come from the metadata loaded locally
        versions = (
            self.github.get_local_container_versions
            if sauc.SV_EXECUTION_METHOD == "container"
            else lambda name: {}
        )

        # Load the services of the current version
        self.current_services = self._load_services(
            version=self.current_version, versions=versions
        )

        # Display the list of services
        services = [
            f"{x.name} (v:{x.version}, comp:{x.component_version}, svc:{x.service_version})"
            for x in self.current_services
        ]
        btul.logging.debug(
            f"Current services loaded ({len(self.current_services)}): {', '.join(services)}",
            prefix=sauc.SV_LOGGER_NAME,
        )

    def _load_latest_services(self):
        # Get the version of all services for container, for the other it will come from the metadata loaded locally
        versions = (
            self.github.get_latest_container_versions
            if sauc.SV_EXECUTION_METHOD == "container"
            else lambda name: {}
        )

        # Load the services of the latest version
        self.latest_services = self._load_services(
            version=self.latest_version, versions=versions
        )
        if len(self.latest_services) == 0:
            raise saue.ServicesLoadError(version=self.latest_version)

        # Display the list of services
        services = [
            f"{x.name} (v:{x.version}, comp:{x.component_version}, svc:{x.service_version})"
            for x in self.latest_services
        ]
        btul.logging.debug(
            f"Latest services loaded ({len(self.latest_services)}): {', '.join(services)}",
            prefix=sauc.SV_LOGGER_NAME,
        )

    def _check_versions(self):
        latest_map = {s.id: s for s in self.latest_services}
        current_map = {s.id: s for s in self.current_services}

        all_ids = set(latest_map.keys()).union(current_map.keys())

        self.services = []
        for service_id in all_ids:
            latest = latest_map.get(service_id)
            current = current_map.get(service_id)

            if current and not latest:
                # Service exists in current, but not in latest — must be removed
                current.must_remove = True
                current.needs_update = False
                current.upgrade_type = None
                btul.logging.info(
                    f"{current.name} no longer exists in latest release. Marked for removal.",
                    prefix=sauc.SV_LOGGER_NAME,
                )
                self.services.append(current)
                continue

            if latest and not current:
                # New service in latest
                latest.needs_update = True
                latest.upgrade_type = "install"
                btul.logging.debug(
                    f"{latest.name} is a new service in latest version. Marked for installation.",
                    prefix=sauc.SV_LOGGER_NAME,
                )
                self.services.append(latest)
                continue

            # Compare versions
            current_version = Version(current.version)
            latest_version = Version(latest.version)

            if current_version != latest_version:
                latest.needs_update = True
                latest.upgrade_type = (
                    "upgrade" if latest_version > current_version else "downgrade"
                )
                btul.logging.debug(
                    f"{latest.name} version change detected: {current.version} -> {latest.version} ({latest.upgrade_type})",
                    prefix=sauc.SV_LOGGER_NAME,
                )
            else:
                latest.needs_update = False
                latest.upgrade_type = None
                btul.logging.debug(
                    f"{latest.name} is already up-to-date at version {latest.version}.",
                    prefix=sauc.SV_LOGGER_NAME,
                )

            self.services.append(latest)

        # Check if services have changed
        self.has_changed = any(
            x for x in self.services if x.must_remove or x.needs_update
        )

    def _rollout_service(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.latest_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            if not service.needs_update:
                continue

            # Execute the setup
            self._execute_setup(service=service)

    def _rollback_services(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.latest_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            if not service.needs_update or service.upgrade_type != "install":
                continue

            # Execute the setup
            self._execute_teardown(service=service)

    async def _rollout_migrations(self):
        # Filter services that need update
        services_to_update = [s for s in self.services if s.needs_update]

        # Create a map of old services (current services) by ID
        current_services_map = {s.id: s for s in self.current_services}

        # Prepare service pairs for migration (new service + previous service)
        service_pairs: List[Tuple[saus.Service, saus.Service]] = []
        for new_service in services_to_update:
            old_service = current_services_map.get(new_service.id)
            service_pairs.append((new_service, old_service))

        # Start services that are new and have migrations
        service_pairs_to_apply: List[Tuple[saus.Service, saus.Service]] = []
        for new_service, old_service in service_pairs:
            # Check if there is any migrations to apply
            has_migrations = self._has_migrations(new_service)

            # Check if there are any migrations to install
            if not has_migrations:
                btul.logging.debug(
                    f"Skipping migrations for {new_service.name} (upgrade_type={new_service.upgrade_type}, has_migrations={has_migrations})",
                    prefix=sauc.SV_LOGGER_NAME,
                )
                continue

            btul.logging.debug(
                f"Migrations found for {new_service.name}", prefix=sauc.SV_LOGGER_NAME
            )

            # Add the service to apply migrations
            service_pairs_to_apply.append((new_service, old_service))

            # If the service is not new, it is already up and running
            if new_service.upgrade_type != "install":
                continue

            btul.logging.info(
                f"⚙️ Preparing new service {new_service.name} before migrations",
                prefix=sauc.SV_LOGGER_NAME,
            )

            # Execute the start script
            self._execute_start(service=new_service)

            # Add the service in the list
            self.previously_started_services.append(new_service.id)

        if len(service_pairs_to_apply) == 0:
            return

        # Create the migration manager with service pairs
        self.migration_manager = MigrationManager(service_pairs)
        self.migration_manager.collect_migrations()
        await self.migration_manager.apply()

    async def _rollback_migrations(self):
        await self.migration_manager.rollback()

    def _stop_current_services(self, service_filter: Callable = None):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            if not service.needs_update and not service.must_remove:
                continue

            if service_filter and not service_filter(service):
                continue

            current_service = next(
                (x for x in self.current_services if x.id == service.id), None
            )
            if not current_service:
                continue

            self._execute_stop(service=current_service)

    def _rollback_stop_current_services(self, service_filter: Callable = None):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            if not service.needs_update and not service.must_remove:
                continue

            if service_filter and not service_filter(service):
                continue

            current_service = next(
                (x for x in self.current_services if x.id == service.id), None
            )
            if not current_service:
                continue

            self._execute_start(service=current_service)

    def _switch_services(self):
        # Ensure the working directory exists
        os.makedirs(sauc.SV_EXECUTION_DIR, exist_ok=True)

        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            if not service.needs_update:
                continue

            # Switch to new version
            service.switch_to_version(version=service.version)

    def _rollback_switch_services(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            if not service.needs_update:
                continue

            # Switch to previous version
            service.switch_to_version(version=service.version)

    def _start_latest_services(self, service_filter: Callable = None):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            if not service.needs_update:
                continue

            if service_filter and not service_filter(service):
                continue

            if service.id in self.previously_started_services:
                btul.logging.debug(
                    f"⏩ Skipping start for {service.name} (already started before migration)",
                    prefix=sauc.SV_LOGGER_NAME,
                )
                continue

            self._execute_start(service=service)

    def _rollback_start_latest_services(self, service_filter: Callable = None):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            if not service.needs_update:
                continue

            if service_filter and not service_filter(service):
                continue

            self._execute_stop(service=service)

    def _prune_services(self):
        if sauc.SV_EXECUTION_METHOD == "container":
            # Prune useless images
            self.github.prune_images()

        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.current_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        has_turndown_services = False
        for service in sorted_services:
            if not service.must_remove:
                continue

            has_turndown_services = True

            # Execute the setup
            self._execute_teardown(service=service)

        if not has_turndown_services:
            btul.logging.debug(f"No services to teardown", prefix=sauc.SV_LOGGER_NAME)

    def _rollback_prune_services(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.current_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        has_turndown_services = False
        for service in sorted_services:
            if not service.must_remove:
                continue

            has_turndown_services = True

            # Execute the setup
            self._execute_setup(service=service)

        if not has_turndown_services:
            btul.logging.debug(f"No services to teardown", prefix=sauc.SV_LOGGER_NAME)

    def _remove_services(self):
        self._remove_assets(version=self.current_version)

    def _rollback_remove_services(self):
        self._pull_assets(version=self.current_version)

    def _finalize_versions(self):
        # Update the new version
        for service in self.services:
            service.version = service.rollback_version
            service.rollback_version = None

    def _load_services(self, version: str, versions: Callable):
        services = []

        # Determine the neuron directory where to find all the services
        path = saup.get_role_directory(version=version)
        if not os.path.exists(path):
            raise saue.MissingDirectoryError(directory_path=path)

        for entry in self.metadata_resolver.list_directory(path=path):
            service_path = os.path.join(path, entry)
            if not self.metadata_resolver.is_directory(path=service_path):
                continue

            # Get the metadata
            metadata = self.metadata_resolver.get_metadata(path=service_path)
            if not metadata:
                continue

            # Build the service name
            service_name = entry.split(".")[-1]

            # Get the versions overrided
            overrided_versions = versions(name=service_name)
            btul.logging.trace(
                f"Overrided version for {service_name}: {metadata} -> {overrided_versions}",
                prefix=sauc.SV_LOGGER_NAME,
            )

            # Override the metadata with the versions (it will be only for container execution)
            metadata = {**metadata, **overrided_versions}

            # Create the instance of service
            service = saus.Service.create(metadata)

            # Add the new service
            services.append(service)

        return services

    def _execute_setup(self, service: saus.Service):
        # Run the script
        self._run(action="setup", service=service)

    def _execute_start(self, service: saus.Service):
        # Define the action
        args = ["--recreate"] if sauc.SV_EXECUTION_METHOD == "container" else []

        # Run the script
        self._run(action="start", service=service, args=args)

    def _execute_stop(self, service: saus.Service):
        # Run the script
        self._run(action="stop", service=service)

    def _execute_teardown(self, service: saus.Service):
        # Run the script
        self._run(action="teardown", service=service)

    def _run(self, action: str, service: saus.Service, args: List[str] = []):
        # Build the setup script path
        script_file = saup.get_service_script(
            service=service, action=action, version=self.latest_version
        )
        if not os.path.exists(script_file):
            raise saue.MissingFileError(file_path=script_file)

        btul.logging.debug(
            f"⚙️ Running {action} for {service.name} (version: {service.version})",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Add the flag as env var to be consumed by the script
        env = os.environ.copy()
        env["SUBVORTEX_FLOATTING_FLAG"] = sauu.get_tag()

        try:
            subprocess.run(
                ["bash", script_file] + args,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.CalledProcessError as e:
            raise saue.RuntimeError(action=action, details=str(e))

    def _pull_assets(self, version: str):
        # Download and unzip the latest version
        path = self.github.download_and_unzip_assets(
            version=version,
            role=sauc.SV_EXECUTION_ROLE,
        )

        btul.logging.debug(
            f"Version {version} pulled in {path}", prefix=sauc.SV_LOGGER_NAME
        )

    def _remove_assets(self, version: str):
        # Build the asset directory
        asset_dir = saup.get_version_directory(version=version)
        if not os.path.exists(asset_dir):
            return

        # Remove the directory
        shutil.rmtree(asset_dir, onerror=lambda *args, **kwargs: None)

        # Notify the success
        btul.logging.debug(
            f"Assets for version {version} have been removed",
            prefix=sauc.SV_LOGGER_NAME,
        )

    def _has_migrations(self, service: saus.Service) -> bool:
        migraton_dir = (
            os.listdir(saup.get_migration_directory(service=service))
            if service.migration
            else None
        )
        return (
            service.migration is not None
            and migraton_dir is not None
            and any(f.endswith(".py") for f in migraton_dir)
        )
