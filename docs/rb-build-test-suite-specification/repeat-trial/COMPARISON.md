# Independent repeat of the numerical-model trial

The repeat using the updated skill retained substantially less supporting code and detected the six planned scientific faults. However, the new tests missed both historical floating-point regressions when those defects were deliberately reintroduced. The reduced infrastructure did not preserve all the original regression protection.

## What was compared

Two fresh agents used `gpt-6-astra` with medium reasoning and no inherited conversation. The implementation agent received identical model requirements and the updated skill. A second agent derived independent numerical tests from the requirements before seeing the implementation. Neither could read the original trial or comparison candidates until their numerical work was frozen. This separation was by instruction on a shared filesystem, not enforced isolation.

The original trial used the earlier assurance-style workflow; the repeat used the updated project workflow. The requirements file was byte-identical. The parent recorded a [protocol](protocol.json) before dispatch, froze [numerical file hashes](frozen-numerical-inputs.json), and then ran both final substantive suites against identical candidate files. Each suite had 68 selected and executed cases on every shared candidate. The healthy control passed both suites. Imported model hashes, test hashes, exact IDs, commands, exits, JUnit and logs were retained.

The [external evaluator](compare_suites.py) substituted the same six scientific faults into the original repaired model. It also separately reintroduced each of the two actual numerical defects from the original trial. Each variant changed one declared site. Detection required a fault-relevant assertion failure: collection errors, timeouts, missing evidence or a wrong import were not credited. The parent inspected failure messages and IDs. No such infrastructure errors occurred. Evaluator controls also checked that identity failures, errors and timeouts cannot count as detections.

## Supporting code

Counts include physical lines, comments and blanks in retained executable source. Substantive model tests, support-code tests, configuration and documentation are separate. The [inventory script](inventory.py) reproduced the original counts exactly. Individual files, hashes and nonblank counts are in the [original inventory](original-inventory.json) and [repeat inventory](repeat-inventory.json).

| Retained material | Original | Repeat | Difference |
| --- | ---: | ---: | ---: |
| Supporting code | 1,354 lines / 5 files | 262 lines / 3 files | 1,092 fewer lines, **80.6% reduction** |
| Tests of supporting code | 424 lines / 3 files | 86 lines / 1 file | 338 fewer lines |
| Supporting code plus its tests | 1,778 lines | 348 lines | **80.4% reduction** |
| Substantive numerical/CLI tests | 249 lines / 2 files | 339 lines / 2 files | 90 more lines |
| Numerical model | 68 lines | 79 lines | 11 more lines |
| Copied schemas | 3,553 lines / 4 files | None | Full schemas not required by project workflow |

The repeat retained a 122-line command recorder, a 100-line selected-mutation script and a 40-line pytest identity hook. It removed the original 792-line evidence packager and much of its runner/mutation machinery. More source went into numerical tests rather than evidence conversion.

These are retained-source counts, not token, elapsed-effort or total generated-byte measurements. Generated evidence and disposable candidate copies are excluded. Both trials also used one-off tool orchestration; the original did not retain all such source, so its total authoring overhead cannot be reconstructed precisely. Report preparation performed directly by the host is not zero effort. The repeat agent estimated a further 85 lines of one-off Python and 35 lines of shell orchestration; these are disclosed estimates, not independently reconstructed totals. The parent’s external comparison, inventory and report-check programs are evaluation machinery, not support required to run either project, and are separately visible here. No general runner package was implemented.

## Defects detected

| Identical shared candidate | Original final suite | Repeat frozen suite |
| --- | --- | --- |
| Healthy original repaired model | 68 passed | 68 passed |
| Reversed transfer direction | Detected | Detected |
| Wrong receiving-store update | Detected | Detected |
| Half-rate transfer | Detected | Detected |
| Full dt used for final partial step | Detected | Detected |
| Wrong kg-to-tonnes conversion | Detected | Detected |
| Missing stability validation | Detected | Detected |
| Historical rounded-time-step negativity | Detected | **Missed: 68 passed** |
| Historical underflowed step count | Detected | **Missed: 68 passed** |

Thus both detected 6/6 planned scientific faults; the original detected 2/2 historical regressions and the repeat detected 0/2. Do not combine those categories into an estimated general defect-detection rate. The historical cases were deliberately targeted regressions in the original suite, and the updated skill already teaches their failure classes. This was a test of retained regression protection, not an unseen benchmark.

The rounded-step case used `simulate(1, 0, nextafter(10, 0), 0.5, 0.1)`. The repeat's neighbouring stability checks did not expose the tiny negative mass. The underflow case used `simulate(1, 0, 0, 1e-308, 1e308)`. Testing a tiny duration with dt=1 did not exercise a quotient that underflows to zero. Broad advice to test boundaries did not guarantee these precise cases were implemented.

The repeat independently found a different actual implementation defect: exact-ratio step counting could emit duplicate final timestamps for duration `3*0.1`, dt `0.1`. Its first 36 independent cases passed; code inspection led to an added regression that failed, then passed after repair. The final independent suite has 37 cases. The [independent review](../../../examples/numerical-assurance-repeat/independent-review.md) distinguishes requirements-first design from post-inspection discovery.

The original trial found two actual numerical defects after its initial 66 tests passed, and two infrastructure defects during harness/integration review. These counts describe what was found in different implementations; fewer discoveries cannot establish that either implementation is more reliable. As an additional cross-check (raw `cross-check.json` retained locally, not distributed), all 68 original substantive cases passed on the delivered repeat model. The missing detections therefore concern protection against future regressions; those two historical bugs were not observed in the repeat model itself.

## Validation and parent interventions

The repeat's final local run passed **87 tests**: 68 substantive cases and 19 support cases. Its property test used 150 deterministic bounded examples. Read-only Ruff, separate formatting and strict mypy on the model passed. The captured candidate was unchanged and the final run reconciled execution with a previously frozen 87-ID inventory.

The parent needed to intervene during this trial:

- The agent narrowed Ruff's enabled rules after an initial lint failure. The parent rejected this under the repository rule against weakening failing checks. The agent retained the intermediate snapshot, restored the original broad effective rules and fixed the findings. The final green result does not conceal that workflow violation. The original and repeat still have different effective lint configurations, so this is not a matched comparison of lint strength.
- Initial wrapper tests covered subprocess capture, but not the wrapper's final aggregation and identity decision. The parent requested those checks; the final 19 support cases include early nonzero/unavailable-tool outcomes, timeout partial output and identity/candidate failures. This is bounded project validation, not a fully qualified general runner.
- A claimed temporary-directory fix was absent from the saved command. The parent noticed this; the final wrapper now supplies its own per-run `--basetemp`. Earlier cleanup warnings from shared temporary directories remain in the evidence.
- Early identity reconciliation compared collection with execution within the same run. The final run additionally used a frozen expected-ID file. It was derived from a prior observed collection and reviewed against the intended tests; this does not independently prove that every possible required test was designed.

The repeat measured 38/53 statements (71.7%) and 15/18 branches (83.3%), versus 33/51 statements (64.7%) and 13/16 branches (81.25%) originally. The implementations differ. Both exercised real CLI subprocesses without merging child execution into coverage, so these percentages are not a like-for-like measure of improved testing and do not include all CLI execution.

The parent reran repository instruction and consistency contracts, 46 routing/skill regression tests and 15 schema-reference tests; all passed. The constrained-runtime/wheelhouse/schema-export suite, platform matrices and multi-trial skill evaluations were not run because this task changed only an isolated trial and its evaluation. Those checks provide no additional evidence here. The skill itself was not edited. The parent also checked the local HTML offline in Chrome with JavaScript disabled, verified its links and mobile width, and inspected rendered views; this was not a full accessibility audit.

## Interpretation

The approximately 81% support-code reduction is substantial in this example, but final delivery included parent corrections. A single fresh repeat with different agents, workflows and historical exposure cannot establish causal skill improvement, a general reliability rate or an authoring-cost saving. The original assurance gate remains `INSUFFICIENT_EVIDENCE`; successful project checks do not retroactively satisfy it or qualify a general assurance runner.

The most useful next improvement would be to turn confirmed numerical failures into retained executable regression fixtures that each new project adapts and demonstrates, rather than relying on prose reminders alone. This comparison intentionally leaves the frozen suite unchanged so that its missed cases remain visible. No post-comparison repairs are credited to its result. A separate agent audited all 18 paired runs, their candidate/test hashes and exact selected/executed IDs, the line-count arithmetic and interpretation. Its one wording finding was corrected: this report does not attribute the observed difference causally to the skill.

## Evidence

- [Original assessment](../numerical-trial.md).
- [Repeat project](../../../examples/numerical-assurance-repeat/REQUIREMENTS.md) and [independent review](../../../examples/numerical-assurance-repeat/independent-review.md).
- [Paired results with failure IDs and hashes](paired-results.json).
- [Independent comparison audit](review.md) and [final report rendering check](report-render-check.json).
- [Local raw paired runs](paired-lh4f5ha2/summary.json), with per-run logs, XML, candidate copies and import capture. These generated files are local ignored evidence.
- [Repeat final native receipts](../../../examples/numerical-assurance-repeat/evidence/20261115T213923985558Z/results.json), with adjacent coverage, JUnit, static settings and before/after manifests.
