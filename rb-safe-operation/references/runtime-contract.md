# Runtime Contract

The `0.3.0` runtime turns a schema-3 constrained plan into exact coordinator actions and proposal-first bounded patch operations. A model can decide the text of a bounded change, but it can only return a strict standard unified diff. The Python coordinator derives the real file changes, assesses the exact proposal, records a durable apply intent, and alone writes the accepted bytes. The plan, assessment, proposal cycle, run, repair, report, verification, and recovery state are all bound to the fixed project-policy identity.

This contract supports static UTF-8 file-state work. It does not run tests, builds, linters, type checkers, applications, browsers, shell commands, arbitrary Python, network operations, subprocesses, MCP tools, or delegated agents. Every accepted criterion and verifier check must be `static_file_state::<description>`. The closed but unsupported modes `executable_test`, `runtime_observation`, and `external_observation` are rejected by deterministic preflight before semantic assessment or mutation.

## Installed Runtime

- Source: `runtime/`; distribution: `rb-safe-operation-runtime`; CLI module: `rb_safe_operation.cli`.
- Runtime version: `0.3.0`; public plan, assessment, run, report, and verification schemas: `3.0`.
- Python: 3.10 or newer. Locked core dependencies: `pydantic==2.13.4`, `pydantic-ai-slim[openai]==2.19.0`, `openai==2.45.0`, and `tiktoken==0.12.0`, plus their exact reviewed transitive dependencies.
- The committed lock is reviewed for the listed Python and platform wheels. A missing compatible wheelhouse is an unrun setup, not permission to download or weaken hash checking.
- Explicit setup only: `scripts/setup_runtime.py --control-root <absolute-control-root> --wheelhouse <approved-wheelhouse> --python <absolute-bootstrap-python>`.
- A successful setup stores its canonical manifest create-only at `<control-root>/manifests/<manifest-hash>.json` before atomically selecting the same bytes as `current.json`. Reusing an identical environment does not rewrite or duplicate the retained identity.
- Explicit rollback only: `<retained-bootstrap> -I -S -B scripts/rollback_runtime.py --control-root <absolute-control-root> --manifest-hash <retained-hash>`. The retained source checkout must still exist unchanged. The command validates the manifest hash, source, locks, launcher, bootstrap, installed interpreter, complete environment, and package before replacing `current.json`. Missing, corrupt, mismatched, or tampered rollback material leaves the current manifest unchanged. Setup and rollback do not delete project `.rb-safe-operation/` run records.
- Normal invocation reads only `launcher_bootstrap_interpreter_path` from `${CODEX_HOME:-~/.codex}/rb-safe-operation/current.json`, then runs `<bootstrap> -I -S -B <installed-skill>/scripts/run_runtime.py <command>`.
- `run_runtime.py` ignores legacy manifest redirection variables. It verifies the bootstrap, launcher, source tree, lock set, complete installed environment, package tree, dependency versions, and manifest before dispatch. It never installs, upgrades, searches sibling imports, or falls back to ambient Python.

Generated schemas contain `runtime_source_hash` as provenance. Drift comparison ignores only that provenance value; filenames, artifact versions, generator version, schema hashes, and complete schema content must match. The mirrors in `rb-create-low-level-plan`, `rb-assess-plan-safety`, `rb-safe-operation`, and `rb-create-safe-operation-policy` must be regenerated through the manifest-pinned launcher and remain byte-identical.

## Readiness And Run Preparation

Invoke `doctor` through the manifest-pinned launcher before compiling, assessing, or executing a constrained phase. The launcher proves the installed runtime, dependency, source, lock, and schema identities before the command starts. The doctor library then inspects the exact project root, fixed project-policy status and identities, control state, selected adapter, requested static verification modes, explicit grant paths, and the four installed schema mirrors. Calling the library directly does not provide the launcher's installation-identity proof.

Doctor is read-only. It does not install dependencies, repair files, remove leases, discover credential values, create grants, change profiles, or start or resume a run. Its result records the observation time, selected adapter and verification modes, and a hash of the complete strict request. It returns exactly one closed status:

- `ready_exact_static` means coordinator-owned exact static file operations are available without a model call.
- `ready_codex_cli` means the exact reviewed Codex executable, CLI revision, model, local ChatGPT login, static modes, schema mirrors, and supplied finite grants are available. The Codex process restrictions are not an operating-system sandbox.
- `ready_framework_proposal` means the explicitly selected PydanticAI proposal profile and supplied finite grants are currently available. Framework tool allocation is not an operating-system sandbox.
- `ready_instruction_only_compatibility` means the JSON-line compatibility profile was explicitly selected. Its role and context restrictions are instructions, so surrounding state checks detect some unauthorised effects after they occur rather than preventing them.
- `not_ready` means at least one named blocking diagnostic exists. The caller must stop; no fallback or repair is implied.

`prepare-run-authority` deterministically constructs a preview containing the adapter capability profile, provider grant, root resource grant, external credential handle, finite limits, expiry, data handling disclosures, permitted automatic-retry classes, and exact assurance limitations. It accepts credential availability only as an explicit operator-supplied fact and never reads or stores the credential value. Provider-call and aggregate model-request ceilings are separate required inputs and must agree.

The preview binds the project root device and inode, every prepared artifact, and the operator inputs into one SHA-256 confirmation binding. It prints an exact `CONFIRM RUN AUTHORITY <hash>` statement. `confirm-run-authority` accepts only that unchanged statement and preview, within the authority window and while the root identity and lease state remain unchanged. The confirmation is instruction-level evidence unless the invoking host authenticates the human principal.

Successful confirmation writes canonical artifacts create-only beneath `.rb-safe-operation/preparations/<preparation-id>/`. Files and newly created directory boundaries are fsynced. A duplicate identifier, stale or expired confirmation, changed root, lease, symbolic-link boundary, partial mismatch, or malformed artifact stops without overwriting an existing preparation. The preparation is a reusable authority envelope for every semantic role call and permitted format retry inside one unchanged run. It does not require a new human statement for each call. A different run, provider, model, plan, policy, target set, effect set, permission set, expiry, or budget requires a new preview and confirmation. Prepared authority is still not plan approval or execution permission; planning, plan assessment, execution-time proposal assessment, approvals, snapshot checks, and mutation-boundary policy enforcement remain separate gates.

## Public Schema Boundary

Schema-1 and schema-2 action-bearing plans, assessment bundles, paused runs, reports, and verification artifacts are historical evidence. The public runtime rejects them before assessment, preflight, execution, repair, resume, or standalone verification with `legacy_artifact_not_executable`. Use `inspect-legacy` for a redacted audit summary and canonical hash. Recompile the source phase as a new schema-3 plan, bind the current fixed project policy, reassess it, and start a new run. No command upgrades or resumes old state in place.

The frozen schema-1 implementation remains private only for regression tests and audit interpretation. It is not a supported library or CLI execution route.

## Fixed Project Policy

The only project policy location is `<project-root>/.rb-safe-operation-policy.json`. The runtime does not search parents or accept a command-line override for action-bearing work. Absence has a canonical hash, so “no policy file” is different from an unreadable, malformed, unobserved, or changed policy.

ProjectPolicy schema 2 may only narrow the installed global policy. Its path rules use canonical project-relative POSIX paths, stable rule IDs, exact or subtree scope, and independent `read`, `create`, `modify`, and `delete` denials. User-facing `write` means all three mutation capabilities. The deterministic merger also intersects allow-lists and network grants, lowers limits, unions denials and requirements, and raises minimum enforcement or observation. It never adds authority.

One path evaluator handles planning evidence, policy-pruned snapshots, instruction discovery, mediated reads, patch preparation, implicit parent creation, each product mutation, repair, verification, and resume. It rejects aliases or uncertain symlink, hard-link, device, mount, case, Unicode, and ancestor effects. A denied read is pruned before content hashing or descendant enumeration. Verification records denied state as `unobserved_policy_denied`; it never calls that state unchanged.

Every current action-bearing artifact carries one `PolicyBinding`: project root, fixed path, presence, global-policy hash, exact source-policy hash, and effective-policy hash. The coordinator reloads and compares this binding before observation and again at each mutation boundary. A changed policy invalidates the run; historical artifacts are not rewritten.

`rb-create-safe-operation-policy` owns the human-facing authoring workflow. `policy-explain` reads the fixed policy or absence identity. A tool-disabled Codex CLI translator, a no-tool PydanticAI compatibility translator, or an explicitly selected caller-mediated translator may return only a typed proposal. `policy-preview` recomputes the complete effective-authority change and classifies it as create, tightening, reason-only, relaxation, or mixed. `policy-confirm` binds the human statement to that exact proposal and preview. Relaxation and mixed changes need an additional explicit flag. `policy-apply` recomputes the preview, acquires the shared lease, rechecks the source identity, writes a durable intent, atomically replaces only the fixed policy, fsyncs and rereads it, then writes a committed or indeterminate record. Translator roles receive no persistence tool or protected file content.

## Provider And Resource Authority

Every schema-3 bounded plan binds the fixed project-policy identity and two explicit authority artifacts:

- `ProviderGrant` fixes the roles, adapter, provider, endpoint, model, separately reported model and host revisions, credential audience, request and response data classes, maximum source classification, retention and training disclosures, redirects, structured-output mode, expiry, and provider-level calls, bytes, tokens, time, cost, temperature, and seed. The Codex profile leaves model revision unset because the ChatGPT-backed interface does not expose a fixed model snapshot, while `host_revision` binds the reviewed CLI build.
- `RunResourceGrant` fixes finite aggregate proposer calls, non-proposer semantic-role calls, model requests, read-tool calls and bytes, patch bytes, request and response bytes, input and output tokens, elapsed time, and cost. `max_assessor_calls` is the aggregate ceiling shared by plan assessor, patch assessor, and verifier calls; it is not a separate allowance for each role. It also fixes the permitted automatic-retry classes and an integer or `unbounded` attempt limit. `unbounded` applies only to the number of eligible attempts; aggregate calls, tokens, bytes, elapsed time, and cost remain finite.

The runtime never discovers an ambient credential or provider and never silently changes adapters. `cost_accounting: observed` requires an adapter-owned cost observer. `declared_zero` is accepted only with a zero cost ceiling. `unavailable` is rejected.

Logical repair may remain unbounded, but the active resource grant is finite. A replacement grant is valid only for a durably `paused_resource` run, must name the immediately previous grant, have a non-decreasing issue time, carry authorization evidence, and become the end of the persisted grant chain. It does not reset earlier charges, approvals, reports, or effects.

## Role Adapters And Assurance

The provider-neutral `ProposalRoleHost` has separate typed methods for plan assessor, proposer, patch assessor, and verifier. None owns workflow state, durable control records, product mutation, or authoritative execution success.

- `pydantic_ai` uses an explicitly supplied model, strict typed output, zero framework retries, tool-mode structured output, and no ambient model construction. The proposer receives no function tool by default. When the plan permits it, the coordinator registers only a bounded `read_file` tool. Plan assessor, patch assessor, and verifier receive no function tools and use `framework_tool_enforced_no_tools`; the proposer uses `framework_tool_enforced_proposer`.
- `json_line` carries the same typed requests and responses for compatibility. It cannot mediate interactive reads, so the coordinator must supply an exact source bundle. Its capability profile is `instruction_only_proposal_host`. Product and control snapshots around the call can detect an unauthorised host mutation after it occurs; they do not prevent it.
- The reviewed routine live profile wraps `json_line` with the fixed Codex CLI transport. It accepts only the absolute bundled executable `/Applications/ChatGPT.app/Contents/Resources/codex`, CLI revision `0.146.0-alpha.3.1`, model `gpt-5.6-sol`, reasoning effort `low`, endpoint label `host-mediated://codex-cli/exec`, and an existing `Logged in using ChatGPT` status. It never reads an API key. Every call uses `codex exec --ephemeral` in a fresh temporary working directory with fresh SQLite and log directories, a read-only sandbox, strict role-specific output schema, and the reviewed disabled-capability list. It accepts reasoning lifecycle events but rejects every tool event, unsupported event, malformed or incomplete JSONL stream, missing usage, multiple final messages, or disagreement between the final message and result file. It still uses `instruction_only_proposal_host`: CLI configuration and observed events do not prove operating-system isolation or complete internal traces.
- The authenticated Codex service receives the complete canonical request, including deliberately selected source bytes and the absolute path names used for policy and identity bindings. The temporary working directory prevents ambient project discovery; it does not keep supplied request data on the local machine. The operator must confirm that both the source packet and path names fit the declared data classification and account policy.
- The older PydanticAI/OpenAI adapter remains implemented as a separately selected compatibility profile. It is not selected by the Codex commands and is not the reviewed routine-use profile.

The plan-assessment request contains the selected source hashes and metadata but deliberately omits their text. It assesses whether the fixed operation may proceed; it is not the later proposer packet. Immediately before proposer dispatch, the coordinator re-reads every selected source, verifies its content hash and metadata against the assessed snapshot, and includes the exact complete text in the fixed proposer packet. `allowed_read_tools` describes only optional additional proposer-side interactive reads. `path_contract.read_roots` has a second purpose: every deliberately selected source file that the coordinator places in a bounded proposal packet must be inside those roots and covered by a declared repository-read effect. The roots do not authorise or limit the coordinator's separated verifier packet. After application, the coordinator observes only the snapshot-selected files and `expected_product_changes`, evaluates every path against the active project policy, and supplies the permitted static contents and hashes to a no-tool verifier. A create-only JSON-line operation therefore needs read roots for its fixed selected source packet, but it does not need to add new product targets as read roots merely to verify their declared postimages.

Allocated-tool filtering and Codex process configuration prevent access through interfaces owned by this coordinator. They do not constrain an unrelated process, a compromised coordinator, the model service, or every possible operating-system access outside the observed interface. Audit records provide evidence, not enforcement. Complete child traces remain unavailable.

Each role call records the role, adapter, assurance profile, grant hash, provider identity, request and response hashes, requests, tool calls, tokens, bytes, elapsed time, and observed or declared-zero cost. A recovered complete role-call record is adopted into the replacement host before any further dispatch, so process or command boundaries do not reset calls, tokens, bytes, elapsed time, or cost. A failed call with incomplete usage is recorded honestly and blocks another call on the same host. A new authorised resource grant and host are required before further provider work.

## Planning And Assessment

Use `host-capabilities --adapter <pydantic_ai|json_line>` and pass the emitted profile unchanged. The Codex CLI profile uses `json_line`; its extra executable and process checks belong to the Codex transport and confirmed provider grant. A caller-authored capability profile is rejected.

The low-level plan must bind the provider and root resource-grant hashes. A bounded task declares:

- proposal protocol `unified_diff_v1`;
- goal and non-goals;
- exact read, create, modify, delete, protected, and working-directory roots;
- source-data classification;
- optional `read_file` tool;
- allowed patch actions and created-file mode;
- forbidden actions and closed permitted adaptations;
- required adapter, assurance profile, provider-grant ID, and root resource-grant ID;
- complete effects, approvals, evidence, static criteria, and finite per-attempt resources.

`assess-preflight` validates the exact plan, current schema-3 policy-pruned snapshot and metadata, fixed source/effective policy identities, capabilities, grants, approvals, evidence, effects, and verification modes. If a deterministic gate fails, it creates the immutable false assessment bundle without invoking a semantic plan assessor. After a passing preflight, `assess` recomputes it, constructs the complete typed plan-assessment request, invokes the caller-mediated JSON-line compatibility host, validates the response against every coordinator-owned binding, and creates the fixed assessment bundle. For the reviewed Codex profile, `codex-run` loads one unchanged confirmed preparation, validates it against the fixed plan and current time, constructs the fixed Codex transport, and validates the executable, version, and ChatGPT login before the workflow can record a first semantic-call intent. It then owns plan assessment, proposal, patch assessment, coordinator commit, and verification in one Python process, revalidating the same provider identity before every dispatch. It has no human-authored semantic proposal or copied hash envelope. The proposer output schema requires the diff string to begin with a supported unified-diff header. Once a complete typed proposer response returns, the coordinator persists it before deterministic patch parsing, so a later syntax or path rejection retains the exact attempted proposal. A recovered complete response is reused and charged to the continuing aggregate grant before later roles run. If the confirmed grant permits `proposal_format_error`, malformed unified-diff syntax may instead create a durable automatic-retry record and a fresh proposer request inside the same unchanged operation. An incomplete or uncertain Codex call is not replayed.

Plan `safe: true` authorises an attempt of that unchanged typed plan. For bounded work it approves only the proposal-generation envelope. It cannot approve diff bytes that did not exist during plan assessment.

## Proposal Cycle

For each bounded operation the coordinator performs this sequence:

1. Build a fresh `ProposalContext` bound to plan, assessment, operation, policy, snapshot, instructions, exact source inputs, mediated reads, grants, repair attempt, request token, prompt packet, and toolset.
2. Call the proposer. Strictly validate `AgentPatchProposal`; the model's paths, effects, evidence, and intent are claims, not authority.
3. Parse and materialise the complete diff in memory. Build the coordinator-owned `BoundedPatchProposal` with derived actions, exact preimages and postimages, hashes, metadata fingerprints, byte counts, and authoritative bindings.
4. Run `PatchProposalPreflight`. Validate the complete source context again, including material non-target reads. A deterministic failure enters `human_required` without commit.
5. Start a fresh no-tool patch assessor. Supply exact preimages, candidate postimages, complete material context, instructions, effects, and preflight. Strictly validate its result and let the coordinator construct `PatchAssessment`.
6. Only an exact `safe: true` patch assessment with complete coverage may reach commit. A semantic safety violation, uncontrolled detrimental effect, malformed binding, or uncertainty enters `human_required`; it is not retried until an acceptable answer appears.

Malformed unified-diff syntax is the one automatic-retry class in this release. It is eligible only when the unchanged confirmed run-resource grant explicitly lists `proposal_format_error`, its attempt limit has not been reached, the preceding proposer call completed with fully accounted usage, the rejected typed response is durable, and product plus protected-control state remains unchanged. The coordinator persists an `AutomaticRetryRecord`, checkpoints `automatic_retry_scheduled`, clears only the rejected current-proposal material, and sends a correction request with a fresh token. Reload from that checkpoint continues with the fresh request and never repeats the completed rejected token.

This retry rule does not include a path escape, target or scope expansion, binary, rename, copy or mode metadata, unsupported action, safety finding, stale snapshot, plan or policy drift, provider identity change, unexpected host side effect, incomplete or uncertain provider call, or ambiguous commit state. Those conditions use their existing fail-closed, pause, or human-intervention transition. A retry remains inside the same run, operation, plan, assessment, policy, provider, target and effect envelope, and every call remains charged to the same finite aggregate resource budget.

Raw prompts, reasoning, credentials, and unbounded model prose are not persisted. Before each semantic call, the coordinator durably records the canonical typed request token and packet. A validated response is recorded create-only before its lifecycle result is committed. Complete persisted responses are reused only where recovery can reproduce the exact transition; an incomplete or uncertain provider call is never repeated and enters `human_required`. A request rejected by the owned host before dispatch may instead enter `paused_resource` and resume under an exact replenishment grant. Proposal content is not written to stdout by default.

## Patch Preparation And Commit

Both exact `apply_patch` and bounded proposals use the same pure preparation and journalled commit code.

- Preparation accepts ordinary UTF-8 `---`, `+++`, and `@@` unified diffs. It rejects NUL bytes, binary patches, modes, symlinks, hard links, renames, copies, combined diffs, absolute paths, traversal, duplicate targets, malformed or overlapping hunks, unsupported metadata, and over-budget content.
- Preparation receives coordinator-captured preimage bytes and creates all candidate postimages in memory. It performs no product write and creates no product-directory temporary file.
- A modified or deleted target discovered through the bounded `read_file` tool must have one complete full-file observation. A partial range can inform a proposal but can never become a patch preimage.
- The runtime derives the create, modify, and delete inventories and checks separate path permissions, protected roots, effect coverage, claimed inventories, live bytes, metadata, and absence of create targets.
- For an authorised nested create, the coordinator creates only the missing parent components beneath the bound working directory. It rejects symlink or non-directory components, uses fixed mode `0755`, fsyncs each new component through its parent, and removes newly created empty components if parent preparation fails before a file is committed.
- On the supported macOS metadata profile, modifications preserve the accepted mode, ownership, ACL, extended attributes, flags, file type, link count, and device properties that can be observed and reproduced. Unsupported states fail before replacement. Creates use the assessed file mode, remove removable undeclared extended attributes, and reject unsafe inherited state. The one exception is an exact parent-matching `com.apple.provenance` value, which macOS automatically attaches and does not remove when requested; it is observed and accepted explicitly rather than mistaken for an empty metadata set.
- Before mutation, the coordinator revalidates lease, plan, policy, capabilities, grants, instructions, complete proposal context, approvals, assessment, snapshot, target identities, preimages, and metadata.
- It fsyncs an `ApplyIntent` containing the exact operation/proposal, approvals, ordered targets, and pre/post hashes before consuming approvals or mutating a file.
- Commit stages restrictive same-directory bytes, checks each target again, applies targets in recorded order, checkpoints the committed prefix, fsyncs supported file and directory boundaries, and removes or reports residue. It does not claim multi-file atomicity.
- A known crash state may continue forward only when every target is an exact recorded preimage or postimage and the committed targets form the journalled prefix. A fully applied proposal is recognised rather than applied again. Any unknown state enters non-resumable `human_required`.

The coordinator creates the authoritative schema-3 `ExecutionReport` from observed postimages and effect coverage. A proposer never creates this report.

## Approvals

Current approvals use schema 3 and bind the schema-3 plan, operation, fixed policy, snapshot, effect class, approval class, and target. They are checked during plan assessment and again at execution. Schema-1 approvals remain audit-readable only.

Bounded mutations that require consent use the same schema-3 approval with additional bindings to the accepted schema-2 `BoundedPatchProposal` and `PatchAssessment`. Exact and proposal-bound approvals are one-use, current, unconsumed, and uniquely matched. High-exposure, externally visible, irreversible, or external-write effects require an idempotency key. Approval consumption records are create-only and fsynced after the apply intent and immediately before commit. Recovery accepts an existing record only when its canonical content matches exactly.

The manual approval channel remains instruction-level consent unless a trusted host authenticates the principal. Ambient conversation, broad consent, duplicate IDs, expired or consumed records, unmatched effect classes, reused idempotency keys, and fabricated capability claims do not count.

## Durable Coordinator And Recovery

`ExecutionCoordinator` is the sole state-machine runner. Construction creates a new run; an existing run directory is not reused. It persists a strict canonical `CoordinatorBundleV2` and append-only audit chain. The bundle contains all authority, grant history, automatic-retry history, proposal-cycle history, current checkpoints, apply-intent history, reports, repair records, snapshots, verification, and human-intervention records required to reload or fail closed.

Legal bounded transitions are:

```text
executing -> proposing -> automatic_retry_scheduled -> proposing
          -> validating_proposal -> assessing_proposal
          -> proposal_approved -> applying_proposal -> executing|verifying
```

Side exits are `paused_resource`, `human_required`, `failed`, or `abandoned`. `human_required`, rejected, malformed, audit-divergent, and terminal runs cannot resume in place.

`ExecutionCoordinator.reload(...)` accepts only schema-3 state. It reloads the fixed project policy before trusting bundle authority, then validates canonical bytes, audit head, lifecycle, complete authority, host capability and provider identity, resource chain, automatic-retry history, repository and control state, proposal inputs, journal, known commit prefix, and repair history. It never invokes the proposer merely because an already persisted canonical proposal exists. A durable format-retry checkpoint may issue only the fresh request authorised by its retry record; it never replays the completed rejected request.

Repair uses immutable `RepairAttemptV2` authority plus separate `RepairOutcomeV2` progress records. A new repair proposal binds the verification finding and attempt hash, preserves a proven unaffected report prefix, and follows the complete proposal cycle again.

## Verification And Human Intervention

After all operations, the coordinator captures the product snapshot and opens a separate verification context. It constructs a strict `VerificationRoleRequest` containing the exact plan, assessment, policy, grants, committed proposals, patch assessments, reports, current file contents and hashes, applicable instructions, criteria, checks, effects, and snapshot binding. The verifier receives this packet without proposer reasoning or mutation tools. In the reviewed Codex profile, the model returns only the semantic decision: coverage, evidence, effects, and findings. The trusted transport derives the request token and immutable plan, assessment, post-execution snapshot, proposal-cycle, context, and policy bindings from the already validated request and materialises the complete `VerificationRoleResponse`. A caller never copies these identities.

The semantic verification decision must cover every exact criterion, check, effect, and typed evidence mapping. The materialised verification proposal must bind every proposal hash, patch-assessment hash, report hash, and other immutable request identity. The coordinator validates all bindings and emits `VerificationReportV2`. `verified` means the approved static file-state claims are covered with no blocking finding. It does not mean tests passed or runtime behaviour is correct.

Every safety, identity, control-state, malformed-evidence, or unknown-commit stop persists a typed `HumanInterventionV2` record. Human acknowledgement cannot relabel the same unsafe proposal. Revision requires a new run identity and full plan and patch reassessment.

## CLI Surface

Supported commands are `runtime-info`, `host-capabilities`, `doctor`, `prepare-run-authority`, `confirm-run-authority`, `policy-explain`, `policy-preview`, `policy-confirm`, `policy-apply`, `validate`, `canonicalize`, `hash`, `merge-policy`, `snapshot`, `inspect-legacy`, `select-phase`, `discover-instructions`, `assess-preflight`, `assess`, `codex-run`, `codex-resume`, `framework-run`, `framework-resume`, `acceptance-summary`, `persist-artifact`, `coordinate`, `coordinate-resume`, `render`, `export-schemas`, and `check-schema-drift`.

- `persist-artifact` creates only the fixed canonical low-level plan.
- `doctor` is read-only and reports one closed readiness status for one explicitly requested profile. Invoke it through the manifest-pinned launcher when installation identity matters.
- `prepare-run-authority` emits a non-secret preview only. `confirm-run-authority` requires the exact preview-bound statement before it creates the fixed preparation directory and canonical authority artifacts.
- `assess-preflight` and `assess` require `--provider-grant` and `--run-resource-grant` and create the fixed assessment bundle under `.rb-safe-operation/artifacts/<run-id>/`. `assess` owns the typed JSON-line plan-assessor exchange; there is no `--semantic-proposal` input.
- `codex-run` requires the fixed plan, fixed confirmed `run-preparation-preview.json`, a verifier context ID, exact reviewed Codex profile, and explicit `--enable-codex-cli`. It validates authority before checking the exact executable revision and local ChatGPT login. It does not accept or resolve an API key, alternate executable, ambient model, or provider fallback.
- `codex-resume` requires the same confirmed preparation, journalled project/run identity, resume evidence, verifier context ID, and Codex switch. Reload validates the durable coordinator bundle and adopts its complete role-call records into the host before another call. It cannot reset resource usage or replay an uncertain call.
- `framework-run` and `framework-resume` are separately selected PydanticAI/OpenAI compatibility commands. They are not implicit fallbacks for the reviewed Codex profile.
- `acceptance-summary` reads one fixed canonical coordinator bundle and emits the typed role sequence, assurance profiles, provider/model and grant identities, request/tool/token/byte/time/cost totals, terminal state, and static-only assurance limits. It never emits prompts, diffs, file contents, model responses, reasoning, or credential values.
- `coordinate` and `coordinate-resume` are stdout-only synchronous JSON-line compatibility drivers. They require the fixed handoffs, capabilities, provider and resource grants, and optional proposal-bound approvals. The driver invokes the same typed verifier host boundary; there is no separate manually assembled `verification_response` protocol.
- `inspect-legacy` emits a redacted metadata record and hash; it does not execute or migrate the input.
- `snapshot --schema-version 1.0` and read-only `render` exist only for historical audit support. Action-bearing commands require schema 3.

Both fixed handoffs are create-only, canonical, restrictive, directory-fsynced, and reject symlinked control roots. Coordinator commands do not accept output paths so a final report cannot become an undeclared product mutation.
