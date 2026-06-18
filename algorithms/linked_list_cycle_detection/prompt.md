# Linked List Cycle Detection — Floyd's Tortoise and Hare

Implement **Floyd's cycle detection** algorithm to determine whether a singly linked list contains a cycle, and if it does, return the starting node of the cycle.

```python
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def detect_cycle(head: ListNode | None) -> int | None:
    """
    Return the 0-based index where the cycle begins if a cycle exists,
    or None if there is no cycle.

    A "cycle" means some node's `next` points back to an earlier node
    in the list (forming a loop). If the head itself is part of the
    cycle, return 0.
    """
```

## Input

- `head`: the head node of a singly linked list, where each node has `val` and `next`. The list may contain a cycle — i.e., some node's `next` may point to an earlier node in the list, forming a loop.

## Output

- Return the **0-based index** (counting from the head) of the first node that is part of the cycle if one exists.
- Return `None` if the list has no cycle.

## Constraints

- Number of nodes: 0 to 10,000.
- Node values are integers in range [-10^5, 10^5].
- You **must** use Floyd's tortoise-and-hare algorithm (two-pointer approach) — O(1) extra space.
- Do NOT use a hash set or visited-list approach.
