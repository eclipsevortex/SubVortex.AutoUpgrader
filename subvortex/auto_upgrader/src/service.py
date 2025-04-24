import subprocess
from pathlib import Path
from typing import List, Literal

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.link as saul


class Service:
    def __init__(
        self,
        id: str,
        name: str,
        version: str,
        execution: str,
        migration: str,
        migration_type: str,
        setup_command: str,
        start_command: str,
        stop_command: str,
        teardown_command: str,
        depends_on: List[str] = [],
    ):
        self.id = id
        self.name = name
        self.version = version
        self.execution = execution
        self.migration = migration
        self.migration_type = migration_type
        self.setup_command = setup_command
        self.start_command = start_command
        self.stop_command = stop_command
        self.teardown_command = teardown_command
        self.depends_on = depends_on
        self.needs_update = False
        self.must_remove = False
        self.upgrade_type = None
        self.rollback_version = None

    @staticmethod
    def create(metadata: dict):
        return Service(
            id=metadata.get("id"),
            name=metadata.get("name"),
            version=metadata.get("version"),
            execution=metadata.get("execution") or sauc.SV_EXECUTION_METHOD,
            migration=metadata.get("migration"),
            migration_type=metadata.get("migration_type"),
            setup_command=metadata.get("setup_command"),
            start_command=metadata.get("start_command"),
            stop_command=metadata.get("setup_command"),
            teardown_command=metadata.get("teardown_command"),
            depends_on=metadata.get("depends_on"),
        )

    def switch_to_version(self, version: str):
        btul.logging.info(
            f"🔀 [{self.name}] Switching to upgraded version.",
            prefix=sauc.SV_LOGGER_NAME,
        )

        # Get the root path of the version
        version_path = self._get_root_path(version=version)

        # Update the symlink
        saul.update_symlink(
            source=version_path,
            target=f"{sauc.SV_EXECUTION_DIR}",
        )

    def run_migration(self, kind: Literal["rollout", "rollback"]):
        pass

    def _run_cmd(self, command: str):
        if not command:
            return

        subprocess.run(command, shell=True, cwd=self.path, check=True)

    def _get_root_path(self, version: str):
        # Normalized the version
        normalized_version = sauv.normalize_version(version=version)

        return f"{sauc.SV_ASSET_DIR}/subvortex-{normalized_version}"

    def __str__(self):
        return (
            f"<Service {self.name} (id={self.id}, version={self.version}, "
            f"execution={self.execution}, needs_update={self.needs_update}, "
            f"must_remove={self.must_remove})>"
        )

    def __repr__(self):
        return self.__str__()
