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
