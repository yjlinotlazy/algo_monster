# Connected Components (Undirected Graph)

Find all **connected components** in an undirected graph using BFS.

```python
def connected_components(n: int, edges: list[tuple[int, int]]) -> list[list[int]]:
    ...
```

## Input

- `n` — the number of nodes (labelled 0 through n−1).
- `edges` — a list of undirected edge pairs `(u, v)`.

## Output

Return a list of connected components, where each component is a sorted list of node IDs belonging to that component. Components should be ordered by their smallest member.

## Examples

```python
# 6 nodes, edges form: 0-1, 2-3, 4-5
connected_components(6, [(0, 1), (2, 3), (4, 5)])
# → [[0, 1], [2, 3], [4, 5]]

# Isolated node:
connected_components(3, [(0, 1)])
# → [[0, 1], [2]]
```

## Invariants

- Every node from 0 to n−1 appears in exactly one component.
- Each component list is sorted ascending.
- The returned list of components is ordered by each component's minimum node ID.
