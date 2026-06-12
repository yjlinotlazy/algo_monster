# Algo Monster

Algo Monster is a lightweight local web app for studying common algorithms by
implementing them from scratch.

The app gives you a focused workspace with an algorithm prompt, an embedded
Python editor, visible test cases, and pass/fail feedback in one browser UI.

## Functionality

- Choose an algorithm from a preloaded study list.
- Read the algorithm prompt and expected behavior.
- Write a Python solution in the embedded editor.
- Review the available test cases.
- Run all test cases at once, or run one test case at a time.
- See pass/fail results and useful failure output.
- Track learning status manually as `to learn`, `learning`, or `learned`.
- See which algorithms currently pass their test cases.
- Keep personal progress and saved solutions locally.

## Usage

Algo Monster is intended to run locally on your machine.

1. Start the local app server:

   ```sh
   python3 server.py
   ```

2. Open the browser UI at `http://127.0.0.1:8000`.
3. Pick an algorithm from the list.
4. Implement the solution in Python.
5. Run the test cases and iterate until they pass.
6. Update the learning status when appropriate.

User-specific progress, settings, and saved solutions are stored under
`~/.config/algo_monster/`.

## Included Algorithms

- Binary Search
- Binary Search Tree
- Union Find
- Breadth-First Search
- Depth-First Search
- Merge Sort

## Requirements

Python 3.10 or newer is recommended. The MVP uses only the Python standard
library and does not require installing frontend or backend dependencies.
