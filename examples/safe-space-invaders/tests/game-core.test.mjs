import test from "node:test";
import assert from "node:assert/strict";

import {
  FIXED_STEP,
  WORLD,
  advanceGame,
  createGame,
  resetGame,
  setInput,
  startGame,
  stepGame,
  togglePause,
} from "../src/game-core.js";
import {
  compose,
  gunshipCamera,
  identity,
  isFiniteMatrix,
  lookAt,
  multiply,
  perspective,
} from "../src/math3d.js";

function game(options = {}) {
  const state = createGame({ seed: 12345, enemyFireRate: 0, ...options });
  startGame(state);
  return state;
}

function almostEqual(actual, expected, tolerance = 1e-6) {
  assert.ok(Math.abs(actual - expected) <= tolerance, `${actual} was not within ${tolerance} of ${expected}`);
}

test("same seed and inputs produce the same complete state", () => {
  const first = game({ enemyFireRate: 0.8 });
  const second = game({ enemyFireRate: 0.8 });
  setInput(first, { right: true, fire: true });
  setInput(second, { right: true, fire: true });
  advanceGame(first, 0.75);
  advanceGame(second, 0.75);
  assert.deepEqual(first, second);
});

test("reset restores seeded initial state and ready mode", () => {
  const state = game();
  state.score = 999;
  state.lives = 1;
  advanceGame(state, 0.4);
  resetGame(state);
  assert.equal(state.mode, "ready");
  assert.equal(state.score, 0);
  assert.equal(state.lives, 3);
  assert.equal(state.invaders.filter((item) => item.alive).length, 45);
  assert.equal(state.rngState, 12345);
});

test("player movement is clamped at both world boundaries", () => {
  const state = game();
  setInput(state, { left: true });
  advanceGame(state, 3);
  almostEqual(state.player.x, WORLD.minX + state.player.width / 2);
  setInput(state, { left: false, right: true });
  for (let index = 0; index < 16; index += 1) advanceGame(state, 0.25);
  almostEqual(state.player.x, WORLD.maxX - state.player.width / 2);
});

test("held fire obeys cooldown and projectile motion points away from the player", () => {
  const state = game();
  setInput(state, { fire: true });
  stepGame(state, FIXED_STEP);
  assert.equal(state.projectiles.length, 1);
  const firstZ = state.projectiles[0].z;
  stepGame(state, FIXED_STEP);
  assert.equal(state.projectiles.length, 1);
  assert.ok(state.projectiles[0].z < firstZ);
  advanceGame(state, state.config.playerFireCooldown + FIXED_STEP);
  assert.equal(state.projectiles.filter((shot) => shot.owner === "player").length, 2);
});

test("player projectile destroys one invader and awards type-adjusted score", () => {
  const state = game();
  const target = state.invaders.find((item) => item.type === 3);
  state.projectiles.push({ id: 900, owner: "player", x: target.x, z: target.z + 14 * FIXED_STEP, speed: -14 });
  stepGame(state, FIXED_STEP);
  assert.equal(target.alive, false);
  assert.equal(state.score, 30);
  assert.equal(state.projectiles.some((shot) => shot.id === 900), false);
});

test("projectiles damage shield cells before entities behind them", () => {
  const state = game();
  const cell = state.shields[0];
  state.projectiles.push({ id: 901, owner: "enemy", x: cell.x, z: cell.z - 8.2 * FIXED_STEP, speed: 8.2 });
  stepGame(state, FIXED_STEP);
  assert.equal(cell.hp, 1);
  assert.equal(state.projectiles.some((shot) => shot.id === 901), false);
});

test("enemy projectile removes a life and grants temporary invulnerability", () => {
  const state = game();
  state.projectiles.push({ id: 902, owner: "enemy", x: state.player.x, z: state.player.z - 8.2 * FIXED_STEP, speed: 8.2 });
  stepGame(state, FIXED_STEP);
  assert.equal(state.lives, 2);
  assert.ok(state.player.invulnerable > 1);
  assert.equal(state.projectiles.some((shot) => shot.id === 902), false);
});

test("pause freezes simulation and resumes without losing input state", () => {
  const state = game();
  setInput(state, { right: true });
  togglePause(state);
  const before = state.player.x;
  advanceGame(state, 0.25);
  assert.equal(state.player.x, before);
  togglePause(state);
  advanceGame(state, 0.25);
  assert.ok(state.player.x > before);
});

test("clearing a non-final formation advances to a faster wave", () => {
  const state = game();
  state.invaders.forEach((item) => { item.alive = false; });
  stepGame(state, FIXED_STEP);
  assert.equal(state.mode, "wave_cleared");
  for (let index = 0; index < 90; index += 1) stepGame(state, FIXED_STEP);
  assert.equal(state.mode, "playing");
  assert.equal(state.wave, 2);
  assert.equal(state.invaders.filter((item) => item.alive).length, 45);
  assert.ok(state.formation.speed > 1.15);
});

test("clearing the configured final wave reaches victory", () => {
  const state = game({ maxWaves: 1 });
  state.invaders.forEach((item) => { item.alive = false; });
  stepGame(state, FIXED_STEP);
  assert.equal(state.mode, "victory");
});

test("last-life collision reaches defeat", () => {
  const state = game();
  state.lives = 1;
  state.projectiles.push({ id: 903, owner: "enemy", x: state.player.x, z: state.player.z - 8.2 * FIXED_STEP, speed: 8.2 });
  stepGame(state, FIXED_STEP);
  assert.equal(state.lives, 0);
  assert.equal(state.mode, "defeat");
});

test("invaders crossing the city line cause defeat", () => {
  const state = game();
  state.invaders[0].z = WORLD.invaderLimitZ;
  stepGame(state, FIXED_STEP);
  assert.equal(state.mode, "defeat");
  assert.equal(state.lives, 0);
});

test("matrix identity, composition, projection, and camera remain finite", () => {
  const base = compose([2, 3, 4], [1.5, 0.5, 2], Math.PI / 7);
  assert.deepEqual([...multiply(identity(), base)], [...base]);
  assert.deepEqual([...multiply(base, identity())], [...base]);
  assert.equal(isFiniteMatrix(perspective(Math.PI / 3, 16 / 9, 0.1, 100)), true);
  assert.equal(isFiniteMatrix(lookAt([0, 12, 16], [0, 0, 0], [0, 1, 0])), true);
  assert.equal(isFiniteMatrix(base), true);
});

test("gunship camera follows lateral movement and looks forward from the cockpit", () => {
  const camera = gunshipCamera(3.25, 0);
  assert.equal(camera.eye[0], 3.25);
  assert.equal(camera.target[0], 3.25);
  assert.ok(camera.eye[2] > WORLD.playerZ);
  assert.ok(camera.target[2] < WORLD.playerZ);
  assert.ok(camera.eye[1] > 2);
  assert.ok(camera.eye[1] > camera.target[1]);
  assert.equal(isFiniteMatrix(lookAt(camera.eye, camera.target, camera.up)), true);
});
