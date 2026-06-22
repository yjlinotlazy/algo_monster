// ── State & DOM refs ───────────────────────────────────────────────
const state = {
  algorithms: [],
  selectedId: null,
  selected: null,
  filter: "",
  resultsByName: new Map(),
};

// Cached DOM element references.
const els = {
  list: document.querySelector("#algorithm-list"),
  search: document.querySelector("#search"),
  title: document.querySelector("#title"),
  category: document.querySelector("#category"),
  prompt: document.querySelector("#prompt"),
  editor: document.querySelector("#editor"),
  tests: document.querySelector("#tests"),
  results: document.querySelector("#results"),
  summary: document.querySelector("#summary"),
  saveState: document.querySelector("#save-state"),
  saveBtn: document.querySelector("#save-btn"),
  runBtn: document.querySelector("#run-btn"),
  clearBtn: document.querySelector("#clear-btn"),
  learningStatus: document.querySelector("#learning-status"),
};

// ── Helpers ────────────────────────────────────────────────────────
// Escaping, markdown rendering, and the fetch wrapper used by all API calls.

function escapeHtml(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

// Render prompt markdown into HTML (h1, h2, code blocks, paragraphs).
function renderMarkdown(markdown) {
  const lines = markdown.split("\n");
  let html = "";
  let inCode = false;
  let paragraph = [];

  function flushParagraph() {
    if (paragraph.length) {
      html += `<p>${inlineMarkdown(paragraph.join(" "))}</p>`;
      paragraph = [];
    }
  }

  for (const line of lines) {
    if (line.startsWith("```")) {
      if (inCode) {
        html += "</code></pre>";
        inCode = false;
      } else {
        flushParagraph();
        html += "<pre><code>";
        inCode = true;
      }
      continue;
    }

    if (inCode) {
      html += `${escapeHtml(line)}\n`;
      continue;
    }

    if (line.startsWith("# ")) {
      flushParagraph();
      html += `<h1>${escapeHtml(line.slice(2))}</h1>`;
    } else if (line.startsWith("## ")) {
      flushParagraph();
      html += `<h2>${escapeHtml(line.slice(3))}</h2>`;
    } else if (!line.trim()) {
      flushParagraph();
    } else {
      paragraph.push(line.trim());
    }
  }

  flushParagraph();
  return html;
}

function inlineMarkdown(value) {
  return escapeHtml(value).replace(/`([^`]+)`/g, "<code>$1</code>");
}

// Fetch JSON from the backend server; throws on non-2xx responses.
async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

// ── Algorithm list & navigation ─────────────────────────────────────

// Load algorithms from server; auto-selects the first one.
async function loadAlgorithms() {
  const data = await api("/api/algorithms");
  state.algorithms = data.algorithms;
  renderAlgorithmList();
  if (!state.selectedId && state.algorithms.length) {
    await selectAlgorithm(state.algorithms[0].id);
  }
}

// Filter and render the sidebar list based on search text.
function renderAlgorithmList() {
  const query = state.filter.toLowerCase();
  const algorithms = state.algorithms.filter((algorithm) => {
    return `${algorithm.title} ${algorithm.category}`
      .toLowerCase()
      .includes(query);
  });

  els.list.innerHTML = "";
  for (const algorithm of algorithms) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `algorithm-item${algorithm.id === state.selectedId ? " active" : ""}`;
    button.innerHTML = `
      <span class="status-dot${algorithm.progress?.passing ? " passing" : ""}"></span>
      <span>
        <span class="algorithm-title">${escapeHtml(algorithm.title)}</span>
        <span class="algorithm-meta">${escapeHtml(algorithm.category || "uncategorized")} · ${escapeHtml(algorithm.progress?.status || "to learn")}</span>
      </span>
    `;
    button.addEventListener("click", () => selectAlgorithm(algorithm.id));
    els.list.appendChild(button);
  }
}

// ── Algorithm detail view ──────────────────────────────────────────
// Load full algorithm data (prompt, starter, solution) and populate the editor area.

async function selectAlgorithm(id) {
  state.selectedId = id;
  state.resultsByName = new Map();
  setBusy(true);
  try {
    const data = await api(`/api/algorithms/${encodeURIComponent(id)}`);
    state.selected = data;
    els.title.textContent = data.meta.title || id;
    els.category.textContent = data.meta.category || "algorithm";
    els.prompt.innerHTML = renderMarkdown(data.prompt);
    els.editor.value = data.solution || data.starter || "";
    els.learningStatus.value = data.progress?.status || "to learn";
    els.summary.textContent = "No run yet";
    els.results.className = "results empty";
    els.results.textContent = "Run tests to see output.";
    els.saveState.textContent = "Saved";
    renderTests();
    renderAlgorithmList();
  } finally {
    setBusy(false);
  }
}

// ── Test runner UI ─────────────────────────────────────────────────
// Render test rows with per-test "Run" buttons wired to runTests(index).

function renderTests() {
  els.tests.innerHTML = "";
  const tests = state.selected?.tests || [];
  tests.forEach((test, index) => {
    const result = state.resultsByName.get(test.name);
    const row = document.createElement("div");
    row.className = `test-row${result ? (result.passed ? " passed" : " failed") : ""}`;
    row.innerHTML = `
      <div>
        <div class="test-name">${escapeHtml(test.name)}</div>
        <div class="test-result${result ? (result.passed ? " passed" : " failed") : ""}">
          ${result ? (result.passed ? "Passed" : "Failed") : "Not run"}
        </div>
      </div>
      <button class="run-one" type="button">Run</button>
    `;
    row
      .querySelector("button")
      .addEventListener("click", () => runTests(index));
    els.tests.appendChild(row);
  });
}

// ── Actions ────────────────────────────────────────────────────────

async function saveSolution() {
  if (!state.selectedId) return;
  setBusy(true);
  try {
    await api(`/api/solutions/${encodeURIComponent(state.selectedId)}`, {
      method: "PUT",
      body: JSON.stringify({ code: els.editor.value }),
    });
    els.saveState.textContent = "Saved";
  } finally {
    setBusy(false);
  }
}

async function saveProgress() {
  if (!state.selectedId) return;
  await api(`/api/progress/${encodeURIComponent(state.selectedId)}`, {
    method: "PUT",
    body: JSON.stringify({ status: els.learningStatus.value }),
  });
  const item = state.algorithms.find(
    (algorithm) => algorithm.id === state.selectedId,
  );
  if (item) {
    item.progress = {
      ...(item.progress || {}),
      status: els.learningStatus.value,
    };
  }
  renderAlgorithmList();
}

// Run a single test (by index) or all tests (null).
async function runTests(testIndex = null) {
  if (!state.selectedId) return;
  setBusy(true);
  try {
    const payload = {
      algorithm_id: state.selectedId,
      code: els.editor.value,
    };
    if (testIndex !== null) {
      payload.test_index = testIndex;
    }
    const result = await api("/api/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showResults(result);
    if (testIndex === null) {
      const item = state.algorithms.find(
        (algorithm) => algorithm.id === state.selectedId,
      );
      if (item) {
        item.progress = { ...(item.progress || {}), passing: result.ok };
      }
      renderAlgorithmList();
      // If all tests passed, also update the learning status to "learned"
      if (result.ok && els.learningStatus.value !== "learned") {
        els.learningStatus.value = "learned";
        saveProgress();
      }
    }
  } finally {
    setBusy(false);
  }
}

// ── Results display ────────────────────────────────────────────────

function showResults(result) {
  state.resultsByName = new Map(
    result.results.map((item) => [item.name, item]),
  );
  const summary = result.summary || { passed: 0, failed: 0, total: 0 };
  els.summary.textContent = `${summary.passed}/${summary.total} passed`;
  els.results.className = "results";
  els.results.innerHTML = result.results.map((item) => {
    const hasStdout = item.stdout && item.stdout.trim();
    const hasError = item.error;
    // Look up the test input code by name.
    const test = (state.selected?.tests || []).find(
      (t) => t.name === item.name,
    );
    const inputCode = test ? escapeHtml(test.code) : null;
    return `
        <div class="result-item">
          <div class="result-title">
            <span>${escapeHtml(item.name)}</span>
            <span class="${item.passed ? "passed" : "failed"}">${item.passed ? "Passed" : "Failed"}</span>
          </div>
          ${inputCode ? `<pre class="result-input">Input: ${inputCode}</pre>` : ""}
          ${hasStdout ? `<pre class="result-stdout">Stdout\n${escapeHtml(item.stdout)}</pre>` : ""}
          ${hasError ? `<pre class="result-error">${escapeHtml(item.error)}</pre>` : ""}
        </div>
      `;
  });
  renderTests();
}

function clearResults() {
  state.resultsByName = new Map();
  els.summary.textContent = "No run yet";
  els.results.className = "results empty";
  els.results.textContent = "Run tests to see output.";
  renderTests();
}

// Disable actionable controls while an async operation is in flight.
function setBusy(isBusy) {
  els.saveBtn.disabled = isBusy;
  els.runBtn.disabled = isBusy;
  els.learningStatus.disabled = isBusy;
  els.clearBtn.disabled = isBusy;
}

// ── Event wiring & bootstrap ───────────────────────────────────────

els.search.addEventListener("input", () => {
  state.filter = els.search.value;
  renderAlgorithmList();
});

els.editor.addEventListener("input", () => {
  els.saveState.textContent = "Unsaved";
});

els.editor.addEventListener("keydown", (event) => {
  if (event.key === "Tab") {
    event.preventDefault();
    const start = els.editor.selectionStart;
    const end = els.editor.selectionEnd;
    const value = els.editor.value;
    els.editor.value = `${value.slice(0, start)}    ${value.slice(end)}`;
    els.editor.selectionStart = start + 4;
    els.editor.selectionEnd = start + 4;
    els.saveState.textContent = "Unsaved";
  }
});

// This function resets the editor back to the original template (starter code) for the current algorithm.
// It fetches fresh starter from the server rather than relying on potentially-stale memory state.
async function resetToTemplate() {
  if (!state.selectedId) return;
  setBusy(true);
  try {
    const { starter } = await api(
      `/api/algorithms/${encodeURIComponent(state.selectedId)}/__starter`,
    );
    els.editor.value = starter || "";

    // Also clear test results so the user sees a full reset.
    clearResults();
  } finally {
    setBusy(false);
  }
}

els.saveBtn.addEventListener("click", saveSolution);
els.runBtn.addEventListener("click", () => runTests(null));
els.clearBtn.addEventListener("click", resetToTemplate);
els.learningStatus.addEventListener("change", saveProgress);

// Boot the app; catch startup errors.
loadAlgorithms().catch((error) => {
  els.results.className = "results";
  els.results.innerHTML = `<div class="result-item"><strong>Startup error</strong><pre>${escapeHtml(error.message)}</pre></div>`;
});
