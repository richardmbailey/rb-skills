# Implementation plan: rb-build-test-suite

The implementation will let an agent build meaningful tests for a project,
run them through a repeatable command, and give the user a report that explains
both the results and the missing evidence. Work starts with a small complete
workflow. Later phases extend the tools, independent verification and operational
evidence without changing what counts as a pass.

Status: the user clarified that the current delivery is skill instructions and
references first. The executable plan is deferred. P0/P1 work and unqualified
P2/report prototypes are preserved under `development/rb-build-test-suite/`.
The active instruction edition does not complete this executable release plan.
The later [builder/auditor workflow](../test-suite-system/README.md) and its narrow
local coordinator are implemented separately; they do not complete the broader
runner, adapter or report-engine phases below.

**Execution Route: standard**

The top-level `rb-build-test-suite/` now contains the separately requested
instruction edition. Resume executable work with independent review of the P2
prototype and then P3; qualify preserved report work under P6. Do not infer
runner readiness from the instruction edition or copy unchecked prototypes
into target projects.

**Delivery workflow:** `$rb-execute-plan` owns phase order, task states and
verification. `$rb-implement-with-tests` owns ordinary implementation tasks;
`$rb-tdd-scientific-code` owns scientific fixtures and numerical evaluators.
`$rb-write-skill` owns skill packaging; `$rb-simplify-language` reviews the
completed instructions and references. `$rb-multi-agent-systems` governs the
verifier boundary. `$rb-create-skill-evals` governs agent behavioural trials.
Adaptive replanning through `$rb-sprint` requires a later request for that mode.

## 1. Requirements and current evidence

The [specification](README.md), [43-capability catalogue](capabilities.md),
[module interface](module-interface.md), [evidence/report contract](evidence-and-report.md)
and [draft skill](skill-draft.md) are the requirements baseline. This plan adds
implementation order and test obligations. It does not weaken those contracts.
If implementation exposes a contradiction, record it and resolve the affected
contract before coding around it.

The four draft schemas and their schema tests are design artifacts. The initial
validation covered nine tests; the review-resolution record documents subsequent
contract additions and checks. [Change assurance](assurance-contract.md) owns the
four review corrections and their F1a–F4c acceptance cases.
The [specification validation record](validation.md) describes their earlier
checks. They do not implement the runner, semantic validation, adapters,
independent verification or renderer. Existing repository routing tests also do
not demonstrate that this new skill works.

The working tree already contains the specification and its README link.
Preserve those changes. There is no project `CONTEXT.md` or existing top-level
implementation plan for this skill. The authoritative repository CI definition
is [validate-skills.yml](../../.github/workflows/validate-skills.yml).

### Goals, users and boundaries

The primary users are researchers and developers working through Codex or
Claude Code. They need substantive project-specific tests, consistent outputs,
repeatable execution and evidence they can inspect without running a web server.

The completed delivery includes all 43 catalogue entries, their applicable
construction workflows, a declared supported execution/import route for each,
the runner, independent-verifier integration, HTML reporting, both host editions
and demonstrated behaviour on healthy and deliberately defective projects.
Support for a human or operational practice means constructing its procedure
and validating real evidence. It does not mean automating human judgement or
providing a connector to every production platform.

Non-goals are fixing target applications without a request, implementing every
tool named in the catalogue, building a remote agent service, collecting real
user telemetry by default, operating production infrastructure, or guaranteeing
correctness against a developer who controls the local runner. Native Windows
and adaptive experiment selection remain later extensions. WSL is not claimed
supported until its own qualification runs pass.

### Planning assumptions and decisions

| Item | Planning basis | Resolution boundary |
| --- | --- | --- |
| Python-first, macOS/Linux, both agent hosts | Proposed defaults carried from the specification | P0 records exact supported versions and host capabilities before compatibility promises |
| Automatic suite-building selection; standard intensity | Proposed discovery/default behaviour | P0 records these as defaults for implementation; a later user change updates routing and evals |
| Independent verification for scientific-core acceptance | Required by the proposed acceptance design | P1 encodes missing evidence; P5 proves honest host handling |
| Implementation library choices | No dependency stack fixed by this plan | P0 selects and locks a maintained typed-model/schema stack after compatibility checks |
| Live targets, spend, thresholds and baselines | Project-specific; absent here | The future skill obtains missing decisions only for affected actions/claims |
| Routine suite adoption | Required project completion policy for generated changes | P2 saves integration; P8 tests all supported implementation routes |
| Protected external gate | Deployment only when requested; local policy is cooperative | P7.8 qualifies templates; P9.1 verifies deployment controls only within separate authority |

These assumptions make the plan concrete. They do not assert that a user has
approved operational access, spending or a baseline. Planning can finish without
those project-specific inputs. Later implementation authority should identify
any changes to these defaults; routine technical choices remain with the agent.

## 2. Task states and verification ownership

- `[ ]` planned
- `[x]` implemented
- `[v]` verified

Every task below begins as planned. A task becomes implemented after the plan
owner inspects the actual change. It becomes verified only when its stated
behavioural checks and required independent review pass. A phase completes when
all its tasks are verified and its exit criteria hold. If later edits invalidate
evidence, return affected tasks to implemented until those checks pass again.

Independent review is required for each phase below because the phase adds a
public contract, execution boundary, scientific oracle, cross-component behaviour
or release claim. One fresh reviewer can cover a coherent phase and return
task-specific findings; do not create a separate agent or repeat an unchanged
suite for every checkbox. The reviewer must not have implemented the reviewed
work. The plan owner owns integration and final completion judgement.

## 3. Architecture and repository placement

Use one local Python package behind thin entry scripts. The package has typed
models, structural and semantic validators, an adapter registry, a process
runner, evidence storage, policy evaluation and report generation. Keep these
boundaries separate in code and tests, without introducing network services.

Proposed source layout below refines the specification's script layout. It is
not a second constrained runtime and must not depend on `rb_safe_operation`.

```text
rb-build-test-suite/
  pyproject.toml, dependency lock
  SKILL.md, agents/openai.yaml              # Added at P8, when workflow is usable
  src/rb_test_suite/
    models/, validation/, adapters/, runner/, evidence/, reporting/
  scripts/
    inspect_project.py, scaffold.py, run_checks.py, build_report.py
    validate_release.py, export_schemas.py
  schemas/                                # Generated from this skill's models
  references/                             # Catalogue and focused instructions
  assets/                                 # Wrapper, config, CI and report assets
  tests/{unit,contract,integration,e2e,security,recovery,scientific,browser}/
  evals/{eval-plan.json,fixtures,validators}/
```

The generated project retains the specification's `.rb-tests/` and
`tests/rb_assurance/` layout. Its `.rb-tests/runner/` contains a versioned bundle
that works without the global skill installation. Target tool environments stay
separate from the runner's dependencies; configuring tests must not silently
upgrade the target project's packages. All schemas are generated locally and
resolved without network access. The existing draft schemas remain traceable
as the pre-implementation baseline.

The host agent selects tests and writes assertions. A bounded verifier designs
independent checks. The runner alone dispatches validated plans, records process
receipts, enforces available limits, evaluates policy and finalises records.
Agents return proposals and evidence. The HTML renderer only presents validated
records. Neither a host tool nor an editable receipt string grants authority.

Use the specified state pipeline with explicit transitions, a run writer lock,
atomic records and append-only events. Persistence supports interruption and
recovery; it does not require a distributed workflow engine. Start with direct
host delegation and local calls. No A2A transport, MCP registry or remote queue
is needed for the stated scope.

## 4. Testing architecture

Tests are designed before their implementation boundary. The table defines
what evidence is required; phase-specific checks add concrete scenarios.

| Boundary | Test level and oracle | Required failure cases |
| --- | --- | --- |
| Models and parsers | Unit/property/contract tests; typed values and published examples | Unknown fields, duplicate YAML/JSON keys, NaN/infinity, unsupported versions, invalid dates, oversized input |
| Cross-record evaluation | Table-driven unit/property tests with independent expected outcomes | Forged pass, absent criterion/artifact, wrong hashes, stale evidence, duplicate IDs, inconsistent counts, empty required suite |
| Files and scaffolding | Filesystem integration and migration tests; before/after hashes | Hand edits, existing wrapper, symlink/path escape, interrupted write, second invocation, partial upgrade |
| Processes and scheduling | Integration/recovery/concurrency tests using real disposable child processes | Timeout descendants, cancellation, output flood, concurrent writer, dependency failure, budget exhaustion, crash after effect |
| Adapters | Real pinned-tool contract fixtures plus malformed-output fixtures | Unsupported version, zero collection, nonzero exit, skipped/xfail requirement, mutation survivor, missing benchmark baseline |
| Scientific checks | Analytical/independent reference tests; reviewed numerical/statistical criteria | Wrong units/sign, non-conservation, incorrect convergence, variance error, data leakage, correlated reference |
| Agent delegation | Stubbed host contract tests and real bounded host trials | Unavailable host, shared write access, contaminated context, stale/wrong-candidate review, missing invocation receipt, budget stop |
| Operational imports | Signed/authenticated test receipts and isolated service integration | Wrong target, forged producer, expired authority, insufficient samples, missing telemetry, unconfirmed external effect |
| HTML and exports | Browser end-to-end tests plus exact evidence-to-view comparisons | Script payloads, unsafe links, wrong totals, missing artifacts, offline/no-JavaScript mode, render failure, narrow/print layouts |
| Whole skill | Held-out fresh-workspace behavioural evaluations | Wrong routing, weak assertions, overwritten work, false pass, needless approval request, unavailable-tool concealment |

### Fixture and oracle policy

Each fixture has a manifest naming its requirement, known-good behaviour, seeded
defect, independent expected result, environment, permitted effects and expected
gate. Healthy and defective variants are paired. Keep evaluator-only answers
outside the coding agent's workspace. Separate authored tests from held-out
evaluation cases; do not tune the skill against hidden answers.

Real subprocesses and real tool integrations are required at those boundaries.
Fakes remain useful for clocks, deterministic transition tables, budget counters
and host-denial paths. A fake tool that prints “passed” does not qualify an
adapter. Operational fixtures use disposable local services and synthetic data;
they do not contact users or production systems.

Scientific expected values originate from an analytical derivation, independently
written algorithm or justified dataset. For stochastic checks, fix the test
design, sample size, seeds and decision rule before trials. Preserve all failures;
do not retry until green. Coverage measures tested decisions and missing failure
paths. No universal line-coverage or mutation-score percentage is introduced.

## 5. Phases and milestones

| Phase | Deliverable | Depends on |
| --- | --- | --- |
| P0 | Baseline, compatibility decisions and independent acceptance fixtures | Specification |
| P1 | Typed contracts and semantic acceptance evaluator | P0 |
| P2 | Read-only discovery and scaffolding that preserves existing files | P1 |
| P3 | Minimal executable runner with evidence and diagnostic report | P1, P2 |
| P4 | Development adapters and scientific verification | P3 |
| P5 | Independent verifier integration and evidence validation | P1, P3; combined gate uses P4 |
| P6 | Complete standalone HTML report and core end-to-end workflow | P4, P5 |
| P7 | Full catalogue workflows and operational evidence | P3, P5, P6 |
| P8 | Skill instructions, host editions and behavioural evaluations | P0–P7 |
| P9 | Release qualification, installation and rollback evidence | P8 |

M1 at P3 is a runnable development skeleton, explicitly incomplete. M2 at P6
is the verified Python core with independent evidence and reporting. M3 at P9
is the complete declared skill release. Reaching M1 or M2 does not complete the
full implementation plan. There are no calendar or cost promises without measured
phase data. Update effort estimates from actual adapter and evaluation results.

P5's host-contract work can proceed alongside P4 after P3. P6's static renderer
can be developed against P1 fixtures while its final integration waits for P5.
Parallel work needs distinct write scopes and small review packets. These
permitted overlaps do not waive the dependency or exit gates in the table.

### P0 — Establish the implementation baseline

**Goal:** Make requirements, environments and independent acceptance evidence
concrete before implementation choices become difficult to change.

**Dependencies:** The specification package and current repository instructions.

**Tasks:**

- [v] P0.1 Record source revisions/digests, current worktree changes, supported scope and the proposed defaults in a baseline manifest; preserve the existing draft.
- [v] P0.2 Select and document exact runner Python/OS versions, model/schema library, safe YAML parser and isolated dependency tooling; prove compatibility in a disposable environment and lock dependencies.
- [v] P0.3 Identify documented Codex and Claude delegation/receipt mechanisms available for this workflow; record capabilities and missing controls without inventing a CLI or host API.
- [v] P0.4 Create a requirement-to-task/evidence manifest using the capability map below, including scientific subtypes and independent-review requirements.
- [v] P0.5 Have an independent verifier derive gate truth tables, known-good/defective fixtures and scientific oracles from the specification before seeing implementation code. Preserve this initial packet and its digest.
- [v] P0.6 Define a finite trial budget and evaluation rubric before agent trials; reserve held-out cases and separate structural checks from semantic judgement.

**Verification:** Dependency resolution/import checks establish environment
readiness only. Fixture evaluators must reject a deliberately bad artifact and
accept a known-good one. Independent review checks traceability, oracle origins,
test discrimination and the compatibility claims.

**Exit criteria:** Every required behaviour has an owning phase and an observable
acceptance case. Compatibility decisions are recorded. Missing production inputs
are assigned to future target-project invocation rather than blocking local work.

### P1 — Implement contracts and semantic acceptance

**Goal:** Ensure results cannot become accepted merely by fitting a JSON shape.

**Dependencies:** P0.

**Tasks:**

- [v] P1.1 Implement typed models for plans, receipts, results, imports, findings, independence, adoption, change impact, execution identity, static scope and reports; generate the four schema counterparts and preserve a compatibility diff against the drafts.
- [v] P1.2 Add the previously specified but not yet supplied configuration schema, catalogue schema, managed-file manifest, lifecycle-event and host-verifier packet schemas. Seed the canonical machine-readable catalogue with all 43 entries and mark routes unsupported until qualified. Record how these contracts compile into or reference the public contracts.
- [v] P1.3 Implement bounded JSON/YAML/XML parsing, duplicate-key rejection, finite-number rules, local schema resolution, UTC date validation and explicit unsupported-version errors.
- [v] P1.4 Implement referential and semantic validation: unique IDs, all 43 dispositions, requiredness, counts, digests, chronological order, criterion compatibility, target identity, evidence freshness and authenticated receipt bindings. Enforce change-impact path accounting and review, import/build identity, exact test IDs and static-scope limitations under the assurance contract.
- [v] P1.5 Implement criterion, module, capability and overall gate evaluation from independent truth tables; preserve failed assertions in partial runs and enforce the specified exit precedence. Missing adoption/impact review, unresolved material coverage and incomplete required checking prevent verified completion; preserve demonstrated failures.
- [v] P1.6 Implement immutable evaluation provenance and explicit version migration rejection/derivation rules; prevent report-only rendering from refreshing evidence or silently applying a new policy.
- [v] P1.7 Add schema-export drift checking and an independent cross-record evaluator test set that does not reuse the implementation's decision functions to calculate expected outcomes.

**Verification:** Unit/property/contract tests cover all state combinations and
predicate boundaries, including optional failures, required missing evidence,
non-applicable required entries, forged success, empty suites, wrong candidates,
invalid dates, duplicate references and identical measurements with wrong units.
Tests distinguish a structurally valid record from a semantically invalid one.
Independent review examines the decision tables and their correspondence to policy.

**Exit criteria:** A forged or incomplete required result cannot yield accepted
status; schema drift is absent; known-good records retain the correct outcomes.

### P2 — Inspect projects and scaffold without losing work

**Goal:** Produce a relocatable suite structure while preserving existing tests,
configuration, environments and user edits.

**Dependencies:** P1.

**Tasks:**

- [x] P2.1 Implement read-only project inspection and deterministic change inventories using structured parsers and diffs. Have the host/domain reviewer reconcile changed behaviour, affected interfaces, scientific effects and requirement/check mappings; record justified exclusions and unresolved coverage without keyword scoring.
- [x] P2.2 Define candidate snapshots over source, tests, config and relevant untracked inputs, with explicit exclusions and checks before/after execution; do not import project code during discovery.
- [x] P2.3 Implement first-run scaffolding from assets, selected directories, all 43 dispositions and the versioned bundle layout; retain the target project's environment manager. The executable runner is supplied and qualified in P3.
- [x] P2.4 Implement managed-file ownership and hash-based three-way update decisions. Preserve hand edits, detect an existing wrapper conflict and avoid duplicate test IDs.
- [x] P2.5 Implement atomic staging of generated changes, interruption recovery and explicit upgrades/rollback that restore only managed files whose current hashes still match the expected state.
- [x] P2.6 Implement `run_tests.sh` path resolution and bootstrap assets without shell interpolation. Test path forwarding against a harmless bootstrap fixture; reserve real runner and target-tool qualification for P3.
- [x] P2.7 Generate the project adoption record and integrate the saved runner and final-candidate completion rule into existing project instructions. Preserve hand edits and supported workflow boundaries; test missing/conflicting instructions and idempotent adoption. Routine implementation invokes the saved suite.

**Verification:** Filesystem integration tests compare original and final hashes
for handwritten content. Cases include repeated invocation, modified templates,
pre-existing scripts, symlinks, traversal, partial writes, read-only paths and
interrupted upgrades. Wrapper tests use the declared harmless bootstrap fixture,
which does not establish that the future runner works. Independent review
checks preservation, ownership, snapshot scope and rollback behaviour.

**Exit criteria:** Unchanged repeated construction is idempotent; conflicts are
visible; user-owned content survives; generated files have explicit ownership
and version metadata. Actual runner portability is a P3 exit requirement.

### P3 — Deliver the minimal executable workflow

**Goal:** Run one real bounded check and retain an honest result and report for
success, failure and interruption.

**Dependencies:** P1 and P2.

**Tasks:**

- [ ] P3.1 Implement and package the runner bootstrap, allow-listed adapter protocol and one minimal real pytest adapter; keep proposal creation separate from runner-owned execution receipts.
- [ ] P3.2 Implement the persisted state pipeline, writer lock, dependency scheduling, per-module/run limits, event ordering and atomic finalisation.
- [ ] P3.3 Implement subprocess argument arrays, controlled environments, process-group termination and the supported host isolation checks; block requested protections that the host cannot enforce.
- [ ] P3.4 Implement permission/target checks before dispatch, scoped receipt lookup and finite retry rules; reject profile-based or editable-config claims of authority.
- [ ] P3.5 Implement all specified CLI modes and exits, including filtering without weakening acceptance, unknown-option rejection and read-only `--list`/`--report-only` behaviour. Validate final-candidate completion identity and all required selections; exercise F1b without treating report-only rendering as a fresh run.
- [ ] P3.6 Implement a minimal escaped static report containing identity, gate, check results, limitations and raw-artifact links; ensure failed checks still produce it and rendering failure preserves evidence.
- [ ] P3.7 Implement cancellation, crash recovery and reconciliation of uncertain external effects. Prevent automatic duplicate dispatch after an ambiguous completion.

**Verification:** A disposable fixture is scaffolded and run end to end with
real pytest through the actual bundled runner and wrapper, including invocation
from another directory and relocation to a path containing spaces. Its healthy
case exits 0 only when its recorded required scope is
satisfied; a failing assertion exits 1; missing required evidence exits 2;
invalid config or report failure exits 3; cancellation exits 130. Process tests
exercise descendants, floods, locks, budgets and failures between effect and
receipt. The static report labels absent independent verification explicitly.
Independent review targets authority, isolation claims, recovery and exit handling.

**Exit criteria:** M1 works through the actual wrapper and retains failures.
No test output can supply authority or overwrite the runner's outcome. This is
an incomplete development skeleton, not a qualified skill release.

### P4 — Add development tools and scientific evidence

**Goal:** Produce useful development tests with real tools and independently
justified numerical expectations.

**Dependencies:** P3.

**Tasks:**

- [ ] P4.1 Expand pytest collection/result handling for unit, functional, component, contract, acceptance, regression, smoke and integration checks. Draft an uninstalled agent construction procedure that derives assertions from project requirements and links the implemented scripts; retain it for P6 trials and P8 packaging.
- [ ] P4.2 Add Hypothesis-backed property/stateful checks and scientific subtypes: dimensional checks, conservation, analytical/limiting cases, convergence, metamorphic and differential comparisons.
- [ ] P4.3 Add pinned Ruff, one selected type-checker and coverage adapters with structured output and qualified output versions on both OS routes. Capture effective nested configuration, actual file scope, exclusions, untyped/Any/import limitations and suppressions. Disable Ruff fixes/fix-only and masked exits; verify unchanged source. Add separate formatting check when required. Exercise F4a–F4c, including compatible gradual-typing controls.
- [ ] P4.4 Add bounded mutation and benchmark adapters. Run mutations in disposable copies; retain survivor classes, raw samples, baseline identity, environment and uncertainty.
- [ ] P4.5 Implement validated reference/baseline metadata and explicit proposal-to-acceptance handling; prevent failed tests from regenerating their own expected answers.
- [ ] P4.6 Build paired scientific fixture projects for wrong units/sign, non-conservation, wrong convergence, stochastic variance and data leakage; include load–compute–save–reload checks of actual output files. Include F2a: an existing passing suite followed by a new exported kg-to-tonnes conversion with a seeded defect; reconcile impact before accepting the changed behaviour.
- [ ] P4.7 Add unsupported-tool/version handling, zero/partial collection detection, skip/xfail semantics, nonzero-exit reconciliation and corrupted-output contract cases for each adapter. Freeze exact required test IDs and reject same-count substitutions while preserving custom discovery.
- [ ] P4.8 Implement in-process import-origin/build-manifest evidence and qualify checkout, editable, built-distribution and script modes. Test stale installed code, checkout shadowing and missing package data using clean artifact installation and a representative delivered workflow. Pair each defective fixture with healthy controls; do not require packaging for scripts.

**Verification:** Real adapter tests exercise healthy and defective fixtures.
Independent scientific checks detect the seeded faults while accepting the healthy
controls under predeclared tolerances/statistical rules. Mutation survivors and
incomparable benchmarks remain visible. An independent reviewer checks oracle
origins, test discrimination and whether parser/exit combinations can conceal failure.

**Exit criteria:** All P4 routes in the capability map have executed evidence.
Developer assertions alone do not determine expected scientific results. Changed
requirements and references require attributable decisions, not automatic repair.

### P5 — Integrate independent verification

**Goal:** Make independent checking observable and preserve its limitations.

**Dependencies:** P1 and P3 for host contracts; P4 for combined scientific trials.

**Tasks:**

- [ ] P5.1 Implement host-neutral specification/test/review packets with explicit versions, candidate and policy digests, budget, tools, permitted files and allowed output types.
- [ ] P5.2 Implement the verified Codex and Claude host handoff paths from P0, including separate initial test design and later code review; preserve the initial packet and tests before exposure to developer explanations.
- [ ] P5.3 Capture actual session, context, write-isolation and oracle provenance separately; record model/tool usage where available without claiming that a different model proves independence.
- [ ] P5.4 Validate reviewer identity, host invocation receipts, findings, test artifacts and candidate bindings. Reject forged, stale, malformed, conflicting or unsupported attestations, including unreviewed change-impact exclusions and unresolved scientific claims in F2c.
- [ ] P5.5 Integrate verifier-authored tests with runner execution and the required gate; retain advisory recommendations separately from deterministic outcomes.
- [ ] P5.6 Implement unavailable delegation, budget exhaustion, cancellation and partial-verification paths. Shell reruns execute deterministic tests without silently starting paid agent calls or reusing stale reviews.
- [ ] P5.7 Demonstrate a wrong implementation that passes developer tests but fails an independently derived check; demonstrate that a shared-file environment is reported as shared rather than isolated.

**Verification:** Stubbed host contracts test deterministic failures and denial;
real bounded trials on each claimed host establish actual invocation and receipt
behaviour. A fresh reviewer checks packets, access limits and raw evidence.
Scientific reference checks remain independently justified even when both agents
use the same model family. Missing host capability produces a blocked result.

**Exit criteria:** Independent verification can be traced from its initial packet
to executable evidence and the candidate. If one host cannot be qualified, its
release claim remains unverified; neither fabricated receipts nor self-review
can satisfy the gate.

### P6 — Complete the standalone HTML report

**Goal:** Make all conclusions and limitations inspectable from a local report.

**Dependencies:** P4 and P5; P1 records can support earlier isolated UI work.

**Tasks:**

- [ ] P6.1 Implement the deterministic report-model projection with embedded criterion definitions, deduplicated counts, all 43 rows, independent-verification details and exact provenance links. Embed adoption/impact mappings, execution/test identities and effective static scope; test that excluded and unchecked code cannot appear fully verified.
- [ ] P6.2 Implement self-contained CSS/data and progressive JavaScript for search, sorting, filters and expandable detail; preserve readable core content without JavaScript and without network fetches.
- [ ] P6.3 Add numerical, convergence and performance plots with exact data tables, units, reference/tolerance explanations, uncertainty and missing-data handling.
- [ ] P6.4 Enforce escaping, JSON embedding safety, safe URLs and artifact path containment; render malicious tool/agent text as inert text and prevent report-triggered actions.
- [ ] P6.5 Add atomic run/latest reports, diagnostic invalid-record views, print/narrow layouts and portable bundle export with clear raw-artifact access limitations.
- [ ] P6.6 Use the provisional construction procedure in bounded real host trials on fresh healthy/defective projects with no supplied developer tests. Verify requirement-derived test construction through developer/verifier execution, gate, report, rerun and report-only reconstruction against evaluator-only oracles.

**Verification:** Browser tests open actual generated files offline, check filters,
keyboard access, no-JavaScript content, narrow/print views and hostile payloads.
Independent assertions compare every summary and plotted value with the evidence.
Corrupt/missing artifacts and render failure cannot replace valid evidence with
an apparent pass. The early host trials must produce substantive assertions,
detect the seeded defect and accept the healthy control within the P0 budget.
They establish the core workflow, not comparative skill benefit or reliable
performance across hosts; P8/P9 own those broader claims. Independent review
includes generated tests, visual inspection and source-to-view checks.

**Exit criteria:** M2 delivers a functioning Python core with independent evidence
and a useful local report. Reports remain truthful on failed, partial and cancelled
runs. Passing report tests does not establish the remaining operational capabilities.

### P7 — Complete all capability workflows and operational evidence

**Goal:** Give every catalogue entry a usable, tested route without pretending
that operational practices are ordinary local unit tests.

**Dependencies:** P3, P5 and P6.

**Tasks:**

- [ ] P7.1 Extend the canonical catalogue seeded in P1 with qualified operational routes and complete construction recipes, support declarations and cross-cutting scientific/reference mappings; preserve the exact IDs below.
- [ ] P7.2 Add bounded fuzz, local UI/accessibility, configuration and profiling routes using one selected tool per promised adapter; preserve permission/platform limitations and actual runtime evidence.
- [ ] P7.3 Add local service fixtures and executable routes for load, soak, performance, replay comparison, shadowing, teeing, traffic/flag controls and fault injection; test forbidden secondary effects and cleanup.
- [ ] P7.4 Implement common observation, procedure and human-review imports with capability-specific payload validation for release/operational monitoring, exceptions, logs, tracing, audits and real-user observations.
- [ ] P7.5 Add construction and import workflows for formal verification, usability, penetration testing, threat models, canaries, A/B experiments, dynamic exploration and on-call evidence; require the declared proof/review/observation, not merely generated plans.
- [ ] P7.6 Validate actual producer authentication, target/configuration binding, observation window, sample count, authority expiry and accepted stop/recovery conditions at operational boundaries. Keep synthetic fixtures labelled as such.
- [ ] P7.7 Add complete report cases for each capability and negative cases for insufficient or forged evidence; ensure absent live systems stay blocked/deferred without preventing unrelated checks.
- [ ] P7.8 Qualify optional protected-CI templates with a final aggregator that rejects missing/skipped/neutral/cancelled/failed/insufficient required results and wrong candidate/producer identity. Test unauthorized policy/workflow weakening against the trusted version. Record protection/bypass inspection requirements; fixture success does not establish deployed enforcement.

**Verification:** Each of the 43 entries has at least one known-good and one
meaningfully bad execution/import fixture. Local operational integration tests
exercise actual behaviour in disposable services. Human/production evidence
fixtures validate handling and rejection only; they do not establish real-world
usability, production health or security. Independent review checks coverage,
side-effect limits, observation sufficiency and the honesty of support claims.

**Exit criteria:** Every entry has construction guidance, declared support,
validated evidence and explicit unavailable paths. Platform-specific production
connectors outside the selected adapter list remain visibly unsupported.

### P8 — Package the skill and evaluate agent behaviour

**Goal:** Make the workflow discoverable on both hosts and prove that following
it produces substantive suites and accurate reports.

**Dependencies:** P0–P7.

**Tasks:**

- [ ] P8.1 Write the concise active `SKILL.md`, focused references and `agents/openai.yaml` using `$rb-write-skill`; link every resource and retain the specified selection boundaries.
- [ ] P8.2 Apply `$rb-simplify-language` to the complete skill and agent-facing references; check actors, conditions, authority, outputs, failure paths and unchanged scientific meaning.
- [ ] P8.3 Update README routing, positive/negative routing cases, instruction and consistency contracts, Claude profile inclusion and host-specific generation rules; preserve current skills and counts derived from the profile.
- [ ] P8.4 Create the behavioural eval manifest, fixtures and deterministic/semantic evaluators with `$rb-create-skill-evals`; verify evaluator discrimination against good and bad outputs before trials.
- [ ] P8.5 Run matched with-skill/without-skill trials in fresh workspaces for the actual deployment hosts/models. Use at least three trials for important nondeterministic cases, with the reliability-critical cases and larger trial count fixed in P0.
- [ ] P8.6 Evaluate completed outcomes: seeded-fault detection, false passes/alarms, preservation, selection, unnecessary questions, independent evidence and report accuracy. Record elapsed time and cost where measurable.
- [ ] P8.7 Correct demonstrated skill defects and rerun affected cases without removing failures; retain a separate held-out set for release qualification and report uncertainty about marginal benefit.
- [ ] P8.8 Integrate the adoption rule into ordinary/scientific implementation and plan/completion skill guidance, metadata and affected contracts/evals without changing suite-construction routing. Run F1a/F1b and F2a/F2b through each supported route and direct project-instruction completion: adopt once, make later changes, and inspect actual runner evidence. Missing runs, later edits and uncovered behaviour cannot produce a verified claim; healthy and adequately covered changes can.

**Verification:** Routing tests include creation, extension and scientific requests,
plus adjacent “run tests”, diagnosis, feature work, diff review and skill-eval
requests. Outcome trials require real generated files and execution evidence.
Cases include missing focus, already-authorised actions, unavailable tools,
malicious repository text, protected references and constrained-only environments.
Independent review examines both behaviour and whether the evaluation gives the
skill unfair access to answers or different conditions from the baseline.

**Exit criteria:** Required outcome and prohibited-action criteria meet the
predeclared rubric. Manifest validation alone cannot close this phase. Missing
host trials remain explicit gaps. Utility claims describe measured differences
and uncertainty; a successful with-skill run alone is insufficient.

### P9 — Qualify, install and verify rollback

**Goal:** Deliver only the host/platform/tool combinations supported by observed
evidence, with reproducible installation and recovery.

**Dependencies:** P8 and all earlier phase gates.

**Tasks:**

- [ ] P9.1 Complete the release validator and CI wiring described below, including explicit failure when an adapter/browser gate is unavailable; archive evidence even on failure. For separately authorized protected deployment, verify required job source, candidate, workflow protection and bypass settings; otherwise retain cooperative/requested status and do not claim external enforcement.
- [ ] P9.2 Run the declared Python/OS/tool matrix, held-out end-to-end fixtures and agent trials; verify a copied target project works without a global skill installation or network access for reporting.
- [ ] P9.3 Obtain an independent final review of the combined diff, requirement/evidence map, public contracts, unresolved findings and support claims; repair blocking findings and rerun only affected checks.
- [ ] P9.4 Prepare a release record with source/test/environment identities, limits, omitted checks and actual compatibility. Check for credentials, confidential fixtures, local paths and unwanted control-state artifacts.
- [ ] P9.5 Run the repository sync dry-run separately for Codex and Claude, inspect conflicts, then install within the execution request's authority using the established sync workflow; preserve existing installations and backups.
- [ ] P9.6 Verify installed discovery and an actual small suite-building task on each claimed host. Exercise generated-project upgrade and rollback in a disposable fixture and verify retained evidence remains readable.
- [ ] P9.7 Record verified task states and handoff evidence in the plan and working diary; report remaining optional limitations and exact installed versions. Commit, push or publish only when requested.

**Verification:** The release validator, repository CI and required independent
review have candidate-bound receipts. Sync destination/profile checks and live
host invocation establish installation; copying files is insufficient. Rollback
restores managed files without overwriting intervening edits or erasing failures.

**Exit criteria:** M3 meets the declared complete scope. Every required task is
verified, every required test/review has evidence, all 43 routes are accounted
for and installation matches the stated host support. If a required gate cannot
run, retain implemented status and report the specific limitation; any exception
needs explicit acceptance under the execution workflow.

## Review-correction verification

The [assurance acceptance matrix](assurance-contract.md#6-required-discriminating-acceptance-cases)
is a required extension of each named phase gate. P1/P2 test inventory and gate
boundaries, including F2b/F2c; P4 uses real tools and packages; P7 tests CI
aggregation; P8 uses fresh multi-turn agent trials; P9 checks the combined
evidence. A phase reviewer must inspect both the defective result and healthy
control. Schema fixtures alone cannot close any runtime or agent acceptance case.
The plan contains 71 tasks across ten phases. Current task markers distinguish
implementation and verified evidence; review-correction documents describe the
earlier design-only checkpoint.

## 6. Capability-to-delivery map

This table assigns implementation ownership for every catalogue ID. P1 models
and P6 reporting cover all rows. `E` means a selected executable route; `I`
means validated evidence import; `H` means a human/operational procedure whose
outcome needs external evidence; `A` means the independent-agent workflow.
These are plan shorthand, not new runtime enums. Detailed evidence/acceptance
rules remain in [the catalogue](capabilities.md).

| # | ID | Delivery phase | Required route and representative proof |
| --- | --- | --- | --- |
| 1 | `unit` | P3/P4 | E: known calculation and invalid input |
| 2 | `functional` | P4 | E: feature result and forbidden side effect |
| 3 | `component` | P4 | E: real subsystem with controlled dependency failure |
| 4 | `fuzz` | P7 | E: bounded campaign and saved reproducer |
| 5 | `property_based` | P4 | E: generated invariant plus shrinking/replay |
| 6 | `formal_verification` | P7 | H/I: model/proof output, assumptions and implementation correspondence |
| 7 | `static_analysis` | P4 | E: real diagnostic and malformed-output rejection |
| 8 | `mutation` | P4 | E: killed/surviving/equivalent-reviewed/timeout distinction |
| 9 | `coverage` | P4 | E: branch/requirement gaps, no assertion-quality inference |
| 10 | `benchmark` | P4 | E: repeated samples, comparable baseline and absent-baseline handling |
| 11 | `contract` | P4 | E: behavioural interface mismatch beyond schema validity |
| 12 | `lint` | P4 | E: repository rules, no automatic source rewrite |
| 13 | `acceptance` | P4/P7 | E/H/I: requirement scenario and required stakeholder attestation |
| 14 | `regression` | P4 | E: trusted reference and failing-before/fixed-after evidence |
| 15 | `smoke` | P3/P4 | E: essential path with limited acceptance claim |
| 16 | `usability` | P7 | H/I: participant/task observations, never a fabricated session |
| 17 | `ui_ux` | P7 | E/H/I: real interactions/rendering plus human-only limitations |
| 18 | `penetration` | P7 | H/I: scoped test evidence, missing authority blocks active work |
| 19 | `threat_modelling` | P7 | H/I: reviewed threats and linked verified controls |
| 20 | `performance` | P4/P7 | E: resource/latency limits and correct outputs |
| 21 | `integration` | P4 | E: real load–compute–save–reload workflow |
| 22 | `tap_compare` | P7 | E/I: correlated pairs, mismatches and missing-pair rejection |
| 23 | `load` | P7 | E: bounded offered/achieved demand and recovery |
| 24 | `shadowing` | P7 | E/I: realistic replay with secondary side effects suppressed |
| 25 | `configuration` | P7 | E: valid/invalid settings produce specified behaviour |
| 26 | `soak` | P7 | E/I: bounded duration/resource trends, shorter-run limitation |
| 27 | `canary` | P7 | H/I: cohort, exposure, guardrails and real release decision evidence |
| 28 | `release_monitoring` | P7 | I: release-bound observation window and sufficient samples |
| 29 | `traffic_shaping` | P7 | E/I: observed routing/backpressure, not weights alone |
| 30 | `feature_flags` | P7 | E/I: targeting, transition and unavailable-provider behaviour |
| 31 | `exception_tracking` | P7 | E/I: synthetic exception ingestion and redaction receipt |
| 32 | `teeing` | P7 | E/I: copy delivery, loss policy and primary-path isolation |
| 33 | `profiling` | P7 | E/I: workload/profile relationship and attachment denial |
| 34 | `logs_events` | P7 | E/I: emitted records, sink failure and protected content |
| 35 | `chaos` | P7 | E/H/I: local fault, abort and recovery; live action separately scoped |
| 36 | `operational_monitoring` | P7 | I: continuing health window and missing-telemetry failure |
| 37 | `ab_experiment` | P7 | H/I: predeclared design, allocation checks and inconclusive result |
| 38 | `tracing` | P7 | E/I: actual propagation across asynchronous/retry boundaries |
| 39 | `dynamic_exploration` | P7 | H/I: bounded charter, recorded actions and reproducible discovery |
| 40 | `real_user_monitoring` | P7 | H/I: actual consented aggregate evidence and sampling gaps |
| 41 | `auditing` | P7 | E/H/I: attributable records, tamper/missing-record rejection |
| 42 | `on_call_experience` | P7 | H/I: real responder/drill evidence; agent walkthrough insufficient |
| 43 | `independent_verification` | P5/P8 | A/E/I: separate test design, receipt, oracle and adverse finding |

Scientific validation, differential/reference tests, convergence, stochastic
checks and ML leakage are subtypes across these entries, especially 1, 5, 13,
14, 20, 21 and 43. They remain mandatory when the project's claims need them;
the fixed catalogue length does not exclude them.

## 7. Independent verification protocol

There are two distinct uses of independent verification. During implementation,
a reviewer checks this skill's code, scientific fixtures and test results.
During use of the finished skill, a verifier checks a target project's claims.
Evidence from the first does not substitute for the second.

Before a phase starts, the plan owner supplies requirements, expected behaviour,
fixture provenance, allowed files/tools, finite budget and known limitations.
For P0, P1, P4 and P5, the reviewer first derives checks without implementation
explanations where feasible. Later review receives the actual diff, test commands,
raw results and candidate identity. A reviewer may reproduce tests and propose
counterexamples but may not silently edit the implementation or weaken criteria.

Each review record identifies phase/task IDs, reviewer/session, candidate and
requirement digests, evidence inspected or rerun, findings, unresolved uncertainty
and a verdict of `PASS`, `CHANGES_REQUIRED` or `UNVERIFIABLE`. The plan owner
checks the artifacts behind the verdict. Implementer and reviewer disagreement
is resolved using evidence or an explicitly recorded requirements decision.
An unavailable reviewer leaves affected tasks implemented, not verified.

Review is bounded: one initial phase review, then focused review of material
repairs. Current passing evidence is reused while its source, fixtures, config
and environment remain valid. A final combined review at P9 checks newly exposed
interactions and support claims; it need not re-audit unchanged functions.
Model choice follows the repository's delegation policy and actual availability;
no new model service, paid budget or extra agent hierarchy is implied.

## 8. CI-equivalent validation and release evidence

Existing repository checks remain authoritative. P0 adds a new test environment;
P3 introduces `scripts/validate_release.py` with core coverage, and P9 completes
it. The following is the planned interface, not a command available today:

```bash
python rb-build-test-suite/scripts/validate_release.py --profile core
python rb-build-test-suite/scripts/validate_release.py --profile full
```

`core` runs models, semantic gate, scaffold, runner and installed core adapter
tests. `full` additionally requires all promised adapters, security/recovery,
scientific fixtures, browser/offline report tests, end-to-end and schema-drift
checks. It fails visibly for missing required dependencies or tests. Test groups
continue to collect diagnostics after failures, but the final exit remains
nonzero. Agent trials are separately budgeted and recorded; the release validator
validates their candidate-bound receipts rather than silently starting paid calls.

Each release evidence entry records the requirement/phase, candidate digest,
test/fixture versions, environment, command, raw artifact path/hash, outcome,
omitted checks and reviewer result. CI jobs are required for each declared OS/
Python combination from P0. Extend `.github/workflows/validate-skills.yml` so its
schema, test and final-outcome checks include this skill and archive evidence on
failure. Keep existing constrained-runtime jobs unchanged.

Canonical existing repository subset, from the root in its supported environment:

```bash
python3 evals/skill-routing/validate_instruction_contracts.py evals/skill-routing/instruction-contracts.json
python3 evals/skill-routing/validate_consistency_contracts.py evals/skill-routing/consistency-contracts.json
python3 evals/skill-routing/validate_publication_hygiene.py
ruby evals/skill-routing/validate_skill_metadata.rb
python3 -m unittest discover -s evals/skill-routing/tests -p 'test_*.py'
for manifest in rb-*/evals/eval-plan.json platforms/claude/skills/*/evals/eval-plan.json; do
  python3 rb-create-skill-evals/scripts/validate_eval_manifest.py "$manifest" || exit 1
done
git diff --check
```

Full repository release CI also includes its existing JSON parsing, compilation,
constrained-runtime tests, generated-schema drift and Python-floor jobs. Local
phase work uses the relevant affordable subset and names omissions; a local
subset is not described as full CI. Native host interaction, true browser file
behaviour, platform matrices and live agent trials each require their own
observed evidence. None can be replaced by a validated manifest.

## 9. Rollout, rollback and completion risks

| Risk | Mitigation and evidence owner |
| --- | --- |
| Building 43 separate frameworks | P1/P3 common contracts; P7 declares routes and reuses adapters without conflating claims |
| Tests mirror the same scientific mistake | P0 independent oracles; P4 paired defects/controls; P5 separated initial design |
| Local runner mistaken for secure enforcement | P3 records actual controls; P5/P7 distinguish local versus authenticated external evidence |
| Useful tests lost during regeneration | P2 ownership/hash checks and interruption/rollback fixtures |
| Green report hides missing checks | P1 deterministic gate; P6 exact record-to-report assertions |
| Host/tool drift breaks promised support | P0/P4 pinned compatibility; P8/P9 actual host trials and versioned receipts |
| Stochastic or performance tests give unstable decisions | P4 predetermined designs, uncertainty and comparable environments; preserve failures |
| Agent evals become expensive or circular | P0 fixed budget/held-out oracles; P8 matched trials and explicit incomplete results |
| Operational testing causes real side effects | P3 authority enforcement; P7 disposable fixtures and separately scoped real environments |
| Tests pass individually but delivery is unusable | P6/P9 end-to-end inspection through actual wrapper, output files, report and installed host |

Installation follows the existing sync workflow only after qualification and
within the later execution request. The project bundle records its version and
managed-file hashes. Rollback uses recorded backups and hash checks, refuses
to overwrite intervening edits and retains immutable run evidence. A previously
rendered report stays identifiable by its original candidate and date.

Final completion requires the declared host/platform matrix, substantive
generated tests, honest independent verification, the complete capability map,
correct gate/exits, usable offline reports and preservation/rollback evidence.
Open required findings or unavailable required checks prevent full completion.
Optional unsupported connectors and scientifically unresolved target claims
remain explicit limitations rather than hidden exceptions.

## 10. Current handoff

All implementation tasks remain planned. The next implementation task, when
requested, is P0.1 under `$rb-execute-plan`. P0 resolves technical compatibility
and fixture design; it does not reopen settled requirements or require production
access. [Plan validation](plan-validation.md) records review and checks of this
planning artifact separately from future implementation evidence.
