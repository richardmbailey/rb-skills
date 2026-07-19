---
name: "rb-safe-operation"
description: "Use when an exact constrained plan has safe true and needs execution and verification."
---

# RB Safe Operation

Execute only an unchanged approved bundle. This is a semi-formal control workflow, not a sandbox; disclose instruction-only role restrictions and incomplete child traces.

## Runtime And Preflight

1. Invoke the installed `scripts/run_runtime.py` only through the manifest-recorded absolute bootstrap interpreter using `-I -S -B`, as specified in `references/runtime-contract.md`. It selects only the canonical manifest-pinned environment and ignores legacy environment redirection. If setup is needed, stop and ask the human to run `scripts/setup_runtime.py` with an approved wheelhouse. Normal operation never installs.
2. Consume only the fixed create-only `.rb-safe-operation/artifacts/<run-id>/low-level-plan.json` and `assessment-bundle.json` handoffs. Revalidate runtime/schema/source/lock identities, plan/assessment/policy/snapshot hashes, approvals, current host capabilities, applicable instructions, and current repository state.
3. Acquire the one project mutation lease at `.rb-safe-operation/execution.lease`. Any existing live, stale, or indeterminate lease stops. The first release has no automatic stale-lease recovery API; a human must investigate and resolve the external control state outside this skill before a newly identified run can be assessed.
4. Reject any stale, changed, unsupported, false, expired, consumed, or insufficiently observed input. Never silently downgrade assurance or leave the approved envelope.

## Execute

1. Request a fresh executor context with only the approved operation, its dependencies, bounded evidence, and typed report schema. On the current host, context freshness is instruction-only rather than host-enforced.
2. The coordinator remains the sole control-plane writer. Agents propose typed events; validate and redact them before append-by-contract persistence.
3. Immediately before every mutation, repeat path containment, link/inode/device, preimage, instruction, lease, approval, and snapshot checks.
4. Dispatch only approved `read_file`, `apply_patch`, or a bounded task limited to `read` and `apply_patch`. `exec_argv`, `check`, subprocess contracts, command-capable bounded tools, and delegation are unavailable under the first-release global policy.
5. Keep executor reports, coordinator observations, and host observations separate. Conflicts block; agent claims never become a complete host trace.
6. Stop for concurrent user change, new path/tool/permission/objective/effect, material uncertainty, audit corruption, stale approval, or any change requiring reassessment. Preserve product state and evidence; never overwrite unexpected user work.

## Repair And Pause

- Reversible local repair may use `attempt_limit: "unbounded"` inside the unchanged envelope; finite `max_calls` is a per-attempt internal tool-call declaration and never becomes a cumulative retry cap. The coordinator enforces a finite `attempt_limit` when chosen and serialized protocol-byte ceilings. On the current host, per-attempt tool calls, model cost, child process count, wall-clock interruption, and product-file I/O metering are external or instruction-only; record this limitation. A host-signalled safe exhaustion becomes `paused_resource`, not failure.
- At repeated findings, record the attempted hypothesis, observed result, reconsidered assumption, and materially different next strategy. Do not add a fixed repeated-text stop rule.
- Destructive, external, costly, privacy-sensitive, security-sensitive, or irreversible replay requires fresh idempotency proof and remaining one-use approval or a new exact approval.
- Resume only after validating the event chain, reacquiring the lease, and revalidating runtime, policy, plan, assessment, approval, capability, instructions, paths, and snapshot. Relevant drift requires human review or reassessment.

## Separated Verification

1. After operations stop normally, capture coordinator-observed product state and enter `verifying`.
2. Request a fresh verifier context without executor reasoning. In `semi_formal`, freshness and read-only behavior are instruction-only and are recorded as such; the runtime does not assert host-proven independence.
3. Compare actual state, declared success criteria, verifier checks, expected effects, forbidden effects, evidence gaps, and audit/provenance conflicts against the exact approved bundle.
4. A repairable in-envelope finding may enter `repairing`; then use a separate repair executor and run fresh verification again.
5. Reach `verified` only when the coordinator-observed product snapshot and the separated agent-reported verifier evidence cover every criterion, with no blocking or undeclared material effect. Keep `independent_context: false` unless a future host can attest isolation.

## Records And Handoff

- Preserve canonical plan, policy, assessment, approvals, snapshot, manifest, event chain, product observations, repair attempts, verification, and the audit event that caused any `human_required` stop. The first-release runtime defines a human-intervention schema but does not persist or resume a post-stop human decision in place; revision uses a new run.
- Redact typed secrets before persistence and omit uncertain free text with a reason. Never change `.gitignore`, stage, commit, delete, or call local hashes tamper-proof automatically.
- End in `verified`, `rejected`, `human_required`, `failed`, or `abandoned`; stop before compiling the next phase.
- Emit a stdout handoff containing state, event head, current phase, all remaining phase IDs, artifact locations, exact next action, enforcement limitations, and any human decision required. After the terminal product snapshot, update the canonical external `${CODEX_HOME:-~/.codex}/diary/` continuity record from that handoff; it is control-plane state, not a product mutation. Do not create or change a project-local progress file unless it was an assessed product operation.

See `references/runtime-contract.md` for CLI/setup commands and supported guarantees.
