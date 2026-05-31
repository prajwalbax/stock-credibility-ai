const form = document.querySelector("#analysis-form");
const tickerInput = document.querySelector("#ticker");
const periodInput = document.querySelector("#period");
const intervalInput = document.querySelector("#interval");
const runButton = document.querySelector("#run-button");
const activityList = document.querySelector("#activity-list");
const scoreRing = document.querySelector("#score-ring");
const scoreValue = document.querySelector("#score-value");
const marketBias = document.querySelector("#market-bias");
const scoreCaption = document.querySelector("#score-caption");
const confidenceValue = document.querySelector("#confidence-value");
const confidenceCaption = document.querySelector("#confidence-caption");
const conflictCount = document.querySelector("#conflict-count");
const conflictCaption = document.querySelector("#conflict-caption");
const agentGrid = document.querySelector("#agent-grid");
const narrative = document.querySelector("#narrative");
const weightsList = document.querySelector("#weights-list");
const conflictsList = document.querySelector("#conflicts-list");
const xaiFactors = document.querySelector("#xai-factors");
const evaluationMetrics = document.querySelector("#evaluation-metrics");

const steps = [
  "Fetching free Yahoo Finance market data",
  "Technical analyst evaluating trend, volume, volatility, and support zones",
  "Sentiment analyst reading Google News RSS narratives",
  "Fundamental analyst checking valuation, leverage, growth, and margins",
  "Score arbiter resolving conflicts and dynamic weights",
  "Report analyst writing the final committee summary",
];

let progressTimer = null;

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const ticker = tickerInput.value.trim().toUpperCase();
  if (!ticker) return;

  setLoading(ticker);
  try {
    const response = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticker,
        period: periodInput.value,
        interval: intervalInput.value,
        max_iterations: 2,
      }),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.detail || `Analysis failed with HTTP ${response.status}`);
    }

    const report = await response.json();
    renderReport(report);
  } catch (error) {
    renderError(error);
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Run Analysis";
    stopProgress();
  }
});

function setLoading(ticker) {
  runButton.disabled = true;
  runButton.textContent = "Running";
  scoreRing.style.setProperty("--score", 0);
  scoreValue.textContent = "--";
  marketBias.textContent = "Analyzing";
  scoreCaption.textContent = `${ticker} committee review in progress.`;
  confidenceValue.textContent = "--";
  confidenceCaption.textContent = "Analysts are forming independent views";
  conflictCount.textContent = "--";
  conflictCaption.textContent = "Waiting for arbitration";
  narrative.textContent = "The final report will appear after the analyst committee finishes.";
  weightsList.innerHTML = "";
  conflictsList.innerHTML = "";
  xaiFactors.innerHTML = "";
  evaluationMetrics.innerHTML = "";
  agentGrid.innerHTML = steps.slice(1, 4).map((step) => `<article class="agent-card placeholder loading">${step}</article>`).join("");
  startProgress();
}

function startProgress() {
  stopProgress();
  let index = 0;
  renderActivity(index);
  progressTimer = window.setInterval(() => {
    index = Math.min(index + 1, steps.length - 1);
    renderActivity(index);
    if (index === steps.length - 1) stopProgress(false);
  }, 1200);
}

function stopProgress(markDone = true) {
  if (progressTimer) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
  if (markDone) {
    activityList.querySelectorAll("li").forEach((item) => {
      item.className = "done";
    });
  }
}

function renderActivity(activeIndex) {
  activityList.innerHTML = steps
    .map((step, index) => {
      const className = index < activeIndex ? "done" : index === activeIndex ? "active" : "";
      return `<li class="${className}">${step}</li>`;
    })
    .join("");
}

function renderReport(report) {
  const score = report.score;
  scoreRing.style.setProperty("--score", score.final_score);
  scoreValue.textContent = score.final_score;
  marketBias.textContent = score.market_bias;
  scoreCaption.textContent = `${report.ticker} credibility analysis completed by ${Object.keys(report.agents).length} agents.`;
  confidenceValue.textContent = `${Math.round(score.confidence * 100)}%`;
  confidenceCaption.textContent = "Committee-level confidence after arbitration";
  conflictCount.textContent = score.conflicts.length;
  conflictCaption.textContent = score.conflicts.length ? "Conflicts affected final weighting" : "No major conflicts detected";
  narrative.textContent = report.narrative;

  agentGrid.innerHTML = Object.values(report.agents).map(renderAgent).join("");
  weightsList.innerHTML = Object.entries(score.weights || {}).map(renderWeight).join("");
  conflictsList.innerHTML = score.conflicts.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
  renderExplainability(report.explainability);
  renderEvaluation(report.evaluation);
}

function renderAgent(agent) {
  const signals = listItems(agent.signals, "No positive signals reported.");
  const risks = listItems(agent.risk_flags, "No major risk flags reported.");
  return `
    <article class="agent-card">
      <header>
        <div>
          <p class="panel-label">${escapeHtml(agent.agent)} Agent</p>
          <h3>${escapeHtml(agent.label)}</h3>
        </div>
        <span class="badge">${Math.round(agent.confidence * 100)}%</span>
      </header>
      <p>${escapeHtml(agent.reasoning?.[0] || "Agent completed its review.")}</p>
      <strong>Signals</strong>
      <ul>${signals}</ul>
      <strong>Risk Flags</strong>
      <ul>${risks}</ul>
    </article>
  `;
}

function renderWeight([name, value]) {
  const percent = Math.round(value * 100);
  return `
    <div class="weight-row">
      <span>${escapeHtml(name)}</span>
      <div class="bar"><span style="--width: ${percent}%"></span></div>
      <strong>${percent}%</strong>
    </div>
  `;
}

function renderExplainability(explainability) {
  if (!explainability) {
    xaiFactors.innerHTML = `<p class="empty-copy">Explainability data was not returned.</p>`;
    return;
  }
  const positives = explainability.top_positive_factors || [];
  const negatives = explainability.top_negative_factors || [];
  xaiFactors.innerHTML = `
    <div>
      <h3>Positive Drivers</h3>
      ${renderFactors(positives, "No positive drivers reported.")}
    </div>
    <div>
      <h3>Risk Drivers</h3>
      ${renderFactors(negatives, "No risk drivers reported.")}
    </div>
    <div class="trace-block">
      <h3>Decision Trace</h3>
      <ol>${(explainability.decision_trace || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
    </div>
  `;
}

function renderFactors(factors, emptyText) {
  if (!factors.length) return `<p class="empty-copy">${emptyText}</p>`;
  return factors
    .map(
      (factor) => `
        <article class="factor-card ${factor.direction}">
          <strong>${escapeHtml(factor.source)} · ${Math.round(factor.impact)} impact</strong>
          <span>${escapeHtml(factor.evidence)}</span>
        </article>
      `,
    )
    .join("");
}

function renderEvaluation(evaluation) {
  if (!evaluation) {
    evaluationMetrics.innerHTML = `<p class="empty-copy">Evaluation metrics were not returned.</p>`;
    return;
  }
  const rows = [
    ["Reliability", evaluation.reliability_score],
    ["Agreement", evaluation.agreement_score],
    ["Data Quality", evaluation.data_quality_score],
    ["Conflict Rate", evaluation.conflict_rate],
    ["Confidence Dispersion", evaluation.confidence_dispersion],
  ];
  evaluationMetrics.innerHTML = `
    ${rows.map(([label, value]) => renderMetricRow(label, value)).join("")}
    ${(evaluation.notes || []).map((note) => `<p class="metric-note">${escapeHtml(note)}</p>`).join("")}
  `;
}

function renderMetricRow(label, value) {
  const percent = Math.max(0, Math.min(100, Math.round(Number(value) * 100)));
  return `
    <div class="metric-row">
      <span>${escapeHtml(label)}</span>
      <div class="bar"><span style="--width: ${percent}%"></span></div>
      <strong>${percent}%</strong>
    </div>
  `;
}

function listItems(items, emptyText) {
  const values = Array.isArray(items) && items.length ? items : [emptyText];
  return values.map((item) => `<li>${escapeHtml(item)}</li>`).join("");
}

function renderError(error) {
  activityList.innerHTML = `<li class="error">${escapeHtml(error.message)}</li>`;
  marketBias.textContent = "Error";
  scoreCaption.textContent = "The committee run could not complete. Check the backend logs for details.";
  agentGrid.innerHTML = `<article class="agent-card placeholder">${escapeHtml(error.message)}</article>`;
  xaiFactors.innerHTML = "";
  evaluationMetrics.innerHTML = "";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
