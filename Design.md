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

## MLE Monster

**MLE monster** is the interview-practice mode. It asks conceptual ML/engineering
questions, accepts a free-text user answer, grades it against an LLM, and
tracks progress independently of algorithm practice.

### Direction

The browser owns the question list, the answer input, grading results, and
progress view. The backend loads interview content from bundled JSON files,
forwards answers to an LLM (local or remote), and persists scoring history.

The content focus is general ML interview questions — fundamentals, deep
learning, LLMs, metrics, data engineering, productionization, and
experimentation — rather than coding puzzles. Users should explain concepts in
their own words; the LLM grades clarity, completeness, and correctness.

### Content Model

Bundled MLE content lives alongside algorithms in the project.

Initial directory structure:

```text
mle/
  categories.json
```

#### `categories.json`

A category-keyed object whose values are arrays of interview question objects:

```json
{
  "ML fundamentals": [
    {
      "id": "ml_fundamentals_overfitting",
      "question": "What is overfitting?",
      "reference_answer": "Overfitting occurs when..."
    }
  ]
}
```

- `id`: stable identifier, such as `ml_fundamentals_overfitting`  
- `question`: the interview question the user sees  
- `reference_answer`: a model answer revealed after grading, used as a
  reference for self-review (not fed to the LLM)  

The category is implied by the top-level key. The backend includes `category`
in API responses for convenience.

### Grading Flow

1. User picks a question from the list (organized by category).
2. The user writes an answer in a text input area.
3. User clicks **Grade me**.
4. Backend forwards the question + user answer to an LLM.
5. The LLM returns:
   - A numeric score (1–5): 1 = "knows nothing", 5 = "passes"
   - Optional feedback text explaining the score
6. After grading, an **Interview Answer** box reveals the `reference_answer`
   for self-review.
7. Score and timestamp are saved to per-user progress automatically.

### LLM Provider

Configurable at runtime via environment variables (all use `os.environ`):

- `OPENAI_API_KEY` — required. Defaults to `sk-placeholder` (Ollama accepts any non-empty key).  
- `OPENAI_BASE_URL` — defaults to `http://localhost:11434/v1` (Ollama's OpenAI-compatible endpoint).

The app uses the same `openai`-compatible HTTP call regardless of provider, so swapping between Ollama and a real LLM only changes these two environment variables. The grading prompt asks for score + feedback in JSON format.

If the configured LLM is unreachable or returns an error, the grade endpoint responds with `ok: false` and a clear error message explaining that grading is unavailable.

### Progress Tracking

MLE progress is stored alongside algorithm progress in
`~/.config/algo_monster/progress.json`, under a top-level `"mle"` key:

```json
{
  "mle": {
    "ml_fundamentals_overfitting": {
      "status": "to learn",
      "score": null,
      "graded_at": null
    }
  }
}
```

`status` values: `to learn`, `learning`, `learned`. The app can auto-advance
the status based on the score (e.g., >=4 -> `learned`). Users may manually reset
any item's progress via a **Reset** button.

### API Endpoints

#### GET `/api/mle/questions`

Returns questions grouped by category:

```json
{
  "categories": {
    "ML fundamentals": [
      { "id": "ml_fundamentals_overfitting", "category": "ML fundamentals",
        "question": "What is overfitting?" }
    ]
  }
}
```

#### GET `/api/mle/questions/:id`

Returns a single question with previous grading history:

```json
{
  "id": "ml_fundamentals_overfitting",
  "category": "ML fundamentals",
  "question": "What is overfitting?",
  "reference_answer": "Overfitting occurs when the model fits training data too closely...",
  "progress": { "status": "learning", "score": 3, "graded_at": "2026-06-15T12:00:00Z" }
}
```

#### POST `/api/mle/grade`

Grades a user answer against the LLM.

Request body:
```json
{
  "question_id": "ml_fundamentals_overfitting",
  "answer": "Overfitting is when the model..."
}
```

Response:
```json
{
  "ok": true,
  "score": 3,
  "feedback": "Good intuition, but missing mention of regularization."
}
```

#### PUT `/api/mle/progress/:id`

Updates progress (status + score) for a question. Sets `graded_at` timestamp
on grading. User can set status to `to learn` to reset.

### UI Layout

The app has two product entry points from the landing page:

1. **Algorithm Monster** — current algorithm practice layout.
2. **MLE Monster** — interview question practice layout at `/mle`.

MLE Monster must render as a three-panel workspace on desktop:

1. **Left sidebar: question tree**
   - Shows MLE questions from `mle/categories.json`.
   - Questions are grouped under category headings.
   - Category headings can be expanded/collapsed.
   - Selecting a question loads that question into the middle panel.
   - The sidebar must not contain the answer editor or LLM feedback.
2. **Middle panel: user answer**
   - Shows the selected category and selected question.
   - Contains the user's free-text answer textarea.
   - Contains the **Grade me** button.
   - Contains status/reset controls for the selected question.
3. **Right sidebar: LLM answer**
   - Shows the LLM grading result: score and feedback.
   - Shows the reference/interview answer after grading.
   - Uses the configured local Ollama-compatible endpoint by default.

On narrow screens the three panels may stack vertically, but the content
ownership remains the same: question navigation first, user answer second,
LLM/reference answer third.

Known MLE UI bugs to guard against:

- The left question tree must be populated from `GET /api/mle/questions`; an
  empty sidebar is a bug when `mle/categories.json` has questions.
- The desktop layout must visibly show three separate panels. If answer or LLM
  content is squeezed into the left sidebar, the layout is broken.
- The frontend and backend must agree on the response shape for
  `/api/mle/questions`; currently the canonical shape is `{ "categories": ... }`.

### Boundaries (updated)

- Bundled algorithm definitions, test cases, and MLE questions live in the
  project. User solutions and progress do not modify these files.
- User-specific data lives outside the project under
  `~/.config/algo_monster/`.
- The browser does not execute Python directly.
- The backend is responsible for validating requests, loading files,
  saving progress, running submitted code, and grading MLE answers.
- Grading requires an LLM endpoint; the app fails gracefully with a visible
  error if no API key or local server is configured.
