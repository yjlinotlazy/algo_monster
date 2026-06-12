# Binary Search Tree

Implement:

```python
class BinarySearchTree:
    def __init__(self):
        ...

    def insert(self, value: int) -> None:
        ...

    def contains(self, value: int) -> bool:
        ...

    def in_order(self) -> list[int]:
        ...
```

## Input

Values are integers.

## Output

`insert(value)` adds `value` to the tree.

`contains(value)` returns whether `value` exists in the tree.

`in_order()` returns all inserted values in ascending order.

Duplicate values should be included in `in_order()`.
