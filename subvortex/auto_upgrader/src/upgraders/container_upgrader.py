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
import yaml
import typing
import shutil
import subprocess
from os import path
from packaging.version import Version

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.upgraders.base_upgrader as sauubu
import subvortex.auto_upgrader.src.migrator as saum
import subvortex.auto_upgrader.src.exception as saue
import subvortex.auto_upgrader.src.docker as saud
import subvortex.auto_upgrader.src.github as saug
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.link as saul


here = path.abspath(path.dirname(__file__))


class ContainerUpgrader(sauubu.BaseUpgrader):
    def __init__(self):
        self.github = saug.Github(repo_owner="eclipsevortex", repo_name="SubVortex")
        self.docker = saud.Docker()
        self.migrator = saum.Migrator()

        self.latest_versions = {}
        self.current_versions = {}

    def should_skip(self):
        return self.latest_versions.get("version") and self.current_versions.get(
            "version"
        )

    def is_upgrade(self, current_version: str, latest_version: str):
        return Version(current_version) < Version(latest_version)

    async def get_latest_version(self):
        # Get the tag configured
        tag = self._get_tag()

        # Get all the components
        components = self.github.get_components()

        # Get all the remote images with their digests
        # self.latest_versions = self.github.get_docker_versions(tag=tag)
        latest_versions = await self.docker.get_remote_versions(
            tag=tag,
            components=components,
            previous_version=self.latest_versions.get("version"),
        )

        # Set the latest version
        version = latest_versions.get("version") or sauc.DEFAULT_LAST_RELEASE["global"]

        if self.latest_versions == latest_versions:
            return version

        self.latest_versions = latest_versions

        if version == sauc.DEFAULT_LAST_RELEASE.get("global"):
            # Remove the previous version sym link
            self._remove_symlink()
        else:
            # Update the link to the new version
            self._update_symlink(version=version)

        return version

    def get_current_version(self):
        # Get the tag configured
        tag = self._get_tag()

        # Get all the local images with their digests
        self.current_versions = self.docker.get_local_versions(search_tag=tag)

        # return tag
        return (
            self.current_versions.get("version") or sauc.DEFAULT_LAST_RELEASE["global"]
        )

    def get_latest_components(self, version: str) -> typing.Dict[str, str]:
        components = {}

        target_path = self._get_target_path(version=version)

        for x, _ in self.latest_versions.items():
            if x == "version":
                continue

            name = x.replace(f"subvortex-{sauc.SV_EXECUTION_ROLE}-", "")
            components[name] = (
                f"{target_path}/subvortex/{sauc.SV_EXECUTION_ROLE}/{name}"
            )

        return components

    def get_current_components(self, version: str) -> typing.Dict[str, str]:
        components = {}

        target_path = self._get_target_path(version=version)

        for x, y in self.current_versions.items():
            if x == "version":
                continue

            name = x.replace(f"subvortex-{sauc.SV_EXECUTION_ROLE}-", "")
            components[name] = (
                f"{target_path}/subvortex/{sauc.SV_EXECUTION_ROLE}/{name}"
            )

        return components

    def get_latest_component_version(self, name: str, path: str):
        component_versions = self.latest_versions.get(name, {})
        return (
            component_versions.get("version")
            or sauc.DEFAULT_LAST_RELEASE[f"{sauc.SV_EXECUTION_ROLE}.{name}"]
        )

    def get_current_component_version(self, name: str, path: str):
        component_versions = self.current_versions.get(name, {})
        return (
            component_versions.get("version")
            or sauc.DEFAULT_LAST_RELEASE[f"{sauc.SV_EXECUTION_ROLE}.{name}"]
        )

    async def upgrade(self, path: str, name: str, previous_version: str, version: str):
        # Rollout the migration
        result, reason = await self.migrator.rollout(
            component_name=name,
            component_path=path,
            version=version,
            previous_version=previous_version,
        )
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not migrate the component {version}: {reason}",
            )

        target_path = self._get_target_path(version=version)

        if self.should_skip():
            return

        # Start the component
        result, reason = self._start_container(path=target_path, name=name)
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not start the component {name}: {reason}",
            )

    async def downgrade(
        self, path: str, name: str, previous_version: str, version: str
    ):
        # Get the previous version path
        normalized_version = sauv.normalize_version(version)
        normalized_previous_version = sauv.normalize_version(previous_version)
        previous_path = path.replace(normalized_version, normalized_previous_version)

        # Rollout the migration
        result, reason = await self.migrator.rollback(
            component_name=name,
            component_path=previous_path,
            version=version,
            previous_version=previous_version,
        )
        if not result:
            raise saue.ComponentException(
                component=name,
                message=f"Could not migrate the component {version}: {reason}",
            )

    def teardown(self, path: str, name: str):
        try:
            target_path = path.replace(sauc.SV_ASSET_DIR, "").split("/")[1]
            target_path = f"{sauc.SV_ASSET_DIR}/{target_path}"

            # Find the right command docker compose
            docker_cmd = self._detect_docker_command()

            # Set the service name
            service_name = f"{sauc.SV_EXECUTION_ROLE}-{name}"

            # Set the docker compose file
            file = (
                f"{target_path}/subvortex/{sauc.SV_EXECUTION_ROLE}/docker-compose.yml"
            )

            if not self._service_exists_in_compose(path=file, name=service_name):
                btul.logging.warning(
                    f"Service {service_name} not found in docker compose"
                )
                return

            env = os.environ.copy()
            env["SUBVORTEX_FLOATTING_FLAG"] = self._get_tag()

            cmd = docker_cmd + ["-f", file, "down", service_name, "--rmi", "all"]

            # Execute the script
            subprocess.run(
                cmd,
                env=env,
                check=True,
                text=True,
            )

        except subprocess.CalledProcessError as e:
            btul.logging.warning(
                f"[{name}] Could not teardown the service: {e}. Please manually stop it.",
                prefix=sauc.SV_LOGGER_NAME,
            )

    def pre_upgrade(self, path: str, name: str):
        btul.logging.info(f"pre_upgrade {name}: {path}")

        # Get the latest version
        latest_version, _ = self.github.get_latest_tag_including_prereleases()
        btul.logging.info(f"Docker compose from version: {latest_version}")

        # Download docker compose to the current version
        version = self.current_versions.get(name, {}).get("version")
        version = version or self.current_versions.get("version")
        self.github.download_docker_compose_from_tag(
            version=version, source_version=version
        )

        # Download docker compose to the latest version
        version = self.latest_versions.get(name, {}).get("version")
        version = version or self.latest_versions.get("version")
        self.github.download_docker_compose_from_tag(
            version=version, source_version=version
        )

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
        # Build the source
        source_env_file = os.path.join(
            here,
            f"../../environment/env.subvortex.{sauc.SV_EXECUTION_ROLE}.{component_name}",
        )

        # Ensure the download directory exists
        os.makedirs(component_path, exist_ok=True)

        # Build the target
        target_env_file = f"{component_path}/.env"

        # Copy the env file to its destination
        shutil.copy2(source_env_file, target_env_file)

    def _has_changed(self, name: str = None):
        if name:
            # Compare the digest for the requested repository
            return self.current_versions.get(name) != self.latest_versions.get(name)

        # Compare if a digest has changed among all the repository
        return self.current_versions != self.latest_versions

    def _get_deployment_dir(self, component_path: str):
        # Build the base script path
        return f"{component_path}/deployment/{sauc.SV_EXECUTION_METHOD}"

    def _get_tag(self):
        if "alpha" == sauc.SV_PRERELEASE_TYPE:
            return "dev"

        if "rc" == sauc.SV_PRERELEASE_TYPE:
            return "stable"

        return "latest"

    def _get_target_path(self, version: str):
        # Normalized the version
        normalized_version = sauv.normalize_version(version=version)

        # Build the archive name
        name = f"subvortex-{normalized_version}"

        # Build the target path
        target_path = os.path.join(sauc.SV_ASSET_DIR, name)

        # Ensure the download directory exists
        os.makedirs(target_path, exist_ok=True)

        return target_path

    def _detect_docker_command(self):
        if shutil.which("docker") is not None:
            try:
                subprocess.run(
                    ["docker", "compose", "version"],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return ["docker", "compose"]
            except subprocess.CalledProcessError:
                pass

        if shutil.which("docker-compose") is not None:
            return ["docker-compose"]

    def _start_container(self, path: str, name: str):
        try:
            docker_cmd = self._detect_docker_command()

            service_name = f"{sauc.SV_EXECUTION_ROLE}-{name}"
            compose_file = (
                f"{path}/subvortex/{sauc.SV_EXECUTION_ROLE}/docker-compose.yml"
            )
            container_name = (
                service_name  # Assumes container name is same as service_name
            )

            # Check if service exists in docker-compose file
            if not self._service_exists_in_compose(
                path=compose_file, name=service_name
            ):
                return False, "Service not found in docker compose"

            # Check if container already exists
            container_exists_cmd = ["docker", "ps", "-a", "--format", "{{.Names}}"]
            result = subprocess.run(
                container_exists_cmd, capture_output=True, text=True
            )

            if result.returncode != 0:
                return (
                    False,
                    f"Error checking existing containers: {result.stderr.strip()}",
                )

            container_names = result.stdout.strip().splitlines()
            container_exists = container_name in container_names

            tag = self._get_tag()
            env = os.environ.copy()
            env["SUBVORTEX_FLOATTING_FLAG"] = tag

            if container_exists:
                restart_cmd = ["docker", "restart", container_name]
                restart_result = subprocess.run(
                    restart_cmd, capture_output=True, text=True, env=env
                )
                if restart_result.returncode != 0:
                    return (
                        False,
                        f"Failed to restart container {container_name}: {restart_result.stderr.strip()}",
                    )
                return True, None

            # Run docker-compose up with pull and recreate
            cmd = docker_cmd + [
                "-f",
                compose_file,
                "up",
                service_name,
                "-d",
                "--pull",
                "always",
                "--force-recreate",
            ]

            result = subprocess.run(cmd, env=env, capture_output=True, text=True)

            if result.returncode != 0:
                stderr = result.stderr
                if "manifest for" in stderr and "not found" in stderr:
                    return (
                        False,
                        f"⚠️ Docker image for subvortex-{sauc.SV_EXECUTION_ROLE}-{service_name}:{tag} not found: {stderr.strip()}",
                    )
                return False, stderr.strip()

            return True, None

        except Exception as e:
            return False, f"Exception occurred: {str(e)}"

    def _start_container2(self, path: str, name: str):
        try:
            docker_cmd = self._detect_docker_command()

            service_name = f"{sauc.SV_EXECUTION_ROLE}-{name}"

            file = f"{path}/subvortex/{sauc.SV_EXECUTION_ROLE}/docker-compose.yml"

            if not self._service_exists_in_compose(path=file, name=service_name):
                return False, f"service not found in docker compose"

            tag = self._get_tag()

            env = os.environ.copy()
            env["SUBVORTEX_FLOATTING_FLAG"] = tag

            cmd = docker_cmd + [
                "-f",
                file,
                "up",
                service_name,
                "-d",
                "--pull",
                "always",
                "--force-recreate",
            ]

            # Execute the script
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                check=False,
                text=True,
            )

            if result.returncode != 0:
                stderr = result.stderr
                if "manifest for" in stderr and "not found" in stderr:
                    return (
                        False,
                        f"⚠️ Docker image for subvortex-{sauc.SV_EXECUTION_ROLE}-{service_name}:{tag} not found: {stderr.strip()}",
                    )

                return False, stderr.strip()

            return True, None

        except subprocess.CalledProcessError as e:
            return False, str(e)

    def _service_exists_in_compose(self, path: str, name: str) -> bool:
        if not os.path.exists(path):
            print(f"❌ Compose file not found: {path}")
            return False

        with open(path, "r", encoding="utf-8") as f:
            try:
                compose = yaml.safe_load(f)
                services = compose.get("services", {})
                return name in services
            except yaml.YAMLError as e:
                print(f"❌ YAML parsing error: {e}")
                return False

    def _remove_symlink(self):
        # Remove the link
        saul.remove_symlink(sauc.SV_EXECUTION_DIR)

        btul.logging.info(
            f"🔗 Symlink removed: {sauc.SV_EXECUTION_DIR}",
            prefix=sauc.SV_LOGGER_NAME,
        )

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
