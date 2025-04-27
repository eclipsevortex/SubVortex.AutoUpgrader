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
from typing import List
from collections import defaultdict, deque

import subvortex.auto_upgrader.src.service as saus


class DependencyResolver:
    def __init__(self, services: List[saus.Service]):
        self.services = {s.id: s for s in services}
        self.graph = defaultdict(list)
        self.indegree = defaultdict(int)
        self._build_graph()

    def _build_graph(self):
        for service in self.services.values():
            for dep in getattr(service, "depends_on", []):
                self.graph[dep].append(service.id)
                self.indegree[service.id] += 1
            if service.id not in self.indegree:
                self.indegree[service.id] = 0

    def resolve_order(self, reverse=False) -> List[saus.Service]:
        queue = deque([sid for sid in self.services if self.indegree[sid] == 0])
        ordered_ids = []

        while queue:
            sid = queue.popleft()
            ordered_ids.append(sid)
            for neighbor in self.graph[sid]:
                self.indegree[neighbor] -= 1
                if self.indegree[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered_ids) != len(self.services):
            raise Exception("Cyclic dependency detected!")

        if reverse:
            ordered_ids.reverse()

        return [self.services[sid] for sid in ordered_ids]
