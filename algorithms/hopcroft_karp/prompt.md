# Hopcroft-Karp — Maximum Bipartite Matching

Implement the **Hopcroft-Karp algorithm** to find the maximum cardinality matching in a bipartite graph.

A **bipartite graph** has two disjoint sets of vertices `L` (left, indexed 0..left_size-1) and `R` (right, indexed 0..right_size-1). Edges only go between the two sets, never within one set. A **matching** is a subset of edges such that no two edges share an endpoint. The **maximum matching** has the largest possible size.

Implement:

```python
def hopcroft_karp(left_size: int, right_size: int, edges: list[tuple[int, int]]) -> int:
    ...
```

## Algorithm overview

Hopcroft-Karp finds a **blocking set of shortest augmenting paths** in each phase and updates the matching simultaneously. This gives an overall time complexity of **O(E · √V)** where V = left_size + right_size.

Key ideas:
- Maintain arrays `match_l` (matching for left nodes, -1 if unmatched) and `match_r` (matching for right nodes, -1 if unmatched).
- In each phase, BFS from all unmatched left nodes to find the shortest augmenting paths (using layered graphs with `dist` array).
- Then DFS from unmatched left nodes to find and push flows along those shortest augmenting paths.
- Repeat phases until no augmenting paths exist (BFS can no longer reach an unmatched right node).

## Input

- `left_size`: number of vertices in the left partition.
- `right_size`: number of vertices in the right partition.
- `edges`: list of `(left_index, right_index)` pairs representing edges.

## Output

Return the size of the maximum matching (an integer).
