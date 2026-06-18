// ── State & DOM refs ───────────────────────────────────────────────
const state = {
  categories: {},
  questions: [],
  selectedId: null,
  selected: null,
};

const els = {
  categoryNav: document.querySelector("#category-nav"),
  questionList: document.querySelector("#question-list"),
  title: document.querySelector("#title"),
  category: document.querySelector("#category"),
  questionText: document.querySelector("#question-text"),
  answerInput: document.querySelector("#answer-input"),
  gradeBtn: document.querySelector("#grade-btn"),
  gradingResult: document.querySelector("#grading-result"),
  referenceAnswer: document.querySelector("#reference-answer"),
  referenceText: document.querySelector("#reference-text"),
  learningStatus: document.querySelector("#learning-status"),
  resetBtn: document.querySelector("#reset-btn"),
};

// ── Helpers ────────────────────────────────────────────────────────

function escapeHtml(value) {
  return value
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
  state.categories = data.questions;
  // Flatten for quick lookup
  state.questions = Object.values(data.questions).flat();
  renderCategoryNav();
  // Select first category and show its first question
  const catKeys = Object.keys(state.categories);
  if (catKeys.length && state.categories[catKeys[0]].length) {
    selectQuestion(state.categories[catKeys[0]][0].id);
  }
}

// ── Sidebar rendering ──────────────────────────────────────────────

function renderCategoryNav() {
  els.categoryNav.innerHTML = "";
  for (const category of Object.keys(state.categories)) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "category-btn";
    btn.textContent = category;
    btn.addEventListener("click", () => showCategory(category));
    els.categoryNav.appendChild(btn);
  }
}

function renderQuestionList(categoryName) {
  const questions = state.categories[categoryName] || [];
  els.questionList.innerHTML = "";

  for (const q of questions) {
    const button = document.createElement("button");
    button.type = "button";
    const statusDot = q.progress?.score ? `<span class="status-dot passing"></span>` : `<span class="status-dot"></span>`;
    const scoreBadge = q.progress?.score ? `<span class="score-badge">${q.progress.score}</span>` : "";
    button.className = `question-item${q.id === state.selectedId ? " active" : ""}`;
    button.innerHTML = `${statusDot}${escapeHtml(q.question).slice(0, 60)}…${scoreBadge}`;
    button.title = q.question;
    button.addEventListener("click", () => selectQuestion(q.id));
    els.questionList.appendChild(button);
  }
}

function showCategory(categoryName) {
  state.selectedId = null;
  renderQuestionList(categoryName);
}

// ── Question detail view ───────────────────────────────────────────

async function selectQuestion(id) {
  state.selectedId = id;
  els.gradeBtn.disabled = true;
  try {
    const data = await api(`/api/mle/questions/${encodeURIComponent(id)}`);
    state.selected = data;
    els.title.textContent = data.question;
    els.category.textContent = data.category;
    els.questionText.textContent = data.question;
    els.answerInput.value = "";
    els.gradingResult.className = "grading-result empty";
    els.gradingResult.innerHTML = "";
    els.referenceAnswer.classList.add("hidden");
    els.learningStatus.value = data.progress?.status || "to learn";

    // Render full question list for this category
    const catKeys = Object.keys(state.categories);
    for (const key of catKeys) {
      if (state.categories[key].find((q) => q.id === id)) {
        renderQuestionList(key);
        break;
      }
    }
  } finally {
    els.gradeBtn.disabled = false;
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
      }),
    });

    if (!result.ok) {
      els.gradingResult.className = "grading-result";
      els.gradingResult.innerHTML = `<div class="feedback" style="color:var(--danger)">Grading unavailable: ${escapeHtml(result.error)}</div>`;
      return;
    }

    // Show score and feedback
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

    // Update progress status
    els.learningStatus.value = result.score >= 4 ? "learned" : (state.selected.progress?.status || "learning");
    saveProgress();

    // Show reference answer
    if (state.selected.reference_answer) {
      els.referenceText.textContent = state.selected.reference_answer;
      els.referenceAnswer.classList.remove("hidden");
    }
  } catch (error) {
    els.gradingResult.className = "grading-result";
    els.gradingResult.innerHTML = `<div class="feedback" style="color:var(--danger)">Error: ${escapeHtml(error.message)}</div>`;
  } finally {
    setBusy(false);
  }
}

// ── Progress ───────────────────────────────────────────────────────

async function saveProgress() {
  if (!state.selectedId) return;
  await api(`/api/mle/progress/${encodeURIComponent(state.selectedId)}`, {
    method: "PUT",
    body: JSON.stringify({ status: els.learningStatus.value }),
  });
}

async function resetProgress() {
  if (!state.selectedId) return;
  await api(`/api/mle/progress/${encodeURIComponent(state.selectedId)}`, {
    method: "PUT",
    body: JSON.stringify({ status: "to learn" }),
  });
  state.selected.progress = { status: "to learn", score: null, graded_at: null };
  els.learningStatus.value = "to learn";
  els.gradingResult.className = "grading-result empty";
  els.referenceAnswer.classList.add("hidden");
}

// ── Busy indicator ─────────────────────────────────────────────────

function setBusy(isBusy) {
  els.gradeBtn.disabled = isBusy;
  els.answerInput.disabled = isBusy;
}

// ── Event wiring & bootstrap ───────────────────────────────────────

els.gradeBtn.addEventListener("click", gradeAnswer);
els.resetBtn.addEventListener("click", resetProgress);
els.learningStatus.addEventListener("change", saveProgress);

// Boot the app
loadQuestions().catch((error) => {
  els.gradingResult.className = "grading-result";
  els.gradingResult.innerHTML = `<div class="feedback" style="color:var(--danger)">Startup error: ${escapeHtml(error.message)}</div>`;
});
