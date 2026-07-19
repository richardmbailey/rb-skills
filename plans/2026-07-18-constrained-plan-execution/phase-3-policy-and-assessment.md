# Phase 3: Policy And Assessment Hardening

## Phase Goal

Make every `safe: true` depend on complete deterministic policy evidence and a validated context-separated semantic assessment, while preserving every rejection and disclosing that freshness is instruction-only on the current host.

## Scope

- Full closed project-policy narrowing algebra and merge proof.
- Effect materiality, approvals, coverage, findings, semantic assessment, injection handling, and reassessment.

## Non-scope

- Product-plane execution and repair.
- Numeric confidence as an authorization signal.

## Task Checklist

- [v] Complete all `P-001` to `P-004` policy operations, semantic intersections, closed orders, conflicts, and field-by-field merge proofs.
- [v] Complete effect derivation, mitigation constraints, cumulative interaction, materiality, and the ordered `E-002` decision table.
- [v] Bind exact current approvals to plan, policy, operation, effect, target, expiry, and idempotency data.
- [v] Implement required-evidence coverage for every operation, capability, path, effect, policy rule, and verification action.
- [v] Validate typed findings and prevent Boolean/status contradictions.
- [v] Build bounded fresh-context assessor packets that omit planner reasoning and treat repository text as evidence.
- [v] Complete `rb-assess-plan-safety` instructions, immutable false behavior, revision linkage, and human-intervention choices.
- [v] Add deterministic fixtures for widening, conflicts, missing evidence, unsupported controls, effects, approvals, and immutable rejection.
- [v] Add matched semantic fixtures for hidden scope, detrimental effects, privacy, credentials, cost, external writes, irreversible actions, and prompt injection.
- [v] Run repeated fresh-context trials, retain every raw result, and label host, harness, and skill failures separately.

## Verification Checklist

- [v] Policy property/table tests prove every accepted project policy is monotonic or deny-all.
- [v] Every materiality decision row and boundary has a passing and blocking fixture.
- [v] Missing, stale, uncertain, contradictory, or insufficiently observed evidence always returns `safe: false`.
- [v] A false artifact remains false; revision creates a new hash and complete reassessment.
- [v] Semantic trials ignore embedded instructions and cite controlling authority or uncertainty.
- [v] Focused tests, repeated-trial report, `git diff --check`, and phase review+fix succeed.

## Evidence

Record merge proofs, assessments, raw semantic trials, typed findings, reassessment links, and aggregate counts under `evidence/phase-3/`.

## Phase Exit Criteria

Every accepted plan has complete deterministic and semantic evidence, every unsupported or uncertain case is false, all tasks are `[v]`, and the phase review is clear.
