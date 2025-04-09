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
import json
import base64
import typing
import requests
import subprocess

import bittensor.utils.btlogging as btul

import subvortex.auto_upgrader.src.constants as sauc


class Docker:
    def __init__(self):
        self.cache = {}

    def get_local_versions(
        self, search_tag: str, namespace: str = "subvortex"
    ) -> typing.Dict[str, str]:
        """
        Returns a dictionary mapping full image names (namespace/name) to their digest
        for images matching the given prefix and tag.
        """
        versions = {}

        try:
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
                prefix = f"{namespace}/subvortex-{sauc.SV_EXECUTION_ROLE}-"

                repo, tag = image.rsplit(":", 1)
                if not repo.startswith(prefix) or tag != search_tag:
                    continue

                service_name = repo.replace("subvortex/", "")

                local_versions = self._get_local_versions(
                    repo_name=service_name, tag=search_tag
                )

                versions[service_name] = local_versions

        except subprocess.CalledProcessError as e:
            pass

        # Set the global version
        global_versions = list(set([x.get("version") for x in versions.values()]))
        versions["version"] = global_versions[0] if len(global_versions) > 0 else None

        return versions

    def get_base64_digest_summary(
        self, prefix: str, search_tag: str, max_length=15
    ) -> str:
        try:
            # Step 1: Get all local images
            result = subprocess.run(
                ["docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            images = result.stdout.strip().split("\n")

            # Step 2: Filter images that match the prefix
            matching_images = []
            for image in images:
                if ":" not in image:
                    continue
                repo, tag = image.rsplit(":", 1)
                if repo.startswith(prefix) and tag == search_tag:
                    matching_images.append(f"{repo}:{tag}")

            if not matching_images:
                return "no-matching-images"

            # Step 3: Inspect and collect digests
            digests = []
            for image in matching_images:
                try:
                    inspect_result = subprocess.run(
                        [
                            "docker",
                            "image",
                            "inspect",
                            "--format={{json .RepoDigests}}",
                            image,
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                    )
                    repo_digests = json.loads(inspect_result.stdout)
                    if repo_digests:
                        # Extract just the digest (after '@')
                        for digest in repo_digests:
                            match = re.search(r"@(.+)", digest)
                            if match:
                                digests.append(match.group(1))
                except subprocess.CalledProcessError:
                    continue  # Skip images that error

            if not digests:
                return "no-digests-found"

            # Step 4: Join and base64-encode
            digest_str = ",".join(sorted(set(digests)))
            encoded = base64.urlsafe_b64encode(digest_str.encode()).decode()

            # Step 5: Return first max_length characters
            return encoded[:max_length]

        except subprocess.CalledProcessError as e:
            return f"error: {e.stderr.strip()}"

    def get_local_docker_digest(image_tag: str) -> str:
        """
        Returns the RepoDigest of a local Docker image (e.g., 'subvortex/subvortex-miner-neuron:latest').

        If the image was never pulled or pushed, the digest may not be available.
        """
        try:
            result = subprocess.run(
                [
                    "docker",
                    "image",
                    "inspect",
                    "--format={{index .RepoDigests 0}}",
                    image_tag,
                ],
                text=True,
                check=True,
            )
            digest = result.stdout.strip()
            if not digest:
                return (
                    None,
                    f"No RepoDigest found for image '{image_tag}' — was it pulled or pushed?",
                )

            return digest, None
        except subprocess.CalledProcessError as e:
            return None, str(e)

    def _is_docker_tax_exists(self, service: str):
        # Create the url to check if the tag exist in docker hub
        url = f"https://hub.docker.com/v2/repositories/subvortex/subvortex-{sauc.SV_EXECUTION_ROLE}-{service}/tags/{sauc.SV_PRERELEASE_TYPE}"

        # Send the request
        response = requests.get(url)

        return response.status_code == 200

    def _get_local_versions(self, repo_name: str, tag: str = "latest"):
        versions = {}

        try:
            # Step 1: List all local images with their tags
            result = subprocess.run(
                [
                    "docker",
                    "inspect",
                    "--format",
                    f'version={{{{ index .Config.Labels "version" }}}} {sauc.SV_EXECUTION_ROLE}.version={{{{ index .Config.Labels "miner.version" }}}}',
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

        except subprocess.CalledProcessError as e:
            print(e)

        return versions
