# Numerical model and test-suite trial

This trial built a new periodic heat-diffusion model and ordinary executable tests,
then used a separate agent to challenge the tests and independently check the
mathematics. The second frozen assessment passed every required command. The
independent auditor approved that exact candidate; the coordinator then returned
`verified_local`, and `status --require-verified` exited zero. The actual review
and acceptance receipt are linked below.

## What was built and checked

The 91-line standard-library model advances temperatures around a periodic ring
using explicit Euler updates. It copies its input, validates the bounded domain
and stability limit, and exports final temperatures with SI units. The demonstration
starts at [400,300,300,300] K and reaches [350,325,300,325] K after one second;
its mean stays 325 K. [Actual exported CSV](evidence/demo.csv).

| Final required check | Observation |
| --- | --- |
| Developer tests | 78 passed; exact native identities reconciled, no skipped/error/failing cases |
| Independent audit | 27 passed: 10 fault experiments, 6 coordinator scenarios, 7 receipt controls, 4 independent scientific checks |
| Reused evidence-parser qualification | 14 passed |
| Ruff E/F/I lint | Passed with `--no-fix --no-fix-only`; all four example Python files checked |
| Formatting | All four Python files passed separate `--check` |
| Types | Strict mypy passed for `heat.py` |
| Coverage | 47/53 statements and 15/16 branches measured; combined native display 90% |
| Candidate integrity | All 20 declared input files unchanged across assessment |

The solver and validation paths have no reported coverage omissions. Unmeasured
lines are the CLI argument parsing/main body and the true `__main__` branch;
real child-process CLI success and failure tests exercise them, but their execution
is not merged into parent coverage. Strict typing covers the model's function
bodies, not test/audit code or every dynamic expression in argparse's namespace.
Coverage and clean static checks do not establish that the scientific assertions
are strong.

Tests cover hand-calculated simultaneous updates, conservation, bounds, cyclic
symmetry, constants, zero steps/diffusivity, final time, invalid types and values,
representable stability neighbours, discrete Fourier modes, fixed-time continuum
convergence, and actual CSV/CLI boundaries. See [test design](TEST_DESIGN.md) and
[requirements](REQUIREMENTS.md) for the predetermined tolerances and model domain.

## What the independent agent challenged

The ten deliberately faulty copies introduced sequential updates, a missing last
step, half-speed diffusion, reversed diffusion, a broken periodic boundary,
removed stability validation, accepted NaN, wrong spatial units, wrong exported
time, and suppressed CLI write failures. Every healthy control passed. Each
faulty copy failed its nominated substantive assertion; timeouts, collection
errors and unrelated crashes did not count as detections. These are selected
fault experiments, not ten bugs discovered in the original model.

Six small fixtures ran the actual existing coordinator. They demonstrated that
an early failed command, generic lint-like/type-like failed commands, a missing
tool and a timeout prevent acceptance even if a later command succeeds. Healthy
commands remain pending until review. The synthetic exits test propagation;
the final assessment separately runs actual Ruff and mypy.

The auditor derived hand cases, Fourier eigenvalues and convergence bounds from
the requirements before reading the developer's implementation and tests. It then
inspected the code and tested additional boundaries. The roles used separate
contexts but the same model family and shared filesystem. See [adoption and
43-capability dispositions](CHECKS.md) and [audit plan](AUDIT_PLAN.md).

## Failures retained and repairs made

1. The builder first ran the written tests without a model. The missing-module
   failure is retained, followed by the first implemented passing suite. Initial
   lint/format failures and repairs are also retained. This is tests-first evidence,
   not a claim that the initial missing-module error detected a scientific bug.
2. The first audit preflight used an outdated exact pytest exception-message
   spelling. The two intended invalid-input faults had been detected, but the
   adapter rejected their receipts. A second preflight had a stale source-replacement
   anchor after formatting. Both invalid experiments were preserved. The auditor
   repaired its adapter/anchor and added negative receipt fixtures; no scientific
   oracle or production assertion was weakened.
3. Frozen round 1 passed nine of ten required commands but failed Ruff: running
   from repository root changed import classification. The coordinator returned
   `needs_repair`, exit 1. The builder added only explicit `known-first-party =
   ["heat"]` configuration and verified lint/format from both working directories.
4. Frozen round 2 reran all ten commands against the changed candidate. All passed;
   it returned `awaiting_review`, exit 3. `status --require-verified` still returned
   1 before the real independent review. This was a bounded two-round assessment,
   not repeated unchanged execution until green.

Some early preflights encountered warnings from pytest's shared temporary cleanup.
Their logs are retained. Final runs use owned temporary paths and disable unrelated
plugin autoload for this standalone example; no unrelated caches were deleted.

## Receipts and rerunning

- [Frozen plan](check-plan.json), [environment](environment.json),
  [project IDs](expected-tests.json), [audit IDs](expected-audit-tests.json).
- [Round 1 assessment](evidence/session/round-001/assessment.json) and
  [round 2 assessment](evidence/session/round-002/assessment.json) preserve exact
  commands, working directory, times, exits, input manifests and command-log hashes.
- [Project JUnit](evidence/session/round-002/native/project.xml),
  [audit JUnit](evidence/session/round-002/native/audit.xml),
  [helper JUnit](evidence/session/round-002/native/helper.xml), and
  [coverage JSON](evidence/session/round-002/native/coverage.json).
- [Final mutation/propagation raw evidence](evidence/audit/attempt-0fcw3zv1/)
  includes healthy and faulty source copies, native XML, commands, stdout/stderr,
  exit values and coordinator fixtures. Earlier attempts remain alongside it.
- [Independent review](evidence/final-review.md),
  [submitted review JSON](evidence/auditor-review.json), and
  [final acceptance receipt](evidence/verified-status.json).

Candidate digest for round 2:
`6094d9b93d23193e32d67050f42f91c2136f3f2135e65bed83e1a6142022eb68`.
The assessment took about 35 seconds locally, excluding agent design/review and
preflights. This is an observed execution time, not a performance guarantee.
Use the [README commands](README.md) to run the model and repeat the workflow.
Raw evidence is retained locally under ignored `evidence/`; it is not automatically
included in a Git checkout or authenticated by an external service.

## Supporting code and limits

New Python: 91 lines of model, 227 lines of developer tests, 50 lines of independent
science tests, and 318 lines of audit fault definitions, tests and narrow subprocess/
receipt support. The 235-line JSON plan is declarative configuration. The existing
coordinator and native JUnit inspector are reused without modification; no new
runner or report-rendering application was added. These counts include comments
and blank lines and are not a controlled comparison with previous trials.

Verified scope is the stated bounded numerical implementation and chosen faults
on Python 3.14.2/macOS ARM64, with pinned tools in `environment.json`. No empirical
material validation, exhaustive proof, universal defect-detection rate, stochastic
inference, latency guarantee or measured skill benefit versus no-skill was tested.
Command executables and dependencies outside declared input paths are not locked
by the coordinator; the environment record describes this run. Agent identities
are host attestations, not cryptographic authentication or enforced isolation.

Hosted CI, other operating systems/Python versions, and repeated semantic skill
trials were not run. Unchanged constrained-runtime/wheelhouse/schema suites were
not rerun for this example-only change. Repository instruction/consistency checks
and whitespace validation passed. No skill source, deployment, commit or push was
changed by this trial. The static HTML report is checked separately for local
links and offline/no-JavaScript reading: desktop, mobile and print checks passed,
and the mobile rendering was visually inspected. See [report-check receipt](evidence/report-check.json).
The installed Playwright default browser build was absent; an existing Chromium
build was used. Its first launch was blocked by the filesystem sandbox; the
authorised local browser launch succeeded outside that sandbox. No browser or
other dependency was installed.


## Publication recheck

The original report and RESULT.json above preserve the completed two-round trial.
Before publication, the displayed interpreter command in AUDIT_PLAN.md was made
portable; the original assessed text remains in local evidence/publication/.
No numerical source, tests, configuration or scientific criteria changed.
The user then requested a final check, commit and push. A new publication
assessment ran all ten required commands and obtained approval from the same
independent auditor. Its final acceptance command exited zero. See the
[portable publication summary](PUBLICATION_RESULT.json); the exact current
candidate digest is recorded there, and the original failed round is not erased.
Raw publication receipts remain local under evidence/release-session/.
