# Frozen numerical requirements and test oracles

This pedagogical model transfers mass from store A to store B in a closed system:
`dA/dt = -k A`, `dB/dt = k A`. Mass is in kilograms and time in days. A forward
Euler step transfers `k * h * A`; the accepted step length `h` must not exceed
`dt`, including floating-point reconstruction of timestamps. Inputs and total mass
must be finite, masses/rate/duration nonnegative, `dt` positive, `k*dt <= 1`, and
requested step count at most 100000. This is implementation verification, not an
empirical claim about physical stores.

| Requirement | Independent oracle | Test identity (prefix `test_model::`) |
| --- | --- | --- |
| Transfer goes A to B | Positive transfer decreases A and increases B | `test_direction` |
| Closed system conserves mass | Initial 100 + 20 = 120 kg at every step | `test_conservation` |
| Specified rate is used | 0.5/day × 1 day × 100 kg = 50 kg transferred | `test_specified_rate` |
| Final fractional step is shortened | At 1 day: 50/70 kg; after another 0.5 day: 37.5/82.5 kg | `test_fractional_endpoint` |
| Export preserves units | Saved/reloaded 1000 kg equals 1 tonne | `test_exported_units` |
| Unstable parameters rejected | k*dt = 2 exceeds the positivity bound 1 | `test_stability_rejected` |
| Rounded time subtraction cannot make a negative store | `simulate(1, 0, nextafter(10, 0), .5, .1)` has nonnegative stores | `test_rounded_step_nonnegative` |
| Every positive duration includes its final sample | `simulate(1, 0, 0, 1e-308, 1e308)` has initial and final rows; zero rate preserves masses | `test_underflow_final_time` |

The hand-calculated values use exactly representable binary fractions and exact
comparison. Exported tonnes allows absolute error below 1e-12 tonne, a small
rounding allowance over 100 Euler steps with a fixed total of 1 tonne; it is not
a model calibration tolerance. Nonnegativity and final timestamps are strict:
rounding tolerances must not hide the two historical defects. The old rounded
step used `time - previous.time_days` without the `dt` bound. The old step count
used `ceil(duration/dt)` without requiring at least one step for positive duration;
that quotient can underflow to zero. These values specifically exercise this
model's implementation and are not universal scientific regression inputs.

The eight faults and their intended test identities are fixed in `audit/support.py`.
The weak suite deliberately replaces the final two checks with `len(rows) >= 1`;
it is an illustrative negative control, not a reproduction of the entire earlier
project suite. All other test source is identical. The bounds above define the
model; this deliberately small suite does not exhaustively test input validation,
convergence, all floating-point limits or all possible scientific defects.
