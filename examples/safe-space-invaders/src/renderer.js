import { compose, gunshipCamera, lookAt, perspective } from "./math3d.js";

const VERTEX_SHADER = `
attribute vec3 aPosition;
attribute vec3 aNormal;
uniform mat4 uProjection;
uniform mat4 uView;
uniform mat4 uModel;
varying vec3 vNormal;
varying vec3 vWorld;
void main() {
  vec4 world = uModel * vec4(aPosition, 1.0);
  vWorld = world.xyz;
  vNormal = normalize(mat3(uModel) * aNormal);
  gl_Position = uProjection * uView * world;
}`;

const FRAGMENT_SHADER = `
precision mediump float;
uniform vec3 uColour;
uniform vec3 uLightDirection;
uniform float uGlow;
varying vec3 vNormal;
varying vec3 vWorld;
void main() {
  float diffuse = max(dot(normalize(vNormal), normalize(-uLightDirection)), 0.0);
  float rim = pow(1.0 - abs(normalize(vNormal).y), 2.0) * 0.18;
  float pulse = 0.94 + 0.06 * sin(vWorld.x * 1.7 + vWorld.z * 0.8);
  vec3 colour = uColour * (0.25 + diffuse * 0.7 + rim + uGlow) * pulse;
  gl_FragColor = vec4(colour, 1.0);
}`;

const CUBE_POSITIONS = new Float32Array([
  -0.5,-0.5, 0.5,  0.5,-0.5, 0.5,  0.5, 0.5, 0.5, -0.5, 0.5, 0.5,
   0.5,-0.5,-0.5, -0.5,-0.5,-0.5, -0.5, 0.5,-0.5,  0.5, 0.5,-0.5,
  -0.5, 0.5, 0.5,  0.5, 0.5, 0.5,  0.5, 0.5,-0.5, -0.5, 0.5,-0.5,
  -0.5,-0.5,-0.5,  0.5,-0.5,-0.5,  0.5,-0.5, 0.5, -0.5,-0.5, 0.5,
   0.5,-0.5, 0.5,  0.5,-0.5,-0.5,  0.5, 0.5,-0.5,  0.5, 0.5, 0.5,
  -0.5,-0.5,-0.5, -0.5,-0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.5,-0.5,
]);

const CUBE_NORMALS = new Float32Array([
   0,0,1, 0,0,1, 0,0,1, 0,0,1, 0,0,-1, 0,0,-1, 0,0,-1, 0,0,-1,
   0,1,0, 0,1,0, 0,1,0, 0,1,0, 0,-1,0, 0,-1,0, 0,-1,0, 0,-1,0,
   1,0,0, 1,0,0, 1,0,0, 1,0,0, -1,0,0, -1,0,0, -1,0,0, -1,0,0,
]);

const CUBE_INDICES = new Uint16Array([
  0,1,2, 0,2,3, 4,5,6, 4,6,7, 8,9,10, 8,10,11,
  12,13,14, 12,14,15, 16,17,18, 16,18,19, 20,21,22, 20,22,23,
]);

const COLOURS = Object.freeze({
  player: [0.18, 0.95, 1],
  enemy1: [0.45, 0.95, 0.65],
  enemy2: [0.85, 0.48, 1],
  enemy3: [1, 0.55, 0.28],
  shield: [0.2, 0.9, 0.58],
  playerShot: [0.4, 0.95, 1],
  enemyShot: [1, 0.3, 0.52],
  floor: [0.05, 0.18, 0.28],
  edge: [0.08, 0.5, 0.66],
});

function compile(gl, type, source) {
  const shader = gl.createShader(type);
  gl.shaderSource(shader, source);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const message = gl.getShaderInfoLog(shader) || "Unknown shader error";
    gl.deleteShader(shader);
    throw new Error(message);
  }
  return shader;
}

function createProgram(gl) {
  const program = gl.createProgram();
  const vertex = compile(gl, gl.VERTEX_SHADER, VERTEX_SHADER);
  const fragment = compile(gl, gl.FRAGMENT_SHADER, FRAGMENT_SHADER);
  gl.attachShader(program, vertex);
  gl.attachShader(program, fragment);
  gl.linkProgram(program);
  gl.deleteShader(vertex);
  gl.deleteShader(fragment);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    throw new Error(gl.getProgramInfoLog(program) || "Unable to link WebGL program");
  }
  return program;
}

function buffer(gl, target, data) {
  const value = gl.createBuffer();
  gl.bindBuffer(target, value);
  gl.bufferData(target, data, gl.STATIC_DRAW);
  return value;
}

function starPositions() {
  const stars = [];
  for (let index = 0; index < 72; index += 1) {
    const x = (((index * 73) % 101) / 100 - 0.5) * 25;
    const z = (((index * 47 + 13) % 103) / 102 - 0.5) * 27;
    const y = 0.04 + ((index * 19) % 7) * 0.012;
    stars.push([x, y, z]);
  }
  for (let index = 0; index < 54; index += 1) {
    const x = (((index * 61 + 7) % 109) / 108 - 0.5) * 30;
    const y = 1.6 + ((index * 29) % 67) * 0.095;
    const z = -17 - ((index * 31) % 13) * 0.42;
    stars.push([x, y, z]);
  }
  return stars;
}

export function createRenderer(canvas, reportError = () => {}) {
  const contextOptions = { alpha: false, antialias: true, preserveDrawingBuffer: true };
  const gl = canvas.getContext("webgl", contextOptions)
    || canvas.getContext("experimental-webgl", contextOptions);
  if (!gl) {
    reportError("WebGL is unavailable in this browser. Enable hardware acceleration or use a WebGL-capable browser.");
    return null;
  }

  let program;
  try {
    program = createProgram(gl);
  } catch (error) {
    reportError(`The 3D renderer could not start: ${error.message}`);
    return null;
  }

  const positions = buffer(gl, gl.ARRAY_BUFFER, CUBE_POSITIONS);
  const normals = buffer(gl, gl.ARRAY_BUFFER, CUBE_NORMALS);
  const indices = buffer(gl, gl.ELEMENT_ARRAY_BUFFER, CUBE_INDICES);
  const locations = {
    position: gl.getAttribLocation(program, "aPosition"),
    normal: gl.getAttribLocation(program, "aNormal"),
    projection: gl.getUniformLocation(program, "uProjection"),
    view: gl.getUniformLocation(program, "uView"),
    model: gl.getUniformLocation(program, "uModel"),
    colour: gl.getUniformLocation(program, "uColour"),
    light: gl.getUniformLocation(program, "uLightDirection"),
    glow: gl.getUniformLocation(program, "uGlow"),
  };
  const stars = starPositions();
  let projection = perspective(Math.PI / 3.2, 1, 0.1, 80);
  let lost = false;

  gl.useProgram(program);
  gl.bindBuffer(gl.ARRAY_BUFFER, positions);
  gl.enableVertexAttribArray(locations.position);
  gl.vertexAttribPointer(locations.position, 3, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ARRAY_BUFFER, normals);
  gl.enableVertexAttribArray(locations.normal);
  gl.vertexAttribPointer(locations.normal, 3, gl.FLOAT, false, 0, 0);
  gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, indices);
  gl.enable(gl.DEPTH_TEST);
  gl.enable(gl.CULL_FACE);
  gl.cullFace(gl.BACK);
  gl.clearColor(0.007, 0.016, 0.055, 1);
  gl.uniform3fv(locations.light, new Float32Array([-0.45, -1, 0.35]));

  function resize() {
    const ratio = Math.min(2, window.devicePixelRatio || 1);
    const width = Math.max(1, Math.round(canvas.clientWidth * ratio));
    const height = Math.max(1, Math.round(canvas.clientHeight * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      gl.viewport(0, 0, width, height);
      projection = perspective(Math.PI / 3.2, width / height, 0.1, 80);
    }
  }

  function cube(position, dimensions, colour, glow = 0, yaw = 0) {
    gl.uniformMatrix4fv(locations.model, false, compose(position, dimensions, yaw));
    gl.uniform3fv(locations.colour, colour);
    gl.uniform1f(locations.glow, glow);
    gl.drawElements(gl.TRIANGLES, CUBE_INDICES.length, gl.UNSIGNED_SHORT, 0);
  }

  function invaderGeometry(invader, time) {
    const colour = COLOURS[`enemy${invader.type}`];
    const hover = 0.54 + Math.sin(time * 3 + invader.column * 0.7) * 0.06;
    cube([invader.x, hover, invader.z], [1.08, 0.46, 0.72], colour, 0.14);
    cube([invader.x, hover + 0.34, invader.z], [0.58, 0.28, 0.48], colour, 0.18);
    const arm = invader.type === 3 ? 0.78 : 0.68;
    cube([invader.x - arm, hover - 0.02, invader.z], [0.32, 0.22, 0.32], colour, 0.08);
    cube([invader.x + arm, hover - 0.02, invader.z], [0.32, 0.22, 0.32], colour, 0.08);
  }

  function gunshipGeometry(state) {
    const x = state.player.x;
    const blink = state.player.invulnerable > 0 && Math.floor(state.time * 12) % 2 === 0;
    if (blink) return;

    cube([x, 1.35, 8.66], [1.4, 0.14, 0.46], COLOURS.player, 0.14);
    cube([x, 1.54, 7.86], [0.14, 0.16, 1.18], COLOURS.player, 0.38);
    cube([x - 0.82, 1.5, 7.98], [0.3, 0.2, 1.02], COLOURS.player, 0.18, -0.12);
    cube([x + 0.82, 1.5, 7.98], [0.3, 0.2, 1.02], COLOURS.player, 0.18, 0.12);
    cube([x - 1.08, 1.4, 8.44], [0.24, 0.14, 0.56], COLOURS.edge, 0.2, -0.2);
    cube([x + 1.08, 1.4, 8.44], [0.24, 0.14, 0.56], COLOURS.edge, 0.2, 0.2);
  }

  function render(state) {
    if (lost) return;
    resize();
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.uniformMatrix4fv(locations.projection, false, projection);
    const camera = gunshipCamera(state.player.x, state.time);
    gl.uniformMatrix4fv(locations.view, false, lookAt(camera.eye, camera.target, camera.up));

    cube([0, -0.18, 0], [21, 0.18, 20], COLOURS.floor, 0);
    cube([-10.25, 0.06, 0], [0.12, 0.12, 20], COLOURS.edge, 0.16);
    cube([10.25, 0.06, 0], [0.12, 0.12, 20], COLOURS.edge, 0.16);
    for (let line = -8; line <= 8; line += 2) {
      cube([line, 0.015, 0], [0.018, 0.025, 20], COLOURS.edge, 0.02);
    }
    for (const star of stars) cube(star, [0.055, 0.025, 0.055], [0.45, 0.72, 1], 0.65);

    for (const invader of state.invaders) if (invader.alive) invaderGeometry(invader, state.time);
    for (const cell of state.shields) {
      if (cell.hp <= 0) continue;
      const strength = cell.hp / 2;
      cube([cell.x, 0.27, cell.z], [0.34, 0.46 * strength, 0.34], COLOURS.shield, 0.08 * strength);
    }
    for (const shot of state.projectiles) {
      const colour = shot.owner === "player" ? COLOURS.playerShot : COLOURS.enemyShot;
      cube([shot.x, 0.46, shot.z], [0.12, 0.52, 0.12], colour, 0.5);
    }
    gunshipGeometry(state);
  }

  canvas.addEventListener("webglcontextlost", (event) => {
    event.preventDefault();
    lost = true;
    reportError("The WebGL context was lost. Reload the page to resume the defence.");
  });

  return {
    gl,
    render,
    resize,
    destroy() {
      gl.deleteBuffer(positions);
      gl.deleteBuffer(normals);
      gl.deleteBuffer(indices);
      gl.deleteProgram(program);
    },
  };
}
