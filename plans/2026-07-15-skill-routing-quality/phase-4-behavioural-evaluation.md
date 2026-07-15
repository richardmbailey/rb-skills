# Phase 4: Behavioural Evaluation And Regression Hardening

## Phase Goal

Expand the walking-skeleton evaluations into repository-wide evidence that the revised skill metadata reduces under-calling and over-calling without weakening outcomes.

## Scope

- Every skill modified in Phases 1–3.
- Routing-family regressions for verification-first skills.
- Outcome tests for materially changed bodies.
- Baseline-versus-revised analysis.

## Non-scope

- Evaluating or modifying `rb-wiki`.
- Claiming universal performance across models or harnesses that were not tested.
- Optimizing wording to evaluator quirks without human review.

## Dependencies

- Stable revised metadata and bodies.
- Validated routing manifest and result schema.
- Baseline snapshot at `9875708`.
- Agreed primary model/harness and execution budget.

## Task Checklist

- [v] Give every modified skill at least three realistic positive prompts and three adjacent-negative prompts.
- [v] Add paraphrases that omit internal names and reuse vocabulary shared with sibling skills.
- [v] Add ambiguous cases with an expected clarification outcome.
- [v] Give the highest-risk families at least ten discriminating cases per family.
- [v] Include real historical prompts or traces when safely available.
- [v] Add outcome validators for changed bodies, not only routing assertions.
- [v] Prefer deterministic validators for paths, schemas, generated artifacts, exact safety boundaries, and executable results.
- [v] Use bounded semantic rubrics for intent, usefulness, restraint, and explanation quality.
- [v] Test every evaluator against one known-good and one deliberately bad result.
- [v] Run every important case in an isolated workspace without access to previous outputs.
- [v] Run at least three trials per critical case.
- [v] Run baseline and revised conditions with matched prompt, model, harness, limits, fixture, and evaluator.
- [v] Record selected skill, forbidden skills selected, clarification, outcome result, latency, token usage when available, and errors.
- [v] Separate routing failures from execution failures and evaluator failures.
- [v] Run a smaller Claude Code compatibility sample if a safe comparable harness is available.
- [v] Manually review every regression and unstable case.
- [v] Revise wording only when the evidence supports a specific routing defect.
- [v] Add regression cases for every defect found during the phase.
- [v] Produce `evals/skill-routing/results/<date>-routing-evaluation.md` with raw-result links and limitations.
- [v] Run phase review+fix and rerun affected cases.

## Metrics

- Correct target-skill selection rate.
- False-negative rate for intended triggers.
- False-positive rate for sibling-skill negatives.
- Appropriate clarification rate for ambiguous cases.
- Outcome pass rate when the target skill is used.
- Trial variance.
- Description token/word cost.
- Harness/model coverage and untested combinations.

Do not aggregate away family-level failures. A good global mean does not excuse a skill that consistently hijacks its sibling's requests.

## Verification Checklist

- [v] Baseline and revised conditions are directly comparable.
- [v] Every critical family has positive, negative, paraphrased, and ambiguous coverage.
- [v] Raw results are preserved and summarized accurately.
- [v] Targeted failures improve without creating a new critical regression.
- [v] Unstable cases are reported rather than converted into a single convenient pass/fail.
- [v] Evaluator limitations and unavailable harnesses are visible.
- [v] `rb-wiki` is absent from the evaluated-change set and remains byte-identical.
- [v] Phase review+fix is complete.

## Execution Record

The complete method, family metrics, regression review, raw-result paths, cost
counts, protected hashes, and harness limitations are recorded in
`evals/skill-routing/results/2026-07-15-routing-evaluation.md`.

No safe comparable Claude Code harness, exact model identifier, or per-case
latency/token telemetry was available. Those checks are marked verified because
the absence and resulting coverage limitation are explicitly recorded, not
because unobserved measurements were inferred.

## Phase Exit Criteria

- The routing changes are supported by repeated baseline-versus-revised evidence.
- Every remaining regression has a documented decision: fix, defer with reason, or revert the responsible wording.
- No improvement claim relies solely on static inspection.
- Every task is `[v]`, review findings are fixed, and `rb-wiki` remains unchanged.
