"""Deterministic prerequisite validation for the fixed curriculum graph."""

from __future__ import annotations

from collections import deque
from typing import Mapping, Sequence


class DagError(RuntimeError):
    """Raised when curriculum prerequisites do not form a valid DAG."""


def topological_order(prerequisites: Mapping[str, Sequence[str]]) -> tuple[str, ...]:
    """Validate references and return a stable topological order."""

    node_ids = set(prerequisites)
    indegree = {node_id: 0 for node_id in node_ids}
    successors = {node_id: [] for node_id in node_ids}
    for node_id, required_ids in prerequisites.items():
        if len(set(required_ids)) != len(required_ids):
            raise DagError(f"duplicate prerequisite on {node_id}")
        for required_id in required_ids:
            if required_id not in node_ids:
                raise DagError(f"unknown prerequisite {required_id} on {node_id}")
            if required_id == node_id:
                raise DagError(f"problem cannot depend on itself: {node_id}")
            indegree[node_id] += 1
            successors[required_id].append(node_id)

    queue = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
    result: list[str] = []
    while queue:
        node_id = queue.popleft()
        result.append(node_id)
        for successor in sorted(successors[node_id]):
            indegree[successor] -= 1
            if indegree[successor] == 0:
                queue.append(successor)
    if len(result) != len(node_ids):
        cyclic = sorted(node_id for node_id, degree in indegree.items() if degree > 0)
        raise DagError(f"curriculum prerequisite cycle: {', '.join(cyclic)}")
    return tuple(result)
