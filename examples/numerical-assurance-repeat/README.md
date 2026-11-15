# Two-store numerical repeat

The model transfers mass from A to B with simultaneous forward Euler updates and exports a real CSV. This trial checks the stated teaching equations; it does not validate a physical reservoir or measure improvement attributable to a skill.

Use the **project workflow**, development focus, standard intensity. There was no pre-existing full assurance policy. Requirements and numerical tolerances were fixed in REQUIREMENTS.md before implementation. No full assurance runner, protected CI gate or operational acceptance is claimed.

## Saved commands and completion rule

From this directory, use the Python environment containing the versions recorded in the final environment.log:

```sh
python run_checks.py
python check_mutants.py
```

Both exits must be zero. Inspect the new run directories, the frozen exact expected-tests.json, independent-review.md, the coverage gaps and the scientific results. For subsequent ordinary, scientific, plan-based or direct changes, update the impact map and justified test selection before assessment; run both commands and compare final source identities. Any later source/test/config/criteria change invalidates affected evidence. Missing required review, test selection or report checks keeps completion incomplete. The report is static and must be updated explicitly; these commands do not manufacture review or rewrite it.

## Latest observed evidence

Final assessment: `evidence/20261115T213923985558Z/`. All 87 tests passed, including 150 deterministic Hypothesis examples inside one property test; no skipped or xfailed cases. Ruff lint with fixes disabled, Ruff format check, strict mypy on model.py and branch coverage capture passed. Native JUnit, logs, coverage JSON, environment versions, before/after manifests, Ruff effective settings and checked files are retained. Manifests matched. Exact IDs match the separately frozen expected-tests.json and executed call outcomes. Actual model import path/hash is captured in the pytest process. The inventory was frozen from a preceding observed collection, not authored independently of discovery. The origin hook is local cooperative evidence, not an authenticated runner.

Mutation assessment: `evidence/mutants-20261115T213830342646Z/`. A healthy control passed. All six predeclared faults failed relevant behavioural assertions: reversed transfer, omitted receiver transfer, halved rate, full-length final step, incorrect tonnes conversion and omitted stability validation. Copies, exact commands, JUnit and failure logs are retained. These six selected faults do not establish general fault-detection probability. The mutation helper has no fully qualified general failure/recovery protocol; its timeout would stop visibly instead of reporting a kill.

Endpoint errors in kg for dt 0.2, 0.1 and 0.05 were 5.449489714574128, 2.715727341859605 and 1.355608378650743. The dt=0.1 error is below the required 3 kg; both refinement ratios lie in [1.9,2.1]. The oracle integrates A'=-kA and then uses conservation for B, independently of candidate outputs. See evidence/numerical-summary.json.

## Impact and coverage

| Files and behaviour | Requirements / checks |
| --- | --- |
| model.py recurrence, timestamps, Sample, validation | R1–R4; exact values, analytical convergence, properties and independent tests |
| model.py CLI/export | R5; real subprocess save/reload, rejection before creation and IO error |
| tests/test_model.py | Developer unit/integration, Hypothesis and floating-point edge tests |
| tests/test_independent.py | Requirements-first numerical review, then labelled regression |
| pyproject.toml | R6; test discovery, Ruff, strict model-only typing, branch coverage |
| tests/conftest.py, expected-tests.json | Import identity and exact selected/executed outcome capture |
| run_checks.py, tests/test_capture.py | Native check recording; success, nonzero and missing tool propagation, timeout partial output, changed source and invalid identity cases |
| check_mutants.py | R7; bounded six-fault sensitivity with healthy control |
| REQUIREMENTS.md | Fixed units, interface and numerical acceptance criteria |

Coverage is 75% combined statement/branch coverage: 53 statements, 15 unmeasured; 18 branches, one partial. Missing lines 54–75 and 79 are the CLI main path exercised in separate subprocesses but not instrumented by this parent-process coverage run. Core simulation branches are measured. No universal coverage target was imposed. Strict mypy covers model.py only; tests and helpers remain dynamically typed and are outside the type claim. There are no model type suppressions or skipped imports. Ruff checks live Python source and tests; evidence is excluded because it deliberately contains mutants and historical candidate snapshots.

## Preserved defects and corrections

The first test-first run failed collection because model.py had not yet been implemented (`evidence/initial-red.log`), then the initial developer suite passed (`first-green.log`). This is not evidence that a scientific mutant was killed.

Independent requirements-first design passed 36 cases, then source review found duplicate final timestamps at duration=3*0.1. The reviewer appended a labelled regression, observed 1 failed/36 passed, and confirmed the repaired implementation with 37 passing cases. The repair merges an unrepresentable final remainder and bounds its transfer interval by dt. See independent-review.md and the parent's real reviewer invocation record. Context separation was instruction-only in a shared filesystem; no enforceable write isolation or human domain review is claimed.

The first full assessment failed lint. I incorrectly narrowed Ruff selection to E4/E7/E9/F and initially described this as unrelated inherited configuration, without evidence: the recorded settings identify the local project config. The parent required restoration. The narrowed candidate is retained in evidence/pre-restoration; original rule selection was restored, actual findings corrected and the final assessment passed without suppressions. This parent intervention is part of the trial outcome, not equivalent uninterrupted compliance. No numerical assertions or tolerances were weakened.

Early pytest commands used the shared default temp area and emitted thousands of unrelated cleanup warnings. A claimed fix initially failed to modify the command. The parent identified that mismatch; the saved command now uses its fresh run directory as basetemp. Those warning logs remain. A later support-test import-placement lint failure and correction are retained. The final run is warning-free. Helpers are not a generally qualified runner; their relevant aggregation paths have focused tests.

## All 43 catalogue dispositions

“Required” applies only to selected entries below. Scientific/reference checks are cross-cutting, not extra catalogue IDs.

| IDs | Disposition / required | Reason |
| --- | --- | --- |
| 1 unit, 2 functional, 3 component, 5 property_based | selected / yes | Numerical function and CLI behaviour, bounded properties |
| 7 static_analysis, 8 mutation, 9 coverage, 12 lint | selected / yes | Explicit R6/R7 tools and reviewed gaps |
| 11 contract, 13 acceptance, 14 regression, 15 smoke, 21 integration, 25 configuration | selected / yes | Interface/CSV contract, fixed acceptance, endpoint regression, real CLI and invalid flags; overlapping checks reused |
| 43 independent_verification | selected / yes | Separate requirements-first design and later source review |
| 17 ui_ux | selected / yes | Local report readability/link/offline check; parent subsequently verified offline rendering and relative links |
| 4 fuzz, 6 formal_verification, 10 benchmark, 20 performance, 33 profiling, 39 dynamic_exploration | deferred / no | Bounded properties and explicit 100000-step cap cover current requirement; no additional performance threshold or formal proof specified |
| 16 usability, 18 penetration, 19 threat_modelling, 22 tap_compare, 23 load, 24 shadowing, 26 soak, 27 canary, 28 release_monitoring, 29 traffic_shaping, 30 feature_flags, 31 exception_tracking, 32 teeing, 34 logs_events, 35 chaos, 36 operational_monitoring, 37 ab_experiment, 38 tracing, 40 real_user_monitoring, 41 auditing, 42 on_call_experience | not applicable / no | No service, deployment, traffic, operational data, users study or audit/security product claim; local stdout/stderr receipts do not establish operational capabilities |

## Code and supporting work accounting

Retained authored code: model.py 79 lines; tests/test_model.py 148; tests/test_independent.py 191; tests/test_capture.py 86; tests/conftest.py 40; run_checks.py 122; check_mutants.py 100. Recount with `wc -l` for exact final line totals. The hook, wrapper and mutation script are supporting code and must count in overhead. Disposable mutant/source copies repeat existing code; they are not additional original implementation. pyproject.toml and expected-tests.json are supporting configuration/inventory. This README, REQUIREMENTS.md, independent-review.md and report.html are documentation/report assets.

One-off orchestration was not retained as scripts: approximately 85 lines of Python editing, manifest/inventory copying and numerical-summary generation, plus approximately 35 shell command/heredoc orchestration lines outside the authored file contents. These estimates explicitly exclude repeated embedded file contents and count supporting work rather than hiding it. No other scratch Python/shell files were created. Native tool caches, pytest temporary CSVs and coverage databases are generated artifacts, not authored application code.

The parent owns full repository validation and the final comparison experiment. This isolated trial did not rerun unrelated constrained-runtime tests, skill metadata/contracts or all eval manifests: no runtime/skill implementation was changed here. Scope-limited git diff --check passed. Residual risk: broader repository integration is outside this local evidence. Report relative links and recorded/actual final hashes were checked with a small one-off HTMLParser/hash script. The parent subsequently verified offline rendering in Chrome with JavaScript disabled, relative links and mobile width. This is a basic report check, not a complete accessibility audit. The separate comparison found two missing historical regression tests, despite the delivered model passing the original substantive suite; see [the comparison](../../docs/rb-build-test-suite-specification/repeat-trial/COMPARISON.md). The numerical suite remains frozen to preserve the measured result.
