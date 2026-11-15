# Two-store testing evidence

The model passes the required numerical and command-line checks after fixing one
endpoint duplication found by independent inspection. This is verification of a
teaching model, not evidence that it describes a real system. The parent separately checked the report and compared frozen suites on shared faulty models; see the linked comparison below.

## Scope and adoption

Project workflow, development focus, standard intensity. Requirements R1–R7 in
REQUIREMENTS.md were supplied before implementation. Native pytest, Hypothesis,
coverage, Ruff and mypy suffice; there is no generalized assurance runner or
protected release gate. Controls are cooperative local instructions.

For later ordinary, scientific, planned or direct changes: review the affected
requirements and capability dispositions, run the commands below with a fresh
evidence directory, inspect results and independent scientific review, and compare
final source/test/configuration hashes against the assessed snapshot. A failed
required check, missing review, stale evidence or unresolved material coverage
prevents completion. Documentation changes may use a justified limited check.

All five inputs, Euler recurrence, endpoint handling, cap and CLI are new in
model.py. R1 and R4 map to exact and boundary unit tests; R2 maps to bounded
Hypothesis trajectories (100 deterministic examples) and independent invariants;
R3 maps to analytical endpoint/convergence assertions; R5 maps to actual child CLI
CSV reload and invalid/output-error cases. R6 maps to both test files, tool settings
in pyproject.toml and native reports. R7 maps to six explicit disposable source
mutations. No empirical data or fitted parameters exist. The kg/day units,
continuous solution, roundoff allowance and 3 kg accuracy bound are taken from
REQUIREMENTS.md, not candidate output. Independent checks additionally test the
full discrete default CSV using 1000*(0.98**index).

## Results and retained evidence

- Initial tests-before-code run: `python -m pytest tests/test_model.py`, exit 2,
  missing model import; [red log](evidence/01-red.log).
- Initial implementation: same command, exit 0, 33 passed;
  [green log](evidence/02-green.log). This run triggered 4856 warnings from
  pre-existing shared pytest temporary-directory cleanup. No unrelated cache was
  deleted; later commands use fresh owned `--basetemp` directories.
- First Ruff assessment: `python -m ruff check --no-fix --no-fix-only model.py
  tests/test_model.py`, exit 1, seven style findings. [Log](evidence/03-lint.log).
  Imports were repaired with Ruff; pairwise iteration and explicit check=False
  were edited without changing numerical assertions. Separate repair output is
  retained. Initial `python -m mypy model.py` passed.
- Combined pre-inspection suite: 79 passed, exit 0;
  [log](evidence/06-review.log), [JUnit](evidence/06-review.xml).
- Independent blind suite: 45 passed. Post-inspection regression found that
  duration=1 and dt=1/3 yielded two samples at time 1. Exact step counting and
  rounded output timestamps disagreed. Reviewer retained the failing 1-failed,
  45-passed run in [review](independent-review.md). The model now stops once an
  emitted timestamp reaches duration. Independent rerun: 46 passed.
- Final combined suite: 80 passed, exit 0; [log](evidence/final/tests.log),
  [JUnit](evidence/final/tests.xml). All 80 selected identities exactly match
  execution, with no skips, errors, failures or expected failures.
- Ruff lint and format: exit 0 on model.py and both test files. Mypy strict:
  exit 0 on model.py. Effective Ruff settings and checked files are retained.
- Measured statement coverage: 37/53 (69.8%); branch coverage: 15/20 (75%).
  The combined tool figure is 71.2%, with one partially covered branch. [Report](evidence/final/coverage.log). Lines 54–76 and 80 are CLI/main;
  child CLI processes are behaviorally tested but absent from parent coverage.
  No arbitrary universal coverage target was added.
- Mutation healthy control: exit 0. All six predeclared mutants returned exit 1
  with relevant assertion failures: direction, receiver, rate, final step, units,
  missing stability. Per-mutant logs and assertion XML are under evidence/final.
  Collection errors/timeouts were not counted as detections. These six examples
  do not establish general detection power or measured skill lift.

## Identity, tools and review boundaries

[Before](evidence/final/before.json) and [after](evidence/final/after.json) manifests
match for model, both test files, pyproject.toml and requirements. The model hash is
`29027f941b2f6ac847edf26f3ec8719ae9fc78f7044ce8519936e3a2885539ef`.
JUnit records model.__file__ and its content hash from within the actual pytest
process, asserted against the intended checkout. Collection IDs are retained in
selection.log; executed exact IDs and outcomes are in JUnit, with reconciliation
in identity.txt. This is standalone script execution, not packaging verification.

Python is 3.14.2. The actual environment is recorded in environment.log. Exact
commands, working directories, start/end epoch times and exits are in
[commands.jsonl](evidence/final/commands.jsonl). Ruff
effective settings are retained; the settings identify the local pyproject.toml. No claim about inherited rule provenance is established here. Mypy strict assesses the entire annotated
model, with no ignores or missing-import suppressions. Tests and one-off host
orchestration are outside the type claim. Coverage has no production exclusions.

Parent invoked `/root/repeat2_reviewer` separately. Reviewer received requirements
before implementation, authored tests blind, then inspected code and added a
labelled regression. I read reviewer tests only after the parent acknowledged my
independent model/developer-test authoring boundary. Shared tools, Python and
workspace remain common; filesystem/write isolation was not enforced. The actual
reviewer artifact and parent-host conversation supply attribution; this note does
not claim a signed reviewer receipt or human domain expertise.

## Source and infrastructure size

Retained substantive Python: model.py 80 physical lines; developer test file 162;
independent test file 214. The latter includes its three small import/CLI/CSV
fixture helpers. Developer runtime-origin assertion is within the 162 lines.
The parent counts the 11-line runtime-origin test as embedded supporting code, leaving 365 substantive numerical/CLI test lines. There are no separate reusable helper files.

One-off orchestration is **74 Python lines**, retained separately at
[evidence/assessment_oneoff.py](evidence/assessment_oneoff.py). It ran native tools,
recorded commands, compared hashes/IDs and created seven disposable control cases;
it is not a qualified reusable runner. Its healthy and six failing controls test
this trial's detection path, not general timeout/malformed-result behavior. The
host also used ad hoc file-writing commands and a short static HTML emission;
those are authoring operations, not hidden reusable framework code. The one-off
script has a fixed local project path and must not be treated as relocatable. It records individual development-check exits without aggregating all failures into its own final exit. The parent inspected the actual receipts, which are green; the script is not a safe unattended acceptance gate. Its compact 74 lines expand to 151 with Ruff formatting. Including the embedded identity capture gives 85 raw supporting lines, or 162 after that formatting adjustment.

## Saved rerun commands

From this directory, use a Python environment containing the versions in
`evidence/final/environment.log`. Run each command and preserve
its own exit; no report command may mask failure. Create a fresh evidence directory
first. Set PY to that interpreter, OUT to the new directory, and TEMP to a fresh
owned temporary directory. No shell wrapper is installed.

```bash
"$PY" -m pytest --collect-only -q tests
"$PY" -m coverage run -m pytest -v tests --basetemp "$TEMP/pytest" --junitxml="$OUT/tests.xml"
"$PY" -m coverage report -m
"$PY" -m coverage json -o "$OUT/coverage.json"
"$PY" -m ruff check --no-fix --no-fix-only model.py tests
"$PY" -m ruff format --check model.py tests
"$PY" -m mypy --strict model.py
```

Freeze and compare source/test/configuration hashes; compare the exact collected
IDs to JUnit classname/name identities and inspect model_origin/model_sha256
properties. Recreate the six replacements recorded in mutant-*.patch.txt in fresh
copies when assessing changed detection behavior; run the same developer tests,
requiring a healthy pass and a relevant assertion failure for each mutant. An
invalid mutation or timeout is incomplete, not a detected defect.

## All 43 capabilities

Selected entries below are required; others are explicitly not applicable or
optional deferred. No unresolved numerical requirement is knowingly hidden.

| IDs | Disposition | Reason |
|---|---|---|
| 1 unit, 2 functional, 3 component, 5 property_based | Selected, required | Numerical recurrence, invariants, API and CLI assertions |
| 7 static_analysis, 12 lint | Selected, required | Mypy strict, Ruff lint and format |
| 8 mutation, 9 coverage | Selected, required | Six specified defects and branch inspection |
| 11 contract, 13 acceptance, 14 regression, 21 integration, 25 configuration | Selected, required | Immutable records, exact CSV, R1–R7, endpoint regression and input parameters |
| 17 ui_ux | Selected, required | Offline no-JavaScript HTML readability; parent check recorded separately |
| 43 independent_verification | Selected, required | Separate requirements-first reviewer then inspection |
| 4 fuzz, 6 formal_verification, 10 benchmark, 20 performance, 33 profiling, 39 dynamic_exploration | Deferred, optional | Bounded properties and explicit cap cases suffice for this standard trial; no throughput target or formal proof claim |
| 15 smoke, 22 tap_compare | Not applicable | Stronger direct behavior and independent numerical checks serve these boundaries; no separate deployment or tap boundary |
| 16 usability, 18 penetration, 19 threat_modelling | Not applicable | No human study, security/service surface or security acceptance claim |
| 23 load, 24 shadowing, 26 soak, 27 canary, 28 release_monitoring, 29 traffic_shaping, 30 feature_flags | Not applicable | Standalone deterministic local script, no serving traffic or rollout |
| 31 exception_tracking, 32 teeing, 34 logs_events, 35 chaos, 36 operational_monitoring, 37 ab_experiment, 38 tracing, 40 real_user_monitoring, 41 auditing, 42 on_call_experience | Not applicable | No operational services, users, telemetry, experiment, responder workflow or audit-enforcement claim |

No full constrained-runtime suite, live operations, packaged install, protected CI
or general runner qualification was attempted: this project changes none of those
boundaries. Parent owns repository-wide checks and the final comparison trial.

## Parent comparison and deterministic execution

[The comparison](../../docs/rb-build-test-suite-specification/repeat-trial-2/COMPARISON.md) records six of six shared scientific faults detected, but zero of two reintroduced historical floating-point regressions detected. The delivered model passed all 68 original substantive tests. Numerical tests remain frozen, so no later repair is credited.

Agents authored ordinary Python assertions; pytest executes them without an LLM judging numerical pass/fail. Hypothesis uses deterministic generation under the recorded tool versions. Agent-based scientific review and overall result synthesis are separate activities. The native rerun commands still require individual exit inspection; no complete automated acceptance gate is claimed.
