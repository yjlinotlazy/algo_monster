# AVL Tree (Self-Balancing Binary Search Tree)

Implement an AVL tree with the following operations:

```python
class TreeNode:
    def __init__(self, key):
        ...

class AVLTree:
    def __init__(self):
        ...

    def insert(self, key: int) -> None:
        ...

    def search(self, key: int) -> bool:
        ...

    def inorder(self) -> list[int]:
        ...
```

## Input

`key` is a non-negative integer.

## Output

- `insert` adds the key to the tree and rebalances it (no return value).
- `search` returns `True` if the key exists in the tree, `False` otherwise.
- `inorder` returns the keys in ascending order via inorder traversal.
