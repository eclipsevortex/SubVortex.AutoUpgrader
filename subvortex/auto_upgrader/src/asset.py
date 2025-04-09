import os
import tarfile

import subvortex.auto_upgrader.src.constants as sauc


def unzip_asset(path: str):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Archive not found: {path}")

    # Ensure the directory exists
    os.makedirs(sauc.SV_ASSET_DIR, exist_ok=True)

    # Extract archive
    with tarfile.open(path, "r:gz") as tar:
        # Get top-level directory from the first member
        top_level_dirs = {
            member.name.split("/")[0]
            for member in tar.getmembers()
            if member.name and "/" in member.name
        }

        if not top_level_dirs:
            raise ValueError("Could not determine top-level directory from archive.")

        top_level_dir = sorted(top_level_dirs)[0]  # In case there's more than one

        # Extract to the asset dir
        tar.extractall(path=sauc.SV_ASSET_DIR)

    return os.path.join(sauc.SV_ASSET_DIR, top_level_dir)
