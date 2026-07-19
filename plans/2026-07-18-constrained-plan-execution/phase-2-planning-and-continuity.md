# Phase 2: Low-Level Planning And Continuity Hardening

## Phase Goal

Compile realistic single phases into complete, reviewable operational contracts without inventing operations or losing later-phase continuity.

## Scope

- Complete exact-action and bounded-agent-task schemas.
- Phase selection, source/snapshot/instruction identity, effects, transitive capabilities, verification, stop conditions, and continuity pointers.
- Human views generated only from canonical JSON.

## Non-scope

- Authorising or executing a plan.
- New operation kinds beyond the four initial adapters and bounded tasks.

## Task Checklist

- [v] Finalise all fields and validators for `read_file`, `apply_patch`, `exec_argv`, `check`, and `bounded_agent_task`.
- [v] Implement exact one-phase extraction and binding for Markdown implementation plans.
- [v] Implement scoped repository-instruction discovery and snapshot binding.
- [v] Validate roots, executable identities, literal argument forms, environment, network, subprocess, delegation, and transitive capability declarations.
- [v] Require direct, indirect, cumulative, and verification-induced effects plus evidence and recovery declarations.
- [v] Require success criteria, verifier checks, stop/escalation conditions, and bounded adaptation dimensions.
- [v] Preserve later phase IDs, artifact locations, current state, and exact next action for diary handoff and resume.
- [v] Generate the human review document only from validated canonical JSON and verify hash correspondence.
- [v] Complete `rb-create-low-level-plan` instructions, examples, diagnostics, and adjacent routing boundaries.
- [v] Add realistic positive, ambiguous, unsupported, stale, over-broad, and continuity-loss fixtures and evaluations.

## Verification Checklist

- [v] Every supported operation has a complete good fixture and targeted missing/widening bad fixtures.
- [v] Ambiguous or unsupported phase content fails visibly without an invented operation.
- [v] Changed source, instruction, executable, path, or snapshot identity invalidates the plan.
- [v] Canonical JSON and generated human view identify the same payload hash.
- [v] Diary resume selects the exact current phase and retains every later phase ID.
- [v] Focused tests, routing checks, `git diff --check`, and phase review+fix succeed.

## Evidence

Record fixtures, canonical plans, rendered views, routing results, and resume simulation under `evidence/phase-2/`.

## Phase Exit Criteria

Representative phases compile completely; ambiguity, widening, unsupported actions, and stale state fail closed; all tasks are `[v]`; and the phase review is clear.
