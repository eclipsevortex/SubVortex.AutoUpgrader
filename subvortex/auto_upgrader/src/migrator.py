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
import re
import os
import sys
import importlib
from os import path

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.version as sauv

LOGGER_NAME = "Migrator"

here = path.abspath(path.dirname(__file__))


class Migrator:
    """
    Executes post-upgrade transformations (e.g. DB schema, Redis keys, config rewrites).
    """

    async def rollout(
        self,
        component_name: str,
        component_path: str,
        version: str,
        previous_version: str,
    ) -> tuple[bool, str | None]:
        # Build the path to the directory containing migration versions
        latest_path = f"{component_path}/migrations/versions"

        # Convert any version into a release version
        release_version = sauv.to_spec_version(version)
        previous_release_version = sauv.to_spec_version(previous_version)

        # True if it is the same version
        same_version = release_version == previous_release_version

        # Get the list of migration files that need to be applied
        btul.logging.debug(
            f"[{component_name}] Searching migrations between {'>=' if same_version else '>'} {previous_release_version} and <= {release_version}",
            prefix=self._get_log_prefix(),
        )
        migrations = self._get_migrations(
            path=latest_path,
            filter_lambda=lambda x: (
                (x[0] > (previous_release_version or 0) and x[0] <= release_version)
                if not same_version
                else x[0] == (previous_release_version or 0)
            ),
        )

        btul.logging.info(
            f"[{component_name}] Migrations {migrations}",
            prefix=self._get_log_prefix(),
        )

        # True if we have to rollback as it it the same version. It happens when releasing pre release
        try:
            # Apply each migration in order
            for migration in migrations:
                module = self._load_migration_from_file(f"{latest_path}/{migration[2]}")
                if not module:
                    continue

                btul.logging.info(
                    f"[{component_name}] Applying migration {migration[1]}",
                    prefix=self._get_log_prefix(),
                )

                # Create instance of the migration
                instance = module()

                if same_version:
                    await instance.rollback()

                # Execute the rollback function defined in the migration module
                await instance.rollout()

            return True, None  # Migration succeeded

        except Exception as e:
            # Log and return failure if any migration step fails
            btul.logging.error(
                f"[{component_name}] ❌ Migration failed: {e}",
                prefix=self._get_log_prefix(),
            )
            return False, str(e)

    async def rollback(
        self,
        component_name: str,
        component_path: str,
        version: str,
        previous_version: str,
    ):
        # Build the path to the directory containing migration versions
        latest_path = f"{component_path}/migrations/versions"

        # Convert any version into a release version
        release_version = sauv.to_spec_version(version)
        previous_release_version = sauv.to_spec_version(previous_version)

        # True if it is the same version
        same_version = release_version == previous_release_version

        # Get the migration(s) matching the specified version, in reverse order
        btul.logging.debug(
            f"[{component_name}] Searching migrations between {'>=' if same_version else '>'} {release_version} and <= {previous_release_version}",
            prefix=self._get_log_prefix(),
        )
        migrations = self._get_migrations(
            reverse=True,
            path=latest_path,
            filter_lambda=lambda x: (
                (x[0] > (release_version or 0) and x[0] <= previous_release_version)
                if not same_version
                else x[0] == (previous_release_version or 0)
            ),
        )

        btul.logging.info(
            f"[{component_name}] Migrations {migrations}",
            prefix=self._get_log_prefix(),
        )

        try:
            # Apply rollback for each migration matching the version
            for migration in migrations:
                module = self._load_migration_from_file(f"{latest_path}/{migration[2]}")
                if not module:
                    continue  # Skip if loading fails

                btul.logging.info(
                    f"Applying migration {migration[1]}",
                    prefix=self._get_log_prefix(),
                )

                # Create instance of the migration
                instance = module()

                # Execute the rollback function defined in the migration module
                await instance.rollback()

            return True, None  # Rollback succeeded

        except Exception as e:
            # Log and return failure if rollback fails
            btul.logging.error(
                f"[{component_name}] ❌ Migration failed: {e}",
                prefix=self._get_log_prefix(),
            )
            return False, str(e)

    def _get_migrations(self, path: str, reverse=False, filter_lambda=None):
        migrations = []

        try:
            if not os.path.exists(path):
                return migrations

            files = os.listdir(path)
            for file in files:
                match = re.match(r"migration-([0-9]+\.[0-9]+\.[0-9]+)\.py", file)
                if not match:
                    continue

                # Get the version
                version = match.group(1)

                # Get the specification version
                spec_version = sauv.to_spec_version(match.group(1))

                # Add the version
                migrations.append((spec_version, version, file))

            if filter_lambda:
                migrations = list(filter(filter_lambda, migrations))

            migrations = sorted(migrations, key=lambda x: x[0], reverse=reverse)

        except Exception as ex:
            btul.logging.error(
                f"Could not load the migrations: {ex}",
                prefix=self._get_log_prefix(),
            )

        return migrations

    def _get_log_prefix(self):
        return f"[{sauc.SV_LOGGER_NAME}][{LOGGER_NAME}]"

    def _load_migration_from_file(self, filepath: str):
        # Ensure project root is in sys.path
        if sauc.SV_EXECUTION_DIR not in sys.path:
            sys.path.insert(0, sauc.SV_EXECUTION_DIR)

        module_name = os.path.splitext(os.path.basename(filepath))[0]
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        if not spec or not spec.loader:
            btul.logging.error(
                f"Failed to load migration spec for: {filepath}",
                prefix=self._get_log_prefix(),
            )
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Extract the Migration class
        migration_class = getattr(module, "Migration", None)
        if migration_class is None:
            btul.logging.error(
                f"No 'Migration' class found in: {filepath}",
                prefix=self._get_log_prefix(),
            )
            return None

        return migration_class
