# Execution, Audit, And State Model

## Purpose

This document defines the mutable state, its owner, the evidence that can support claims about it, and the lifecycle of an assessed run. The audit is durable and append-only in meaning, not a claim of storage-level immutability.

## Repository State And Concurrency

### `R-001` Repository Snapshot

Before assessment and again before execution, capture a typed `RepositorySnapshot` containing:

- absolute resolved project root, platform/OS, filesystem case behaviour, Unicode normalization, and relevant device/mount identities;
- Git HEAD and branch when present; index tree/state; staged, unstaged, and untracked path summaries, using a fixed absolute Git executable whose path and content hash are bound into the snapshot;
- a full project inventory outside `.git` and the canonical control root, including file content or link target, file type, mode, ownership, device, inode, link count, and empty directories, so non-Git repositories do not degrade to selected-file observation;
- selected file and applicable repository-instruction hashes;
- resolved symlink targets and detectable hard-link identities for assessed/protected paths;
- declared expected product-plane changes and the policy for pre-existing untracked paths;
- excluded control-plane roots, with separate hashes for policy and prior audit payloads.

Do not hash secrets or unnecessary full file contents into the audit. Use content hashes and bounded metadata.

### `R-002` Snapshot Invalidation

Any change to source phase, global/project policy, applicable instructions, operation input, executable/script/config identity, allowed/protected path identity, expected preimage, Git index entry, relevant untracked path, mount/device, or required host capability invalidates assessment. Changes are expected only after execution starts, only where declared by the operation, and only in operation order. Declared product output changes do not invalidate later operations when their expected predecessor operation and resulting hash are recorded.

### `R-003` Project Execution Lease

One constrained run may hold the project-root mutation lease. The first-release locator is `<resolved-project-root>/.rb-safe-operation/execution.lease`, outside every run-specific directory; external audit roots are unsupported. Its `project_key` is lowercase SHA-256 of `b"rb-safe-operation\0project-root\0" + utf8_nfc_resolved_root + b"\0" + device_identity_ascii`. The lease payload also includes run ID, random ownership token, process/session metadata, creation time, heartbeat, and prior event hash. The coordinator creates it with create-if-absent/exclusive semantics after validating the `.rb-safe-operation` path under `X-001`; only the holder presenting the ownership token and expected current lease hash may heartbeat or release it. Any existing live, stale, or indeterminate lease stops execution and is never silently stolen. Automatic stale recovery is outside the first release. If project-local control writes or atomic create-if-absent are unavailable, the profile is unsupported; a per-run lock is never sufficient.

### `R-004` Concurrent Or External Change

If the user, another agent, Git operation, watcher, or process changes an assessed path or relevant instruction/policy during execution, stop before the next mutation, record the coordinator-observed state, preserve the event stream, and enter `human_required` or `paused_resource` as appropriate. Only `paused_resource` can resume in place, after lease recovery and snapshot revalidation. A `human_required` stop is exit-only in the first release; resolution or material drift requires a newly identified and reassessed run. Never overwrite or “clean up” an unexpected user change.

### `R-005` Time-Of-Check/Time-Of-Use Limit

Containment, identity, and lease checks are repeated immediately before mutation, but a host without atomic descriptor-relative enforcement cannot eliminate the interval between check and use. This residual risk is disclosed in semi-formal assessments. A policy requiring atomic enforcement makes the active host unsupported rather than accepting the race silently.

## Product And Control Planes

### `D-001` Plane Separation And Ownership

Product-plane state is the target repository content, index, working tree, external systems, and generated outputs that implement the phase. Control-plane state is policy snapshots, canonical plan/assessment payloads, manifests, locks, audit events, host observations, and working-diary pointers. Proposal production, external source authority, and durable writing are distinct; each durable mutable artifact has one writer:

| Artifact | Plane | Sole durable writer/mutation role | Proposal or external source | Readers |
| --- | --- | --- | --- | --- |
| Low-level plan version | Control | Coordinator | Planner proposes typed payload | Assessor, executor, verifier |
| Deterministic assessment | Control | Coordinator | Validator returns result | Assessor, executor, verifier |
| Semantic assessment result | Control | Coordinator after schema validation | Assessor proposes | Executor, verifier |
| Global policy snapshot | Control | Coordinator | Versioned runtime package is source | All roles read scoped copy |
| Project policy snapshot | Control | Coordinator | Project owner file is source | All roles read scoped copy |
| Runtime environment/manifest | Control | Explicit human-invoked setup command holding the setup lock | `$rb-safe-operation` source and pinned dependencies | All three skills invoke/read |
| Prior assessment/approval snapshot | Control | Coordinator | Earlier immutable run/human event | Executor/verifier read |
| Lease and lifecycle manifest | Control | Coordinator | Agents submit typed requests only | All roles read state |
| Audit event | Control | Coordinator | Executor/verifier submit typed reports | All roles read bounded history |
| Product files and allowed external effects | Product | Current leased executor through approved operations | Planner/assessor define envelope | Verifier reads; coordinator observes |
| Verification report | Control | Coordinator after schema validation | Verifier proposes | Human/coordinator read |
| Working-diary checkpoint | Control | Coordinator | Run state supplies pointer fields | All roles read pointer only |

The unsafe path may write declared control-plane records but must make no product-plane mutation.

### `D-002` Audit Root And State Comparison

The audit root is project-local at `.rb-safe-operation/runs/<run-id>/`. It is explicitly excluded from product-state comparisons and included in separate control-plane integrity checks before and after executor or subprocess handoffs. The workflow never changes `.gitignore`, stages, commits, or deletes records automatically. External audit roots fail schema validation in the first release.

### `D-003` Protected Control State

Global/project policy payloads, prior plan/assessment/approval payloads, prior events, and lease ownership are outside executor and verifier write scopes. On the probed Codex profile this protection is partly instruction-only because agents share filesystem capabilities; the coordinator therefore compares hashes and rejects unexpected changes. Strict profile availability requires host-enforced write protection.

### `D-004` Evidence Provenance

Every observation is labelled `host_observed`, `coordinator_observed`, or `agent_reported` and links to the observer, time envelope, operation/event ID, and bounded evidence. Agent-reported calls or effects are never described as a complete host trace. Conflicts are preserved as separate observations and produce a blocking finding; one report must not overwrite another.

Plan-authored evidence cannot promote itself to host provenance. In the first release, `host_observed` is forbidden in a low-level plan. `coordinator_observed` plan evidence must name an exact selected-file or instruction locator already bound into the coordinator-created repository snapshot; `agent_reported` evidence must use its structural `agent-report:<evidence-id>` locator. Effect observation sources must exactly match the provenance of their referenced evidence, and agent-only evidence cannot support `full` or `partial` detectability.

### `D-005` Event Creation And Recovery

The coordinator validates and redacts a proposed event, writes it to a temporary file under the audit root, flushes where supported, and atomically renames it to a monotonically numbered write-once-by-contract filename. This is `instruction_only` against equivalent-authority writers on the project-local host. Each persisted event contains run ID, sequence, event UUID, stable payload, payload hash, provenance, redacted observation envelope, previous event-record hash (`null` only for sequence zero), algorithm, and event-record hash. The event-record hash is lowercase hexadecimal SHA-256 over the `C-001` canonical full event object with only `event_record_hash` omitted, domain-separated as `rb-safe-operation`, `event-record`, and its schema version under `C-002`; thus run/sequence/UUID, payload hash, provenance, redacted envelope, and previous hash are covered. Duplicate UUID or payload/sequence conflicts are rejected and recorded in a recovery event. On restart, scan and validate the chain, quarantine incomplete temporary files, preserve forks/corruption as evidence, and require human review before resume.

Reload parses strict JSON, rejects duplicate or normalization-colliding keys, validates the typed event, and requires the persisted bytes to equal its canonical encoding plus one final newline. Hash chaining detects accidental replacement relative to an independently retained expected head. Project-local hashes do not prevent malicious equivalent-authority tampering and are not called tamper-proof or truly append-only.

### `D-006` Redaction Before Persistence

Validate typed fields and redact or omit secrets before durable event creation. Structured secret handles are recorded by name/audience and optional one-way fingerprint, never value. Tool adapters must bound and filter stdout/stderr before returning it to the coordinator where practical. If sensitive raw output has already entered inaccessible host logs, record that limitation; copying it into the project audit is prohibited. Uncertain free text is omitted with a redaction reason rather than persisted for later semantic cleanup.

### `D-007` Human Intervention Record

The typed human-intervention schema can carry decision type (`revise_and_reassess`, `leave_constrained_pipeline`, `approve_declared_gate`, `abandon`, or `resume_after_pause`), exact plan/assessment/policy/snapshot hashes, affected operation/effect, UTC timestamp, stated rationale, resulting version/exit outcome, and approval expiry/idempotency data when relevant. The first-release coordinator persists the structured audit event that enters `human_required`, then closes and rejects reload; it does not yet authenticate, persist, or apply a later human-decision artifact in place. Manual declared-gate approval therefore uses the bounded procedure in the runtime contract, always records `identity_verification: unavailable`, and enters a newly identified reassessment whose bundle retains the exact approval. A rejected assessment remains `safe: false`; revision creates a newly identified run, and leaving the pipeline does not make the rejected artifact executable. If the protected project-local control store is itself the corrupted object, the coordinator stops without attempting another audit write through it; the stdout handoff discloses that the final stop event could not be persisted.

### Coordinator-Bound Execution And Verification

There is no artifact-only mutation or caller-asserted verification CLI. The verified synchronous coordinator driver revalidates the exact plan, original semantic proposal, assessment, immutable installed global policy, no-wider active policy, current snapshot, host capability profile, and approval bindings; acquires the project lease; advances lifecycle; appends audit events; and holds the lease through execution and verification. Exact actions are private dispatcher calls beneath that coordinator. The coordinator requests a separated verifier context and issues a one-use context binding to the exact plan and assessment hashes. A typed `VerificationProposal` must repeat those hashes and the snapshot hash, name the issued context, provide only `agent_reported` evidence with structural locators, and enumerate the exact success criteria, verifier checks, observed effects, and findings. The coordinator combines that proposal with its own snapshot binding and creates the final report. Current fresh-context separation is `instruction_only`, so `independent_context` remains false. Missing, extra, conflicting, stale, rejected, or unbound evidence cannot reach `verified`.

## Lifecycle

### `L-001` Canonical States

The run manifest uses one of: `drafting`, `validating`, `rejected`, `approved`, `executing`, `verifying`, `repairing`, `paused_resource`, `human_required`, `verified`, `failed`, or `abandoned`. `active_state` is the closed set `{drafting, validating, approved, executing, verifying, repairing}`; the only first-release `resumable_state` is `{paused_resource}`; `terminal_state` is `{rejected, human_required, verified, failed, abandoned}`. A paused manifest contains required `suspended_from`, constrained to `active_state`; nested suspension is illegal. `human_required` may retain `suspended_from` for diagnosis but cannot reload or resume.

- `rejected` is the immutable outcome of an assessment artifact with `safe: false`.
- `failed` means the current run cannot complete inside the assessed envelope after a non-resumable technical or policy failure; it does not imply that all future revised runs must fail.
- `paused_resource` is resumable and is not failure.
- `human_required` is a fail-closed, non-resumable first-release stop; resolving it requires a new assessed run.
- `verified` is the only successful terminal state.
- `abandoned` is an explicit human terminal decision.

### `L-002` Legal Transitions And Evidence

| From | To | Required evidence |
| --- | --- | --- |
| `drafting` | `validating` | Canonical plan payload and initial snapshot |
| `validating` | `rejected` | Valid assessment artifact with `safe: false` and findings |
| `validating` | `approved` | Deterministic and semantic pass, `safe: true`, hashes, capability/profile pass |
| `approved` | `executing` | Lease, current snapshot revalidation, identity and approval checks |
| `executing` | `verifying` | Operations stopped normally, event head, product-state observation |
| `executing` | `repairing` | In-envelope task/check failure and diagnostic record |
| `repairing` | `executing` | Revised in-envelope strategy and renewed operation preflight |
| `verifying` | `repairing` | Blocking verifier finding that is repairable inside the envelope |
| `verifying` | `verified` | Independent valid report, success criteria met, no blocking finding |
| any `active_state` | `paused_resource` | Host resource/cancellation evidence, safe stop point, preserved head, and `suspended_from` |
| any `active_state` | `human_required` | Scope drift, material uncertainty, policy/approval/concurrency issue and `suspended_from` |
| `active_state` except `drafting` | `failed` | Non-resumable in-envelope failure with evidence and recovery status |
| any live `active_state` or `paused_resource` | `abandoned` | Explicit close request while the coordinator is still available |
| `paused_resource` | exact `suspended_from` | Human resume event plus full lease, identity, policy, artifact, and snapshot revalidation |
| `paused_resource` | `human_required` | Resume revalidation finds material drift/conflict; preserve original `suspended_from` and evidence |

`rejected`, `human_required`, `verified`, `failed`, and `abandoned` are terminal for first-release execution-state transitions. Revision after `rejected` or `human_required` creates a linked new run while the prior run remains unchanged. Later authenticated human-decision append/resume behavior is outside the first release.

### `L-003` Unbounded Reversible Repair

`attempt_limit: "unbounded"` means no workflow-level numeric cap for reversible local repairs that remain inside the assessed envelope. Host time, context, model, tool, and cost limits still apply. Exhaustion moves to `paused_resource`; resume revalidates every artifact and relevant state. Progress events record attempted hypothesis, observed result, and next strategy without converting a host pause into final failure.

### `L-004` Diagnostic Checkpoints And High-Risk Replay

Repeated findings do not trigger an automatic stop merely because their text matches. They trigger a diagnostic checkpoint recording why prior action failed, which assumption is reconsidered, and whether the next strategy is materially different. The LLM may stop itself when genuinely blocked. Destructive, external, costly, privacy-sensitive, security-sensitive, or irreversible operations may not replay on this basis: each replay needs fresh idempotency proof and remaining one-use approval or a new approval. New scope, permissions, tools, paths, objectives, or effect classes always require reassessment.

## Resume Procedure

1. Validate event filenames, hashes, sequence, duplicates, and redaction status.
2. Re-establish the project lease under `R-003`.
3. Revalidate runtime/schema versions, policy hashes, plan/assessment identity, approval validity, repository snapshot, path identities, and applicable instructions.
4. Compare coordinator-observed product state with the last accepted event; preserve conflicts.
5. Resume only the legal prior state and next operation. Otherwise enter `human_required`.
