import os
import shutil
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
import subvortex.auto_upgrader.src.resolvers.dependency_resolver as saudr
import subvortex.auto_upgrader.src.github as saug
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.resolvers.metadata_resolver as saumr
from subvortex.auto_upgrader.src.migration_manager import MigrationManager

here = path.abspath(path.dirname(__file__))


class Orchestrator:
    def __init__(self):
        self.rollback_steps: List[Tuple[str, callable]] = []

        self.current_version = None
        self.latest_version = None

        self.services: List[saus.Service] = []
        self.current_services: List[saus.Service] = []
        self.latest_services: List[saus.Service] = []

        self.github = saug.Github()
        self.metadata_resolver = saumr.MetadataResolver()

    def run_plan(self):
        btul.logging.info("Running the plan...", prefix=sauc.SV_LOGGER_NAME)
        self.rollback_steps.clear()

        # Get version before auto upgrader
        last_version_before_auo_upgrader = sauc.DEFAULT_LAST_RELEASE.get("global")

        # Get the current version
        self._step(
            "Get current version",
            self._rollback_nop,
            self._get_current_version,
        )

        # Get the latest version
        self._step(
            "Get latest version",
            self._rollback_nop,
            self._get_latest_version,
        )

        # Pull the assets of the current version for the neuron
        self._step(
            "Pull current version",
            self._rollback_nop,
            self._pull_current_version,
            condition=lambda: self.current_version != last_version_before_auo_upgrader,
        )

        # Pull the assets of the latest version for the neuron
        self._step(
            "Pull latest version",
            self._rollback_pull_latest_version,
            self._pull_latest_version,
        )

        if self.current_version == self.latest_version:
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
        self._step(
            "Load current services",
            self._rollback_nop,
            self._load_current_services,
            condition=lambda: self.current_version != last_version_before_auo_upgrader,
        )

        # Load the services of the latest version
        self._step(
            "Load latest services", self._rollback_nop, self._load_latest_services
        )

        # Check the latest version and the current one
        self._step("Check versions", self._rollback_nop, self._check_versions)

        # Copy the env var file in the latest version services
        self._step(
            "Copying environement variables",
            self._rollback_nop,
            self._copy_env_files,
        )

        # Upgrade the services that have changed
        self._step(
            f"{action} services".capitalize(),
            self._rollback_services_changes,
            self._rollout_service,
        )

        # Rollout migrations
        self._step(
            "Run migrations", self._rollback_migrations, self._rollout_migrations
        )

        # Stop previous services
        self._step(
            "Stop previous services",
            self._rollback_stop_current_services,
            self._stop_current_services,
        )

        # Switch services to new version
        self._step(
            "Switching to new version",
            self._rollback_switch_services,
            self._switch_services,
        )

        # Start latest services
        self._step(
            "Start new services",
            self._rollback_start_latest_services,
            self._start_latest_services,
        )

        # Remove prune services
        self._step(
            "Remove prune services",
            self._rollback_prune_services,
            self._prune_services,
        )

        # Remove previous services
        self._step(
            "Remove previous version",
            self._rollback_remove_services,
            self._remove_services,
        )

        # Finalize service versions
        self._step(
            "Finalize service versions",
            self._rollback_nop,
            self._finalize_versions,
        )

        btul.logging.success(
            f"{emoji} {action} {self.current_version} -> {self.latest_version} completed succesfully".capitalize(),
            prefix=sauc.SV_LOGGER_NAME,
        )

        return True

    def run_rollback_plan(self):
        btul.logging.info("Rolling back the plan...", prefix=sauc.SV_LOGGER_NAME)

        success = True
        for desc, rollback_func in reversed(self.rollback_steps):
            btul.logging.info(f"Rolling back: {desc}", prefix=sauc.SV_LOGGER_NAME)
            try:
                rollback_func()
            except Exception as e:
                success = False
                btul.logging.error(
                    f"Failed to rollback {desc}: {e}", prefix=sauc.SV_LOGGER_NAME
                )
                btul.logging.debug(traceback.format_exc())

        if success:
            btul.logging.success(
                "↩️ Rollback completed succesfully",
                prefix=sauc.SV_LOGGER_NAME,
            )

    def _step(
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

        btul.logging.info(f"▶️ Starting: {description}", prefix=sauc.SV_LOGGER_NAME)
        self.rollback_steps.append((description, rollback_func))

        if service_filter:
            action_func(service_filter=service_filter)
        else:
            action_func()

    def _rollback_nop(self):
        pass  # For steps that don't change state

    def _get_current_version(self):
        # Get the latest version
        version = sauv.get_local_version() or sauc.DEFAULT_LAST_RELEASE["global"]

        # Set the current version in a denormlized wayt
        self.current_version = sauv.denormalize_version(version)

        btul.logging.debug(
            f"Current version: {self.current_version}", prefix=sauc.SV_LOGGER_NAME
        )

    def _get_latest_version(self):
        # Get the latest version
        version = self.github.get_latest_version()

        # Set the current version in a denormlized wayt
        self.latest_version = sauv.denormalize_version(version)

        btul.logging.debug(
            f"Latest version: {self.latest_version}", prefix=sauc.SV_LOGGER_NAME
        )

    def _pull_current_version(self):
        # Download and unzip the latest version
        self._pull_assets(version=self.current_version)

        btul.logging.debug("Current assets pulled", prefix=sauc.SV_LOGGER_NAME)

    def _pull_latest_version(self):
        # Download and unzip the latest version
        self._pull_assets(version=self.latest_version)

        # Install subvortex as editable
        # self._install_in_editable_mode()

        # Buid the path of the the version directory
        path = saup.get_version_directory(version=self.latest_version)
        if not os.path.exists(path):
            raise saue.MissingDirectoryError(directory_path=path)

        btul.logging.debug("Latest assets pulled", prefix=sauc.SV_LOGGER_NAME)

    def _copy_env_files(self):
        for service in self.latest_services:
            # Create the env file path
            source_file = saup.get_au_environment_file(service=service)
            if not os.path.exists(source_file):
                raise saue.MissingFileError(file_path=source_file)

            # Build the target env file
            target_dir = saup.get_service_directory(service=service)
            if not os.path.exists(target_dir):
                raise saue.MissingDirectoryError(directory_path=target_dir)

            # Create the env file
            env_file = f"{target_dir}/.env"

            # Copy the env file to the service directory
            shutil.copy2(source_file, env_file)

            # Check if the file is there
            if not os.path.exists(env_file):
                raise saue.MissingFileError(file_path=env_file)

    def _rollback_pull_latest_version(self):
        # Remove the latest version
        self._remove_assets(version=self.latest_version)

        btul.logging.debug("Latest assets removed", prefix=sauc.SV_LOGGER_NAME)

    def _load_current_services(self):
        # Load the services of the current version
        self.current_services = self._load_services(self.current_version)

        # Display the list of services
        services = [x.name for x in self.current_services]
        btul.logging.debug(
            f"Current services loaded ({len(self.current_services)}): {', '.join(services)}",
            prefix=sauc.SV_LOGGER_NAME,
        )

    def _load_latest_services(self):
        # Load the services of the latest version
        self.latest_services = self._load_services(self.latest_version)
        if len(self.latest_services) == 0:
            raise saue.ServicesLoadError(version=self.latest_version)

        # Display the list of services
        services = [x.name for x in self.latest_services]
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
                btul.logging.info(
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
                btul.logging.info(
                    f"{latest.name} version change detected: {current.version} -> {latest.version} ({latest.upgrade_type})",
                    prefix=sauc.SV_LOGGER_NAME,
                )
            else:
                latest.needs_update = False
                latest.upgrade_type = None
                btul.logging.info(
                    f"{latest.name} is already up-to-date at version {latest.version}.",
                    prefix=sauc.SV_LOGGER_NAME,
                )

            self.services.append(latest)

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

        # Install subvortex as editable
        self._install_in_editable_mode()

    def _can_rollout_service(self, service: saus.Service):
        if service.execution != "container":
            return True

        # Chekc if the container is created
        result = os.system(
            f"docker ps --format '{{{{.Names}}}}' | grep -q '{service.name}'"
        )

        return result != 0

    def _rollback_services_changes(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.latest_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            if not service.needs_update:
                continue

            if service.execution == "container":
                # Check if container for service is already running
                result = os.system(
                    f"docker ps --format '{{{{.Names}}}}' | grep -q '{service.name}'"
                )

                if result == 0:
                    btul.logging.info(
                        f"🔄 Skipping {service.name}: container already running.",
                        prefix=sauc.SV_LOGGER_NAME,
                    )

                    continue

            # Execute the setup
            self._execute_setup(service=service, rollback=True)

    def _rollout_migrations(self):
        # Filter out services that do not need any update
        services = [x for x in self.services if x.needs_update]

        # Create the migrations manager and apply the migrations
        self.migration_manager = MigrationManager(services)
        self.migration_manager.collect_migrations()
        self.migration_manager.apply()

    def _rollback_migrations(self):
        self.migration_manager.rollback()

    def _stop_current_services(self, service_filter: Callable = None):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.current_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            if service_filter and not service_filter(service):
                continue

            self._execute_stop(service=service, rollback=True)

    def _rollback_stop_current_services(self, service_filter: Callable = None):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.current_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            if service_filter and not service_filter(service):
                continue

            self._execute_start(service=service)

    def _switch_services(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.latest_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            # Switch to new version
            service.switch_to_version(version=service.version)

    def _rollback_switch_services(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.latest_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            current_service = next(
                (x for x in self.current_services if x.id == service.id), None
            )
            if not current_service:
                continue

            # Switch to previous version
            service.switch_to_version(version=current_service.version)

    def _start_latest_services(self, service_filter: Callable = None):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.latest_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            if service_filter and not service_filter(service):
                continue

            self._execute_start(service=service)

    def _rollback_start_latest_services(self, service_filter: Callable = None):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.latest_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            if service_filter and not service_filter(service):
                continue

            self._execute_start(service=service, rollback=True)

    def _prune_services(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.current_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order(reverse=True)

        for service in sorted_services:
            if not service.must_remove:
                continue

            # Execute the setup
            self._execute_teardown(service=service)

    def _rollback_prune_services(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.current_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            if not service.must_remove:
                continue

            # Execute the setup
            self._execute_setup(service=service)

    def _remove_services(self):
        self._remove_assets(version=self.current_version)

    def _rollback_remove_services(self):
        self._pull_assets(version=self.current_version)

    def _finalize_versions(self):
        for service in self.services:
            service.version = service.rollback_version
            service.rollback_version = None

    def _load_services(self, version: str):
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

            # Create the instance of service
            service = saus.Service.create(metadata)

            # Add the new service
            services.append(service)

        return services

    def _execute_setup(self, service: saus.Service, rollback: bool = False):
        # Define the action
        action = "teardown" if rollback else "setup"

        # Run the script
        self._run(action=action, service=service, rollback=rollback)

    def _execute_start(self, service: saus.Service, rollback: bool = False):
        # Define the action
        action = "stop" if rollback else "start"

        # Run the script
        self._run(action=action, service=service, rollback=rollback)

    def _execute_stop(self, service: saus.Service, rollback: bool = False):
        # Define the action
        action = "start" if rollback else "stop"

        # Run the script
        self._run(action=action, service=service, rollback=rollback)

    def _execute_teardown(self, service: saus.Service, rollback: bool = False):
        # Define the action
        action = "setup" if rollback else "teardown"

        # Run the script
        self._run(action=action, service=service, rollback=rollback)

    def _run(self, action: str, service: saus.Service, rollback: bool = False):
        # Build the setup script path
        script_file = saup.get_service_script(service=service, action=action)
        if not os.path.exists(script_file):
            raise saue.MissingFileError(file_path=script_file)

        btul.logging.info(
            f"⚙️ Running {action} for {service.name} (version: {service.version})",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Add the flag as env var to be consumed by the script
        env = os.environ.copy()
        env["SUBVORTEX_FLOATTING_FLAG"] = sauu.get_tag()

        try:
            subprocess.run(
                ["bash", script_file],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.CalledProcessError as e:
            raise saue.RuntimeError(action=action, details=str(e))

    def _pull_assets(self, version: str):
        # Download and unzip the latest version
        self.github.download_and_unzip_assets(
            version=version,
            role=sauc.SV_EXECUTION_ROLE,
        )

    def _remove_assets(self, version: str):
        # Build the asset directory
        asset_dir = saup.get_version_directory(version=version)
        if not os.path.exists(asset_dir):
            return

        # Remove the directory
        shutil.rmtree(asset_dir)

        # Notify the success
        btul.logging.info("Assets removed", prefix=sauc.SV_LOGGER_NAME)

    def _install_in_editable_mode(self):
        btul.logging.info(
            "Installating the subnet in editable mode", prefix=sauc.SV_LOGGER_NAME
        )

        # Get the version directory
        version_dir = saup.get_version_directory(version=self.latest_version)

        # Check if the pyproject is there
        if not os.path.exists(f"{version_dir}/pyproject.toml"):
            raise saue.MissingFileError(file_path=f"{version_dir}/pyproject.toml")

        # Install the subnet
        try:
            subprocess.run(
                ["pip", "install", "-e", "."],
                cwd=version_dir,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.CalledProcessError as e:
            raise saue.RuntimeError(action="install_editable", details=str(e))
