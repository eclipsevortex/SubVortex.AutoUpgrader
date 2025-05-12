# The MIT License (MIT)
# Copyright © 2024 Eclipse Vortex

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
import glob
from os import path

import subvortex.auto_upgrader.src.constants as sauc
import subvortex.auto_upgrader.src.version as sauv
import subvortex.auto_upgrader.src.service as saus

here = path.abspath(path.dirname(__file__))


def get_version_directory(version: str):
    if not version:
        return None

    # Get the normalized version
    normalized_version = sauv.normalize_version(version)

    # Buid the path of the the version directory
    path = f"{sauc.SV_ASSET_DIR}/subvortex-{normalized_version}"

    return path


def get_role_directory(version: str):
    if not version:
        return None

    # Get the version directory
    version_path = get_version_directory(version=version)

    # Build the path of the role (miner/validator) directory
    path = f"{version_path}/subvortex/{sauc.SV_EXECUTION_ROLE}"

    return path


def get_service_template(service: saus.Service, version: str = None):
    if not service.version:
        return None

    # Get the version directory
    version_path = get_version_directory(version=version or service.version)

    # Build the path of the role (miner/validator) directory
    path = f"{version_path}/subvortex/{sauc.SV_EXECUTION_ROLE}/{service.key}/deployment/templates"

    return path


def get_service_directory(
    service: saus.Service, version: str = None #, use_version_dir: bool = False
):
    if not service.version:
        return None

    # Get the version directory
    version_path = (
        get_version_directory(version=version or service.version)
        # if use_version_dir
        # else sauc.SV_EXECUTION_DIR
    )

    # Build the path of the role (miner/validator) directory
    path = f"{version_path}/subvortex/{sauc.SV_EXECUTION_ROLE}/{service.key}"

    return path


def get_au_template_files():
    # Build the template directory
    template_dir = os.path.join(here, "../template")

    # Match all files that start with 'template-'
    pattern = os.path.join(template_dir, "template-*")

    # Return all matching template files
    return glob.glob(pattern)


def get_au_environment_file(service: saus.Service):
    # Build the env directory
    env_dir = os.path.join(here, "../environment")

    # Build the env file path for the service
    path = os.path.join(env_dir, f"env.subvortex.{service.role}.{service.key}")

    return path


def get_environment_file(service: saus.Service):
    if not service.version:
        return None

    # Build the env directory
    service_dir = get_service_directory(service=service)

    # Build the env file path for the service
    path = os.path.join(service_dir, ".env")

    return path


def get_migration_directory(service: saus.Service):
    if not service.version:
        return None

    # Get the version directory
    service_dir = get_service_directory(service=service)

    # Build the path of the script
    path = os.path.join(service_dir, service.migration)

    return path


def get_service_script(
    service: saus.Service,
    action: str,
    version: str = None,
    # use_version_dir: bool = False,
):
    if not service.version:
        return None

    # Get the version directory
    service_dir = get_service_directory(
        service=service, version=version#, use_version_dir=use_version_dir
    )

    # Get the execution method
    # TODO: rename docker to container in SubVOrtex to remove the following
    method = (
        "docker"
        if sauc.SV_EXECUTION_METHOD == "container"
        else sauc.SV_EXECUTION_METHOD
    )

    # Build script name
    script_name = f"{service.key}_{method}_{action}.sh"

    # Build the path of the script
    path = os.path.join(service_dir, "deployment", method, script_name)

    return path
