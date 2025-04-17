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
import json

import subvortex.auto_upgrader.src.constants as sauc

CACHE_PATH = f"{sauc.SV_ASSET_DIR}/.subvortex-cache"


def should_skip_version(version: str, release_time: str) -> bool:
    cache = _load_cache()
    if version in cache:
        cached = cache[version]
        return cached["status"] == "failed" and cached["timestamp"] == release_time
    return False


def mark_version_failed(version: str, release_time: str):
    cache = _load_cache()
    cache[version] = {"timestamp": release_time, "status": "failed"}
    _save_cache(cache)


def clear_version_status(version: str):
    cache = _load_cache()
    if version in cache:
        del cache[version]
        _save_cache(cache)


def _load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_cache(data):
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2)
