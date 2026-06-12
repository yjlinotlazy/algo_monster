# Union Find

Implement:

```python
class UnionFind:
    def __init__(self, n: int):
        ...

    def find(self, x: int) -> int:
        ...

    def union(self, a: int, b: int) -> None:
        ...

    def connected(self, a: int, b: int) -> bool:
        ...
```

## Input

`n` is the number of elements. Elements are integers from `0` to `n - 1`.

## Output

`find(x)` returns the representative for `x`.

`union(a, b)` merges the sets containing `a` and `b`.

`connected(a, b)` returns whether `a` and `b` are in the same set.
