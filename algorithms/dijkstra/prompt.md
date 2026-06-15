# Dijkstra's Algorithm — Shortest Path in Weighted Graph

Implement **Dijkstra's shortest path** algorithm to find the minimum distance from a source vertex to all other vertices in a directed graph with non-negative edge weights.

```python
def dijkstra(n: int, edges: list[tuple[int, int, int]], src: int) -> list[float]:
    ...
```

## Input

- `n`: number of vertices, indexed 0 to n - 1.
- `edges`: list of `(u, v, w)` tuples representing a directed edge from `u` to `v` with weight `w`.
- `src`: the source vertex index.

All edge weights are non-negative integers. The graph may be disconnected — unreachable vertices should have distance `inf`. Self-loops and parallel edges may appear; handle them correctly (use the shorter edge when there are duplicates).

## Output

Return a list of length `n` where each element is the shortest distance from `src` to that vertex. Use `float('inf')` for unreachable vertices. The distance to the source itself should be `0`.
