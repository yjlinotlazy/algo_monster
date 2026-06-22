// ── State & DOM refs ───────────────────────────────────────────────
const state = {
  /** @type {Record<string, Array<{id: string, question: string, reference_answer?: string}>>} */
  categories: {},
  selectedId: null,
  selectedCategory: null,
  selected: null,
};

const els = {
  categoryTree: document.querySelector("#category-tree"),
  title: document.querySelector("#title"),
  category: document.querySelector("#category"),
  questionText: document.querySelector("#question-text"),
  answerInput: document.querySelector("#answer-input"),
  modelSelector: document.querySelector("#model-selector"),
  gradeBtn: document.querySelector("#grade-btn"),
  gradingResult: document.querySelector("#grading-result"),
  referenceAnswer: document.querySelector("#reference-answer"),
  referenceText: document.querySelector("#reference-text"),
  learningStatus: document.querySelector("#learning-status"),
  resetBtn: document.querySelector("#reset-btn"),
  saveBtn: document.querySelector("#save-btn"),
};

const _expanded = new Set();

// ── Helpers ────────────────────────────────────────────────────────

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

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

// ── Load questions ─────────────────────────────────────────────────

async function loadQuestions() {
  const data = await api("/api/mle/questions");
  state.categories = data.categories || data.questions || {};
  _expanded.clear();
  // Auto-expand first category
  const keys = Object.keys(state.categories);
  if (keys.length) _expanded.add(keys[0]);

  renderCategoryTree();

  // Select first question
  const firstCat = keys[0];
  if (firstCat && state.categories[firstCat]?.length) {
    selectQuestion(state.categories[firstCat][0].id, firstCat);
  }
}

// ── Sidebar rendering ──────────────────────────────────────────────

function countByStatus(questions) {
  const counts = { learned: 0, learning: 0, "to learn": 0 };
  for (const q of questions) {
    const s = q.progress?.status || "to learn";
    if (counts[s] !== undefined) counts[s]++;
  }
  return counts;
}

function progressPercent(counts) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  return total ? Math.round((counts.learned / total) * 100) : 0;
}

function findLocalQuestion(id) {
  for (const [category, questions] of Object.entries(state.categories)) {
    const question = questions.find((q) => q.id === id);
    if (question) return { category, question };
  }
  return null;
}

function updateLocalProgress(id, progress) {
  const found = findLocalQuestion(id);
  if (!found) return;
  found.question.progress = progress || {};
  if (state.selected?.id === id) {
    state.selected.progress = found.question.progress;
  }
}

function renderCategoryTree() {
  els.categoryTree.innerHTML = "";

  for (const [category, questions] of Object.entries(state.categories)) {
    const counts = countByStatus(questions);
    const pct = progressPercent(counts);
    const isExpanded = _expanded.has(category);

    // Category row
    const row = document.createElement("div");
    row.className = "category-row";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "category-toggle";
    btn.setAttribute("aria-expanded", isExpanded ? "true" : "false");
    btn.innerHTML = `
      <span class="toggle-chevron">&#9660;</span>
      <span class="category-label">${escapeHtml(category)}</span>
      <span class="question-count">${questions.length}</span>
    `;
    btn.addEventListener("click", () => {
      if (_expanded.has(category)) _expanded.delete(category);
      else _expanded.add(category);
      renderCategoryTree();
    });

    // Question list container (with height transition)
    const container = document.createElement("div");
    container.className =
      "question-list-container" + (isExpanded ? "" : " collapsed");
    if (!isExpanded) container.style.height = "0";

    const list = document.createElement("nav");
    list.className = "question-list";
    list.setAttribute("aria-label", `Questions in ${category}`);

    for (const q of questions) {
      const itemBtn = document.createElement("button");
      itemBtn.type = "button";
      const statusDot = q.progress?.score ? "passing" : "";
      const scoreBadge = q.progress?.score
        ? `<span class="score-badge">${q.progress.score}</span>`
        : "";
      const label =
        q.question.length > 56 ? `${q.question.slice(0, 56)}...` : q.question;
      itemBtn.className = `question-item${q.id === state.selectedId ? " active" : ""}`;
      itemBtn.innerHTML = `<span class="status-dot ${statusDot}"></span><span class="question-label">${escapeHtml(label)}</span>${scoreBadge}`;
      itemBtn.title = q.question;
      itemBtn.addEventListener("click", () => selectQuestion(q.id, category));

      list.appendChild(itemBtn);
    }

    container.appendChild(list);

    // Progress bar
    const progBar = document.createElement("div");
    progBar.className = "category-progress";
    progBar.innerHTML = `<span class="progress-bar"><span class="progress-fill" style="width:${pct}%"></span></span><span>${counts.learned}/${questions.length}</span>`;

    row.appendChild(btn);
    row.appendChild(container);
    row.appendChild(progBar);
    els.categoryTree.appendChild(row);
  }
}

// ── Question detail view ───────────────────────────────────────────

async function selectQuestion(id, category) {
  state.selectedId = id;
  state.selectedCategory = category || "Unknown";
  els.gradeBtn.disabled = true;
  try {
    const data = await api(`/api/mle/questions/${encodeURIComponent(id)}`);
    state.selected = data;
    els.title.textContent = data.question;
    els.category.textContent = data.category || category || "Unknown";
    state.selectedCategory = data.category || category || "Unknown";
    els.questionText.textContent = data.question;
    els.learningStatus.value = data.progress?.status || "to learn";

    // Re-render sidebar to update active highlight
    updateLocalProgress(id, data.progress || {});
    renderCategoryTree();

    // Restore saved graded answer if one exists.
    restoreGradedAnswer(data.graded);
  } finally {
    els.gradeBtn.disabled = false;
  }
}

function restoreGradedAnswer(graded) {
  // Always reset UI state first to prevent persistence from previous questions.
  els.answerInput.value = "";
  els.gradingResult.className = "grading-result empty";
  els.gradingResult.innerHTML = "";
  els.referenceAnswer.classList.add("hidden");

  if (!graded) return;

  const scoreColors = {
    1: "var(--danger)",
    2: "var(--warning)",
    3: "#7a6b00",
    4: "var(--accent)",
    5: "var(--success)",
  };
  const color = scoreColors[graded.score] || "var(--text)";

  // Grading result with saved score and feedback.
  els.gradingResult.className = "grading-result";
  els.gradingResult.innerHTML = `
    <div class="score" style="color:${color}">${graded.score} / 5</div>
    <div class="feedback">${escapeHtml(graded.llm_feedback || "No feedback available.")}</div>
  `;

  // Restore user's answer if saved.
  if (graded.user_answer !== undefined && graded.user_answer !== null) {
    els.answerInput.value = graded.user_answer;
  }

  // Show reference answer if available.
  if (graded.reference_answer) {
    els.referenceText.textContent = graded.reference_answer;
    els.referenceAnswer.classList.remove("hidden");
  } else if (state.selected?.reference_answer) {
    els.referenceText.textContent = state.selected.reference_answer;
    els.referenceAnswer.classList.remove("hidden");
  }
}

// ── Grading ────────────────────────────────────────────────────────

async function gradeAnswer() {
  if (!state.selected) return;
  const answer = els.answerInput.value.trim();
  if (!answer) {
    els.gradingResult.className = "grading-result";
    els.gradingResult.innerHTML = `<div class="feedback">Please write an answer before grading.</div>`;
    return;
  }

  setBusy(true);
  try {
    const result = await api("/api/mle/grade", {
      method: "POST",
      body: JSON.stringify({
        question_id: state.selected.id,
        answer: answer,
        model_type: els.modelSelector.value || "ollama",
      }),
    });

    if (!result.ok) {
      els.gradingResult.className = "grading-result";
      els.gradingResult.innerHTML = `<div class="feedback" style="color:var(--danger)">Grading unavailable: ${escapeHtml(result.error)}</div>`;
      return;
    }

    const scoreColors = {
      1: "var(--danger)",
      2: "var(--warning)",
      3: "#7a6b00",
      4: "var(--accent)",
      5: "var(--success)",
    };
    const color = scoreColors[result.score] || "var(--text)";

    els.gradingResult.className = "grading-result";
    els.gradingResult.innerHTML = `
      <div class="score" style="color:${color}">${result.score} / 5</div>
      <div class="feedback">${escapeHtml(result.feedback || "")}</div>
    `;

    const progress = result.progress || {
      status:
        result.score >= 4
          ? "learned"
          : state.selected.progress?.status || "learning",
      score: result.score,
    };
    updateLocalProgress(state.selected.id, progress);
    els.learningStatus.value = progress.status || "learning";
    renderCategoryTree();

    if (state.selected.reference_answer) {
      els.referenceText.textContent = state.selected.reference_answer;
      els.referenceAnswer.classList.remove("hidden");
    }

    // Save graded answers in background; errors are non-fatal.
    saveGradedAnswer().catch(() => {});
  } catch (error) {
    els.gradingResult.className = "grading-result";
    els.gradingResult.innerHTML = `<div class="feedback" style="color:var(--danger)">Error: ${escapeHtml(error.message)}</div>`;
  } finally {
    setBusy(false);
  }
}

// ── Save graded answers (user answer + LLM feedback) per category ──

async function saveGradedAnswer() {
  if (!state.selectedId || !state.selectedCategory) return;
  const userAnswer = els.answerInput.value.trim();
  const gradingEl = els.gradingResult.querySelector(".feedback");
  const llmFeedback = gradingEl ? gradingEl.textContent : "";
  const scoreText = els.gradingResult.querySelector(".score");
  const score = scoreText ? parseInt(scoreText.textContent, 10) : null;
  const res = await api("/api/mle/graded/save", {
    method: "POST",
    body: JSON.stringify({
      question_id: state.selectedId,
      category: state.selectedCategory,
      user_answer: userAnswer,
      score: score,
      llm_feedback: llmFeedback,
    }),
  });
  return res.ok ? res : null;
}

// ── Progress ───────────────────────────────────────────────────────

async function saveProgress() {
  if (!state.selectedId) return;
  const data = await api(
    `/api/mle/progress/${encodeURIComponent(state.selectedId)}`,
    {
      method: "PUT",
      body: JSON.stringify({ status: els.learningStatus.value }),
    },
  );
  updateLocalProgress(state.selectedId, data.progress);
  renderCategoryTree();
}

async function resetProgress() {
  if (!state.selectedId) return;
  const data = await api(
    `/api/mle/progress/${encodeURIComponent(state.selectedId)}`,
    {
      method: "PUT",
      body: JSON.stringify({ status: "to learn", reset: true }),
    },
  );
  updateLocalProgress(state.selectedId, data.progress);
  els.learningStatus.value = "to learn";
  els.answerInput.value = "";
  els.gradingResult.className = "grading-result empty";
  els.gradingResult.innerHTML = "";
  els.referenceAnswer.classList.add("hidden");
  renderCategoryTree();
}

// ── Busy indicator ─────────────────────────────────────────────────

function setBusy(isBusy) {
  els.gradeBtn.disabled = isBusy;
  els.answerInput.disabled = isBusy;
}

// ── Event wiring & bootstrap ───────────────────────────────────────
els.gradeBtn.addEventListener("click", gradeAnswer);
els.resetBtn.addEventListener("click", resetProgress);
els.saveBtn.addEventListener("click", () => {
  if (!state.selectedId) return;
  els.saveBtn.textContent = "Saving…";
  els.saveBtn.disabled = true;
  saveGradedAnswer().finally(() => {
    els.saveBtn.textContent = "Save";
    els.saveBtn.disabled = false;
  });
});
els.learningStatus.addEventListener("change", saveProgress);

loadQuestions().catch((error) => {
  els.gradingResult.className = "grading-result";
  els.gradingResult.innerHTML = `<div class="feedback" style="color:var(--danger)">Startup error: ${escapeHtml(error.message)}</div>`;
});
