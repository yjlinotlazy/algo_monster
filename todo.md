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

## MLE Monster

- [ ] Create `mle/questions.json` with sample questions across categories.

### Content

- [ ] Create `mle/questions.json` with sample questions across categories
  (`ML fundamentals`, `Deep learning`, `LLM / AI`, `Metrics / Evaluation`,
  `Data`, `Productionization`, `Experimentation`).
  Each question has `id`, `category`, `question`, and `reference_answer`.

### Backend

- [ ] Add LLM grading function that calls the configured provider:
  - Ollama at `http://localhost:11434/v1` (default, uses qwen-large2)
    Accepts any non-empty `OPENAI_API_KEY` value.
  - OpenAI-compatible endpoint (custom URL via `OPENAI_BASE_URL`).
  - Both use the same OpenAI chat completions format; provider choice is just
    two env vars (`OPENAI_API_KEY`, `OPENAI_BASE_URL`) with Ollama defaults.
- [ ] Add `GET /api/mle/questions` — returns questions grouped by category.
- [ ] Add `GET /api/mle/questions/:id` — returns question + prior grading history.
- [ ] Add `POST /api/mle/grade` — forwards user answer to LLM, parses
  score (1-5) + feedback from response, saves progress automatically.
- [ ] Add `PUT /api/mle/progress/:id` — updates status + score for a question.
  (Reuses existing `save_progress()` + progress schema.)
- [ ] Progress data is stored under the `"mle"` key in the existing
  `~/.config/algo_monster/progress.json`.

### Frontend

- [ ] Add a toggle/tab between Algorithm and MLE modes in the top bar.
- [ ] In MLE mode: render question list (grouped by category) in the sidebar.
- [ ] In MLE mode: render answer input area + **Grade me** button in the
  main content area.
- [ ] Show grading result (score, feedback) and post-grading reveal of
  `reference_answer` box below the input.
- [ ] Wire up progress status control (same as algorithm mode).

### Graceful degradation

- [ ] If no LLM endpoint is reachable, grade returns `ok: false` with a visible
  error explaining that grading is unavailable.
