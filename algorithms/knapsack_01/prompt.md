# 0/1 Knapsack — Dynamic Programming

Implement the classic **0/1 knapsack** dynamic programming algorithm. Given a set of items, each with a weight and value, determine the maximum total value that can fit into a knapsack of a given capacity. Each item can be taken at most once.

```python
def knapsack_01(capacity: int, weights: list[int], values: list[int]) -> int:
    """
    Given *capacity* (maximum weight the knapsack can hold), and parallel lists
    of *weights* and *values* for each item, return the maximum total value
    achievable. Each item may be taken at most once (0/1 choice).
    """
```

## Input

- `capacity`: the maximum weight the knapsack can carry (non-negative integer).
- `weights`: a list of positive integers representing each item's weight.
- `values`: a list of non-negative integers representing each item's value, parallel to `weights`.

## Output

- An integer: the maximum total value achievable without exceeding the capacity.

## Constraints

- Number of items: 0 to 1,000.
- Capacity: 0 to 10,000.
- Weights are positive integers in range [1, 100].
- Values are non-negative integers in range [0, 1000].
- Use a DP approach with O(n * W) time and O(W) space complexity.
