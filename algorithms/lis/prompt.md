# Longest Increasing Subsequence — Dynamic Programming

Implement a dynamic programming algorithm to find the **length** of the longest strictly increasing subsequence in an array of integers.

```python
def length_of_lis(nums: list[int]) -> int:
    """
    Return the length of the longest strictly increasing subsequence
    (not necessarily contiguous) within *nums*.

    A subsequence is obtained by deleting zero or more elements from the
    original array while preserving the relative order of remaining elements.
    """
```

## Input

- `nums`: a list of integers.

## Output

- An integer: the length of the longest strictly increasing subsequence.

## Constraints

- Number of elements: 0 to 10,000.
- Element values are integers in range [-10^4, 10^4].
- Use a DP approach with O(n log n) time complexity via patience sorting (binary search on the tails array).
