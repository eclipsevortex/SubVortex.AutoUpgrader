import os
import shutil
import traceback
from typing import List, Tuple, Callable
from packaging.version import Version

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.service as saus
import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.resolvers.dependency_resolver as saudr
import subvortex.auto_upgrader.src.github as saug
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.resolvers.metadata_resolver as saumr
from subvortex.auto_upgrader.src.migrations.base import Migration
from subvortex.auto_upgrader.src.migration_manager import MigrationManager


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
        btul.logging.info("Runing the plan...", prefix=sauc.SV_LOGGER_NAME)

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

        # Pull the assets of the latest version for the neuron
        self._step(
            "Pull current version",
            self._rollback_nop,
            self._pull_current_version,
        )

        # Pull the assets of the latest version for the neuron
        self._step(
            "Pull latest version",
            self._rollback_pull_latest_version,
            self._pull_latest_version,
        )

        if self.current_version == self.latest_version:
            btul.logging.info(
                "No new release available. All services are up-to-date.",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return

        # Set the action
        action = "upgade" if self.current_version < self.latest_version else "downgrade"

        # Load the services of the latest version
        self._step(
            "Load current services", self._rollback_nop, self._load_current_services
        )

        # Load the services of the latest version
        self._step(
            "Load latest services", self._rollback_nop, self._load_latest_services
        )

        # Get the execution of the latest version
        execution = self._get_execution()

        # Check the latest version and the current one
        self._step("Check versions", self._rollback_nop, self._check_versions)

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
            condition=lambda: execution != "container",
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
            condition=lambda: execution != "container",
        )

        # Finalize service versions
        self._step(
            "Finalize service versions",
            self._rollback_nop,
            self._finalize_versions,
        )

        btul.logging.success("Plan executed succesfully", prefix=sauc.SV_LOGGER_NAME)

    def run_rollback_plan(self):
        for desc, rollback_func in reversed(self.rollback_steps):
            btul.logging.info(f"Rolling back: {desc}", prefix=sauc.SV_LOGGER_NAME)
            try:
                rollback_func()
            except Exception as e:
                btul.logging.error(
                    f"Failed to rollback {desc}: {e}", prefix=sauc.SV_LOGGER_NAME
                )
                btul.logging.debug(traceback.format_exc())

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

        btul.logging.debug(f"▶️ Starting: {description}", prefix=sauc.SV_LOGGER_NAME)
        self.rollback_steps.append((description, rollback_func))

        if service_filter:
            action_func(service_filter=service_filter)
        else:
            action_func()

    def _rollback_nop(self):
        pass  # For steps that don't change state

    def _get_current_version(self):
        # Get the latest version
        self.current_version = sauv.get_local_version() or sauc.DEFAULT_LAST_RELEASE["global"]

        btul.logging.debug(
            f"Current version: {self.current_version}", prefix=sauc.SV_LOGGER_NAME
        )

    def _get_latest_version(self):
        # Get the latest version
        self.latest_version = self.github.get_latest_version()

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

        btul.logging.debug("Latest assets pulled", prefix=sauc.SV_LOGGER_NAME)

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
            f"Current services loaded: {','.join(services)}", prefix=sauc.SV_LOGGER_NAME
        )

    def _load_latest_services(self):
        # Load the services of the latest version
        self.latest_services = self._load_services(self.latest_version)

        # Display the list of services
        services = [x.name for x in self.current_services]
        btul.logging.debug(
            f"Latest services loaded: {','.join(services)}", prefix=sauc.SV_LOGGER_NAME
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
                    f"{current} no longer exists in latest release. Marked for removal.",
                    prefix=sauc.SV_LOGGER_NAME,
                )
                self.services.append(current)
                continue

            if latest and not current:
                # New service in latest
                latest.needs_update = True
                latest.upgrade_type = "install"
                btul.logging.info(
                    f"{latest} is a new service in latest version. Marked for installation.",
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
                    f"{latest} version change detected: {current.version} -> {latest.version} ({latest.upgrade_type})",
                    prefix=sauc.SV_LOGGER_NAME,
                )
            else:
                latest.needs_update = False
                latest.upgrade_type = None
                btul.logging.info(
                    f"{latest} is already up-to-date at version {latest.version}.",
                    prefix=sauc.SV_LOGGER_NAME,
                )

            # Set the previous version for the latest service
            # latest.previous_version = current.version

            self.services.append(latest)

    def _rollout_service(self):
        # Create the dependency resolver
        dependency_resolver = saudr.DependencyResolver(services=self.latest_services)

        # Sort the services
        sorted_services = dependency_resolver.resolve_order()

        for service in sorted_services:
            if not service.needs_update:
                continue

            if False and not self._can_rollout_service(service):
                continue

            # Execute the setup
            self._execute_setup(service=service)

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
                        f"🔄 Skipping {service}: container already running.",
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
            current_service = next(
                (x for x in self.current_services if x.id == service.id), None
            )
            if not current_service:
                continue

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

        # Get the normalized version
        normalized_version = sauv.normalize_version(version)

        # Determine the neuron directory where to find all the services
        path = f"{sauc.SV_WORKING_DIRECTORY}/subvortex-{normalized_version}/subvortex/{sauc.SV_EXECUTION_ROLE}"

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
        setup_script = os.path.join(
            sauc.SV_WORKING_DIRECTORY,
            service.teardown_command if rollback else service.setup_command,
        )

        # Check if the script exist
        if not os.path.exists(setup_script):
            btul.logging.warning(
                f"⚠️ No {action}.sh found for {service}. Skipping.",
                prefix=sauc.SV_LOGGER_NAME,
            )
            return

        btul.logging.info(
            f"⚙️ Running {action} for {service} (version: {service.version})",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Execute the script
        result = os.system(f"bash {setup_script}")
        if result != 0:
            raise RuntimeError(f"{action}.sh failed for {service}")

    def _pull_assets(self, version: str):
        # Get the denormalized version
        denormalized_version = sauv.denormalize_version(version=version)

        # Download and unzip the latest version
        self.github.download_and_unzip_assets(
            version=denormalized_version,
            role=sauc.SV_EXECUTION_ROLE,
        )

    def _remove_assets(self, version: str):
        # Get the normalized version
        normalized_version = sauv.normalize_version(version=version)

        # Build the asset directory
        asset_dir = f"{sauc.SV_WORKING_DIRECTORY}/subvortex-{normalized_version}"

        if not os.path.exists(asset_dir):
            return

        # Remove the directory
        shutil.rmtree(asset_dir)

        # Notify the success
        btul.logging.info("Assets removed", prefix=sauc.SV_LOGGER_NAME)

    def _get_execution(self):
        # Get the list of execution for each service
        executions = [x.execution for x in self.latest_services]

        # For now all the execution will be same and come from the auto upgrader env var `SUBVORTEX_EXECUTION_METHOD`
        return executions[0]
