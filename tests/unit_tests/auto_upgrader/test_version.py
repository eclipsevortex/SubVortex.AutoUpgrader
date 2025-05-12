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
import pytest

from subvortex.auto_upgrader.src.version import (
    normalize_version,
    denormalize_version,
)


@pytest.mark.parametrize(
    "input_version, expected",
    [
        ("v1.2.3", "1.2.3"),
        ("1.2.3", "1.2.3"),
        ("v1.2.3-alpha.1", "1.2.3a1"),
        ("v2.0.0-beta.5", "2.0.0b5"),
        ("1.0.0-rc.2", "1.0.0rc2"),
    ],
)
def test_normalize_version(input_version, expected):
    assert normalize_version(input_version) == expected


@pytest.mark.parametrize(
    "input_version, expected",
    [
        ("1.2.3", "1.2.3"),
        ("1.2.3a1", "1.2.3-alpha.1"),
        ("2.0.0b5", "2.0.0-beta.5"),
        ("1.0.0rc2", "1.0.0-rc.2"),
    ],
)
def test_denormalize_version(input_version, expected):
    assert denormalize_version(input_version) == expected
