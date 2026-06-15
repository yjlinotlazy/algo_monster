# Level Order Traversal (Binary Tree)

Implement **level order traversal** of a binary tree, returning nodes level by level from top to bottom, left to right.

```python
class TreeNode:
    def __init__(self, val: int):
        self.val = val
        self.left: 'TreeNode | None' = None
        self.right: 'TreeNode | None' = None


def level_order(root: 'TreeNode | None') -> list[list[int]]:
    ...
```

## Input

`root` is the root node of a binary tree. Each `TreeNode` has an integer `val`, and optional `left` and `right` children.

## Output

Return a list of lists, where each inner list contains the values of nodes at that level. The outer list is ordered from the root level (level 0) to the deepest level. Empty levels should not produce empty inner lists — a tree with no nodes returns `[]`.
