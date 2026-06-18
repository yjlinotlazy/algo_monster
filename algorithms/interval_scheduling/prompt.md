# Interval Scheduling — Maximum Non-Overlapping Intervals

Implement the classic **greedy interval scheduling** algorithm to select the maximum number of non-overlapping intervals from a given set.

```python
def interval_scheduling(intervals: list[tuple[int, int]]) -> int:
    """
    Given a list of intervals [start, end], return the maximum number
    of non-overlapping intervals that can be selected.

    Two intervals [a, b] and [c, d] overlap if max(a, c) < min(b, d).
    Intervals where one ends exactly when another starts do NOT overlap
    (e.g., [1, 2] and [2, 3] are compatible).
    """
```

## Input

- `intervals`: a list of `[start, end]` pairs representing time intervals. Each start is strictly less than its end.

## Output

- An integer: the maximum number of mutually non-overlapping intervals that can be scheduled.

## Constraints

- Number of intervals: 0 to 10,000.
- Start and end values are integers in range [0, 10^6].
- You **must** use a greedy strategy — sort by finish time and always pick the next compatible interval that finishes earliest.
- Time complexity should be O(n log n).
