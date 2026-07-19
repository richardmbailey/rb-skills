# Phase 0: Plan Hardening And Feasibility Gates

## Phase Goal

Revise the constrained-execution design so every claimed control is implementable, its enforcement strength is stated honestly, and every review finding has a testable resolution before the walking skeleton begins.

This phase changes planning, design, and capability-evidence artifacts only. It does not create the three skills, install Pydantic, perform production or external writes, or execute a constrained implementation phase. Read-only host/CLI capability probes are permitted and must record their own control-plane effects and limitations.

## Scope

- The top-level constrained-execution implementation plan.
- Host capability evidence for Codex and, where safely available, Claude Code.
- The threat and assurance model.
- Agent roles, permissions, handoffs, and observation limits.
- Operation, path, environment, subprocess, network, and side-effect contracts.
- Global and project policy structure.
- Repository snapshots, concurrency, and control-plane state.
- Audit ownership, provenance, lifecycle, redaction, and human-intervention records.
- Canonical JSON, hashing, schema evolution, and dependency packaging.
- The validation matrix and safe fake-capability test strategy.
- Reduction of repeated normative material without losing requirements.

## Non-scope

- Creating or installing `$rb-create-low-level-plan`, `$rb-assess-plan-safety`, or `$rb-safe-operation`.
- Implementing the Pydantic models, policy engine, audit writer, executor, or verifier.
- Installing Pydantic or Pydantic AI.
- Running destructive, external-write, credential, or production tests.
- Changing the agreed optional, plan-wide, one-phase-at-a-time workflow.
- Removing independent assessor or verifier roles; this phase clarifies how strongly their boundaries can be enforced.
- Introducing a fixed repair-attempt cap for reversible local coding work.
- Modifying unrelated repository files or current user work.

## Dependencies

- [Top-level implementation plan](IMPLEMENTATION_PLAN.md).
- The completed review findings from 2026-07-18.
- Current `AGENTS.md`, `$rb-multi-agent-systems`, `$rb-working-diary`, `$rb-write-skill`, `$rb-create-skill-evals`, and `$rb-sync-skills-repo` contracts.
- Current Codex collaboration semantics: fresh contexts are available, while agents share the filesystem and tool surface unless the host provides a narrower mechanism.
- Current repository installation support for symlink and copy modes.
- A clean separation from unrelated working-tree changes.

## Required Deliverables

Keep the top-level plan as the concise workflow overview and place detailed normative contracts under this plan directory:

```text
plans/2026-07-18-constrained-plan-execution/
├── IMPLEMENTATION_PLAN.md
├── phase-0-plan-hardening-and-feasibility.md
├── references/
│   ├── assurance-and-threat-model.md
│   ├── operation-and-policy-contract.md
│   ├── execution-audit-state-model.md
│   └── validation-matrix.md
├── evidence/
│   ├── host-capability-probe.md
│   ├── phase-0-baseline.md
│   ├── revision-note.md
│   ├── preexisting-worktree.json
│   ├── review-findings.json
│   └── final-review.md
└── scripts/
    └── validate_phase0_docs.py
```

The reference files are normative extensions of the top-level plan. They must not duplicate one another. Each top-level invariant should have a stable identifier and one authoritative definition.

## Review Finding Coverage

| ID | Finding to resolve | Task groups | Primary deliverable | Completion evidence |
| --- | --- | --- | --- | --- |
| F-01 | Read-only sub-agent isolation is not necessarily host-enforced | A, B, I, J | `assurance-and-threat-model.md`, host probe | Capability matrix records fresh-context and tool-isolation levels separately |
| F-02 | Exact argv can hide interpreters and transitive execution | C, H, I, J | `operation-and-policy-contract.md` | Capability rules cover shells, interpreters, scripts, plugins, child processes, environment, and network |
| F-03 | Allowed paths can escape through traversal, links, aliases, or races | D, H, I, J | `operation-and-policy-contract.md` | Normative path-resolution algorithm and adversarial fixture list |
| F-04 | Complete tool-call capture and append-only audit provenance are not guaranteed | A, F, H, I, J | `execution-audit-state-model.md`, host probe | Evidence-source taxonomy and audit-owner decision |
| F-05 | Audit and diary control-plane writes contradict “no target writes” and affect state hashes | D, F, I, J | `execution-audit-state-model.md` | Product/control-plane separation and corrected Phase 1 exit wording |
| F-06 | “Project policy can only tighten” lacks a deterministically monotonic grammar | E, H, I, J | `operation-and-policy-contract.md` | Closed policy algebra with permitted narrowing operations and rejection cases |
| F-07 | Repository snapshots and concurrent mutation handling are underspecified | D, F, H, I, J | `execution-audit-state-model.md` | Snapshot schema, lease/conflict policy, and revalidation points |
| F-08 | Repository evidence can prompt-inject assessor, executor, and verifier | B, H, I, J | `assurance-and-threat-model.md` | Instruction-precedence and evidence-provenance rules plus adversarial cases |
| F-09 | Detrimental side-effect and confidence decisions lack a verdict rule | E, H, I, J | `operation-and-policy-contract.md` | Materiality matrix and evidence-coverage gate |
| F-10 | Unbounded repairs, final verification, resource exhaustion, and human intervention lack lifecycle states | F, H, I, J | `execution-audit-state-model.md` | State machine and transition table with resumable pauses |
| F-11 | Canonical JSON, hashes, artifact identity, threat model, and schema evolution are incomplete | B, G, H, I, J | `assurance-and-threat-model.md`, `operation-and-policy-contract.md` | Canonicalization and version-support decision with stated limits |
| F-12 | Pydantic dependency and cross-skill copy-mode packaging are unresolved | A, G, I, J | `host-capability-probe.md`, top-level plan | Tested packaging decision and fail-fast dependency contract |
| F-13 | Negative tests lack instrumented fake capabilities | H, I, J | `validation-matrix.md` | Fixture/adaptor inventory covers every prohibited capability safely |
| F-14 | Boolean representation, human records, and repeated normative material need cleanup | F, G, I, J | All references and revised top-level plan | Canonical `safe: true|false`, intervention schema, invariant cross-reference audit |

No finding may be removed from the matrix unless the phase notes record why it was invalid or superseded and the completion review accepts that decision.

## Task Checklist

### A. Baseline and feasibility evidence

- [v] Record the current top-level plan hash, line count, headings, open questions, and the F-01 through F-14 coverage matrix in the phase notes.
- [v] Update `$rb-working-diary` when Phase 0 starts with the authoritative plan path, current phase, remaining phases, current evidence location, and exact next action; do not duplicate the full plan or review.
- [v] Inspect the current Codex sub-agent interface and record, from observable evidence, whether it supports fresh context, per-agent tool restriction, filesystem isolation, parent-visible tool traces, cancellation, and typed result validation.
- [v] If a safe documented Claude Code sub-agent probe is available, record the same capabilities; otherwise mark them `unknown` without blocking the Codex-first plan.
- [v] Create `evidence/host-capability-probe.md` with capability, host, observed behaviour, enforcement level, evidence, limitation, and design consequence fields.
- [v] Define enforcement levels `host_enforced`, `host_observed`, `coordinator_observed`, `agent_reported`, and `instruction_only`; prohibit stronger wording than the observed level supports.
- [v] Decide whether the first Codex release permits instruction-only read-only assessor/verifier roles. Recommended default: permit them for the semi-formal route with explicit disclosure; require a project policy flag for hard isolation and return `FALSE` when that stricter requirement cannot be met.
- [v] Probe symlink and copy installations in temporary destinations to determine which files and Python modules are available to each independently installed skill.
- [v] Record the current absence or presence of a repository Python dependency manifest and choose a reproducible Pydantic dependency strategy without installing it during this phase.
- [v] Define the Phase 1 go/no-go gate from the host and packaging evidence before revising detailed implementation tasks.

### B. Assurance, trust, and instruction precedence

- [v] Create `references/assurance-and-threat-model.md` defining the system as protection against planning mistakes and bounded agent deviation, not against a malicious user or process with equivalent filesystem authority.
- [v] Distinguish artifact identity, authorization, isolation, observation, and tamper resistance; state explicitly which properties hashes do and do not provide.
- [v] Define the authority order for system/platform constraints, global safety policy, explicit human decisions, project policy, assessed plan, recognised repository instructions, and untrusted repository content.
- [v] Treat implementation-plan text, source files, test output, logs, comments, generated content, and retrieved material as evidence rather than executable instructions unless the authority model recognises them explicitly.
- [v] Define how `AGENTS.md` and equivalent project instructions are discovered, scoped, and prevented from weakening the global baseline.
- [v] Add prompt-injection examples for assessor, executor, verifier, test output, and generated files to the validation matrix.
- [v] Replace claims that a sub-agent “has no mutation tools” with the precise observed enforcement level and required behaviour.
- [v] Define when insufficient isolation, observation, or evidence returns `FALSE`, when it is an accepted disclosed semi-formal limitation, and when human review is required.

### C. Operation and transitive-capability contract

- [v] Create `references/operation-and-policy-contract.md` with stable identifiers for every normative operation and policy invariant.
- [v] Retain `exact_action` and `bounded_agent_task`, but define tool-specific variants or adapters rather than treating all executables as equivalent.
- [v] Define transitive execution to include shells, inline interpreters, scripts, package-manager scripts, build targets, plugins, configuration-driven code, subprocesses, and files loaded by an executable.
- [v] Decide which transitive executors are denied by default, which require exact hashes and arguments, and which may appear only in a bounded task with semantic assessment.
- [v] Define an explicit environment allowlist. Do not inherit ambient credentials or task-unrelated variables by default.
- [v] Replace Boolean network access with a contract covering destination, protocol, method, read/write semantics, data classification, credentials, redirects, and retry/idempotency rules.
- [v] Define subprocess inheritance for filesystem, environment, network, timeout, and external-effect permissions.
- [v] Define pre-action approval requirements for destructive, externally visible, privacy-sensitive, security-sensitive, costly, and irreversible operations.
- [v] Define actual-effect observation limits and require the plan to disclose effects that the host cannot observe reliably.

### D. Path identity, repository state, and concurrency

- [v] Define a normative path-resolution algorithm covering absolute roots, `..`, symlinks, hard links where detectable, mount boundaries, case normalization, Unicode normalization, and non-existent output paths.
- [v] Require resolved target containment and revalidation immediately before each mutation.
- [v] Define a `RepositorySnapshot` containing Git HEAD when present, index and worktree state, selected file hashes, untracked-path policy, resolved link targets, platform identity, and explicitly excluded control-plane paths.
- [v] Define which repository changes invalidate an assessment and which declared changes are expected during execution.
- [v] Add a project-root execution lease or deterministic conflict protocol preventing concurrent constrained runs from silently mutating the same workspace.
- [v] Define behaviour when the user or another process changes an assessed path during execution: stop, record actual state, and require revalidation or reassessment.
- [v] Record the unavoidable time-of-check/time-of-use residual risk when the host cannot provide atomic enforcement.

### E. Monotonic policy and side-effect decisions

- [v] Define the global policy as immutable for a run and identify its canonical source, version, and hash.
- [v] Define a closed project-policy algebra that permits only additional denials, narrower allowlists/roots/endpoints, lower resource maxima, stronger approvals, and stricter evidence requirements.
- [v] Reject free-form project-policy overrides, unknown operations, conflicting rules, and any attempted widening.
- [v] Keep semantic project guidance separate from the deterministic merge and prevent it from authorising an otherwise denied action.
- [v] Define a side-effect classification covering severity, likelihood, exposure, reversibility, detectability, mitigation, recovery, affected party, and cumulative interaction.
- [v] Define the materiality rule that maps classified effects to `safe: false`, human review, or an allowed documented effect.
- [v] Make evidence coverage and unresolved uncertainty the primary gate. Treat self-reported numeric confidence as supplementary unless an evaluation demonstrates calibration.
- [v] Define rule IDs and typed findings so each deterministic or semantic verdict cites the exact controlling invariant.

### F. Control plane, audit provenance, and lifecycle

- [v] Create `references/execution-audit-state-model.md` and assign a single owner to every mutable artifact.
- [v] Separate product-plane mutations from control-plane records such as audit events, policy reads, locks, manifests, and diary pointers.
- [v] Decide whether the default audit root remains project-local. If it does, exclude it explicitly from product-state comparisons while hashing and protecting it as control-plane state.
- [v] Protect the project policy, prior assessment, and prior audit events from executor writes by scope rule; record when this is instruction-only rather than host-enforced.
- [v] Define evidence sources `host_observed`, `coordinator_observed`, and `agent_reported`; never present agent-reported events as a complete host trace.
- [v] Define atomic event creation, ordering, crash recovery, duplicate detection, and hash chaining if useful, while stating that project-local hashes are not a malicious-tamper defence.
- [v] Define redaction before persistence where practical, not only after raw sensitive output has already entered a log.
- [v] Define a human-intervention record with decision type, artifact hashes, timestamp, stated rationale, revision/exit outcome, and the limits of identity verification.
- [v] Define canonical lifecycle states at least for `drafting`, `validating`, `rejected`, `approved`, `executing`, `verifying`, `repairing`, `paused_resource`, `human_required`, `verified`, `failed`, and `abandoned`.
- [v] Define all legal state transitions and the evidence required for each transition.
- [v] Preserve unbounded workflow-level repair attempts for reversible local work, but make host exhaustion a resumable `paused_resource` state followed by state and artifact revalidation.
- [v] Define diagnostic checkpoints without an automatic repeated-finding stop, and prohibit replay of high-risk side effects without a fresh idempotency or approval check.
- [v] Change Phase 1's unsafe-path criterion from “no target writes” to “no product-plane mutation; only declared control-plane records may be written.”

### G. Canonical artifacts and dependency packaging

- [v] Define canonical JSON behaviour for key ordering, UTF-8 and Unicode normalization, numbers, paths, line endings, nullability, timestamps, and unknown fields.
- [v] Separate the stable hashable payload from volatile metadata such as observation time, host session ID, or display text.
- [v] Use canonical JSON Boolean `safe: true|false`; reserve uppercase `TRUE` and `FALSE` for human-facing presentation only.
- [v] Define schema-version support, compatibility, migrations, unsupported-version failure, and hash changes across migrations.
- [v] Choose and document the Pydantic version range and dependency declaration; no helper may install it automatically.
- [v] Choose a canonical runtime package layout that works in both symlink and copy installations without handwritten model duplication.
- [v] If schemas are exported into consumer skills, define the generator, source hash, drift check, and runtime ownership; prove that schema availability is not mistaken for Python-runtime availability.
- [v] Define clear diagnostics for missing Pydantic, missing runtime files, version mismatch, schema drift, and unsupported host capability.

### H. Safe validation strategy

- [v] Create `references/validation-matrix.md` mapping F-01 through F-14 and every normative invariant to at least one deterministic, semantic, manual, or host-capability check.
- [v] Define fake filesystem, subprocess, network, external-service, approval, secret, and clock adapters for prohibited-operation tests.
- [v] Add canary fixtures for path traversal, symlink escape and swap, case aliases, untracked-file loss, out-of-scope writes, and concurrent mutation.
- [v] Add command fixtures for shells, inline interpreters, package scripts, build targets, plugins, child processes, inherited secrets, redirects, and external writes.
- [v] Add prompt-injection fixtures in plans, source comments, logs, test failures, generated files, and repository instructions.
- [v] Add audit fixtures for missing host trace, conflicting agent report, redaction-before-write, corrupted event order, duplicate events, policy tampering, and crash recovery.
- [v] Add lifecycle fixtures for unbounded local repair, resource pause/resume, repeated findings with strategy change, high-risk retry denial, human intervention, and abandoned runs.
- [v] Require known-good and deliberately bad fixtures for every deterministic validator.
- [v] Require repeated semantic trials and preserve every failure; do not let a successful rerun overwrite an earlier failed result.
- [v] Define release claims by enforcement level so an instruction-only test cannot be reported as host-enforced containment.

### I. Revise and simplify the top-level plan

- [v] Move detailed normative material into the four reference documents and keep `IMPLEMENTATION_PLAN.md` focused on goals, workflow, phases, risks, rollout, and success criteria.
- [v] Assign stable invariant IDs and replace repeated prose in goals, requirements, failure containment, validation, risks, and success criteria with precise references where readability improves.
- [v] Preserve all agreed decisions: optional route, plan-wide selection, one phase at a time, working-diary continuity, hybrid assessment, immutable `false`, no human relabelling, exact and bounded operations, separated verification with assurance accurately disclosed, flexible local repair, high-risk retry controls, and append-only-in-meaning records.
- [v] Correct every overstatement identified by the host probe, especially “no mutation tools,” “record every actual tool call,” “append-only,” and “no target writes.”
- [v] Resolve or relocate every existing open question. No blocking feasibility issue may remain assigned to Phase 1.
- [v] Update the architecture boundary table with responsibility, input, output, state owner, permission level, observation source, and failure mode for every agent and deterministic component.
- [v] Update Phase 1 ordering so capability and packaging prerequisites are already resolved and the walking skeleton begins with an executable supported path.
- [v] Update risks and success criteria to distinguish host-enforced, host-observed, coordinator-observed, agent-reported, and instruction-only controls.
- [v] Add a compact revision note listing which F-01 through F-14 changes were made and where their authoritative definitions now live.

### J. Phase completion review and fix cycle

- [v] Review the complete Phase 0 diff for contradictions, weakened safety, untestable claims, duplicated authority, broken links, stale terminology, and accidental changes outside the constrained-plan directory.
- [v] Use `$rb-review-pr-or-diff` for the revised plan and references; record every finding and fix all actionable Phase 0 issues.
- [v] Use `$rb-multi-agent-systems` to recheck agent boundaries, permissions, handoffs, state ownership, failure containment, observability, budgets, and durability.
- [v] Verify every F-01 through F-14 row has an implemented resolution and at least one verification result.
- [v] Rerun all structural, link, whitespace, coverage, and capability checks affected by review fixes.
- [v] Update `$rb-working-diary` at the completion checkpoint with the Phase 0 outcome, residual risks, Phase 1 readiness, and exact resume point.
- [v] Mark tasks `[v]` only after the evidence exists and the second verification pass confirms it.

## Verification Checklist

- [v] `evidence/host-capability-probe.md` separates observed facts from proposed behaviour and records unknowns honestly.
- [v] The threat model states the protected failure classes and excluded malicious-authority case.
- [v] Every agent boundary records fresh-context status, tool-isolation level, state ownership, and observation source.
- [v] Exact actions cannot be declared safe merely because their argv lacks shell metacharacters.
- [v] Path containment covers traversal, links, aliases, non-existent outputs, and revalidation.
- [v] Environment, subprocess, network, credential, and external-effect inheritance are explicit.
- [v] Project policy is structurally monotonic and has no generic override field.
- [v] Side-effect materiality produces a deterministic outer verdict rule with semantic evidence inside it.
- [v] Product-plane and control-plane writes are separate and Phase 1 uses the corrected language.
- [v] Repository snapshots, concurrency, user edits, and resume revalidation are specified.
- [v] Audit provenance never presents agent-reported evidence as a complete host trace.
- [v] Lifecycle states permit unbounded reversible repair without ambiguous “final” failure semantics.
- [v] Canonical JSON and schema evolution produce reproducible artifact identity.
- [v] Pydantic packaging is viable in both supported installation modes and requires no hidden auto-installation.
- [v] Prompt-injection and fake-capability fixtures cover assessor, executor, verifier, and control-plane failure paths.
- [v] Human intervention records preserve immutable rejected verdicts and distinguish revision from leaving the pipeline.
- [v] Canonical machine output uses `safe: true|false`.
- [v] The revised top-level plan is shorter or more authoritative per line, with no requirement lost through deduplication.
- [v] Every F-01 through F-14 item maps to an authoritative definition, a completed task, and verification evidence.
- [v] No repository file outside `plans/2026-07-18-constrained-plan-execution/` is changed by Phase 0; the required global working-diary checkpoints are the only external control-plane exception.
- [v] Final `$rb-review-pr-or-diff` and `$rb-multi-agent-systems` passes have no unresolved blocking finding.

## Tests And Checks

Run or create the following checks during Phase 0. Commands that depend on new files must be added to the phase notes when those files are implemented.

```bash
git diff --check
git status --short
rg -n '^## |^### ' plans/2026-07-18-constrained-plan-execution/
rg -n 'F-(0[1-9]|1[0-4])' plans/2026-07-18-constrained-plan-execution/
rg -n 'TRUE|FALSE|safe: true|safe: false' plans/2026-07-18-constrained-plan-execution/
```

Add deterministic checks for:

- all local Markdown links resolving;
- every F-ID appearing in the coverage matrix, task plan, validation matrix, and revision note;
- every normative invariant having one authoritative definition;
- every architecture role having input, output, state owner, permission level, observation source, and failure mode;
- no unsupported claim of host-enforced isolation or complete tool tracing;
- no changed path outside the constrained-plan directory;
- no unresolved P1 finding before Phase 1 begins.

Record manual or host probes with exact host, date, method, output summary, and limitation. Do not infer Claude Code capabilities from Codex results or vice versa.

## Phase Exit Criteria

- Every checklist task is `[v]`.
- Every F-01 through F-14 finding has an authoritative resolution and recorded verification evidence.
- The host-capability probe establishes an honest, usable Codex-first assurance level.
- The plan no longer claims hard read-only isolation or complete audit capture where only instruction-level behaviour is available.
- The operation contract covers transitive execution, path identity, environment, subprocesses, network, and external effects.
- The project-policy grammar is deterministically monotonic.
- Product-plane state, control-plane records, repository snapshots, concurrency, lifecycle, audit provenance, and resume behaviour are unambiguous.
- Prompt injection, side-effect materiality, canonicalization, schema evolution, dependency packaging, and safe negative-test instrumentation are fully specified.
- The top-level plan remains readable and materially less repetitive while preserving every agreed decision.
- Phase 1 has no unresolved prerequisite or blocking feasibility question.
- The phase completion review+fix cycle reports no blocking finding.

## Risks And Handling

- **The feasibility probe reveals no enforceable read-only sub-agent mode.** Keep the semi-formal route with disclosed instruction-only isolation if the agreed policy permits it; otherwise make the strict isolation profile unavailable rather than inventing enforcement.
- **Full child tool traces are unavailable.** Record observation coverage and rely on coordinator-observed state/diffs plus agent-reported events without calling them complete.
- **Copy-mode runtime sharing is impractical.** Prefer generated contracts plus a deliberately duplicated generated runtime artifact only if a drift check proves identity; otherwise require a separately installed support package and document it explicitly.
- **The revised plan grows further while adding detail.** Move normative details into the four references, use invariant IDs, and remove repeated restatements from the overview.
- **The hardening phase becomes product implementation.** Stop at contracts, evidence, and plan revision; defer Pydantic models and skill code to Phase 1.
- **Unrelated worktree changes complicate diff review.** Restrict Phase 0 edits to the constrained-plan directory and inspect changed paths explicitly before completion.
