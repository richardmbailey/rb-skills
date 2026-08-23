export function identity() {
  return new Float32Array([1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]);
}

export function multiply(a, b) {
  const out = new Float32Array(16);
  for (let column = 0; column < 4; column += 1) {
    for (let row = 0; row < 4; row += 1) {
      let value = 0;
      for (let index = 0; index < 4; index += 1) {
        value += a[index * 4 + row] * b[column * 4 + index];
      }
      out[column * 4 + row] = value;
    }
  }
  return out;
}

export function translation(x, y, z) {
  const out = identity();
  out[12] = x;
  out[13] = y;
  out[14] = z;
  return out;
}

export function scale(x, y, z) {
  const out = identity();
  out[0] = x;
  out[5] = y;
  out[10] = z;
  return out;
}

export function rotationY(angle) {
  const c = Math.cos(angle);
  const s = Math.sin(angle);
  return new Float32Array([c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]);
}

export function perspective(fieldOfViewRadians, aspect, near, far) {
  const f = 1 / Math.tan(fieldOfViewRadians / 2);
  const range = 1 / (near - far);
  return new Float32Array([
    f / aspect, 0, 0, 0,
    0, f, 0, 0,
    0, 0, (near + far) * range, -1,
    0, 0, near * far * 2 * range, 0,
  ]);
}

export function normalise(vector) {
  const length = Math.hypot(vector[0], vector[1], vector[2]);
  if (length < 1e-9) return [0, 0, 0];
  return [vector[0] / length, vector[1] / length, vector[2] / length];
}

export function cross(a, b) {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

export function lookAt(eye, target, up) {
  const z = normalise([eye[0] - target[0], eye[1] - target[1], eye[2] - target[2]]);
  const x = normalise(cross(up, z));
  const y = cross(z, x);
  return new Float32Array([
    x[0], y[0], z[0], 0,
    x[1], y[1], z[1], 0,
    x[2], y[2], z[2], 0,
    -(x[0] * eye[0] + x[1] * eye[1] + x[2] * eye[2]),
    -(y[0] * eye[0] + y[1] * eye[1] + y[2] * eye[2]),
    -(z[0] * eye[0] + z[1] * eye[1] + z[2] * eye[2]),
    1,
  ]);
}

export function gunshipCamera(playerX, time = 0) {
  const bob = Math.sin(time * 1.8) * 0.025;
  return {
    eye: [playerX, 2.2 + bob, 9.35],
    target: [playerX, 0.54, -4.8],
    up: [0, 1, 0],
  };
}

export function compose(position, dimensions, yaw = 0) {
  return multiply(translation(...position), multiply(rotationY(yaw), scale(...dimensions)));
}

export function isFiniteMatrix(matrix) {
  return matrix.length === 16 && [...matrix].every(Number.isFinite);
}
