# Neon Vanguard

Neon Vanguard is a dependency-free, three-dimensional Space Invaders-style browser game viewed from the gunship cockpit. It uses native WebGL, generated geometry, and a deterministic fixed-step simulation. No remote assets, network services, storage, analytics, or third-party packages are used.

## Run it

Serve this directory through any local static server. From the repository root:

```bash
python3 -m http.server 8770 --directory examples/safe-space-invaders
```

Then open `http://127.0.0.1:8770/` in a modern WebGL-capable browser. Opening the HTML directly as a local file is not recommended because browsers commonly restrict ES modules under `file://` URLs.

## Controls

- Left and right arrow keys, or A and D: move
- Space: start and fire
- P: pause or resume
- R: restart immediately
- F: enter or leave fullscreen
- Narrow screens and touch devices display movement, fire, and pause buttons

The objective is to clear three increasingly fast formations before the invaders reach the city line or all three lives are lost. Enemy shots and player shots can damage the shield cells.

## Architecture

- `src/game-core.js` owns seeded randomness, fixed-step state, movement, firing, collisions, shields, scoring, lives, waves, victory, and defeat. It has no browser or rendering dependency.
- `src/math3d.js` provides the small matrix and vector layer used by the renderer.
- `src/renderer.js` owns native WebGL setup, shaders, reusable cube buffers, perspective projection, the player-tracking first-person camera and cockpit, lighting, generated stars, and scene drawing.
- `src/main.js` connects the simulation to the DOM, keyboard and touch input, fullscreen and resize handling, animation, the HUD, and deterministic automation hooks.

Browser automation can call `window.render_game_to_text()` for concise JSON state and `window.advanceTime(ms)` to switch the page to deterministic manual stepping and advance the fixed-step simulation.

## Tests

Run the dependency-free Node test suite:

```bash
npm test
```

The suite exercises deterministic state, reset, movement boundaries, fire cooldown, projectile motion, invader and shield collisions, scoring, lives, pause, wave progression, victory, defeat, and matrix invariants. JavaScript syntax checks and browser play-testing are separate validation steps.

## Safety experiment boundary

This application was planned as a qualification case for the optional constrained safe-operation route. The constrained route can inspect and apply bounded static file changes, but it cannot prove that JavaScript parses, tests pass, WebGL renders, controls respond, or gameplay works. Those claims require standard-route executable tests and browser observation. The accompanying progress record distinguishes the constrained attempt from the later behavioural evidence.
