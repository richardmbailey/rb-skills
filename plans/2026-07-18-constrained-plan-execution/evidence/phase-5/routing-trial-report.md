# Constrained routing trial report

The revised routing descriptions classified every blinded case correctly in all three trials. The result was stable across repetitions: 36 of 36 classifications passed, with no case-level errors.

## Results

| Trial | Condition | Passed | Failed | Accuracy |
|---|---|---:|---:|---:|
| 1 | revised | 12/12 | 0 | 100% |
| 2 | revised | 12/12 | 0 | 100% |
| 3 | revised | 12/12 | 0 | 100% |
| Aggregate | revised | 36/36 | 0 | 100% |

Every trial produced the same selection distribution: three `rb-create-low-level-plan`, three `rb-assess-plan-safety`, three `rb-safe-operation`, and one each of `rb-create-implementation-plan`, `rb-execute-plan`, and `rb-implement-with-tests`.

## Case-level errors

None. The scorer returned an empty `failures` array for each trial and for the aggregate run. There were no wrong outcomes, wrong selected skills, or forbidden-skill hits.

## Commands and results

Run from the repository root:

```bash
python3 evals/skill-routing/score_results.py plans/2026-07-18-constrained-plan-execution/evidence/phase-5/constrained-routing-manifest.json plans/2026-07-18-constrained-plan-execution/evidence/phase-5/routing-result-trial-1.jsonl
python3 evals/skill-routing/score_results.py plans/2026-07-18-constrained-plan-execution/evidence/phase-5/constrained-routing-manifest.json plans/2026-07-18-constrained-plan-execution/evidence/phase-5/routing-result-trial-2.jsonl
python3 evals/skill-routing/score_results.py plans/2026-07-18-constrained-plan-execution/evidence/phase-5/constrained-routing-manifest.json plans/2026-07-18-constrained-plan-execution/evidence/phase-5/routing-result-trial-3.jsonl
python3 evals/skill-routing/score_results.py plans/2026-07-18-constrained-plan-execution/evidence/phase-5/constrained-routing-manifest.json plans/2026-07-18-constrained-plan-execution/evidence/phase-5/routing-result-trial-1.jsonl plans/2026-07-18-constrained-plan-execution/evidence/phase-5/routing-result-trial-2.jsonl plans/2026-07-18-constrained-plan-execution/evidence/phase-5/routing-result-trial-3.jsonl
```

All four commands exited with status 0. The three individual summaries each reported `total: 12`, `passed: 12`, `failed: 0`, and `pass_rate: 1.0`; the aggregate summary reported `total: 36`, `passed: 36`, `failed: 0`, and `pass_rate: 1.0`.

## Scope

These result files contain only the `revised` condition. They demonstrate perfect repeated revised-routing accuracy, but they do not provide a matched baseline result or a baseline-to-revised lift estimate.
