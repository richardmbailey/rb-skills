"use strict";

const byId = (id) => document.getElementById(id);
const controls = {
  model: byId("model-type"), angle: byId("repose-angle"),
  size: byId("grid-size"), seed: byId("seed"), mode: byId("drop-mode"),
  noise: byId("central-noise"), batch: byId("batch-size"), interval: byId("interval"), xmin: byId("xmin"),
  start: byId("start"), pause: byId("pause"), step: byId("step"), reset: byId("reset"),
};
let running = false;
let requestInFlight = false;
let timer = null;
let lastPayload = null;

function setStatus(message, isError = false) {
  const node = byId("status");
  node.textContent = message;
  node.style.color = isError ? "#ff9a79" : "";
}

async function request(path, options = {}) {
  const response = await fetch(path, options);
  let payload;
  try { payload = await response.json(); } catch { throw new Error(`Server returned ${response.status} without valid JSON`); }
  if (!response.ok) throw new Error(payload.error || `Request failed with status ${response.status}`);
  return payload;
}

function numberValue(control, name) {
  const value = Number(control.value);
  if (!Number.isInteger(value)) throw new Error(`${name} must be an integer`);
  return value;
}

function syncSourceControls(model = null) {
  if (model) {
    controls.model.value = model.model_type;
    controls.angle.value = String(model.angle_of_repose_degrees);
    controls.size.value = String(model.size);
    controls.seed.value = String(model.seed);
    controls.mode.value = model.drop_mode;
    controls.noise.value = String(model.central_noise_radius || 0);
  }
  controls.noise.disabled = controls.mode.value !== "center";
  controls.angle.disabled = controls.model.value !== "slope";
}

async function post(path, body) {
  return request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

function heightColour(height, maximumHeight, modelType, lightnessOffset = 0) {
  if (modelType === "btw") {
    const colours = ["#17201d", "#566c51", "#d49542", "#ec6c32"];
    return colours[height] || "#ff5f45";
  }
  if (height === 0) return lightnessOffset < 0 ? "#111815" : "#17201d";
  const ratio = Math.min(1, height / Math.max(1, maximumHeight));
  const hue = 105 - ratio * 85;
  const lightness = Math.max(16, 28 + ratio * 28 + lightnessOffset);
  return `hsl(${hue}, 52%, ${lightness}%)`;
}

function drawPile(model) {
  const canvas = byId("pile");
  const context = canvas.getContext("2d");
  const grid = model.grid;
  const size = grid.length;
  const cell = canvas.width / size;
  const maximumHeight = model.maximum_height_layers;
  context.clearRect(0, 0, canvas.width, canvas.height);
  for (let row = 0; row < size; row += 1) {
    for (let column = 0; column < size; column += 1) {
      context.fillStyle = heightColour(grid[row][column], maximumHeight, model.model_type);
      context.fillRect(column * cell, row * cell, Math.ceil(cell), Math.ceil(cell));
    }
  }
  if (cell >= 7) {
    context.strokeStyle = "rgba(255,255,255,.065)";
    context.lineWidth = 1;
    for (let index = 0; index <= size; index += 1) {
      const point = Math.round(index * cell) + .5;
      context.beginPath(); context.moveTo(point, 0); context.lineTo(point, canvas.height); context.stroke();
      context.beginPath(); context.moveTo(0, point); context.lineTo(canvas.width, point); context.stroke();
    }
  }
}

function fillPolygon(context, points, colour) {
  context.fillStyle = colour;
  context.beginPath();
  context.moveTo(points[0][0], points[0][1]);
  for (let index = 1; index < points.length; index += 1) context.lineTo(points[index][0], points[index][1]);
  context.closePath();
  context.fill();
}

function drawRelief(model) {
  const canvas = byId("pile-3d");
  const context = canvas.getContext("2d");
  const width = canvas.width, height = canvas.height;
  const grid = model.grid, size = grid.length;
  const cameraAngle = 40 * Math.PI / 180;
  const margin = 42;
  const maximumHeight = model.model_type === "slope" ? model.maximum_height_layers : 3;
  // tileWidth spans a projected cell diagonal, so one cell edge is tileWidth / sqrt(2).
  const projectedLayerHeight = model.model_type === "slope"
    ? model.layer_height_cells * Math.cos(cameraAngle) / Math.sqrt(2)
    : .62;
  const tileWidth = Math.min(
    (width - margin * 2) / size,
    (height - margin * 2) / (size * Math.sin(cameraAngle) + maximumHeight * projectedLayerHeight),
  );
  const tileHeight = tileWidth * Math.sin(cameraAngle);
  const heightStep = tileWidth * projectedLayerHeight;
  const originX = width / 2;
  const originY = margin + maximumHeight * heightStep + tileHeight / 2;
  const topColours = ["#26332e", "#738b68", "#d6a14e", "#ef7540"];
  const leftColours = ["#17201d", "#41523f", "#8d612f", "#9b4428"];
  const rightColours = ["#111815", "#53664c", "#aa7738", "#bd5330"];

  context.clearRect(0, 0, width, height);
  const backdrop = context.createLinearGradient(0, 0, 0, height);
  backdrop.addColorStop(0, "#111815");
  backdrop.addColorStop(1, "#080d0b");
  context.fillStyle = backdrop;
  context.fillRect(0, 0, width, height);

  for (let diagonal = 0; diagonal <= (size - 1) * 2; diagonal += 1) {
    const firstRow = Math.max(0, diagonal - size + 1);
    const lastRow = Math.min(size - 1, diagonal);
    for (let row = firstRow; row <= lastRow; row += 1) {
      const column = diagonal - row;
      const grains = grid[row][column];
      const centreX = originX + (column - row) * tileWidth / 2;
      const baseY = originY + (column + row) * tileHeight / 2;
      const topY = baseY - grains * heightStep;
      const top = [centreX, topY - tileHeight / 2];
      const right = [centreX + tileWidth / 2, topY];
      const bottom = [centreX, topY + tileHeight / 2];
      const left = [centreX - tileWidth / 2, topY];

      if (grains > 0) {
        const leftColour = model.model_type === "slope" ? heightColour(grains, maximumHeight, model.model_type, -12) : leftColours[grains];
        const rightColour = model.model_type === "slope" ? heightColour(grains, maximumHeight, model.model_type, -7) : rightColours[grains];
        fillPolygon(context, [left, bottom, [bottom[0], bottom[1] + grains * heightStep], [left[0], left[1] + grains * heightStep]], leftColour);
        fillPolygon(context, [right, bottom, [bottom[0], bottom[1] + grains * heightStep], [right[0], right[1] + grains * heightStep]], rightColour);
      }
      const topColour = model.model_type === "slope" ? heightColour(grains, maximumHeight, model.model_type) : topColours[grains];
      fillPolygon(context, [top, right, bottom, left], topColour);
      context.strokeStyle = "rgba(244,234,216,.09)";
      context.lineWidth = Math.max(.45, tileWidth / 45);
      context.beginPath();
      context.moveTo(top[0], top[1]);
      context.lineTo(right[0], right[1]);
      context.lineTo(bottom[0], bottom[1]);
      context.lineTo(left[0], left[1]);
      context.closePath();
      context.stroke();
    }
  }

  if (model.drop_mode === "center") {
    const source = Math.floor(size / 2);
    const noiseRadius = model.central_noise_radius || 0;
    const grains = grid[source][source];
    const sourceX = originX;
    const sourceBaseY = originY + source * tileHeight;
    const sourceTopY = sourceBaseY - grains * heightStep - tileHeight / 2;
    const markerTop = Math.max(24, sourceTopY - Math.max(24, tileWidth * .9));
    if (noiseRadius > 0) {
      const projectedRadius = noiseRadius / Math.sqrt(2);
      context.save();
      context.strokeStyle = "rgba(255,208,122,.72)";
      context.lineWidth = Math.max(1.5, tileWidth / 24);
      context.setLineDash([Math.max(3, tileWidth / 8), Math.max(3, tileWidth / 10)]);
      context.beginPath();
      context.ellipse(
        sourceX,
        sourceBaseY,
        projectedRadius * tileWidth,
        projectedRadius * tileHeight,
        0,
        0,
        Math.PI * 2,
      );
      context.stroke();
      context.restore();
    }
    context.strokeStyle = "#ffd07a";
    context.fillStyle = "#ffd07a";
    context.lineWidth = Math.max(2, tileWidth / 18);
    context.beginPath(); context.moveTo(sourceX, markerTop); context.lineTo(sourceX, sourceTopY - 5); context.stroke();
    context.beginPath(); context.arc(sourceX, markerTop, Math.max(4, tileWidth / 8), 0, Math.PI * 2); context.fill();
  }
}

function drawLogPlot(canvasId, points, xKey, yKey, yLabel) {
  const canvas = byId(canvasId);
  const context = canvas.getContext("2d");
  const width = canvas.width, height = canvas.height;
  const pad = { left: 78, right: 24, top: 24, bottom: 58 };
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#0b100e"; context.fillRect(0, 0, width, height);
  const valid = points.filter((point) => point[xKey] > 0 && point[yKey] > 0);
  context.font = "13px system-ui"; context.fillStyle = "#9eaa9f";
  if (!valid.length) { context.textAlign = "center"; context.fillText("Positive avalanches will appear here", width / 2, height / 2); return; }
  const xs = valid.map((point) => Math.log10(point[xKey]));
  const ys = valid.map((point) => Math.log10(point[yKey]));
  let xmin = Math.min(...xs), xmax = Math.max(...xs), ymin = Math.min(...ys), ymax = Math.max(...ys);
  if (xmin === xmax) { xmin -= .5; xmax += .5; }
  if (ymin === ymax) { ymin -= .5; ymax += .5; }
  const projectX = (value) => pad.left + (Math.log10(value) - xmin) / (xmax - xmin) * (width - pad.left - pad.right);
  const projectY = (value) => height - pad.bottom - (Math.log10(value) - ymin) / (ymax - ymin) * (height - pad.top - pad.bottom);
  context.strokeStyle = "rgba(244,234,216,.2)"; context.lineWidth = 1;
  context.beginPath(); context.moveTo(pad.left, pad.top); context.lineTo(pad.left, height - pad.bottom); context.lineTo(width - pad.right, height - pad.bottom); context.stroke();
  context.strokeStyle = "#edae49"; context.fillStyle = "#edae49"; context.lineWidth = 2;
  context.beginPath(); valid.forEach((point, index) => { const x = projectX(point[xKey]), y = projectY(point[yKey]); index ? context.lineTo(x, y) : context.moveTo(x, y); }); context.stroke();
  valid.forEach((point) => { context.beginPath(); context.arc(projectX(point[xKey]), projectY(point[yKey]), 3.5, 0, Math.PI * 2); context.fill(); });
  context.fillStyle = "#9eaa9f"; context.textAlign = "center"; context.fillText("Avalanche size (log scale)", (pad.left + width - pad.right) / 2, height - 18);
  context.save(); context.translate(20, (pad.top + height - pad.bottom) / 2); context.rotate(-Math.PI / 2); context.fillText(yLabel, 0, 0); context.restore();
  context.textAlign = "left"; context.fillText(`10^${xmin.toFixed(1)}`, pad.left, height - pad.bottom + 22);
  context.textAlign = "right"; context.fillText(`10^${xmax.toFixed(1)}`, width - pad.right, height - pad.bottom + 22);
}

function render(payload) {
  const model = payload.model, analysis = payload.analysis, fit = analysis.power_law_fit;
  controls.noise.max = String(payload.limits.maximum_central_noise_radius);
  controls.angle.min = String(payload.limits.minimum_repose_angle_degrees);
  controls.angle.max = String(payload.limits.maximum_repose_angle_degrees);
  syncSourceControls(model);
  lastPayload = payload;
  drawPile(model);
  drawRelief(model);
  drawLogPlot("frequency", analysis.frequency, "size", "frequency", "Relative frequency");
  drawLogPlot("ccdf", analysis.ccdf, "size", "probability", "P(S ≥ size)");
  byId("added").textContent = model.total_added.toLocaleString();
  byId("retained").textContent = model.retained_mass.toLocaleString();
  byId("lost").textContent = model.total_lost.toLocaleString();
  byId("positive").textContent = model.positive_avalanches.toLocaleString();
  byId("largest").textContent = model.largest_avalanche.toLocaleString();
  byId("maximum-height").textContent = model.maximum_height_layers.toLocaleString();
  byId("maximum-slope").textContent = model.model_type === "slope" ? `${model.maximum_slope_degrees.toFixed(1)}°` : "—";
  byId("height-units").textContent = model.model_type === "slope" ? "Layers" : "BTW states";
  byId("height-max").textContent = model.maximum_height_layers.toLocaleString();
  byId("residual").textContent = model.mass_balance_residual.toLocaleString();
  byId("residual").style.color = model.mass_balance_residual === 0 ? "" : "#ff9a79";
  byId("tail-n").textContent = fit.n.toLocaleString();
  if (fit.status === "estimated") {
    byId("alpha").textContent = fit.alpha.toFixed(3);
    byId("ks").textContent = fit.ks_distance.toFixed(3);
    byId("fit-message").textContent = `Approximate discrete-tail estimate for avalanche sizes at or above ${fit.xmin}.`;
  } else {
    byId("alpha").textContent = "—"; byId("ks").textContent = "—";
    byId("fit-message").textContent = `The selected tail needs at least ${fit.minimum_tail} observations; it currently has ${fit.n}.`;
  }
  setStatus(running ? "Experiment running" : "Ready");
}

async function addStep() {
  if (requestInFlight) return;
  requestInFlight = true;
  controls.step.disabled = true;
  try {
    const payload = await post("/api/step", {
      count: numberValue(controls.batch, "Grains per step"),
      xmin: numberValue(controls.xmin, "Tail threshold"),
      drop_mode: controls.mode.value,
      central_noise_radius: numberValue(controls.noise, "Central jitter radius"),
    });
    render(payload);
  } catch (error) { pause(); setStatus(error.message, true); }
  finally { requestInFlight = false; controls.step.disabled = false; }
}

function schedule() {
  if (!running) return;
  addStep().finally(() => { if (running) timer = window.setTimeout(schedule, Math.max(40, numberValue(controls.interval, "Step interval"))); });
}

function start() {
  if (running) return;
  running = true; controls.start.disabled = true; controls.pause.disabled = false; setStatus("Experiment running"); schedule();
}

function pause() {
  running = false; window.clearTimeout(timer); timer = null; controls.start.disabled = false; controls.pause.disabled = true;
  if (!requestInFlight) setStatus("Paused");
}

async function reset() {
  pause();
  try {
    const payload = await post("/api/reset", {
      size: numberValue(controls.size, "Grid size"), seed: numberValue(controls.seed, "Random seed"),
      drop_mode: controls.mode.value, xmin: numberValue(controls.xmin, "Tail threshold"),
      central_noise_radius: numberValue(controls.noise, "Central jitter radius"),
      model_type: controls.model.value,
      angle_of_repose_degrees: numberValue(controls.angle, "Angle of repose"),
    });
    render(payload); setStatus("Experiment reset");
  } catch (error) { setStatus(error.message, true); }
}

controls.start.addEventListener("click", start);
controls.pause.addEventListener("click", pause);
controls.step.addEventListener("click", addStep);
controls.reset.addEventListener("click", reset);
controls.mode.addEventListener("change", () => syncSourceControls());
controls.model.addEventListener("change", () => {
  syncSourceControls();
  setStatus("Reset experiment to apply the model change");
});
controls.angle.addEventListener("change", () => setStatus("Reset experiment to apply the repose angle"));
syncSourceControls();
window.addEventListener("beforeunload", pause);
request("/api/state").then(render).catch((error) => setStatus(error.message, true));

window.render_game_to_text = () => JSON.stringify(lastPayload ? {
  coordinate_system: "rows run top-to-bottom; columns run left-to-right; heights are integer grain layers; physical layers are 0.1 horizontal-cell widths high",
  source: lastPayload.model.drop_mode === "center" ? "central source with optional jitter" : "uniform random across platform",
  model_type: lastPayload.model.model_type,
  angle_of_repose_degrees: lastPayload.model.angle_of_repose_degrees,
  central_noise_radius_cells: lastPayload.model.central_noise_radius,
  maximum_height_layers: lastPayload.model.maximum_height_layers,
  maximum_height_cells: lastPayload.model.maximum_height_cells,
  maximum_slope_degrees: lastPayload.model.maximum_slope_degrees,
  grid_size: lastPayload.model.size,
  total_added: lastPayload.model.total_added,
  retained_mass: lastPayload.model.retained_mass,
  total_lost: lastPayload.model.total_lost,
  mass_balance_residual: lastPayload.model.mass_balance_residual,
  largest_avalanche: lastPayload.model.largest_avalanche,
  view: lastPayload.model.model_type === "slope"
    ? "two-dimensional lattice plus physically scaled isometric relief viewed at approximately 40 degrees"
    : "two-dimensional lattice plus vertically exaggerated BTW relief viewed at approximately 40 degrees",
} : { status: "connecting" });
