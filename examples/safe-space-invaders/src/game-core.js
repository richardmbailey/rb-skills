export const FIXED_STEP = 1 / 60;
export const WORLD = Object.freeze({ minX: -10, maxX: 10, playerZ: 8, invaderLimitZ: 6.8 });

const DEFAULTS = Object.freeze({
  seed: 0x5eeda11,
  maxWaves: 3,
  enemyFireRate: 0.42,
  playerSpeed: 9,
  playerFireCooldown: 0.28,
});

function xorshift32(value) {
  let x = value >>> 0;
  x ^= x << 13;
  x ^= x >>> 17;
  x ^= x << 5;
  return x >>> 0;
}

function random(state) {
  state.rngState = xorshift32(state.rngState || 1);
  return state.rngState / 0x100000000;
}

function createFormation(wave) {
  const invaders = [];
  const rows = 5;
  const columns = 9;
  const startZ = -7.2 + Math.min(1.2, (wave - 1) * 0.35);
  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      invaders.push({
        id: `w${wave}-r${row}-c${column}`,
        type: row === 0 ? 3 : row < 3 ? 2 : 1,
        row,
        column,
        x: (column - (columns - 1) / 2) * 1.65,
        z: startZ + row * 1.22,
        alive: true,
      });
    }
  }
  return invaders;
}

function createShields() {
  const shields = [];
  const centres = [-6, -2, 2, 6];
  for (let shield = 0; shield < centres.length; shield += 1) {
    for (let row = 0; row < 3; row += 1) {
      for (let column = 0; column < 7; column += 1) {
        if (row === 2 && column >= 2 && column <= 4) continue;
        shields.push({
          id: `s${shield}-r${row}-c${column}`,
          shield,
          x: centres[shield] + (column - 3) * 0.38,
          z: 4.4 + row * 0.38,
          hp: 2,
        });
      }
    }
  }
  return shields;
}

export function createGame(options = {}) {
  const config = { ...DEFAULTS, ...options };
  const seed = (config.seed >>> 0) || 1;
  return {
    config,
    seed,
    rngState: seed,
    mode: "ready",
    previousMode: "playing",
    time: 0,
    accumulator: 0,
    score: 0,
    lives: 3,
    wave: 1,
    nextEntityId: 1,
    waveTransition: 0,
    player: {
      x: 0,
      z: WORLD.playerZ,
      width: 1.35,
      speed: config.playerSpeed,
      cooldown: 0,
      invulnerable: 0,
    },
    input: { left: false, right: false, fire: false },
    formation: { direction: 1, speed: 1.15, descent: 0.58 },
    invaders: createFormation(1),
    projectiles: [],
    shields: createShields(),
  };
}

export function startGame(state) {
  if (state.mode === "ready") state.mode = "playing";
  return state;
}

export function resetGame(state, options = {}) {
  const replacement = createGame({ ...state.config, ...options });
  Object.keys(state).forEach((key) => delete state[key]);
  Object.assign(state, replacement);
  return state;
}

export function setInput(state, partial) {
  state.input = { ...state.input, ...partial };
}

export function togglePause(state) {
  if (state.mode === "playing") {
    state.previousMode = "playing";
    state.mode = "paused";
  } else if (state.mode === "paused") {
    state.mode = state.previousMode || "playing";
  }
  return state.mode;
}

function projectile(state, owner, x, z) {
  state.projectiles.push({
    id: state.nextEntityId,
    owner,
    x,
    z,
    speed: owner === "player" ? -14 : 8.2 + state.wave * 0.45,
  });
  state.nextEntityId += 1;
}

function bottomShooters(state) {
  const byColumn = new Map();
  for (const invader of state.invaders) {
    if (!invader.alive) continue;
    const current = byColumn.get(invader.column);
    if (!current || invader.z > current.z) byColumn.set(invader.column, invader);
  }
  return [...byColumn.values()];
}

function intersects(a, b, halfX, halfZ) {
  return Math.abs(a.x - b.x) <= halfX && Math.abs(a.z - b.z) <= halfZ;
}

function resolveProjectileCollisions(state) {
  const surviving = [];
  for (const shot of state.projectiles) {
    let consumed = false;

    for (const cell of state.shields) {
      if (cell.hp > 0 && intersects(shot, cell, 0.28, 0.28)) {
        cell.hp -= 1;
        consumed = true;
        break;
      }
    }
    if (consumed) continue;

    if (shot.owner === "player") {
      for (const invader of state.invaders) {
        if (invader.alive && intersects(shot, invader, 0.66, 0.5)) {
          invader.alive = false;
          state.score += invader.type * 10 * state.wave;
          consumed = true;
          break;
        }
      }
    } else if (
      state.player.invulnerable <= 0 &&
      intersects(shot, state.player, state.player.width * 0.45, 0.48)
    ) {
      state.lives -= 1;
      state.player.invulnerable = 1.25;
      state.player.x = 0;
      consumed = true;
      if (state.lives <= 0) state.mode = "defeat";
    }

    if (!consumed && shot.z > -11 && shot.z < 10.5) surviving.push(shot);
  }
  state.projectiles = surviving;
}

function beginNextWave(state) {
  state.wave += 1;
  state.invaders = createFormation(state.wave);
  state.projectiles = [];
  state.formation = {
    direction: state.wave % 2 === 0 ? -1 : 1,
    speed: 1.15 + (state.wave - 1) * 0.34,
    descent: 0.58 + (state.wave - 1) * 0.06,
  };
  state.waveTransition = 0;
  state.mode = "playing";
}

export function stepGame(state, dt = FIXED_STEP) {
  if (!Number.isFinite(dt) || dt <= 0) return state;
  if (state.mode !== "playing" && state.mode !== "wave_cleared") return state;

  const boundedDt = Math.min(dt, 0.05);
  state.time += boundedDt;
  state.player.cooldown = Math.max(0, state.player.cooldown - boundedDt);
  state.player.invulnerable = Math.max(0, state.player.invulnerable - boundedDt);

  if (state.mode === "wave_cleared") {
    state.waveTransition -= boundedDt;
    if (state.waveTransition <= 0) beginNextWave(state);
    return state;
  }

  const axis = Number(state.input.right) - Number(state.input.left);
  state.player.x += axis * state.player.speed * boundedDt;
  const halfWidth = state.player.width / 2;
  state.player.x = Math.max(WORLD.minX + halfWidth, Math.min(WORLD.maxX - halfWidth, state.player.x));

  if (state.input.fire && state.player.cooldown <= 0) {
    projectile(state, "player", state.player.x, state.player.z - 0.65);
    state.player.cooldown = state.config.playerFireCooldown;
  }

  const liveInvaders = state.invaders.filter((invader) => invader.alive);
  if (liveInvaders.length > 0) {
    const delta = state.formation.direction * state.formation.speed * boundedDt;
    const edge = liveInvaders.some((invader) => {
      const nextX = invader.x + delta;
      return nextX < WORLD.minX + 0.7 || nextX > WORLD.maxX - 0.7;
    });
    if (edge) {
      state.formation.direction *= -1;
      for (const invader of liveInvaders) invader.z += state.formation.descent;
    } else {
      for (const invader of liveInvaders) invader.x += delta;
    }

    const chance = state.config.enemyFireRate * (1 + state.wave * 0.12) * boundedDt;
    if (random(state) < chance) {
      const shooters = bottomShooters(state);
      if (shooters.length > 0) {
        const shooter = shooters[Math.floor(random(state) * shooters.length)];
        projectile(state, "enemy", shooter.x, shooter.z + 0.58);
      }
    }
  }

  for (const shot of state.projectiles) shot.z += shot.speed * boundedDt;
  resolveProjectileCollisions(state);

  if (state.mode === "defeat") return state;
  if (state.invaders.some((invader) => invader.alive && invader.z >= WORLD.invaderLimitZ)) {
    state.lives = 0;
    state.mode = "defeat";
    return state;
  }
  if (!state.invaders.some((invader) => invader.alive)) {
    if (state.wave >= state.config.maxWaves) {
      state.mode = "victory";
    } else {
      state.mode = "wave_cleared";
      state.waveTransition = 1.35;
    }
  }
  return state;
}

export function advanceGame(state, seconds) {
  if (!Number.isFinite(seconds) || seconds <= 0) return state;
  state.accumulator += seconds;
  while (state.accumulator + 1e-12 >= FIXED_STEP) {
    stepGame(state, FIXED_STEP);
    state.accumulator -= FIXED_STEP;
  }
  return state;
}

export function serialiseGame(state) {
  return {
    coordinateSystem: "right-handed: +x right, +y up, +z toward the player; playfield lies on x-z",
    mode: state.mode,
    time: Number(state.time.toFixed(3)),
    score: state.score,
    lives: state.lives,
    wave: state.wave,
    player: {
      x: Number(state.player.x.toFixed(3)),
      z: state.player.z,
      cooldown: Number(state.player.cooldown.toFixed(3)),
      invulnerable: Number(state.player.invulnerable.toFixed(3)),
    },
    invaders: state.invaders.filter((item) => item.alive).map((item) => ({
      id: item.id,
      type: item.type,
      x: Number(item.x.toFixed(3)),
      z: Number(item.z.toFixed(3)),
    })),
    projectiles: state.projectiles.map((item) => ({
      id: item.id,
      owner: item.owner,
      x: Number(item.x.toFixed(3)),
      z: Number(item.z.toFixed(3)),
    })),
    shields: state.shields.filter((cell) => cell.hp > 0).map((cell) => ({
      id: cell.id,
      x: cell.x,
      z: cell.z,
      hp: cell.hp,
    })),
    formation: { direction: state.formation.direction, speed: state.formation.speed },
  };
}
