# Periodic heat diffusion example

This educational model solves dT/dt = D d²T/dx² on a uniform periodic ring.
Temperature is in kelvin, position in metres, time in seconds, and diffusivity
D in m²/s. There are no sources, sinks or external boundaries. This is numerical
verification of a specified idealisation, not empirical validation of a material.

## Public contract

- R1: `heat.simulate(initial, *, diffusivity_m2_s, dx_m, dt_s, steps)` returns a
  frozen `Solution` with `temperature_K` (tuple), `dx_m`, and `time_s`. The
  initial sequence is copied and never modified. The result has the same size.
- R2: Advance exactly `steps` explicit Euler steps, using simultaneous values:
  T_new[i] = T[i] + r*(T[(i-1)%n] - 2*T[i] + T[(i+1)%n]),
  where r = D*dt/dx². `time_s = steps*dt_s`. A zero-step call returns the initial
  temperatures. Zero diffusivity is valid and preserves temperatures exactly.
- R3: Require 3..256 cells, finite real scalar inputs (no booleans), each initial
  temperature in [0, 1e6] K, D in [0, 1e6], dx and dt in [1e-6, 1e6]. Steps must
  be a genuine integer (no booleans), in [0, 10000]. Reject violations with
  ValueError. This bounded domain prevents undefined or unbounded work; support
  for arbitrary floating magnitudes is deliberately outside this example.
- R4: Require the computed r <= 0.5, including zero-step calls; reject values
  above it with ValueError. Exercise representable neighbours of 0.5. The
  validation must reject NaN and infinity before they enter arithmetic.
- R5: Preserve the mean temperature and initial minimum/maximum bounds within
  justified floating-point roundoff. A constant field remains constant. Cyclic
  shifts commute with the update. A localized warm cell diffuses to both periodic
  neighbours. These invariants supplement, rather than replace, individual values.
- R6: Verify a nonconstant discrete Fourier mode independently: after m steps its
  amplitude is multiplied by [1 - 4*r*sin(pi*k/n)^2]^m. Also demonstrate convergence
  toward the continuum heat solution, whose amplitude is exp(-D*q²*t), with
  q=2*pi*k/L, when dx and dt are refined at fixed r and final time. Specify the
  convergence regime and error bounds before executing the acceptance test.
- R7: `heat.write_csv(solution, path)` writes one row per cell with exact header
  `x_m,time_s,temperature_K`, x=i*dx and the solution's final time. Reloading using
  the standard CSV reader must preserve float values, cell order and units.
  `python heat.py --output PATH` runs a documented fixed demonstration and writes
  that CSV. Output failures must propagate as a nonzero CLI exit.
- R8: Required completion includes deterministic project tests, independent
  executable fault challenges with healthy controls, Ruff without fixes, a
  separate formatting check, strict typing of the model, branch coverage review,
  and current-candidate independent scientific review. Exact expected test IDs,
  actual import origin, commands, versions and raw native results are retained.
  The local coordinator governs acceptance, with at most three assessment rounds.

## Oracle and history policy

Derive references from the equation above, analytic Fourier modes and hand-worked
small cases. Do not copy output from the implementation into expected answers.
Document each tolerance and numerical regime before running the corresponding
check. Use no randomness unless fixed, bounded generation adds justified value.

This new interface has no inherited confirmed implementation bugs. The prior
transfer-model regressions involving duration/dt underflow and subtraction of
rounded timestamps do not map directly: this API takes an integer step count
and does not derive step lengths by subtracting timestamps. Keep this explicit
non-applicability decision under independent review; still challenge floating
stability neighbours and exact zero/final-step handling here. Any newly found
failure becomes an exact regression retained through subsequent repairs.
