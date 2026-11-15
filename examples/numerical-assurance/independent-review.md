# Independent numerical checks

These checks compare the model with the stated equations and exact small
transfers. They do not validate a real physical system.

## Design provenance

A separate agent designed `tests/test_independent.py` after reading only
`AGENTS.md` and this example's `REQUIREMENTS.md`. It had not read the candidate
implementation or any other tests. The parent supplied the file destinations,
requirements-first restriction, and the request to derive numerical oracles.
The agent shares the filesystem; this is instruction-level separation, not
write isolation. The requirements themselves supplied the equations, continuous
solution, proposed bound, and convergence acceptance range. Independence here
means checking those statements and constructing tests without candidate output;
it does not mean independently choosing the scientific problem or acceptance
thresholds.

## Derivation

Integrating `dA/dt = -k A` gives `A(t) = A0 exp(-k t)`. Adding the two differential
equations gives zero change in total mass, so `B(t) = B0 + A0 - A(t)`.
For a constant Euler step let `x = k h`, with `0 <= x < 1`. The donor after
`n` steps is `A0 (1-x)^n`. Write

`r = -log(1-x) - x = sum(x^j/j, j=2..infinity)`.

Every term is nonnegative and `1/j <= 1/2`, giving
`0 <= r <= x^2 / (2(1-x))`. Thus

`A_exact - A_Euler = A0 exp(-nx) (1-exp(-nr))`

lies between zero and `A0 exp(-nx) n x^2 / (2(1-x))`, using
`1-exp(-y) <= y` for nonnegative `y`. For the specified 100 steps and `x=0.02`,
this is below 2.77 kg and therefore below the required 3 kg. The test checks
both stores against the continuous solution, preventing an accurate donor
from concealing a defective receiver update. Its extra 1e-9 kg allowance
matches the stated roundoff scale for a total of 1000 kg.

For fixed `T = n h`, expanding the same logarithm gives
`A_Euler = A_exact exp(-k^2 T h/2 + O(h^2))`. Hence the leading endpoint error
is `A_exact k^2 T h/2`; halving `h` approaches a factor of two. This asymptotic
argument alone does not establish a universal finite-step ratio. The test uses
only the requirements' specified `h = 0.2, 0.1, 0.05` regime and its [1.9, 2.1]
acceptance interval. It is not a claim about arbitrary inputs.

The exact binary-representable trajectory starts from `(A,B)=(16,3)`, uses
`k=0.5`, `h=0.5`, and ends at `T=1.25`. Its states are `(12,7)`, `(9,10)`,
and `(7.875,11.125)`. These follow from transfers of 4, 3, and 1.125 kg;
the last step lasts 0.25 days. This detects direction, receiver, rate-factor,
and final-step errors without a tolerance. The positivity boundary `k h=1`
empties the donor on the first full step and leaves it empty thereafter.

Other cases check zero duration, zero rate, an empty donor, small masses,
nonfinite inputs in every argument position, negative values, a step immediately
above the positivity limit, overflow of total mass, and excessive step counts
including an overflowing duration/step quotient. The independent file is a
focused numerical subset; CLI integration and other required tool checks remain
separate responsibilities.

## Observed execution and review

At design handoff, these tests have not been executed and the implementation has
not been inspected. Passing results and implementation review must be recorded
only after those actions occur.

### First execution and implementation inspection

After the design handoff, the parent authorised implementation inspection. The
agent read `model.py` and `tests/test_model.py`, then added two explicitly marked
post-inspection regression tests. Both reproduced actual defects: rounding of
successive timestamps could increase the effective step above the stability
limit and produce a negative donor, and underflow of `duration/dt` could omit a
positive final time. The observed input for the first defect was
`(1, 0, nextafter(10, 0), 0.5, 0.1)`; the donor became approximately
`-2.7369e-48` kg at the third step. The second input was
`(1, 0, 0, 1e-308, 1e308)` and returned only time zero.

A focused pytest execution with plugin autoload disabled and a new owned
base-temp directory reported **34 passed, 2 failed**. These were assertion
failures, not infrastructure failures. The original requirements-first tests
all passed; the two new regressions failed. The model inspected at this stage
had SHA-256 `0ff711c07b88cefaa0598ac8daa2dbf837608be12144505c71a10655fd912955`.

Measured endpoint errors for steps 0.2, 0.1, and 0.05 days were respectively
5.449489714574099, 2.715727341859548, and 1.355608378650686 kg. Adjacent error
ratios were 2.006640957866799 and 2.0033273507520404. The analytical upper bound
at 0.1 days was 2.761944555849239 kg. These are deterministic observations of
this version and these inputs, not evidence of empirical validity or a general
reliability rate.

### Fix review and independent re-execution

The parent changed positive-duration integration to request at least one step,
forced the final recorded time to the requested duration, and bounded each
transfer's step by `dt`. The last change prevents subtraction of rounded time
labels from increasing the transfer step above the validated stability limit.
It changes only the floating-point representation of a nominal full step when
the time-label difference exceeds `dt`; partial steps remain shortened. This
is a numerical roundoff safeguard, not a physical clipping rule for mass.

The independent agent inspected the revised loop and reran the focused suite:
**36 passed in 0.07 seconds**. Both previously failing assertions passed without
changing their inputs or tolerances. The independently checked model SHA-256
was `2264b4a4afea32d9411ccc23c64426447486793ccf035623299a07bcac435811`.
No further defect was identified in this focused review. This does not establish
exhaustive correctness over all finite floating-point inputs. Full-suite tool,
CLI, coverage, and mutation results are reported separately by the parent.
