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
import pytest
from subvortex.auto_upgrader.src.service import Service
from subvortex.auto_upgrader.src.resolvers.dependency_resolver import DependencyResolver

def create_service(id, depends_on=None):
    return Service(
        id=id,
        name=f"service-{id}",
        version="1.0.0",
        component_version="1.0.0",
        service_version="1.0.0",
        execution="process",
        migration="",
        setup_command="",
        start_command="",
        stop_command="",
        teardown_command="",
        depends_on=depends_on or [],
    )


def test_no_dependencies():
    services = [create_service("a"), create_service("b"), create_service("c")]
    resolver = DependencyResolver(services)
    ordered = resolver.resolve_order()
    assert sorted([s.id for s in ordered]) == ["a", "b", "c"]


def test_linear_dependencies():
    services = [
        create_service("a"),
        create_service("b", depends_on=["a"]),
        create_service("c", depends_on=["b"]),
    ]
    resolver = DependencyResolver(services)
    ordered = resolver.resolve_order()
    assert [s.id for s in ordered] == ["a", "b", "c"]


def test_branching_dependencies():
    services = [
        create_service("a"),
        create_service("b", depends_on=["a"]),
        create_service("c", depends_on=["a"]),
        create_service("d", depends_on=["b", "c"]),
    ]
    resolver = DependencyResolver(services)
    ordered = resolver.resolve_order()
    assert [s.id for s in ordered] == ["a", "b", "c", "d"] or ["a", "c", "b", "d"]


def test_reverse_order():
    services = [
        create_service("a"),
        create_service("b", depends_on=["a"]),
        create_service("c", depends_on=["b"]),
    ]
    resolver = DependencyResolver(services)
    ordered = resolver.resolve_order(reverse=True)
    assert [s.id for s in ordered] == ["c", "b", "a"]


def test_detects_cycles():
    services = [
        create_service("a", depends_on=["c"]),
        create_service("b", depends_on=["a"]),
        create_service("c", depends_on=["b"]),
    ]
    resolver = DependencyResolver(services)
    with pytest.raises(Exception, match="Cyclic dependency detected"):
        resolver.resolve_order()
