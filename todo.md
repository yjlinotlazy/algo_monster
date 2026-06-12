# Todo

## Documentation

- [x] Update `README` to clarify that Algo Monster focuses on textbook algorithms,
  not interview-style puzzle prompts.
- [x] Update `Design.md` with the textbook algorithm focus.
- [x] Document that algorithm prompts should be minimal API/input/output specs.
- [x] Document that prompts should not include implementation hints or approach
  guidance.

## Algorithm Content Format

- [x] Define the initial algorithm directory structure:

  ```text
  algorithms/
    union_find/
      prompt.md
      tests.json
      starter.py
      meta.json
  ```

- [x] Define `prompt.md` conventions:
  - required function or class signature
  - input contract
  - output contract
  - deterministic behavior rules where needed
  - no implementation hints

- [x] Define `tests.json` conventions:
  - tests call the required function or class API directly
  - graph traversal tests specify neighbor visit order
  - data structure tests instantiate and exercise the class
  - test output is structured per test case

## Initial Algorithm Set

- [x] Binary Search
- [x] Binary Search Tree
- [x] Union Find
- [x] Breadth-First Search
- [x] Depth-First Search
- [x] Merge Sort

## Implementation

- [x] Scaffold the local Python backend.
- [x] Add endpoints for algorithms, solutions, progress, and test execution.
- [x] Implement local user storage under `~/.config/algo_monster/`.
- [x] Build the Python execution harness with subprocess isolation and a timeout.
- [x] Scaffold the browser frontend.
- [x] Add an embedded Python editor.
- [x] Build the main study UI:
  - algorithm list
  - prompt panel
  - editor
  - test case list
  - result output
  - learning status control
- [x] Seed the initial textbook algorithms.
- [x] Verify the full loop with one algorithm:
  - open app
  - choose algorithm
  - write solution
  - run tests
  - view results
  - save solution and progress
