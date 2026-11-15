# Predetermined test design

Requirements R1–R8 are frozen in REQUIREMENTS.md. This file was written before
model implementation or test execution. The domain and units come from that
contract. These tests verify the idealised equation, not physical observations.

The one-step fixtures use integer values and r=1/4, so expected values are
exact binary floats. Zero-step, zero-diffusivity, constants, copying, and CSV
round trips require exact equality. Stability uses nextafter(0.5, ±infinity),
with D=r and dx=dt=1, avoiding a rounded reconstruction of the boundary.

For finite floating-point evolution the update has a conservative operation
budget of eight roundings per cell per step. With binary64 epsilon 2^-52,
scale at most 1e6 K, and 10000 steps, the first-order worst-case bound is
8*epsilon*1e6*10000 < 1.8e-5 K. Invariant tests use 2e-5 K absolute tolerance
and zero relative tolerance. This bound is deliberately conservative; it does
not replace exact-value checks at smaller scales. Shift symmetry uses exact
comparison because each shifted cell performs identical ordered arithmetic.

Fourier tests use T=300+10*cos(2*pi*k*i/n), n=32, modes 1,7,16, r=0.2
or 0.5, and 1 or 37 steps. The independent discrete eigenvalue is
1-4*r*sin(pi*k/n)^2. The error bound 8*epsilon*310*37, plus trigonometric
input/eigenvalue rounding, is below 3e-11 K; use 1e-10 K absolute and zero
relative tolerance. Mode 16 at r=0.5 tests a negative eigenvalue.

Continuum convergence fixes L=D=1 and t=1/64, r=1/4, n=16,32,64,
steps=n²/16 and starts at 300+10*cos(2*pi*x). The Euler amplification
logarithm gives exponent -q²*t + q^4*t*(1/12-r/2)*dx² + O(dx^4).
Here the leading absolute amplitude error is
10*exp(-pi²/16)*pi^4/96 / n², approximately 5.48/n² K.
For n>=16, the sine and log Taylor remainders are bounded by their next
terms (angle <=pi/16 and 4*r*sin²(angle)<0.039); a conservative bracket
is 4/n² < error < 7/n² K, and refinement ratios must lie in [3.8,4.2].
These broad bounds allow truncation and roundoff without being tuned to output.

R1/R2: frozen result, no aliasing, hand-worked simultaneous periodic updates,
zero/final steps and zero diffusion. R3/R4: invalid domain classes, inclusive
endpoints, nonfinite fields, scalar types and stability neighbours. R5/R6:
extremal bounded fields, long-run conservation, symmetry, Fourier and continuum
checks. R7: standard-reader exact CSV reload, real CLI output and failure exit.
R8: import origin is asserted and printed in the test process; native collection,
JUnit, coverage and static outputs are retained. CLI subprocesses have a 10 s
limit; their lines are outside parent-process coverage, explicitly reviewed.

Exact collected IDs will be appended from pytest's native collection before audit.

## Frozen expected test IDs

Native collection and executed JUnit IDs agree: 78 tests, no skips.

```text
test_heat.py::test_import_origin
test_heat.py::test_hand_worked_periodic_simultaneous_step
test_heat.py::test_result_copy_frozen_and_time
test_heat.py::test_zero_diffusion[0]
test_heat.py::test_zero_diffusion[1]
test_heat.py::test_zero_diffusion[10000]
test_heat.py::test_zero_steps
test_heat.py::test_invalid_scalar[diffusivity_m2_s-nan]
test_heat.py::test_invalid_scalar[diffusivity_m2_s-inf]
test_heat.py::test_invalid_scalar[diffusivity_m2_s--inf]
test_heat.py::test_invalid_scalar[diffusivity_m2_s-True]
test_heat.py::test_invalid_scalar[diffusivity_m2_s-1]
test_heat.py::test_invalid_scalar[diffusivity_m2_s-None]
test_heat.py::test_invalid_scalar[dx_m-nan]
test_heat.py::test_invalid_scalar[dx_m-inf]
test_heat.py::test_invalid_scalar[dx_m--inf]
test_heat.py::test_invalid_scalar[dx_m-True]
test_heat.py::test_invalid_scalar[dx_m-1]
test_heat.py::test_invalid_scalar[dx_m-None]
test_heat.py::test_invalid_scalar[dt_s-nan]
test_heat.py::test_invalid_scalar[dt_s-inf]
test_heat.py::test_invalid_scalar[dt_s--inf]
test_heat.py::test_invalid_scalar[dt_s-True]
test_heat.py::test_invalid_scalar[dt_s-1]
test_heat.py::test_invalid_scalar[dt_s-None]
test_heat.py::test_invalid_parameter_range[diffusivity_m2_s--1]
test_heat.py::test_invalid_parameter_range[diffusivity_m2_s-1000001]
test_heat.py::test_invalid_parameter_range[dx_m-0]
test_heat.py::test_invalid_parameter_range[dx_m-9.999999999999997e-07]
test_heat.py::test_invalid_parameter_range[dx_m-1000001]
test_heat.py::test_invalid_parameter_range[dt_s-0]
test_heat.py::test_invalid_parameter_range[dt_s-9.999999999999997e-07]
test_heat.py::test_invalid_parameter_range[dt_s-1000001]
test_heat.py::test_invalid_parameter_range[steps--1]
test_heat.py::test_invalid_parameter_range[steps-10001]
test_heat.py::test_invalid_parameter_range[steps-True]
test_heat.py::test_invalid_parameter_range[steps-1.0]
test_heat.py::test_invalid_parameter_range[steps-nan]
test_heat.py::test_invalid_parameter_range[steps-1]
test_heat.py::test_invalid_initial[values0]
test_heat.py::test_invalid_initial[values1]
test_heat.py::test_invalid_initial[values2]
test_heat.py::test_invalid_initial[values3]
test_heat.py::test_invalid_initial[values4]
test_heat.py::test_invalid_initial[values5]
test_heat.py::test_invalid_initial[values6]
test_heat.py::test_invalid_initial[values7]
test_heat.py::test_invalid_initial[values8]
test_heat.py::test_invalid_initial[values9]
test_heat.py::test_invalid_initial[values10]
test_heat.py::test_inclusive_domain_endpoints[1e-06-1e-06-0]
test_heat.py::test_inclusive_domain_endpoints[1000000.0-1000000.0-500000.0]
test_heat.py::test_inclusive_domain_endpoints[1000000.0-1e-06-1000000.0]
test_heat.py::test_stability_accepted[0.49999999999999994]
test_heat.py::test_stability_accepted[0.5]
test_heat.py::test_stability_rejected[0]
test_heat.py::test_stability_rejected[1]
test_heat.py::test_conservation_bounds_and_constants[0.01]
test_heat.py::test_conservation_bounds_and_constants[0.25]
test_heat.py::test_conservation_bounds_and_constants[0.5]
test_heat.py::test_shift_symmetry
test_heat.py::test_discrete_fourier[1-0.2-1]
test_heat.py::test_discrete_fourier[1-0.2-7]
test_heat.py::test_discrete_fourier[1-0.2-16]
test_heat.py::test_discrete_fourier[1-0.5-1]
test_heat.py::test_discrete_fourier[1-0.5-7]
test_heat.py::test_discrete_fourier[1-0.5-16]
test_heat.py::test_discrete_fourier[37-0.2-1]
test_heat.py::test_discrete_fourier[37-0.2-7]
test_heat.py::test_discrete_fourier[37-0.2-16]
test_heat.py::test_discrete_fourier[37-0.5-1]
test_heat.py::test_discrete_fourier[37-0.5-7]
test_heat.py::test_discrete_fourier[37-0.5-16]
test_heat.py::test_continuum_convergence
test_heat.py::test_csv_roundtrip
test_heat.py::test_csv_failure
test_heat.py::test_cli_roundtrip_and_failure
test_heat.py::test_unrepresentable_real_rejected
```
