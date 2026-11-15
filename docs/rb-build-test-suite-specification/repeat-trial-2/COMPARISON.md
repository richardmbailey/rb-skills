# Second independent numerical-model repeat

This fresh repeat used much less supporting code than the original trial, and caught all six planned scientific faults. It again missed both historical floating-point regressions. The result supports keeping the smaller project workflow, but does not support treating its newly generated tests as a replacement for retained regression fixtures.

Two new GPT-6 Astra agents, using medium reasoning and no inherited conversation, independently implemented the model and designed numerical tests. Both were instructed not to inspect the original trial, first repeat or comparison candidates. They shared a filesystem, so separation was by instruction. Requirements were byte-identical to the original. The skill was unchanged from the first repeat. The [protocol](protocol.json) records scope, counting rules and skill hashes.

## Supporting code actually used

| Material | Original trial | Second repeat |
| --- | ---: | ---: |
| Retained supporting Python/shell source | 1,354 lines | **85 lines**, including the one-off script below |
| Of the repeat's support: embedded import-identity check | — | 11 lines |
| Of the repeat's support: one-off assessment script | Unretained orchestration not fully reconstructable | 74 lines |
| Separate tests of supporting infrastructure | 424 lines | None; identity check itself asserts the import path |
| Numerical/CLI tests, excluding embedded identity capture | 249 lines | 365 lines |
| Model | 68 lines | 80 lines |
| Copied full-contract schemas | 3,553 lines | None |

The second repeat has no separate reusable runner, evidence packager or capture plugin. It uses native pytest/JUnit, coverage, Ruff and mypy outputs, with an 11-line test recording the actual model origin/hash. The parent counted that code as supporting infrastructure even though it is embedded in a numerical test file. The 74-line assessment script was copied from its temporary location into retained evidence; it is also included rather than hidden as one-off work.

Physical line counts are sensitive to formatting: Ruff expands the compact 74-line assessment script to 151 lines without changing its behaviour. On that basis the repeat has **162 supporting lines**, rather than 85. Both figures are substantially below the original 1,354, but neither measures authoring effort or reliability. Unretained shell/editing operations also occurred in both trials, and their total effort cannot be reconstructed. The parent comparison and report-check programs are external evaluation work, not infrastructure needed by the numerical project.

The one-off script is not a reusable quality gate. It has fixed local paths and a single-use output directory. It records native check exits but does not aggregate all of them into its own exit status; its timeout handling is not qualified. The parent checked the actual receipts: all required development commands returned zero. The healthy mutation control passed and all six selected faults caused relevant assertions. These observed results do not qualify the script for unattended future use. The note instead gives native rerun commands whose individual exits require inspection.

See the [file inventory](repeat-inventory.json), [embedded/one-off accounting](support-accounting.json), [original inventory](../repeat-trial/original-inventory.json) and [retained assessment script](../../../examples/numerical-assurance-repeat-2/evidence/assessment_oneoff.py).

## Same candidate files, frozen test suites

After [freezing the numerical source and test hashes](frozen-numerical-inputs.json), the parent reused the first comparison's evaluator. Both suites ran against the same healthy original repaired model and eight single-fault variants. Original runs selected/executed 68 cases; repeat runs selected/executed 80, including its one identity-capture case. No collection errors, timeouts, skipped cases or wrong imports were credited as detections. The parent inspected the fault-related failure messages.

| Shared candidate | Original final suite | Second repeat |
| --- | --- | --- |
| Healthy repaired model | Passed | Passed |
| Reversed transfer direction | Detected | Detected |
| Wrong receiving-store update | Detected | Detected |
| Half-rate transfer | Detected | Detected |
| Full dt on the shortened final interval | Detected | Detected |
| Wrong kg-to-tonnes conversion | Detected | Detected |
| Missing stability validation | Detected | Detected |
| Historical rounded-time-step negativity | Detected | **Missed** |
| Historical underflowed step count | Detected | **Missed** |

The repeat caught **6/6 planned scientific faults and 0/2 historical regressions**, exactly the pattern seen in the first fresh repeat. The original caught all eight. The historical cases were deliberate regressions in the original suite, and their failure classes are taught in the updated skill; they are not an unseen benchmark. Two repeats do not establish a general detection probability or a causal skill effect.

The missed cases are narrowly different from the repeat's boundary checks. `simulate(1, 0, nextafter(10, 0), 0.5, 0.1)` exposes negative mass from a rounded time difference. `simulate(1, 0, 0, 1e-308, 1e308)` exposes a positive duration omitted when duration/dt underflows. Testing a tiny duration with dt=1 does not exercise that quotient underflow. The frozen repeat tests were not changed after seeing these results.

An additional cross-check (raw `cross-check.json` retained locally, not distributed) ran the original suite against the new repeat model: **68 passed**. Those historical defects were therefore not observed in the delivered model. The gap is that the new suite would not detect their reintroduction.

## Actual discovery and local checks

The requirements-first reviewer initially passed 45 cases. During subsequent code inspection it found an extra zero-length step for duration=1 and dt=1/3: exact ratio counting requested another step even though the emitted timestamp had already rounded to the endpoint. A labelled regression failed before repair, then passed after the model stopped at the emitted endpoint. The final independent suite passed 46 cases. This is the same duplicate-endpoint class found at a different input in the first repeat, not a second unrelated defect class.

The original trial found two numerical defects after its initial green suite and later two infrastructure defects. Counts of bugs found in different implementations do not measure relative reliability. Requirements-first design and post-inspection discoveries remain separate in the [review record](../../../examples/numerical-assurance-repeat-2/independent-review.md).

Final local evidence records **80 passing tests** (79 numerical/CLI cases plus identity capture), including 100 deterministic Hypothesis examples in one property test. Ruff lint, formatting and strict model-only mypy passed. Final model/test/configuration/requirements hashes matched; the actual imported model hash in JUnit matched the manifest. Native collection IDs were reconciled with JUnit execution identities. This proves agreement with the observed collection, not that collection independently contains every necessary test.

Measured coverage was 37/53 statements (69.8%) and 15/20 branches (75%). The tool's combined figure is 71.2%; it must not be labelled branch coverage. As in the original, real CLI subprocess tests passed but child execution was not merged into coverage. Different implementations and coverage denominators prevent a simple coverage-improvement claim.

This repeat fixed actual lint findings without narrowing the rule set. Initial shared pytest temporary-directory cleanup warnings were retained, then owned temporary directories were used. Parent intervention requested retention/counting of the one-off assessment source; no common numerical fault cases were disclosed before freeze. The parent corrected report coverage wording and documented the assessment script's limited failure handling after delivery, without changing frozen numerical files.

## Deterministic tests and agent judgement

The agents wrote ordinary Python test code. Pytest executes fixed numerical assertions without asking an LLM to decide whether values are correct. Hypothesis uses `derandomize=True` with the recorded environment; repeatability is conditional on those tool versions. Independent scientific review and final interpretation remain agent activities. The one-off command collector does not implement a reliable deterministic overall acceptance gate, even though the individual tests and native checks run as code.

## Report and repository verification

The project uses a static HTML report and a compact note covering all 43 capability IDs. [Parent report-rendering checks](report-render-check.json) passed offline with JavaScript disabled; desktop and mobile lower-section images were inspected. The [independent comparison audit](review.md) found no material discrepancies. The numerical source remains frozen.

Instruction contracts, consistency contracts and `git diff --check` passed in this turn. The previous turn's 46 routing/skill regression and 15 reference-schema tests were not repeated because this turn changes only the isolated second example and its evaluation, not the skill or those contracts. The full constrained-runtime, wheelhouse/schema-export and platform suites were not run; their behaviour is outside this evidence. This is not a repeated with/without-skill experiment or a protected release qualification. The original assurance gate remains `INSUFFICIENT_EVIDENCE` under its original requirements.

The practical finding is consistent across the two fresh repeats: much less supporting infrastructure is possible, while prose guidance alone did not reliably preserve known edge-case regressions. Retaining those failures as executable fixtures remains the clearest next improvement. No skill change or post-comparison repair is included in this evaluation.

## Evidence

- [Original trial](../numerical-trial.md) and [first fresh repeat](../repeat-trial/COMPARISON.md).
- [Second project evidence note](../../../examples/numerical-assurance-repeat-2/CHECKS.md) and [HTML report](../../../examples/numerical-assurance-repeat-2/report.html).
- [Portable derived paired results](paired-results.public.json). Original `paired-results.json`, `cross-check.json` and raw paired runs remain local; the published summary preserves outcomes, test identities and hashes while omitting execution paths.
- [Final native command receipts](../../../examples/numerical-assurance-repeat-2/evidence/final/commands.jsonl), with adjacent JUnit, logs, coverage and manifests.
