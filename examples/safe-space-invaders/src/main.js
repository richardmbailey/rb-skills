import {
  advanceGame,
  createGame,
  resetGame,
  serialiseGame,
  setInput,
  startGame,
  togglePause,
} from "./game-core.js";
import { createRenderer } from "./renderer.js";

const canvas = document.querySelector("#game-canvas");
const shell = document.querySelector("#game-shell");
const overlay = document.querySelector("#game-overlay");
const overlayKicker = document.querySelector("#overlay-kicker");
const overlayTitle = document.querySelector("#overlay-title");
const overlayCopy = document.querySelector("#overlay-copy");
const startButton = document.querySelector("#start-button");
const errorPanel = document.querySelector("#renderer-error");
const noticePanel = document.querySelector("#game-notice");
const scoreValue = document.querySelector("#score-value");
const livesValue = document.querySelector("#lives-value");
const waveValue = document.querySelector("#wave-value");
const statusValue = document.querySelector("#status-value");

const game = createGame();
let previousTimestamp = performance.now();
let manualStepping = false;
let lastOverlayMode = null;
let noticeTimer = null;

function showRendererError(message) {
  errorPanel.textContent = message;
  errorPanel.hidden = false;
  overlay.hidden = true;
  shell.classList.add("has-error");
}

function showNotice(message) {
  noticePanel.textContent = message;
  noticePanel.hidden = false;
  if (noticeTimer !== null) window.clearTimeout(noticeTimer);
  noticeTimer = window.setTimeout(() => {
    noticePanel.hidden = true;
    noticeTimer = null;
  }, 2600);
}

const renderer = createRenderer(canvas, showRendererError);

function modeLabel(mode) {
  return ({
    ready: "Ready",
    playing: "Defending",
    paused: "Paused",
    wave_cleared: "Sector clear",
    victory: "System secure",
    defeat: "Defence breached",
  })[mode] || mode;
}

function updateOverlay() {
  if (lastOverlayMode === game.mode) return;
  lastOverlayMode = game.mode;
  if (game.mode === "playing" || game.mode === "wave_cleared") {
    overlay.hidden = true;
    return;
  }
  overlay.hidden = false;
  if (game.mode === "ready") {
    overlayKicker.textContent = "ORBITAL DEFENCE // ONLINE";
    overlayTitle.textContent = "Neon Vanguard";
    overlayCopy.textContent = "Break the descending formation across three escalating waves. Protect the shield line and keep the last city lit.";
    startButton.textContent = "Begin defence";
  } else if (game.mode === "paused") {
    overlayKicker.textContent = "SIMULATION HOLD";
    overlayTitle.textContent = "Paused";
    overlayCopy.textContent = "The formation is frozen. Press P or use the button below to continue.";
    startButton.textContent = "Resume";
  } else if (game.mode === "victory") {
    overlayKicker.textContent = `FINAL SCORE // ${game.score}`;
    overlayTitle.textContent = "System secure";
    overlayCopy.textContent = "All three formations are gone. The horizon belongs to the city again.";
    startButton.textContent = "Defend again";
  } else if (game.mode === "defeat") {
    overlayKicker.textContent = `FINAL SCORE // ${game.score}`;
    overlayTitle.textContent = "Defence breached";
    overlayCopy.textContent = "The formation reached the city line. Recalibrate and launch another defence.";
    startButton.textContent = "Retry mission";
  }
}

function render() {
  scoreValue.textContent = String(game.score).padStart(6, "0");
  livesValue.textContent = "◆".repeat(Math.max(0, game.lives)) || "—";
  waveValue.textContent = `${game.wave} / ${game.config.maxWaves}`;
  statusValue.textContent = modeLabel(game.mode);
  updateOverlay();
  renderer?.render(game);
}

function beginOrResume() {
  if (game.mode === "ready") startGame(game);
  else if (game.mode === "paused") togglePause(game);
  else if (game.mode === "victory" || game.mode === "defeat") {
    resetGame(game);
    startGame(game);
  }
  render();
}

startButton.addEventListener("click", beginOrResume);

const controlledKeys = new Set(["ArrowLeft", "ArrowRight", "KeyA", "KeyD", "Space"]);
window.addEventListener("keydown", (event) => {
  if (controlledKeys.has(event.code)) event.preventDefault();
  if (event.repeat && ["KeyP", "KeyR", "KeyF"].includes(event.code)) return;
  if (event.code === "ArrowLeft" || event.code === "KeyA") setInput(game, { left: true });
  if (event.code === "ArrowRight" || event.code === "KeyD") setInput(game, { right: true });
  if (event.code === "Space") {
    if (game.mode === "ready") startGame(game);
    else setInput(game, { fire: true });
  }
  if (event.code === "KeyP") togglePause(game);
  if (event.code === "KeyR") {
    resetGame(game);
    startGame(game);
  }
  if (event.code === "KeyF") toggleFullscreen();
  render();
});

window.addEventListener("keyup", (event) => {
  if (event.code === "ArrowLeft" || event.code === "KeyA") setInput(game, { left: false });
  if (event.code === "ArrowRight" || event.code === "KeyD") setInput(game, { right: false });
  if (event.code === "Space") setInput(game, { fire: false });
});

window.addEventListener("blur", () => setInput(game, { left: false, right: false, fire: false }));

for (const button of document.querySelectorAll("[data-control]")) {
  const control = button.dataset.control;
  const activate = (event) => {
    event.preventDefault();
    try {
      button.setPointerCapture?.(event.pointerId);
    } catch {
      // Pointer capture is an enhancement; synthetic and interrupted pointers may not be capturable.
    }
    if (control === "left" || control === "right" || control === "fire") {
      setInput(game, { [control]: true });
    } else if (control === "pause") {
      togglePause(game);
    }
    render();
  };
  const release = (event) => {
    event.preventDefault();
    if (control === "left" || control === "right" || control === "fire") {
      setInput(game, { [control]: false });
    }
  };
  button.addEventListener("pointerdown", activate);
  button.addEventListener("pointerup", release);
  button.addEventListener("pointercancel", release);
  button.addEventListener("lostpointercapture", release);
}

async function toggleFullscreen() {
  if (typeof shell.requestFullscreen !== "function") {
    showNotice("Fullscreen is unavailable in this browser.");
    return;
  }
  try {
    if (!document.fullscreenElement) await shell.requestFullscreen();
    else if (typeof document.exitFullscreen === "function") await document.exitFullscreen();
  } catch (error) {
    showNotice(`Fullscreen could not be changed: ${error.message}`);
  }
}

document.addEventListener("fullscreenchange", () => {
  renderer?.resize();
  render();
});
window.addEventListener("resize", () => {
  renderer?.resize();
  render();
});
document.addEventListener("visibilitychange", () => {
  previousTimestamp = performance.now();
  if (document.hidden && game.mode === "playing") togglePause(game);
});

function frame(timestamp) {
  const elapsed = Math.min(0.1, Math.max(0, (timestamp - previousTimestamp) / 1000));
  previousTimestamp = timestamp;
  if (!manualStepping) {
    advanceGame(game, elapsed);
    render();
  }
  requestAnimationFrame(frame);
}

window.render_game_to_text = () => JSON.stringify(serialiseGame(game));
window.advanceTime = (milliseconds) => {
  manualStepping = true;
  const seconds = Math.max(0, Number(milliseconds) / 1000);
  const chunks = Math.ceil(seconds / 0.25);
  for (let index = 0; index < chunks; index += 1) {
    advanceGame(game, Math.min(0.25, seconds - index * 0.25));
  }
  render();
  return window.render_game_to_text();
};

render();
requestAnimationFrame(frame);
