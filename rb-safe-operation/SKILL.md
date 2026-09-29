---
name: "rb-safe-operation"
description: "Use when checking constrained-runtime readiness, preparing explicit run authority, or executing an unchanged safe-true constrained plan with static verification."
---

# RB Safe Operation

Execute only an unchanged approved schema-3 bundle. A bounded language-model role may propose exact diff bytes, but it never applies them. The deterministic coordinator validates and assesses the proposal, records an apply intent, and alone writes the accepted bytes. Every observation and mutation is rechecked against the fixed project-policy identity. This remains a static-only, semi-formal control workflow rather than an operating-system sandbox.

## Executable Verification Limit

- The first-release global policy does not permit `exec_argv`, `check`, subprocesses, command-capable bounded tools, or delegation. Therefore this workflow cannot run unit tests, integration tests, builds, linters, formatters, type checkers, benchmarks, application commands, or CI-equivalent workflows.
- Every accepted success criterion and verifier check must be typed `static_file_state::<description>`.
- Reject any criterion or check that is untyped or uses `executable_test`, `runtime_observation`, or `external_observation`; deterministic preflight must fail before mutation.
- Do not use source inspection, hashes, generated plans, or agent-reported reasoning as a substitute for executable behavioural evidence.
- If any success criterion depends on executing code or observing runtime behaviour, stop before mutation as unsupported, or enter `human_required` if the limitation is discovered later. Return to the standard route or wait for a reviewed release with contained command capability.
- Reach `verified` only for criteria that are fully and truthfully observable through the supported static file-state operations. A documentation, configuration, schema, or exact text transformation may qualify; ordinary behavioural code changes generally do not.

## Operator workflow

1. Identify whether the request is readiness inspection, authority preparation, execution, or recovery. Read `references/runtime-contract.md` for the manifest-pinned invocation and exact command inputs. Readiness inspection alone does not authorise preparation or execution.
2. Invoke the installed `scripts/run_runtime.py` only through the manifest-recorded absolute bootstrap interpreter using `-I -S -B`. Normal operation never installs. Missing or mismatched setup stops; setup or installation rollback uses the explicit reviewed commands in the runtime contract.
3. Before acquiring the lease, invoke manifest-pinned `doctor` for the requested profile, fixed policy, four schema mirrors, verification modes, and explicitly supplied grants. Stop on `not_ready`. Do not repair, discover credentials, widen authority, or choose a fallback.
4. If the authorised task includes preparation and semantic calls need authority, use `prepare-run-authority`, show the exact preview, and persist authority only through its exact preview-bound confirmation. General permission to work does not replace this confirmation. One unchanged run reuses its confirmed authority within its finite aggregate limits.
5. For execution, consume only the fixed create-only `low-level-plan.json` and `assessment-bundle.json` handoffs, selected profile, exact grants, and approvals. Require unchanged schema-3 identities and static criteria. Existing live, stale, or indeterminate leases stop; never remove one automatically.
6. Use manifest-pinned `codex-run` with the unchanged confirmed preparation and explicit `--enable-codex-cli` for the reviewed Codex-native profile. Use separately selected compatibility commands only as specified in the runtime contract. Never substitute an ambient executable, model, login, API key, or adapter.
7. Let the coordinator own validation, proposal dispatch, assessment, mutation, journalling, and verification. Read `references/coordinator-protocol.md` when interpreting a proposal rejection, repair, pause, or recovery state. Do not perform those internal steps through ad hoc shell or Python commands.

## Execute Bounded Proposal Operations

The proposer returns `AgentPatchProposal`; it never writes product files. The coordinator derives candidate bytes, runs `PatchProposalPreflight`, obtains a fresh no-tool `PatchAssessment`, and applies only the exact approved bytes after a durable `ApplyIntent`. A passing plan assessment approves the proposal envelope, not a future diff. Never bypass exact patch assessment or create an application tool for the proposer.

The confirmed grant may permit `proposal_format_error` correction with a fresh request token. Every attempt consumes the same finite aggregate budget. Scope, identity, state, policy, safety, side-effect, and uncertain-call failures are not format retries.

## Separated Verification

Require coordinator-observed product state and fresh verifier evidence for every exact typed static criterion. A repairable in-envelope finding may enter `repairing` through the same assessment and verification path. `attempt_limit: "unbounded"` never removes finite per-attempt or aggregate resource limits. Do not claim runtime correctness or host-proven independence; preserve `instruction_only_proposal_host` and the actual separation disclosure.

## Pause and recovery

Use `codex-resume` only for the same journalled run and confirmed authority, with complete state and identity revalidation. Resource replenishment needs the grant-chain authority required by the runtime; it does not reset charged history. Never repeat a provider call whose durable request has an incomplete or uncertain outcome. Do not regenerate a complete valid proposal, overwrite concurrent user changes, or replay an uncertain commit. Report `human_required` when the coordinator cannot establish a supported recovery state. A rejected run requires a new identity and reassessment, not relabelling.

## Records And Handoff

- Preserve the canonical plan, policy, plan assessment, provider and resource-grant chain, host capabilities, create-only semantic request and response records, role-call usage, automatic-retry records, proposal contexts, runtime-mediated read records, agent proposals, bounded proposals, deterministic preflights, patch assessments, apply intents, approval-consumption records, coordinator reports, snapshots, manifest, event chain, repair attempts and outcomes, verification artifacts, and typed `HumanIntervention` record for every `human_required` stop. Never repeat a provider call whose durable request has an incomplete or uncertain outcome. A post-stop human decision does not relabel or resume the rejected proposal in place; revision uses a new run and full reassessment.
- For an authorised acceptance trial, run manifest-pinned `acceptance-summary` after the terminal handoff. Record only its typed identities and operational totals. Do not copy prompts, diffs, source contents, model responses, reasoning, or credential values into the acceptance report.
- Redact typed secrets before persistence and omit uncertain free text with a reason. Never change `.gitignore`, stage, commit, delete, or call local hashes tamper-proof automatically.
- End in `verified`, `rejected`, `human_required`, `failed`, or `abandoned`; stop before compiling the next phase.
- Emit a stdout handoff containing state, event head, current phase, all remaining phase IDs, artifact locations, exact next action, enforcement limitations, verification modes, executable-testing limitations, and any human decision required. After the terminal product snapshot, update the canonical external `${CODEX_HOME:-$HOME/.codex}/diary/` continuity record from that handoff; it is control-plane state, not a product mutation. Do not create or change a project-local progress file unless it was an assessed product operation.

See `references/runtime-contract.md` for CLI/setup commands and supported guarantees.
