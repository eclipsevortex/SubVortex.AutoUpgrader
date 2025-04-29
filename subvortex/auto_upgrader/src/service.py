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
import subprocess
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
        component_version: str,
        service_version: str,
        execution: str,
        migration: str,
        setup_command: str,
        start_command: str,
        stop_command: str,
        teardown_command: str,
        depends_on: List[str] = [],
        migration_type: str = None,
    ):
        self.id = id
        self.name = name
        self.version = version
        self.component_version = component_version
        self.service_version = service_version
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
        service_name = metadata.get("id").split("-")[-1]
        component_version = metadata.get(f"{sauc.SV_EXECUTION_ROLE}.version")
        service_version = metadata.get(f"{sauc.SV_EXECUTION_ROLE}.{service_name}.version")
        return Service(
            id=metadata.get("id"),
            name=metadata.get("name"),
            version=metadata.get("version"),
            component_version=component_version,
            service_version=service_version,
            execution=metadata.get("execution") or sauc.SV_EXECUTION_METHOD,
            migration=metadata.get("migration"),
            migration_type=metadata.get("migration_type"),
            setup_command=metadata.get("setup_command"),
            start_command=metadata.get("start_command"),
            stop_command=metadata.get("setup_command"),
            teardown_command=metadata.get("teardown_command"),
            depends_on=metadata.get("depends_on"),
        )

    @property
    def role(self):
        if not self.id or not self.version:
            return None

        # Details of the id
        details = self.id.split("-")

        return details[-2]

    @property
    def key(self):
        if not self.id or not self.version:
            return None

        # Details of the id
        details = self.id.split("-")

        return details[-1]

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
            f"component_version={self.component_version}, service_version={self.service_version}, "
            f"execution={self.execution}, needs_update={self.needs_update}, must_remove={self.must_remove}, "
            f"migration={self.migration}, migration_type={self.migration_type}, "
            f"depends_on={self.depends_on})>"
        )

    def __repr__(self):
        return self.__str__()
