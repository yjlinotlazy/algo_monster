# Min-Heap

Implement a min-heap using an array.

```python
class MinHeap:
    def push(self, val: int) -> None:
        ...

    def pop(self) -> int:
        ...

    def peek(self) -> int:
        ...

    def is_empty(self) -> bool:
        ...
```

## API

- `push(val)` — insert a value into the heap.
- `pop()` — remove and return the smallest value. Raise `IndexError` if empty.
- `peek()` — return the smallest value without removing it. Raise `IndexError` if empty.
- `is_empty()` — return `True` when the heap contains no elements.

## Invariants

- The smallest element is always at index 0.
- Every parent node is $\leq$ its children.
- The underlying array is kept as compact as possible (no gaps).
