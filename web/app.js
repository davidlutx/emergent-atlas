import { formatRule, makeGrid, parseRule, stepGrid } from "./ca.js";

let size = 50;
const COLORS = ["#2d7890", "#b26832", "#74579b", "#7d7627", "#a04665"];
const FEATURE_LABELS = {
  mean_density: "Mean density", final_density: "Final density", activity: "Activity",
  growth: "Growth trend", entropy: "Binary entropy", normalized_lifespan: "Lifespan",
  recurrence: "Recurrence", component_count: "Components",
};

const canvas = document.querySelector("#grid");
const context = canvas.getContext("2d");
let grid = makeGrid(size);
let initialGrid = grid.slice();
let ruleBits = parseRule("B3/S23");
let generation = 0;
let running = false;
let lastFrame = 0;
let drawing = false;
let drawValue = 1;
let lastDrawn = -1;
let analysisData = null;

const $ = (selector) => document.querySelector(selector);
const population = () => grid.reduce((sum, cell) => sum + cell, 0);

function renderGrid() {
  const cell = canvas.width / size;
  context.fillStyle = "#ffffff";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "#243f56";
  for (let i = 0; i < grid.length; i += 1) {
    if (!grid[i]) continue;
    const row = Math.floor(i / size);
    const col = i % size;
    const inset = size <= 50 ? 1 : 0.5;
    context.fillRect(col * cell + inset, row * cell + inset, cell - inset * 2, cell - inset * 2);
  }
  context.strokeStyle = size <= 75 ? "rgba(70,85,95,.14)" : "rgba(70,85,95,.08)";
  context.lineWidth = 1;
  for (let i = 0; i <= size; i += 1) {
    context.beginPath(); context.moveTo(i * cell, 0); context.lineTo(i * cell, canvas.height); context.stroke();
    context.beginPath(); context.moveTo(0, i * cell); context.lineTo(canvas.width, i * cell); context.stroke();
  }
  $("#generation").textContent = generation.toLocaleString();
  $("#population").textContent = population().toLocaleString();
  const rule = formatRule(ruleBits);
  $("#rule-readout").textContent = rule;
  $("#rule-title").textContent = rule;
}

function advance() {
  const noise = Number($("#noise").value) / 100;
  grid = stepGrid(grid, size, ruleBits, noise, Math.random, $("#boundary").value);
  generation += 1;
  renderGrid();
}

function animationLoop(timestamp) {
  if (!running) return;
  const delay = 1000 / Number($("#speed").value);
  if (timestamp - lastFrame >= delay) {
    advance();
    lastFrame = timestamp;
  }
  requestAnimationFrame(animationLoop);
}

function setRunning(value) {
  const wasRunning = running;
  running = value;
  $("#run").classList.toggle("active", value);
  $("#pause").classList.toggle("active", !value);
  if (value && !wasRunning) requestAnimationFrame(animationLoop);
}

function saveInitial() {
  initialGrid = grid.slice();
  generation = 0;
}

function setRule(rule, scroll = false) {
  ruleBits = parseRule(rule);
  document.querySelectorAll(".toggles button").forEach((button) => {
    const enabled = Boolean(ruleBits[Number(button.dataset.bit)]);
    button.classList.toggle("on", enabled);
    button.textContent = enabled ? "✓" : "";
    button.setAttribute("aria-pressed", String(enabled));
  });
  renderGrid();
  if (scroll) document.querySelector("#simulator").scrollIntoView({ behavior: "smooth" });
}

function buildRuleEditor() {
  for (const [selector, offset] of [["#birth-toggles", 0], ["#survival-toggles", 9]]) {
    const container = $(selector);
    for (let count = 0; count <= 8; count += 1) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = ruleBits[offset + count] ? "✓" : "";
      button.dataset.bit = offset + count;
      button.setAttribute("aria-label", `${offset ? "Survive" : "Birth"} with ${count} neighbors`);
      button.addEventListener("click", () => {
        const bit = Number(button.dataset.bit);
        ruleBits[bit] ^= 1;
        button.textContent = ruleBits[bit] ? "✓" : "";
        setRule(formatRule(ruleBits));
      });
      container.append(button);
    }
  }
  setRule("B3/S23");
}

function canvasIndex(event) {
  const bounds = canvas.getBoundingClientRect();
  const col = Math.max(0, Math.min(size - 1, Math.floor((event.clientX - bounds.left) / bounds.width * size)));
  const row = Math.max(0, Math.min(size - 1, Math.floor((event.clientY - bounds.top) / bounds.height * size)));
  return row * size + col;
}

function drawAt(event) {
  const index = canvasIndex(event);
  if (index === lastDrawn) return;
  grid[index] = drawValue;
  lastDrawn = index;
  renderGrid();
}

canvas.addEventListener("pointerdown", (event) => {
  drawing = true;
  lastDrawn = -1;
  drawValue = grid[canvasIndex(event)] ? 0 : 1;
  canvas.setPointerCapture(event.pointerId);
  drawAt(event);
});
canvas.addEventListener("pointermove", (event) => { if (drawing) drawAt(event); });
canvas.addEventListener("pointerup", () => { drawing = false; saveInitial(); renderGrid(); });
canvas.addEventListener("pointercancel", () => { drawing = false; });

$("#run").addEventListener("click", () => setRunning(true));
$("#pause").addEventListener("click", () => setRunning(false));
$("#step").addEventListener("click", () => { setRunning(false); advance(); });
function randomizeGrid() {
  setRunning(false);
  grid = makeGrid(size, Number($("#density").value) / 100);
  saveInitial(); renderGrid();
}

function loadPattern(name) {
  const patterns = {
    block: [[0, 0], [0, 1], [1, 0], [1, 1]],
    blinker: [[0, -1], [0, 0], [0, 1]],
    glider: [[-1, 0], [0, 1], [1, -1], [1, 0], [1, 1]],
  };
  setRunning(false);
  grid = makeGrid(size);
  const center = Math.floor(size / 2);
  for (const [rowOffset, colOffset] of patterns[name]) {
    grid[(center + rowOffset) * size + center + colOffset] = 1;
  }
  saveInitial();
  renderGrid();
}

$("#randomize").addEventListener("click", randomizeGrid);
$("#clear").addEventListener("click", () => { setRunning(false); grid = makeGrid(size); saveInitial(); renderGrid(); });
$("#reset").addEventListener("click", () => { setRunning(false); grid = initialGrid.slice(); generation = 0; renderGrid(); });
$("#speed").addEventListener("input", (event) => { $("#speed-value").textContent = `${event.target.value} gen/s`; });
$("#density").addEventListener("input", (event) => { $("#density-value").textContent = `${event.target.value}%`; });
$("#density").addEventListener("change", randomizeGrid);
$("#noise").addEventListener("input", (event) => { $("#noise-value").textContent = `${event.target.value}%`; });
$("#grid-size").addEventListener("change", (event) => {
  size = Number(event.target.value);
  randomizeGrid();
});
document.querySelectorAll("[data-rule]").forEach((button) => button.addEventListener("click", () => setRule(button.dataset.rule, true)));
document.querySelectorAll("[data-pattern]").forEach((button) => button.addEventListener("click", () => loadPattern(button.dataset.pattern)));

function extent(values, padding = 0.08) {
  const min = Math.min(...values); const max = Math.max(...values); const range = max - min || 1;
  return [min - range * padding, max + range * padding];
}
const scale = (value, [min, max], [outMin, outMax]) => outMin + (value - min) / (max - min) * (outMax - outMin);

function svgElement(name, attributes = {}) {
  const element = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value);
  return element;
}

function drawAxes(svg, xRange, yRange, bounds) {
  for (let i = 0; i <= 4; i += 1) {
    const x = bounds.left + i * (bounds.right - bounds.left) / 4;
    const y = bounds.top + i * (bounds.bottom - bounds.top) / 4;
    svg.append(svgElement("line", { x1: x, y1: bounds.top, x2: x, y2: bounds.bottom, class: "plot-grid" }));
    svg.append(svgElement("line", { x1: bounds.left, y1: y, x2: bounds.right, y2: y, class: "plot-grid" }));
  }
  svg.append(svgElement("line", { x1: bounds.left, y1: bounds.bottom, x2: bounds.right, y2: bounds.bottom, class: "plot-axis" }));
  svg.append(svgElement("line", { x1: bounds.left, y1: bounds.top, x2: bounds.left, y2: bounds.bottom, class: "plot-axis" }));
  const xLabel = svgElement("text", { x: (bounds.left + bounds.right) / 2, y: bounds.bottom + 42, "text-anchor": "middle", class: "axis-label" });
  xLabel.textContent = "PCA COMPONENT 1"; svg.append(xLabel);
  const yLabel = svgElement("text", { x: 18, y: (bounds.top + bounds.bottom) / 2, "text-anchor": "middle", class: "axis-label", transform: `rotate(-90 18 ${(bounds.top + bounds.bottom) / 2})` });
  yLabel.textContent = "PCA COMPONENT 2"; svg.append(yLabel);
}

function showRuleDetail(point) {
  const detail = $("#rule-detail");
  detail.innerHTML = `<span class="detail-cluster" style="color:${COLORS[point.cluster]}">Cluster ${point.cluster + 1}${point.is_outlier ? " · ML outlier" : ""}</span><h3>${point.rule}</h3><div class="feature-list">${Object.entries(point.features).map(([name, value]) => `<div><span>${FEATURE_LABELS[name]}</span><strong>${name === "component_count" ? value.toFixed(1) : value.toFixed(3)}</strong></div>`).join("")}</div><button class="load-rule">Load rule</button>`;
  detail.querySelector("button").addEventListener("click", () => setRule(point.rule, true));
}

function renderBehaviorMap(data) {
  const svg = $("#behavior-map");
  const bounds = { left: 64, right: 730, top: 42, bottom: 505 };
  const xRange = extent(data.rules.map((point) => point.pca_x));
  const yRange = extent(data.rules.map((point) => point.pca_y));
  drawAxes(svg, xRange, yRange, bounds);
  const tooltip = $("#plot-tooltip");
  for (const point of data.rules) {
    const cx = scale(point.pca_x, xRange, [bounds.left, bounds.right]);
    const cy = scale(point.pca_y, yRange, [bounds.bottom, bounds.top]);
    if (point.is_outlier) svg.append(svgElement("circle", { cx, cy, r: 11, class: "outlier-ring" }));
    const circle = svgElement("circle", { cx, cy, r: 5.5, fill: COLORS[point.cluster], class: "point", "data-cluster": point.cluster });
    circle.addEventListener("pointerenter", (event) => {
      tooltip.hidden = false;
      tooltip.innerHTML = `<strong>${point.rule}</strong><br>Cluster ${point.cluster + 1}<br>Density ${point.features.mean_density.toFixed(3)}<br>Activity ${point.features.activity.toFixed(3)}`;
      tooltip.style.left = `${event.clientX + 14}px`; tooltip.style.top = `${event.clientY + 14}px`;
    });
    circle.addEventListener("pointermove", (event) => { tooltip.style.left = `${event.clientX + 14}px`; tooltip.style.top = `${event.clientY + 14}px`; });
    circle.addEventListener("pointerleave", () => { tooltip.hidden = true; });
    circle.addEventListener("click", () => {
      svg.querySelectorAll(".point").forEach((item) => item.classList.remove("selected"));
      circle.classList.add("selected"); showRuleDetail(point);
    });
    svg.append(circle);
  }
  const legend = $("#cluster-legend");
  data.clusters.forEach((cluster) => {
    const button = document.createElement("button");
    button.innerHTML = `<i style="background:${COLORS[cluster.cluster]}"></i> C${cluster.cluster + 1}`;
    button.addEventListener("mouseenter", () => svg.querySelectorAll(".point").forEach((point) => point.classList.toggle("dimmed", Number(point.dataset.cluster) !== cluster.cluster)));
    button.addEventListener("mouseleave", () => svg.querySelectorAll(".point").forEach((point) => point.classList.remove("dimmed")));
    legend.append(button);
  });
}

function clusterDescription(features) {
  if (features.mean_density < 0.32) return "Sparse outcomes with declining population and many fragmented structures.";
  if (features.mean_density > 0.6) return "Dense, persistent worlds with relatively low average temporal change.";
  return "Persistent, high-entropy worlds with the strongest ongoing cellular activity.";
}

function renderFindings(data) {
  const comparisons = data.supervised.cross_validation || [];
  const forest = comparisons.find((item) => item.model === "Random Forest");
  const majority = comparisons.find((item) => item.model === "Majority baseline");
  const accuracy = forest?.accuracy_mean ?? data.supervised.accuracy;
  $("#accuracy").textContent = `${(accuracy * 100).toFixed(1)}%`;
  $("#baseline").textContent = forest && majority
    ? `Repeated 5-fold CV: ± ${(forest.accuracy_std * 100).toFixed(1)} points · baseline ${(majority.accuracy_mean * 100).toFixed(1)}%`
    : `Majority baseline: ${(data.supervised.majority_baseline * 100).toFixed(1)}% · n=${data.supervised.test_size} test rules`;
  const variance = data.metadata.pca_explained_variance.reduce((sum, value) => sum + value, 0);
  $("#variance").textContent = `${(variance * 100).toFixed(1)}%`;
  $("#outlier-rule").textContent = data.metadata.outlier_rule;
  $("#outlier-preset").dataset.rule = data.metadata.outlier_rule;
  $("#load-outlier").addEventListener("click", () => setRule(data.metadata.outlier_rule, true));

  const cards = $("#cluster-cards");
  data.clusters.forEach((cluster) => {
    const card = document.createElement("article"); card.className = "cluster-card";
    card.style.borderTopColor = COLORS[cluster.cluster];
    card.innerHTML = `<header><h3>Cluster ${cluster.cluster + 1}</h3><span>${cluster.size} rules</span></header><p>${clusterDescription(cluster.features)}</p><p>Exemplar: <strong>${cluster.representative_rule}</strong></p>`;
    cards.append(card);
  });

  const importance = $("#importance-chart");
  const maximum = data.supervised.feature_importance[0].importance;
  data.supervised.feature_importance.slice(0, 10).forEach((item) => {
    const row = document.createElement("div"); row.className = "bar-row";
    row.innerHTML = `<strong>${item.feature}</strong><div class="bar-track"><div class="bar-fill" style="width:${item.importance / maximum * 100}%"></div></div><span class="bar-value">${item.importance.toFixed(3)}</span>`;
    importance.append(row);
  });
  renderNoiseChart(data.noise);
}

function renderNoiseChart(records) {
  const svg = $("#noise-chart");
  const bounds = { left: 48, right: 596, top: 18, bottom: 314 };
  const xRange = extent(records.map((item) => item.pca_x));
  const yRange = extent(records.map((item) => item.pca_y));
  drawAxes(svg, xRange, yRange, bounds);
  const rules = [...new Set(records.map((item) => item.rule))];
  rules.forEach((rule, ruleIndex) => {
    const subset = records.filter((item) => item.rule === rule).sort((a, b) => a.noise - b.noise);
    const points = subset.map((item) => `${scale(item.pca_x, xRange, [bounds.left, bounds.right])},${scale(item.pca_y, yRange, [bounds.bottom, bounds.top])}`).join(" ");
    svg.append(svgElement("polyline", { points, stroke: COLORS[ruleIndex % COLORS.length], class: "noise-path" }));
    subset.forEach((item) => {
      const dot = svgElement("circle", { cx: scale(item.pca_x, xRange, [bounds.left, bounds.right]), cy: scale(item.pca_y, yRange, [bounds.bottom, bounds.top]), r: 5, fill: COLORS[ruleIndex % COLORS.length], class: "noise-dot" });
      const title = svgElement("title"); title.textContent = `${rule} · noise ${item.noise} · displacement ${item.displacement.toFixed(2)}`; dot.append(title); svg.append(dot);
    });
  });
}

async function loadAnalysis() {
  try {
    const response = await fetch("data/rule_analysis.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    analysisData = await response.json();
    renderBehaviorMap(analysisData); renderFindings(analysisData);
  } catch (error) {
    $("#rule-detail").innerHTML = `<h3>Data unavailable</h3><p>Serve the project over HTTP so the browser can load the generated analysis JSON.</p>`;
    console.error(error);
  }
}

buildRuleEditor();
grid = makeGrid(size, 0.3); saveInitial(); renderGrid();
loadAnalysis();
