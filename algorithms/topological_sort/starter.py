from collections import deque


def topological_sort(graph: dict[int, list[int]]) -> list[int] | None:
    """Return a topological ordering of the DAG, or ``None`` if a cycle exists.

    Uses Kahn's BFS algorithm.  Nodes that appear only as neighbours (not as keys)
    are included in the output.  Ties at each step are broken by smallest node ID first.
    """
    ...
