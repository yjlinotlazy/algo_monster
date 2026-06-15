# Edmonds-Karp — Maximum Flow

Implement the **Edmonds-Karp algorithm** to find the maximum flow from a source node to a sink node in a directed graph with edge capacities.

The graph is represented as an adjacency matrix where `capacity[u][v]` is the capacity of the edge from node `u` to node `v`. A value of `0` means no edge exists.

Implement:

```python
def edmonds_karp(capacity: list[list[int]], source: int, sink: int) -> int:
    ...
```

## Algorithm overview

Edmonds-Karp is a specialisation of Ford-Fulkerson that uses **BFS** to find the shortest augmenting path (in terms of number of edges) at each step. This guarantees termination and gives an overall time complexity of **O(V · E²)**.

Key ideas:
- Build a **residual graph**: for each edge `(u, v)` with capacity `C` and flow `f`, the residual capacity from `u → v` is `C - f`, and from `v → u` it is `f`.
- Repeatedly BFS from `source` to `sink` in the residual graph. If a path exists, push as much flow as possible along that path (the minimum residual capacity on the path).
- Update the residual graph and repeat until no augmenting path exists.
- The **max-flow min-cut theorem** guarantees that when no augmenting path remains, the total flow equals the minimum cut capacity.

## Input

- `capacity`: a square matrix of non-negative integers where `capacity[u][v]` is the capacity from node `u` to node `v`.
- `source`: the index of the source node.
- `sink`: the index of the sink node.

## Output

Return the maximum flow value (an integer).
