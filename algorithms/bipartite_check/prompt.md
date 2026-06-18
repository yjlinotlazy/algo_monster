# Bipartite Check

Determine whether an undirected graph is **bipartite** — i.e. its vertices can be partitioned into two disjoint sets such that every edge connects a vertex in one set to a vertex in the other.

```python
def is_bipartite(n: int, edges: list[tuple[int, int]]) -> bool:
    ...
```

## Input

- `n` — number of nodes (labelled 0 through n−1).
- `edges` — a list of undirected edge pairs `(u, v)`.

## Output

- Return `True` if the graph is bipartite.
- Return `False` if there exists any odd-length cycle (the graph cannot be 2-coloured).

## Algorithm

Use BFS/DFS to 2-colour the graph greedily. Start with an uncoloured node, colour it red, and alternate colours for neighbours. If any edge connects two nodes of the same colour, the graph is not bipartite.
