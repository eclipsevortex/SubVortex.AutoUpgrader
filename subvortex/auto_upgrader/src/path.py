import os
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


def get_service_directory(service: saus.Service):
    if not service.version:
        return None
    
    # Get the version directory
    version_path = get_version_directory(version=service.version)

    # Build the path of the role (miner/validator) directory
    path = f"{version_path}/subvortex/{sauc.SV_EXECUTION_ROLE}/{service.key}"

    return path


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


def get_service_script(service: saus.Service, action: str):
    if not service.version:
        return None
    
    # Get the version directory
    service_dir = get_service_directory(service=service)

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
