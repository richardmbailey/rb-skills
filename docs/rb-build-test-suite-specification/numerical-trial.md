# Numerical-model trial, 15 November 2026

The user requested a short numerical script, application of the new skill,
executed tests and an assessment of the tools. Created the self-contained
[example project](../../examples/numerical-assurance/README.md), with a 68-line
[mass-transfer script](../../examples/numerical-assurance/model.py). The model
uses forward Euler and has an independently derived exponential solution.

## Observed results

- The first 66 tests passed. Requirements-first independent test design followed
  by code inspection found two previously untested floating-point defects:
  rounded time differences could create negative mass near the stability limit;
  an underflowed duration/step quotient could omit a positive final time.
  Both regressions failed before repair and passed afterward without changed
  tolerances. Independent numerical checks: 36 cases passed.
- Final local suite: 99 tests passed, including 150 bounded deterministic
  Hypothesis examples within one property test. Read-only Ruff lint, separate
  formatting and strict mypy on the model passed. Exact test identities and
  actual model import/hash were reconciled; authored inputs remained unchanged.
- All six predeclared scientific mutants caused relevant assertion failures,
  without collection errors or timeouts. All six passed Ruff and mypy. A weak
  conservation-only check also passed the reversed-transfer mutant. Three
  separate controls verified lint, typing and formatting rejection in their
  respective domains.
- Endpoint errors for steps 0.2, 0.1 and 0.05 days were approximately 5.449490,
  2.715727 and 1.355608 kg. Ratios 2.006641 and 2.003327 support first-order
  convergence in the specified regime. The default error met the predetermined
  3 kg tolerance and analytical upper bound; this is not empirical validation.
- Coverage measured 33/51 statements and 13/16 branches. Separate CLI subprocess
  tests exercised solve/write/reload and error handling, but their execution was
  not merged into coverage. No coverage threshold was weakened.
- The full harness initially caught a nested pytest fixture inheriting parent
  configuration. An independent integration review also found missing mutation
  raw artifacts in the evidence package. Both were fixed with focused regressions,
  retained failures and review follow-up.
- The saved wrapper also passed all local checks after moving the project to a
  temporary path containing spaces and invoking it from another working directory.
- The assessment HTML was checked in headless Chrome offline with JavaScript
  disabled: displayed values and all 52 data rows matched, native details opened,
  mobile width did not overflow the body, print limitations remained visible and
  no page errors occurred. This is not a full accessibility or renderer audit.

## Evidence and interpretation

The [HTML assessment](../../examples/numerical-assurance/artifacts/assessment.html)
contains the measured tool matrix and source links. Raw commands, JUnit, coverage,
before/after regression evidence, mutations and schema-valid post-run observation
imports are retained under the example's ignored `artifacts/` directory. These
generated files are local evidence, not committed artifacts.

The complete skill gate remains `INSUFFICIENT_EVIDENCE`. The local checks succeeded,
but this bounded harness and post-run importer do not qualify the proposed general
runner, executable adapters, authenticated host integration, complete normalized
impact/static records or full report interactions. Actual independent review did
occur; the formal adapter gap must not be confused with absence of review.

This trial supports combining behavioural assertions, independent mathematical
references, property checks, linting and typing. It does not estimate a general
defect-detection rate or causal skill improvement: there was no matched
without-skill agent baseline, and six chosen mutations are not exhaustive.

The instruction edition supplied useful safeguards but required substantial
project-local supporting code for a very small model. A reusable lightweight
scientific profile and qualified adapters would reduce that construction burden.
Those are findings for future work, not implemented features or a new authorised
implementation phase.

Unrelated repository and constrained-runtime suites were not rerun: this turn
added only the isolated example and this assessment. Existing working-tree changes
were preserved. No commit, push, deployment or live operational test was performed.
