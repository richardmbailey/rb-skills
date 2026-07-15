# Phase 1: Evaluation Walking Skeleton And Planning Family

## Phase Goal

Prove the complete improvement loop on one high-overlap family: capture a baseline, create discriminating routing cases, revise the planning-family descriptions, rerun the same cases, and record whether routing improves.

## Scope

- `rb-discuss`
- `rb-create-implementation-plan`
- `rb-execute-plan`
- `rb-create-issues`
- `rb-implement-with-tests`
- `rb-tdd-scientific-code`
- repository-level routing-eval structure under `evals/skill-routing/`

## Non-scope

- Other skill families.
- Body cleanup beyond wording required to keep the planning-family contracts consistent.
- Any `rb-wiki/` file.

## Dependencies

- Baseline commit `9875708`.
- `rb-create-skill-evals/scripts/validate_eval_manifest.py`.
- A safe method for running isolated routing trials or, if unavailable, an explicit manual execution protocol.

## Task Checklist

- [v] Record baseline metadata, description word counts, active model/harness, and the `rb-wiki` hashes.
- [v] Create `evals/skill-routing/eval-plan.json` with typed expected-routing fields or extend the existing eval schema in a backward-compatible way.
- [v] Add positive prompts for unresolved feature discussion, top-level implementation planning, existing-plan execution, issue decomposition, ordinary implementation, and scientific implementation.
- [v] Add adjacent-negative prompts that deliberately reuse shared words such as plan, implement, review, test, and phase.
- [v] Add ambiguous prompts whose correct behaviour is to ask one bounded clarification rather than silently choose.
- [v] Add a deterministic validator for manifest structure, unique case IDs, declared expected skill, and declared forbidden sibling skills.
- [v] Test the validator against a known-good manifest and a deliberately malformed manifest.
- [v] Run or manually record the baseline cases against commit `9875708` without changing prompts between trials.
- [v] Rewrite `rb-discuss` so it triggers on unresolved material requirements and does not intercept already-agreed implementation.
- [v] Rewrite `rb-create-implementation-plan` so it owns top-level planning from a rough idea and not execution of an existing plan.
- [v] Rewrite `rb-execute-plan` so it owns an existing plan, checklist, or phase and not initial idea formation.
- [v] Clarify `rb-create-issues` as issue decomposition from an existing PRD/plan, not general planning or external issue-tracker mutation.
- [v] Verify whether `rb-implement-with-tests` and `rb-tdd-scientific-code` already have sufficient boundaries; edit only if a case fails for a metadata reason.
- [v] Rerun the exact same cases under matched conditions.
- [v] Record baseline versus revised routing, trial variance, under-calls, over-calls, clarifications, and execution limitations.
- [v] Review the phase diff, fix actionable findings, and rerun affected cases.

## Verification Checklist

- [v] The eval manifest validator accepts the good suite and rejects the bad fixture.
- [v] Every planning-family skill has at least one positive and two sibling-negative cases.
- [v] Revised descriptions preserve natural paraphrases rather than relying on exact skill names.
- [v] No previously passing critical case regresses without an explicit decision.
- [v] The descriptions and README rows agree.
- [v] `git diff --check` passes.
- [v] No `rb-wiki/` path appears in the diff and all three hashes match.

## Tests And Commands

```bash
python3 rb-create-skill-evals/scripts/validate_eval_manifest.py evals/skill-routing/eval-plan.json
git diff --check
git diff --name-only -- rb-wiki/
shasum -a 256 rb-wiki/SKILL.md rb-wiki/agents/openai.yaml rb-wiki/references/design.md
```

The actual harness commands, raw-result locations, scores, and limitations are recorded in `evals/skill-routing/results/2026-07-15-phase-1-planning-family.md`.

## Phase Exit Criteria

- The routing-evaluation walking skeleton runs or has an honest, repeatable manual protocol.
- The planning-family baseline and revised results are directly comparable.
- The revised family shows clearer ownership of discussion, planning, execution, issue decomposition, and implementation.
- Every task is `[v]`, the phase review+fix cycle is complete, and `rb-wiki` remains unchanged.
