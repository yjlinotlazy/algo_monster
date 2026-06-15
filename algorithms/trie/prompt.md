# Trie (Prefix Tree)

Implement a Trie data structure with the following operations:

```python
class Trie:
    def __init__(self):
        ...

    def insert(self, word: str) -> None:
        ...

    def search(self, word: str) -> bool:
        ...

    def starts_with(self, prefix: str) -> bool:
        ...
```

## Input

`word` and `prefix` are non-empty strings containing only lowercase English letters.

## Output

- `insert` adds a word to the trie (no return value).
- `search` returns True if the word exists in the trie, False otherwise.
- `starts_with` returns True if any inserted word has the given prefix, False otherwise.
