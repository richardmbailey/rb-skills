# Assessed Low-Level Plan Execution Skills Implementation Plan

Execution Route: constrained

## Summary

Add an optional higher-assurance route between an approved implementation plan and execution. The normal `$rb-execute-plan` route remains available. When the constrained route is selected, one implementation phase at a time is compiled into a typed operational contract, assessed against immutable versioned policy, executed inside the approved envelope, and verified using separated agent evidence plus coordinator-observed product state.

The route introduces:

- `$rb-create-low-level-plan`: compiles the current phase into exact actions and bounded agent tasks;
- `$rb-assess-plan-safety`: runs deterministic and context-separated semantic assessment and returns human-facing `TRUE` only when canonical `safe: true` is justified;
- `$rb-safe-operation`: executes an unchanged approved bundle, coordinates repair inside its envelope, obtains context-separated verification, and owns the internal shared Pydantic runtime/CLI used by all three skills.

This is a semi-formal control layer, not a sandbox or proof of safety. On the probed Codex host, assessor and verifier read-only behaviour is instruction-only and child tool traces are incomplete. A stricter profile fails closed when the host cannot enforce its requirements.

## Agreed Product Decisions

- The constrained route is optional and is advertised when an implementation plan is created.
- Route selection is plan-wide by default, but compilation, assessment, execution, and verification happen one phase at a time against current state.
- The implementation plan retains every later phase; `$rb-working-diary` records the current phase, remaining phase IDs, artifact links, and exact next action.
- Assessment is hybrid: deterministic validation first, then semantic judgment in a fresh task context.
- A rejected assessment remains `safe: false`. A human may revise and reassess or leave the constrained pipeline, but cannot relabel the rejected artifact.
- The operation language supports typed exact actions and semantically bounded LLM tasks; it does not try to program every coding decision.
- Verification uses a requested fresh context, but on the semi-formal host both freshness and read-only behaviour are instruction-only. The final report records this limitation and does not claim host-proven independence.
- Reversible local repair may use `attempt_limit: "unbounded"`; normal host resource limits still apply. Repeated findings trigger diagnosis, not a fixed automatic stop.
- Destructive, external, costly, privacy-sensitive, security-sensitive, and irreversible retries need fresh idempotency and approval checks.
- Records are append-only in meaning: later versions and events preserve prior failures. Project-local files and hashes are not malicious-tamper-proof storage.

## Goals

- Improve fidelity, scope control, side-effect review, verification, and record keeping for implementation phases that merit additional assurance.
- Fail visibly on unsupported operations, missing evidence, detrimental effects, stale state, policy widening, or unavailable required host capabilities.
- Keep the ordinary implementation workflow intact and avoid over-triggering the constrained route.
- Provide reproducible typed artifacts and evidence without hidden dependency installation or real dangerous test actions.

## Non-goals

- Defending against a malicious user or process with equivalent filesystem/runtime authority.
- Compiling all phases in advance, replacing existing implementation skills, or requiring deterministic scripts for all coding work.
- Treating Pydantic, an LLM assessment, local hashes, or audit files as a security sandbox.
- Building a standalone Pydantic AI service, durable workflow platform, provider router, or telemetry deployment in the first release.
- Automatically installing dependencies, committing audit records, editing target `.gitignore`, or making external writes without normal authority.

## Normative References

Detailed rules live in one authoritative location each:

- [Assurance and threat model](references/assurance-and-threat-model.md): `A-*` authority, evidence, enforcement, isolation, and threat invariants.
- [Operation and policy contract](references/operation-and-policy-contract.md): `O-*`, `X-*`, `P-*`, `E-*`, `C-*`, and `K-*` operation, path, policy, side-effect, canonicalization, and packaging invariants.
- [Execution, audit, and state model](references/execution-audit-state-model.md): `R-*`, `D-*`, and `L-*` snapshot, concurrency, ownership, provenance, audit, and lifecycle invariants.
- [Validation matrix](references/validation-matrix.md): safe fake adapters, invariant checks, adversarial fixtures, and F-01 through F-14 coverage.
- [Host capability probe](evidence/host-capability-probe.md): observed Codex/Claude capabilities and honest enforcement levels.

If overview prose conflicts with a referenced invariant, the invariant controls after higher platform/human authority is applied under `A-003`.

## Workflow

1. `$rb-create-implementation-plan` presents `standard`, `constrained`, and `undecided` route choices without auto-selecting the constrained route.
2. When constrained is selected, `$rb-execute-plan` selects only the next phase and invokes `$rb-create-low-level-plan`.
3. The planner captures a repository snapshot, compiles the phase, declares direct/foreseeable/cumulative effects, and emits strict canonical JSON plus a generated human view.
4. `$rb-assess-plan-safety` validates schema, identity, policy, capabilities, paths, transitive execution, effects, evidence coverage, and repository state before invoking a fresh semantic assessor.
5. Any blocking condition produces immutable `safe: false`, findings, and human intervention. Only a complete pass produces `safe: true` for exact artifact and policy hashes.
6. `$rb-safe-operation` revalidates the bundle, policy, approvals, lease, paths, and current snapshot, then delegates approved operations to a fresh executor context.
7. The coordinator owns control-plane events and reconciles agent reports with state/diff observations. The executor may adapt only inside a bounded task's envelope.
8. A fresh verifier compares the actual state and evidence with the assessed contract. In-envelope reversible repairs may loop through diagnosis; new scope or high-risk replay requires reassessment/approval.
9. The phase ends only at `verified`, `rejected`, `human_required`, `failed`, or `abandoned`. It stops before compiling the next phase and checkpoints the working diary.

Machine artifacts use `safe: true|false`; `TRUE` and `FALSE` are display labels only (`C-003`).

## Architecture And Boundaries

| Role/component | Responsibility | Input | Output | State owner | Permission level | Context/handoff | Observation source | Failure mode |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Route coordinator | Select route/phase and sequence handoffs | Authoritative implementation plan, diary pointer | Phase/run identity and next invocation | Route coordinator | Control-plane writes only | Current coordinator context; typed/hash-checked handoffs | `coordinator_observed` | Stop on ambiguous route/phase |
| Phase planner | Compile one phase without executing it | Phase, snapshot, recognised instructions | Canonical low-level plan proposal | Coordinator | Repository read; declared control-plane proposal | Current planning context; private reasoning excluded from assessor bundle | Agent output plus coordinator validation | Invalid/incomplete plan; no assessment |
| Deterministic validator | Enforce schemas, hashes, policy, paths, capability gates | Canonical artifacts and observed state | Typed results/findings | Coordinator | Read-only computation | Process-local deterministic call; no agent context | `coordinator_observed` | Fail closed |
| Semantic assessor | Judge fidelity, hidden scope, harm, cumulative effects, uncertainty | Bounded evidence bundle without planner reasoning | Typed assessment proposal | Coordinator | Instruction-only read-only in semi-formal profile | Fresh task context; strict post-return typed validation | `agent_reported` | Invalid/failing/uncertain result -> false |
| Execution coordinator | Revalidate, hold lease, dispatch, persist events | Approved exact bundle and current state | Ordered events and product observations | Execution coordinator | Declared control-plane writes; dispatch only approved product actions | Current durable context; hash-checked executor/verifier handoffs | `coordinator_observed` plus host observations | Pause/stop; never silently broaden |
| Executor | Perform exact actions or bounded adaptation | Approved operation, scoped evidence | Product changes and typed event proposals | Current leased executor | Assessed envelope; platform gates remain | Fresh task context for phase execution; bounded prior evidence only | `agent_reported`, reconciled with state | Stop on drift/new scope/effect |
| Verifier | Compare result to contract; never repair directly | Current state, assessed bundle, reconciled evidence | Typed verification proposal | Coordinator | Instruction-only read-only in semi-formal profile | Fresh task context; no executor private reasoning | `agent_reported` plus coordinator state | Blocking finding -> repair/human/failure |
| Repair executor | Diagnose and repair within unchanged envelope | Finding, prior attempts, approved bundle | New product state and events | Current leased repair executor | Same envelope; high-risk replay separately gated | Fresh or deliberately refreshed task context with typed attempt history | Same as executor | Pause or reassess when envelope insufficient |
| Shared runtime | Typed models, canonicalization, merge, validators, schema generation | Strict JSON and deterministic inputs | Validated objects, hashes, schemas, diagnostics | Explicit runtime setup command holding setup lock | Deterministic computation and configured control reads | Process-local CLI; manifest/version/hash checked | `coordinator_observed` | Named fail-fast diagnostic |
| Human reviewer | Revise, leave pipeline, approve declared gate, resume, or abandon | Immutable artifacts/findings | Human intervention event | Coordinator | Platform-recognised decision only | Platform interaction; exact artifact hashes displayed | `host_observed` where available | Identity limit disclosed; no relabelling |

The first release uses the `semi_formal` Codex profile under `A-007`. `strict_isolation` and Claude profiles remain unavailable until capability probes establish their requirements.

## Data, Policy, And Packaging Decisions

- Strict Pydantic v2 models reject unknown fields and generate JSON Schema; canonical bytes and artifact identity follow `C-001` to `C-004`.
- Runtime dependency is Python 3.9+ with `pydantic>=2.12,<3`, declared and pinned inside `$rb-safe-operation`; a separately approved setup provisions the dedicated environment, while normal helpers never install (`K-001`). Pydantic AI is not required.
- Symlink and copy installations select the three user-facing skills together. `$rb-safe-operation` owns the handwritten runtime; all three invoke one manifest-pinned installed CLI and do not import private sibling files (`K-002`). Generated schemas include source/schema hashes and have deterministic drift checks (`K-003`).
- The global policy is immutable for a run. Project policy has only the closed monotonic narrowing algebra in `P-001` to `P-004`.
- Default audit root is `.rb-safe-operation/runs/<run-id>/`, excluded from product-state comparisons but protected and hashed as control-plane state (`D-001` to `D-003`).
- Repository identity, expected changes, user edits, and concurrency follow `R-001` to `R-005`; path containment follows `X-001` and `X-002`.

## Implementation Phases

### Phase 0: Plan Hardening And Feasibility Gates

Complete [the Phase 0 checklist](phase-0-plan-hardening-and-feasibility.md). It resolves F-01 through F-14 in normative references, records host/installation evidence, removes unsupported assurance claims, and leaves no Phase 1 prerequisite open.

Exit only when every Phase 0 task is `[v]` and final review has no blocking finding.

### Phase 1: Supported End-To-End Walking Skeleton

Complete [the Phase 1 checklist](phase-1-supported-walking-skeleton.md).

- Scaffold the three skills, with the runtime Python project owned by `$rb-safe-operation`, plus metadata, dependency declaration, and generated-schema drift tooling.
- Implement the minimum strict artifacts, canonicalization, hashing, policy merge, audit manifest/event writer, snapshot, and capability gate required by the fixtures.
- Install all three folders together into temporary symlink and copy destinations; explicitly provision temporary runtime environments and prove every skill invokes the same manifest-pinned version and source hash.
- Compile one disposable-repository phase containing one supported exact action and one bounded task.
- Run an unsafe fixture through deterministic and semantic assessment to immutable `safe: false`; it may write declared control-plane records but must make no product-plane mutation.
- Run a safe fixture through `safe: true`, lease/revalidation, clean-context execution, separated verification, and diary-handoff simulation.
- Record evidence provenance accurately; do not claim complete child trace or host-enforced role isolation.

Exit when both paths are observable, identity is reproducible, scope escape is blocked/detected according to the semi-formal profile, and all Phase 0 packaging/capability prerequisites remain true.

### Phase 2: Low-Level Planning And Continuity Hardening

Complete [the Phase 2 checklist](phase-2-planning-and-continuity.md).

- Finalise supported exact adapters and bounded-task fields from realistic fixtures.
- Enforce one-phase-at-a-time compilation, current snapshots, effects, path identity, transitive capabilities, stop conditions, verification, and later-phase continuity.
- Generate human review views only from canonical JSON.
- Add planning/routing evaluations for fidelity, ambiguity, over-broad scope, unsupported operations, and working-diary resume.

Exit when representative phases compile completely and unsafe ambiguity fails visibly without invented operations.

### Phase 3: Policy And Assessment Hardening

Complete [the Phase 3 checklist](phase-3-policy-and-assessment.md).

- Implement the full monotonic project-policy algebra and materiality/evidence rules.
- Expand deterministic and semantic fixtures for policy weakening, injection, hidden scope, direct/cumulative/verification effects, privacy, credentials, cost, external writes, and irreversible actions.
- Enforce immutable rejection and complete reassessment after revision.
- Repeat semantic trials, preserve every failure, and distinguish host/harness/skill failure.

Exit when each `safe: true` has complete deterministic and semantic evidence and every unsupported, uncertain, or violating case is false.

### Phase 4: Execution, Verification, Repair, And Resume Hardening

Complete [the Phase 4 checklist](phase-4-execution-verification-and-resume.md).

- Implement all operation adapters, mutation-time path checks, snapshot invalidation, lease/conflict handling, event provenance/redaction/recovery, and lifecycle transitions.
- Reconcile agent-reported actions with coordinator/host observations without claiming a complete trace.
- Exercise separated verification, unbounded reversible repair, diagnostic strategy changes, host pause/resume, and high-risk retry gates.
- Stop and preserve evidence for scope drift, concurrent user change, stale approval, new effects, corrupted audit state, or required reassessment.

Exit when reversible work can adapt naturally, high-risk effects cannot replay silently, resume never reuses stale approval, and both coordinator snapshot evidence and separated verifier evidence are required for `verified`.

### Phase 5: Workflow Integration And Release Readiness

Complete [the Phase 5 checklist](phase-5-integration-and-release.md).

- Add the optional route reminder and route field to `$rb-create-implementation-plan`; update `$rb-execute-plan`, README, metadata, sibling routing boundaries, and working-diary guidance.
- Add routing, instruction-contract, deterministic, adversarial, repeated semantic, with/without-skill, installation, redaction, and stale-reference evaluations.
- Validate all three installable skill folders and the internal runtime environment, then refresh active skills through the repository sync script only after source checks pass.
- Review safety claims, portability, routing, hidden fallback, generated drift, and record integrity; fix all actionable findings and rerun affected checks.

Exit when the route is discoverable but optional, ordinary execution remains intact, behavioural evidence supports claims at the stated enforcement levels, and final review is clear.

Each implementation phase gets a dedicated `$rb-execute-plan` phase file with `[ ]`, `[x]`, and `[v]` tasks and evidence paths.

## Validation Strategy

The [validation matrix](references/validation-matrix.md) is authoritative. In summary:

- use structured parsing/Pydantic for syntax and LLM judgment only for meaning;
- run dangerous cases entirely through ledgered fake filesystem, subprocess, network, service, approval, secret, clock, resource, and agent adapters;
- require good and bad cases for every deterministic validator;
- repeat semantic trials and preserve all raw failures;
- inspect complete diffs and changed paths, run metadata/routing/instruction/schema/install checks, and use `$rb-review-pr-or-diff` plus `$rb-multi-agent-systems` at phase gates;
- mark `[v]` only after implementation evidence and a second verification pass.

## Rollout And Rollback

1. Implement and evaluate in source and disposable repositories without changing installed skills.
2. Prove the Codex semi-formal walking skeleton and both installation modes.
3. Integrate the optional reminder only after the route passes focused checks.
4. Install the three skills together, provision the internal runtime explicitly, smoke-test discovery, and keep standard `$rb-execute-plan` available.
5. Advertise strict or Claude profiles only after their own capability suites pass.

Rollback removes the optional reminder and installed constrained skills through normal source/Git and sync procedures. It does not delete user audit bundles or alter the standard route. Withdrawn schema/runtime versions become unsupported and fail closed; earlier failure evidence remains visible.

## Principal Risks

- **Assurance overclaim:** enforce `A-006`; release claims use the weakest observed level.
- **Correlated LLM mistakes/injection:** fresh contexts, deterministic gates, bounded evidence, authority rules, repeated trials, and visible uncertainty.
- **Transitive or path escape:** executable/input classification, explicit inheritance, `X-001`/`X-002`, snapshots, lease, and adversarial fakes.
- **Irreversible harm before verification:** policy prohibition or exact pre-action approval/idempotency; post-checking alone is insufficient.
- **Unbounded repair consumes resources or repeats harm:** host pause/resume for local work; fresh gates for every high-risk replay.
- **Incomplete audit or local tampering:** provenance labels, coordinator snapshots, event recovery, and explicit equivalent-authority exclusion.
- **Secrets in records:** redact/omit before durable writes and report inaccessible host-log limitations.
- **Copy installation/runtime drift:** explicit three-skill install with the internal runtime owned by `$rb-safe-operation`, declared dependency, generated-schema hashes, and temporary install tests.
- **Routing overlap:** matched positives and adjacent negatives for every sibling skill; ordinary route remains available.

## Success Criteria

- The optional route is reminded but never automatically selected; one current phase is processed while later phases and diary continuity remain visible.
- Every accepted artifact is strict, versioned, canonical, hash-identifiable, policy-bound, and unchanged at handoff.
- Project policy can only narrow the global baseline, and unsupported hosts/operations fail visibly.
- Assessment covers fidelity, hidden scope, detrimental direct/cumulative/verification effects, and evidence uncertainty under `E-001` to `E-004`.
- Rejection is immutable; human decisions create explicit records and never relabel false as true.
- Semi-formal assessor/verifier limits and incomplete trace coverage are disclosed; no result is promoted to a stronger assurance level than tested.
- Executor adaptation and unbounded reversible repair remain inside the assessed envelope; high-risk actions cannot retry indefinitely or bypass approval.
- Unsafe fixtures make no product-plane mutation; successful phases reach `verified` only with both evidence sources and no undeclared material effect.
- Audit events preserve earlier failures, redact before persistence where practical, survive recovery checks, and leave a usable next-action diary pointer.
- The three skills and their single `$rb-safe-operation`-owned runtime work in both symlink and copy installations with no handwritten model duplication or hidden installation.
- Release-scoped routing, deterministic, adversarial, semantic, installation, and final-review evidence has no unresolved blocking finding; target-matrix cases not implemented in the first release are listed explicitly rather than counted as passes.

## Resolved Phase 0 Questions

- Runtime ownership: `$rb-safe-operation` owns the one handwritten runtime; all three skills use its separately provisioned manifest-pinned CLI.
- Initial active adapters: `read_file`, `apply_patch`, and bounded `read`/`apply_patch` tasks. `exec_argv` and `check` are typed but disabled by the immutable first-release policy; expansion is evidence-led.
- Codex agent controls: semi-formal requested fresh contexts with instruction-only freshness, resource, and role read-only behaviour; strict isolation unavailable on the probed host.
- Claude controls: compatibility remains unadvertised until authenticated runtime probing succeeds.
- Redaction: typed secret handles and adapter filtering before persistence; uncertain free text is omitted with a reason.
- Isolation harness: ledgered fake-agent capability tests plus a repeatable manual host probe; no invented claim of a complete non-interactive host trace.

No blocking feasibility question remains for the Codex-first Phase 1 path.
