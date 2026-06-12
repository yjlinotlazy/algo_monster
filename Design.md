# Design

## Direction

Algo Monster runs as a local browser-based app. The browser UI provides the
algorithm list, prompt, code editor, and test results. A local Python backend
loads algorithm definitions, persists user progress, and executes submitted
solutions against test cases.

The browser owns editing and display. The backend owns filesystem access and
Python code execution.

The content focus is textbook algorithms and data structures, not interview
puzzle prompts. Each exercise should ask the user to implement a named
algorithm or data structure behind a specified Python API.

## MVP

- Load a preloaded list of algorithms from text files in the project.
- Show the selected algorithm prompt, test cases, editor, and test output in a
  single browser UI.
- Let the user edit and save Python solutions.
- Run the current solution against all test cases or a selected test case.
- Report pass/fail status and useful failure output per test.
- Track implementation success separately from learning status.
- Persist user status, settings, and saved solutions under
  `~/.config/algo_monster/`.

## Algorithm Content

Bundled algorithm content lives in the project. User solutions and progress do
not modify these files.

Initial directory structure:

```text
algorithms/
  union_find/
    prompt.md
    tests.json
    starter.py
    meta.json
```

### `meta.json`

Stores algorithm metadata used by the algorithm list.

Expected fields:

- `id`: stable identifier, such as `union_find`
- `title`: display name, such as `Union Find`
- `category`: broad topic, such as `data structures` or `graphs`

### `prompt.md`

Prompts should be minimal API/input/output specifications.

They should include:

- required function or class signature
- input contract
- output contract
- deterministic behavior rules where needed

They should not include:

- implementation hints
- step-by-step approach guidance
- interview-style story framing

For graph traversal prompts, neighbor visit order must be specified so tests
can assert deterministic output.

### `starter.py`

Provides the initial code shown in the editor. It should contain only the
required function or class skeleton and minimal placeholders.

### `tests.json`

Defines test cases for the required API.

Tests should:

- call the required function or class API directly
- instantiate and exercise data structures through their public methods
- specify graph neighbor order when traversal output order matters
- produce structured per-test results

## Initial Algorithm Set

- Binary Search
- Binary Search Tree
- Union Find
- Breadth-First Search
- Depth-First Search
- Merge Sort

## Initial Stack

- Python standard-library backend using `http.server`.
- Browser frontend using plain HTML, CSS, and JavaScript.
- Embedded Python editor using a styled `<textarea>`.
- Python submissions run in a subprocess with a timeout.

The MVP intentionally avoids third-party dependencies. A later version can
replace the editor with CodeMirror or Monaco if richer editing becomes worth
the added build tooling.

## Boundaries

- Bundled algorithm definitions and test cases live in the project.
- User-specific data lives outside the project under `~/.config/algo_monster/`.
- The browser does not execute Python directly.
- The backend is responsible for validating requests, loading files, saving
  progress, and running submitted code.
