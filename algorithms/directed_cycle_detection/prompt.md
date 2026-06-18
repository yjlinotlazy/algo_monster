# Directed Cycle Detection

Implement **cycle detection** in a directed graph using DFS with three-colour marking.

```python
def has_cycle(graph: dict[int, list[int]]) -> bool:
    ...
```

## Input

`graph` is an adjacency list where keys are node IDs and values are lists of outgoing neighbour node IDs.
Nodes that appear only as neighbours (not as keys) should be treated as having no outgoing edges.

## Output

- Return `True` if the graph contains at least one directed cycle.
- Return `False` otherwise (the graph is a DAG).

## Algorithm

Use DFS with three colours for each node:

- **WHITE** (0): not yet visited
- **GREY** (1): currently on the recursion stack
- **BLACK** (2): fully processed

A cycle exists iff during DFS we encounter an edge to a GREY node.
