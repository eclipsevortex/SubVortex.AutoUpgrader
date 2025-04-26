import asyncio
import subprocess

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.utils as sauu


class Docker:
    def __init__(self):
        self.latest_versions = {}
        self.local_versions = {}

    async def get_latest_version(self):
        # Get the floating tag
        ftag = sauu.get_tag()

        # Get the list of images
        images = await self._get_images()

        # Get the images/digests of the current floating tag
        tasks = [
            self._get_digest_and_label(
                name=image.split("-")[-1], image=f"{image}:{ftag}"
            )
            for image in images
        ]
        results = await asyncio.gather(*tasks)

        # Merge the result
        merged_results = {}
        for result in results:
            merged_results.update(result)

        version = (
            next(iter(versions))
            if (versions := {v["version"] for v in merged_results.values()})
            and len(versions) == 1
            else None
        )
        merged_results["version"] = version

        self.latest_versions = merged_results
        btul.logging.debug(
            f"Latest versions: {self.latest_versions}", prefix=sauc.SV_LOGGER_NAME
        )

        return self.latest_versions["version"]

    async def get_local_version(self):
        versions = {}

        try:
            # Get the floating tag
            ftag = sauu.get_tag()

            # Step 1: List all local images with their tags
            result = subprocess.run(
                ["docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            images = result.stdout.strip().split("\n")

            # Step 2: Filter matching images
            for image in images:
                if ":" not in image:
                    continue

                # Build the image prefix
                prefix = f"subvortex/subvortex-{sauc.SV_EXECUTION_ROLE}-"

                repo, tag = image.rsplit(":", 1)
                if not repo.startswith(prefix) or tag != ftag:
                    continue

                repo_name = repo.replace("/subvortex", "")
                service_name = repo.replace(prefix, "")
                btul.logging.info(
                    f"SERVICE FROM IMAGE: {repo} / {prefix} / {service_name}"
                )

                local_versions = self._get_local_versions(repo_name=repo_name, tag=ftag)

                versions[service_name] = local_versions

        except subprocess.CalledProcessError as e:
            pass

        # Set the global version
        global_versions = list(set([x.get("version") for x in versions.values()]))
        versions["version"] = global_versions[0] if len(global_versions) > 0 else None

        # Store the versions
        self.local_versions = versions
        btul.logging.debug(
            f"Local versions: {self.local_versions}", prefix=sauc.SV_LOGGER_NAME
        )

        return self.local_versions["version"]

    def get_latest_service_version(self, name: str):
        # Get the default versions
        default_versions = self._get_default_versions(name=name)

        # Get the service versions
        versions = self.latest_versions.get(name, default_versions)

        return versions

    def get_local_service_version(self, name: str):
        # Get the default versions
        default_versions = self._get_default_versions(name=name)

        # Get the service versions
        versions = self.local_versions.get(name, default_versions)

        return versions

    async def _get_images(self):
        # Get all the images named subvortex
        proc_digest = await asyncio.create_subprocess_exec(
            "docker",
            "search",
            "subvortex",
            "--format",
            "{{.Name}}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_digest, _ = await proc_digest.communicate()

        # Get the image from the stdout
        images = stdout_digest.decode().splitlines()

        # Filter the image to take the one that follow our format
        images = [
            x
            for x in images
            if x.startswith(f"subvortex/subvortex-{sauc.SV_EXECUTION_ROLE}")
        ]

        return images

    async def _get_digest_and_label(self, name: str, image: str):
        component_version = f"{sauc.SV_EXECUTION_ROLE}.version"
        service_version = f"{sauc.SV_EXECUTION_ROLE}.{name}.version"

        # Get image quietly
        await asyncio.create_subprocess_exec(
            "docker",
            "pull",
            "--quiet",
            image,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        btul.logging.debug(f"Image {image} pulled", prefix=sauc.SV_LOGGER_NAME)

        # Get labels
        proc_labels = await asyncio.create_subprocess_exec(
            "docker",
            "inspect",
            image,
            "--format",
            f'version={{{{ index .Config.Labels "version" }}}} {component_version}={{{{ index .Config.Labels "{component_version}" }}}} {service_version}={{{{ index .Config.Labels "{service_version}" }}}}',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_labels, _ = await proc_labels.communicate()
        output = stdout_labels.decode()

        versions = dict(item.split("=", 1) for item in output.split())

        btul.logging.debug(
            f"Image version labels: {versions}", prefix=sauc.SV_LOGGER_NAME
        )

        return {name: versions}

    def _get_local_versions(self, repo_name: str, tag: str = "latest"):
        versions = {}

        component_name = repo_name.replace("subvortex-", "").split("-")[0]
        service_name = ".".join(repo_name.replace("subvortex-", "").split("-"))

        # Step 1: List all local images with their tags
        result = subprocess.run(
            [
                "docker",
                "inspect",
                "--format",
                f'version={{{{ index .Config.Labels "version" }}}} {component_name}.version={{{{ index .Config.Labels "{component_name}.version" }}}} {service_name}.version={{{{ index .Config.Labels "{service_name}.version" }}}}',
                repo_name,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if not result.stdout:
            return versions

        # Extract the output
        output = result.stdout.strip()
        if not output:
            return versions

        # Parse the output into a dictionary
        versions = dict(item.split("=", 1) for item in output.split())

        btul.logging.debug(
            f"Image version labels: {versions}", prefix=sauc.SV_LOGGER_NAME
        )

        return versions

    def _get_default_versions(self, name: str):
        component = sauc.SV_EXECUTION_ROLE
        service = f"{component}.{name}"
        return {
            "version": sauc.DEFAULT_LAST_RELEASE.get("global"),
            f"{component}.version": sauc.DEFAULT_LAST_RELEASE.get(component),
            service: sauc.DEFAULT_LAST_RELEASE.get(service),
        }
