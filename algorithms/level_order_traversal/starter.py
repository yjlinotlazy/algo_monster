class TreeNode:
    def __init__(self, val: int):
        self.val = val
        self.left: 'TreeNode | None' = None
        self.right: 'TreeNode | None' = None


def level_order(root: 'TreeNode | None') -> list[list[int]]:
    ...
