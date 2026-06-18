# Topological Sort

Implement **topological sort** for a directed acyclic graph (DAG) using Kahn's algorithm (BFS-based).

```python
def topological_sort(graph: dict[int, list[int]]) -> list[int] | None:
    ...
```

## Input

`graph` is an adjacency list where keys are node IDs and values are lists of outgoing neighbour node IDs.

## Output

- Return a list of node IDs such that for every directed edge `u → v`, `u` appears before `v` in the result.
- Return `None` if the graph contains a cycle (no valid topological ordering exists).

## Invariants

- Every node that appears as a key in *graph* must appear in the output, even if it has no outgoing edges.
- When multiple nodes have zero in-degree simultaneously, prefer them by their natural order (smallest ID first).
- A graph with only isolated nodes should return all nodes sorted by value.
