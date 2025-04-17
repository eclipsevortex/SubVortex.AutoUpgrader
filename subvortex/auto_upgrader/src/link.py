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
import shutil
from pathlib import Path


def update_symlink(deploy_source: str, deploy_link: str):  # , temp_link: str):
    deploy_source: Path = Path(deploy_source).resolve()
    deploy_link: Path = Path(deploy_link)
    temp_link: Path = Path(f"{deploy_source}.tmp")

    # Create or update the temporary symlink
    if temp_link.exists() or temp_link.is_symlink():
        temp_link.unlink()
    temp_link.symlink_to(deploy_source)

    # Remove the old link or directory if it exists
    if deploy_link.exists() or deploy_link.is_symlink():
        if deploy_link.is_symlink() or deploy_link.is_file():
            deploy_link.unlink()
        else:
            shutil.rmtree(deploy_link)

    # Move temp symlink to final location
    temp_link.rename(deploy_link)


def remove_symlink(link: str):
    link: Path = Path(link)

    if not link.exists() and not link.is_symlink():
        return

    # Remove the link
    link.unlink()
