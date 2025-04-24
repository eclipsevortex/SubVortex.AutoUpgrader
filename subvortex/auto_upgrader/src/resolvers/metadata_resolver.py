import os
import json


class MetadataResolver:
    def __init__(self):
        pass

    def list_directory(self, path):
        return os.listdir(path)

    def is_directory(self, path: str):
        return os.path.isdir(path)

    def get_metadata(self, path: str):
        metadata_path = f"{path}/metadata.json"

        if not os.path.exists(metadata_path):
            return None

        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
