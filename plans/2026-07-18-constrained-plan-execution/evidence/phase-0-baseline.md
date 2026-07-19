# Phase 0 Baseline And Feasibility Record

## Baseline

- Captured: 2026-07-18, Codex desktop, Europe/London.
- Authoritative plan: `../IMPLEMENTATION_PLAN.md`.
- Pre-Phase-0 SHA-1: `6c1cbbf0d24985326c129dd4b530315b51cf2ff2`.
- Pre-Phase-0 size: 498 lines.
- Phase checklist: `../phase-0-plan-hardening-and-feasibility.md`, initially 273 lines and 110 unchecked tasks.
- Initial top-level headings: Summary, Goals, Non-goals, Users, Requirements, Assumptions, Constraints, Proposed Approach, Implementation Phases, Validation Plan, Rollout and Rollback, Risks, Success Criteria, Open Questions.
- Initial open questions: runtime package ownership; first exact-action variants; portable agent controls; sensitive-value redaction; non-interactive isolation harness.
- Worktree caution: unrelated modified, deleted, and untracked paths existed before Phase 0. Phase 0 owns only `plans/2026-07-18-constrained-plan-execution/` plus the required external working-diary checkpoint.

The F-01 through F-14 coverage matrix in the phase file is the baseline review inventory. No finding has been removed or superseded.

## Feasibility Decisions

1. The first release is Codex-first and offers two assurance profiles:
   - `semi_formal`: fresh assessor and verifier task contexts are required; their read-only behaviour may be instruction-only if disclosed.
   - `strict_isolation`: every required isolation capability must be `host_enforced`; otherwise assessment returns `safe: false` with `unsupported_host_capability`.
2. Claude Code remains a compatibility target, but its runtime capability status is `unknown` until an authenticated probe succeeds. Documented CLI switches are not treated as runtime proof.
3. `$rb-safe-operation` owns the canonical internal Python runtime so the public workflow remains three skills. All three skills are selected together in symlink and copy installations. An explicitly human-invoked setup provisions a pinned dedicated environment and manifest under a host control root; normal helpers never install dependencies. All three invoke the manifest-pinned CLI. Generated JSON Schemas are inspectable contracts, not executable runtime code.
4. The runtime declares `pydantic>=2.12,<3` and Python 3.9 or newer in its own `pyproject.toml`, with locked or hash-pinned deployment data. Helpers diagnose a missing, stale, or incompatible environment and never repair it implicitly. Pydantic AI is not a dependency for the typed vocabulary.
5. Phase 1 may begin only if all three skills can be selected and installed in both supported modes, the `$rb-safe-operation` setup works in temporary host control roots, every skill invokes the same manifest-pinned runtime version/source hash, generated schemas match their recorded source hash, and the Codex `semi_formal` profile passes the safe and unsafe walking-skeleton fixtures.

The Pydantic range selects the current stable v2.12 API family and Python 3.9+ support observed in the [official installation documentation](https://pydantic.dev/docs/validation/latest/get-started/install/) on 2026-07-18 and deliberately excludes the next major version. Phase 1 must lock exact transitive versions in a development environment for reproducible tests; the reusable skill must not modify a target project's environment automatically.

## Installation Probe

- Method: `rb-sync-skills-repo/scripts/sync_skills_repo.py` installed the existing `rb-execute-plan` skill to two temporary destinations.
- Temporary root: `/tmp/rb-constrained-install-probe.81oKcQ`.
- Symlink result: destination pointed to the complete source skill directory.
- Copy result: destination contained only the selected skill's `SKILL.md` and `agents/openai.yaml`.
- Dependency manifests at repository root: none found by the Phase 0 manifest scan.
- Consequence: an independently copied skill cannot import a sibling's private Python files, and copying a `pyproject.toml` does not install it. Shared handwritten code therefore runs through an explicitly selected, explicitly provisioned, manifest-pinned runtime CLI. Any exported schema must be generated and hash-checked.

## Finding Status

| Finding | Resolution owner | Phase 0 state |
| --- | --- | --- |
| F-01 | `assurance-and-threat-model.md`, host probe | Defined |
| F-02 | `operation-and-policy-contract.md` | Defined |
| F-03 | `operation-and-policy-contract.md` | Defined |
| F-04 | `execution-audit-state-model.md`, host probe | Defined |
| F-05 | `execution-audit-state-model.md` | Defined |
| F-06 | `operation-and-policy-contract.md` | Defined |
| F-07 | `execution-audit-state-model.md` | Defined |
| F-08 | `assurance-and-threat-model.md`, validation matrix | Defined |
| F-09 | `operation-and-policy-contract.md` | Defined |
| F-10 | `execution-audit-state-model.md` | Defined |
| F-11 | assurance, operation, and audit references | Defined |
| F-12 | this record and top-level plan | Defined |
| F-13 | `validation-matrix.md` | Defined |
| F-14 | all references and revision note | Defined |
