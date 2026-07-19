# Phase 4: Execution, Verification, Repair, And Resume Hardening

## Phase Goal

Execute only unchanged approved bundles, reconcile actual observations, repair reversible local work inside the envelope, and resume only after complete revalidation.

## Scope

- Active read/patch adapters, bounded read/patch task coordination, path and snapshot revalidation, lease/conflicts, audit/recovery, lifecycle, verification, repair, pause, and resume. Command adapters remain typed but disabled.

## Non-scope

- New adapter kinds or strict-isolation claims.
- Real high-risk effects in tests.

## Task Checklist

- [v] Complete real and fake dispatch code for all four typed adapters, while the immutable first-release policy activates only `read_file` and `apply_patch`; prove `exec_argv` and `check` fail assessment until reviewed host-enforced capability containment exists, because executable and input hashes alone are not confinement.
- [v] Revalidate containment, links, identity, preimages, applicable instructions, lease, approvals, and snapshots immediately before mutation.
- [v] Complete project lease acquisition, heartbeat, release, concurrent-change handling, and fail-closed refusal of every existing lease; automatic stale-lease recovery is explicitly outside the first release.
- [v] Complete audit event write, hash chain, provenance separation, redaction-before-persistence, corruption/fork/partial recovery, and the structured event that enters non-resumable `human_required`; later authenticated human decisions remain outside the first release.
- [v] Enforce every legal lifecycle transition and reject every unlisted or unevidenced transition.
- [v] Reconcile executor reports with coordinator/host observations without claiming a complete trace.
- [v] Run a context-separated verifier that never repairs, record freshness as instruction-only, and combine its agent evidence with coordinator snapshot evidence as the only path to `verified`.
- [v] Implement reversible in-envelope repair with `attempt_limit: "unbounded"`, no cumulative retry cap from per-attempt `max_calls`, coordinator-enforced finite attempt limits and serialized protocol-byte ceilings, host-signalled resource pause, diagnostic checkpoints, and changed strategies. Record per-attempt internal tool-call, model-cost, child-process, interruptible wall-time, and product-I/O metering as unavailable/instruction-only on the current host.
- [v] Implement resource pause/resume with event-chain, lease, artifact, policy, approval, capability, and snapshot revalidation.
- [v] Require reassessment or fresh approval/idempotency evidence for scope drift and every high-risk replay.

## Verification Checklist

- [v] The implemented first-release `R-*`, `D-*`, and `L-*` subset passes against ledgers and disposable repositories; the validation matrix explicitly names deferred race-mode, exhaustive path-platform, fake-network/process-tree, schema-migration, and post-stop human-decision cases.
- [v] Link identity, concurrent edit, live/stale/indeterminate lease, corrupt audit, secret canary, and conflicting-report cases stop without overwriting product state; no exhaustive atomic-race harness is claimed.
- [v] Five reversible repair cycles and a resource pause can continue, while a high-risk retry cannot replay silently.
- [v] Resume after relevant drift never reuses stale assessment or approval.
- [v] Only complete agent-reported verifier evidence plus bound coordinator-observed snapshot evidence reaches `verified`; no host-proven independence is claimed.
- [v] Focused tests, broader tests, `git diff --check`, and phase review+fix succeed.

## Evidence

Record fake ledgers, event chains, recovery reports, lease/state traces, repair history, resume revalidation, and final verifier reports under `evidence/phase-4/`.

## Phase Exit Criteria

Reversible work can adapt naturally inside scope, high-risk effects cannot replay silently, stale state cannot resume, all tasks are `[v]`, and the phase review is clear.
