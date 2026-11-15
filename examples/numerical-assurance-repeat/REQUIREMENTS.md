# Two-store mass-transfer example

This is a deterministic teaching model and a trial of testing tools. It makes
no empirical claim about a real reservoir, chemical or ecological system.
Testing focus is development, intensity standard; no live operational actions.

## Model and interface

Mass moves from store A to store B in a closed system:
`dA/dt = -k A`, `dB/dt = k A`. Time is days, mass is kg and `k` is per day.
The independent continuous solution is `A(t) = A0 exp(-k t)` and
`B(t) = B0 + A0 (1 - exp(-k t))`. These follow by integrating the first
linear differential equation and using conservation; no candidate output is
used to create the reference.

`model.simulate(a0, b0, rate, duration, dt)` returns a list of immutable `Sample`
objects with `time_days`, `a_kg`, `b_kg`. Use explicit forward Euler steps with
one simultaneous transfer per step. Include the initial state and the requested
final time; shorten the last step when duration is not a multiple of dt.
`Sample.total_tonnes` returns `(a_kg + b_kg) / 1000`.

All five inputs must be finite. Initial masses, rate and duration must be
nonnegative; dt must be positive and `rate * dt <= 1` for nonnegative Euler
updates. Reject non-finite total mass or more than 100000 steps with ValueError.
Zero duration returns only the initial state. Zero rate leaves both stores
unchanged. The step cap bounds this example's time and memory use.

`python model.py --output result.csv` runs defaults A0=1000, B0=0, k=0.2,
duration=10, dt=0.1. Support flags `--a0`, `--b0`, `--rate`, `--duration`,
`--dt`. CSV columns are exactly `time_days,a_kg,b_kg,total_tonnes`. Invalid
parameters fail with a nonzero exit before creating the output. Output IO errors
must also return nonzero. This is a standalone script, not a distributed package.

## Acceptance fixed before implementation

- R1: Single-step values match the simultaneous Euler recurrence, including
  a non-integer final step. Tests use exact small cases where representable.
- R2: Nonnegative stores, monotone transfer and conserved total hold throughout
  explored valid inputs. Roundoff allowance is `1e-12 * max(1, A0+B0)` kg for
  bounded test trajectories; it is not a physical measurement tolerance.
- R3: At k=0.2/day, t=10 days, A0=1000 kg, dt=0.1 days, endpoint absolute
  error is at most 3 kg. For x=k*dt=0.02 and 100 steps,
  `0 <= exp(-2) - (1-x)^100 <= exp(-2) * 100*x*x/(2*(1-x))`;
  multiplying by 1000 bounds the error below 2.77 kg. Halving dt from
  0.2 to 0.1 to 0.05 days must reduce endpoint error by ratios in [1.9,2.1],
  checking first-order convergence in this specified regime.
- R4: Invalid inputs, unstable steps and excessive step counts are rejected;
  zero rate/duration and the positivity boundary are supported.
- R5: The real CLI writes a CSV that reloads with the correct times, masses,
  column names and kg-to-tonnes conversion. No in-memory-only substitute.
- R6: Required development checks include pytest unit/integration tests,
  Hypothesis properties, independent numerical tests, Ruff lint and format,
  mypy on model.py, and branch coverage inspection. No universal coverage target.
- R7: Predeclared disposable mutants cover wrong direction, wrong receiving
  store, wrong rate factor, wrong final step, bad kg-to-tonnes conversion and
  missing stability validation. Each must be caught by a relevant behavioural
  assertion; compilation errors and timeouts do not count as detection.

Independent test design is required for this scientific-core example. Record
the separate agent's context and actual check results, without claiming write
isolation or empirical validation. A matched with/without-skill experiment is
outside this one-project trial; it cannot measure skill lift or general reliability.
