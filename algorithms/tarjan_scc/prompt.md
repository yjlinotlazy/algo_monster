# Tarjan's Algorithm — Strongly Connected Components

Implement **Tarjan's algorithm** to find all strongly connected components (SCCs) in a directed graph.

A **strongly connected component** is a maximal set of vertices such that every vertex in the set can reach every other vertex in the set via directed paths. Vertices belonging to different SCCs form a DAG when collapsed.

Implement:

```python
def tarjan_scc(num_nodes: int, adj: list[list[int]]) -> list[list[int]]:
    ...
```

## Algorithm overview

Tarjan's algorithm uses a single DFS traversal with two arrays:
- `discovery[v]`: the time at which vertex `v` was first visited.
- `low_link[v]`: the smallest discovery time reachable from `v` (including itself) via tree edges and at most one back edge in the DFS tree.

During DFS, maintain a stack of vertices currently being explored. When a node `v` is popped off the stack and `low_link[v] == discovery[v]`, all nodes above `v` on the stack form one SCC (including `v` itself).

Time complexity: **O(V + E)**.

## Input

- `num_nodes`: total number of vertices, indexed 0 to num_nodes - 1.
- `adj`: adjacency list where `adj[u]` contains the list of neighbours reachable from vertex `u`.

## Output

Return a list of SCCs. Each SCC is a list of vertex indices. The order of SCCs in the returned list does not matter, and the order within each SCC does not matter.
