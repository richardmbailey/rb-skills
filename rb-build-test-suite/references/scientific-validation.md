# Scientific checks and claim boundaries

A scientific test needs a justified answer or relationship that could expose a
wrong implementation. Agreement with a second program is useful only to the
extent that its assumptions, code and data provide independent evidence.

## Establish the claim

Record physical meaning, units, dimensions, domain, input/output shapes, valid
ranges, assumptions and intended inference. Separate implementation verification,
numerical accuracy, statistical behaviour and empirical validity. Use reviewed
requirements and domain expertise where needed. Missing domain decisions remain
unresolved; the agent must not invent a scientific acceptance threshold.

Choose the applicable checks from these families:

- Analytical and small hand-calculated cases, limiting cases and dimensional
  consistency. Test directions and individual values as well as conserved totals;
  a wrong transfer direction can still conserve mass.
- Invariants, monotonicity, symmetries and metamorphic relations justified by the
  model. Test the assumptions behind a transformation before treating it as an oracle.
- Convergence under discretization or solver refinement, with justified error
  measures and expected order. Separate discretization, optimization and floating
  point error. A smooth plot or finite result is not a convergence check.
- Floating-point boundary cases where relevant: adjacent values near stability
  limits, cancellation when subtracting timestamps, underflow/overflow in step
  counts, and inclusion of a positive final time. Check these with explicit cases;
  bounded random generators may never sample the narrow failure region.
- Differential comparison with a genuinely independent implementation or trusted
  dataset. Record versions, provenance, shared dependencies and known limitations.
- Stochastic checks with predeclared sample size, seeds or sampling procedure,
  uncertainty, power and acceptance rule. Preserve failed trials and counterexamples;
  do not repeat draws until acceptance.
- Empirical comparisons using appropriate observations, domain coverage and held-out
  data. Check leakage, preprocessing consistency, train/test separation and whether
  calibration data are being reused as validation evidence.
- Real load–compute–save–reload workflows. Check exported units, shapes, missing data
  and metadata; in-memory unit tests can miss a wrong conversion in a report.

For numerical comparisons, justify absolute/relative tolerances and scale near
zero. Explicitly define treatment of NaN, infinity, shape, dtype where relevant,
and missing observations. A library default is not a domain tolerance. Preserve
accepted references and expected values; failed tests cannot regenerate their
own oracle or loosen bounds.

## Review and change impact

Map a scientific change to implementation, assumptions, tolerances and empirical
validity separately. A new kg-to-tonnes output needs coverage even when old mass
conservation tests pass. Existing adequate checks can be reused with matching
identities; new behaviour cannot disappear behind a new source hash.

Independent verification is required for scientific-core acceptance under this
skill's default policy. Give the verifier the requirements and independent oracle
sources before developer explanations where feasible. Required human/domain
expertise remains human expertise; a second model is not an automatic substitute.

After requirements-first design, let the reviewer inspect the implementation and
challenge assumptions and generator bounds. Record which tests came from each
stage. Keep wrong-direction, wrong-rate and wrong-unit counterexamples where
plausible: conservation, lint and typing can all pass scientifically wrong code.

Report exactly what the evidence supports. Correct implementation of a model does
not establish that its assumptions describe nature or that its conclusions extend
beyond the tested domain. See [NASA verification](https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html)
and [NASA validation](https://www.grc.nasa.gov/www/wind/valid/tutorial/valassess.html)
for this distinction.
