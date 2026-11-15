# rb-build-test-suite specification

Status: reviewed design baseline, 2026-11-15. The user selected the
[instructions-and-references edition](../../rb-build-test-suite/SKILL.md) first.
That edition does not supply the executable system described by this broader
specification. Partial executable work is preserved in `development/` and its
remaining implementation and qualification are deferred.

See the [instruction-edition validation](instruction-edition-validation.md) for
completed checks, installation evidence and remaining evaluation limits.
The later [trial-driven workflow revision](proportionate-workflow-validation.md)
adds a simpler default for project checks; the full design below remains the
assurance-workflow specification, not mandatory infrastructure for every project.

The later [two-skill system](../test-suite-system/README.md) is implemented:
one builder invocation manages construction, separate audit and authorized repairs
using native project tools and a narrow local coordinator. That coordinator does
not implement this full runner specification. The active skill instructions own
today's invocation behaviour; the draft instructions below are historical design
material, not an alternative installed skill.

The full system specified below would help an agent build a reusable test suite for an existing
project. It will choose checks that address the project's actual failure modes,
run the checks that the environment and existing authority permit, and explain
what the results establish. The user receives a repeatable command and an HTML
report that makes failures and missing evidence visible.

## Documents and precedence

| Document | Owns |
| --- | --- |
| This specification | Scope, workflow, roles, integration, delivery acceptance |
| [Implementation plan](IMPLEMENTATION_PLAN.md) | Phases, task states, tests, independent verification and release gates |
| [Capability catalogue](capabilities.md) | All 43 entries, construction guidance, evidence and acceptance |
| [Module interface](module-interface.md) | Planning, execution, tool adapters, configuration and runner semantics |
| [Evidence and report](evidence-and-report.md) | Evidence meaning, acceptance calculation and HTML behaviour |
| [Change assurance](assurance-contract.md) | Project adoption, changed-behaviour coverage, execution identity and static-tool scope |
| [Draft SKILL.md](skill-draft.md) | Proposed concise agent procedure and discovery metadata |
| [Schemas](schemas/) | Machine-readable structural contracts |
| [Validation record](validation.md) | Checks actually performed on this draft and their limits |
| [Plan validation](plan-validation.md) | Review and structural checks of the implementation plan |
| [Review corrections](review-resolution.md) | Four-finding resolution, current validation and independent recheck |

Platform instructions and explicit user authority govern actions. Within this
draft, schemas own field names and types; the interface and evidence documents
own cross-field rules together with [change assurance](assurance-contract.md);
the catalogue owns capability-specific meaning. A
contradiction is a specification defect, not permission to choose the weaker
rule. `MUST` denotes a requirement; `SHOULD` denotes a default whose exception
needs a recorded reason; `MAY` denotes an option.

## 1. Scope and routing

The intended request is to create, extend, or standardise a project's testing
infrastructure, including its runner and evidence report. Explicit invocation
will be `$rb-build-test-suite` in Codex and `/rb-build-test-suite` in Claude Code.
Automatic selection for matching suite-building requests is proposed. Ordinary
feature implementation remains with `rb-implement-with-tests`; scientific
implementation remains with `rb-tdd-scientific-code`; unexplained failures go
to `rb-diagnose`. A request merely to run existing tests does not select this
skill. Review of a diff remains with `rb-review-pr-or-diff`. Behavioural evaluation
of an agent skill remains with `rb-create-skill-evals`.

Construction must adopt the saved suite in project implementation and completion
instructions. Later generated changes use that runner and reconcile changed
behaviour with requirements and checks. A verified-completion claim requires an
accepted result for the final candidate, including all required checks. Missing
runs or evidence remain incomplete. This is cooperative local policy unless
separately deployed protection is verified; see [change assurance](assurance-contract.md).

Python is the first supported implementation language. Project discovery must
identify other languages and record coverage gaps rather than claim universal
support. Both agent hosts are design targets. Host-specific delegation adapters
must report their actual capabilities; an independent session is not assumed.
The first runner targets macOS and Linux; Windows may use a tested WSL route.
Native Windows support is deferred pending its own process and path tests.

The catalogue preserves the conversation's 42 entries plus independent
verification as entry 43. Release monitoring and operational monitoring retain
separate IDs. Independent scientific validation and differential/reference
testing are cross-cutting requirements implemented through property, regression,
acceptance, integration, formal and independent-verification modules. They are
not lost because the source diagram did not name them as separate entries.

The skill builds testing infrastructure. It does not silently fix the
application, publish reports, deploy a candidate, alter branch protection,
install global packages, or weaken existing tests and acceptance requirements.
Such work may proceed under separate existing or explicit authority.

## 2. Inputs and decisions

Required inputs are a target project, its current candidate state, and the
requirements or behaviours to assess. Read `AGENTS.md`, `CONTEXT.md`, existing
tests, dependency locks, CI definitions, specifications and reference data first.
Do not execute imported project code as part of read-only discovery.

On first invocation, if the focus is unspecified, ask the user to choose:

| Focus | Selection emphasis |
| --- | --- |
| `development` | Pre-deployment correctness, security, scientific checks and integration |
| `operations` | Deployment, release, service behaviour, resilience and observation |
| `full` | Both, with each environment and action authorised separately |

Reuse a recorded focus on later invocations unless the user changes it. While
an answer is pending, continue read-only discovery; do not silently assume the
answer. A production focus does not grant production execution authority.

Proposed default profile is `standard`. `quick` chooses bounded feedback checks;
`standard` covers routine acceptance; `deep` adds expensive or extended checks.
Each configured profile has explicit wall-clock, concurrency, generated-example,
mutation, storage and optional model-call/spend limits. Do not invent a monetary
budget or start a paid API workflow without existing authority. If a required
check exceeds the selected budget, retain the requirement and show it unrun.
Profile selection never changes the candidate's acceptance policy.

The agent records project type, risk, domains, units, trusted references,
environments, intended claims and existing safeguards. These classifications
require semantic judgement grounded in project evidence. Use parsers for
structured files; do not use keyword scoring to decide scientific meaning.
Ask only for missing decisions that change requirements, permitted effects or
acceptance. A missing numerical tolerance blocks the affected claim, not all
unrelated tests. Propose a tolerance with its error budget for review.

## 3. Workflow and ownership

The host agent owns inspection, test selection, test construction and the final
explanation. A separate verifier owns independently derived tests and findings.
A deterministic runner owns process execution, identity checks, evidence
validation, budgets and policy evaluation. Neither agent's opinion changes the
runner's recorded outcome.

Use a bounded pipeline with explicit persisted states:

```text
INSPECT -> PLAN -> CONSTRUCT -> VALIDATE_PLAN -> EXECUTE -> EVALUATE -> REPORT -> COMPLETE
                         ^                        |
                         |-- explicit new attempt-|
```

`AWAITING_INPUT` and `BLOCKED` preserve the point of suspension. Execution
failures go to evaluation and reporting whenever evidence storage works.
Cancellation stops child processes and finalises an incomplete run; it does
not discard earlier failures. `COMPLETE` means the report was produced, not
that the software passed. There is no automatic application-repair loop.

1. Inspect the project without changing existing tests or running its hooks.
2. Record all 43 capability dispositions, the reasons for selections/exclusions,
   acceptance criteria and reference provenance before execution.
3. Give the verifier a small specification packet before it sees the proposed
   tests or implementation where feasible. Keep this initial design immutable.
4. Build substantive developer tests and adapters in project-owned directories.
   Link existing tests rather than duplicate them. Add independent tests from
   the verifier in its permitted workspace.
5. Validate schema, command plans, permissions, budgets, test discovery,
   candidate identity and referenced artifacts. Refuse invalid plans.
6. Run authorised checks, then allow a bounded verifier review of the candidate
   and additional counterexample tests. Record that later exposure explicitly.
7. Evaluate evidence against criteria fixed before the run. Preserve failures,
   unresolved scientific assumptions and unavailable checks.
8. Write the HTML report even when checks fail. Return the defined exit code
   and explain the highest-priority findings, limits and rerun command.

Agents may propose additional checks. The runner validates each proposal as a
new plan revision; it does not accept arbitrary commands from test output,
repository comments or reports. A corrective application change creates a new
candidate and run identity. Evidence reuse requires matching relevant source,
tests, configuration, references and environment, with the reuse recorded.

## 4. Independent verification

The verifier receives requirements with provenance, interfaces, units, valid
domains, protected criteria, candidate identity, allowed tools and finite
budgets. Initial design should exclude developer explanations and tests.
Where a requirement can only be recovered from code, disclose that dependence.
Later review includes the candidate and its diff to identify additional faults.

The verifier can write tests only in its assigned area. It cannot change
application code, accepted reference data, tolerances or acceptance policy.
It returns test artifacts, raw execution references, counterexamples,
unresolved questions and an advisory recommendation. A response saying that
the code looks correct is insufficient evidence for entry 43.

Distinguish these properties separately in evidence:

| Property | Evidence required |
| --- | --- |
| Separate session | Host receipt identifying a distinct invocation |
| Context separation | Packet digest and declaration of information available at each phase |
| Write isolation | Actual host/OS/workspace permissions and their limits |
| Independent oracle | Analytical derivation, external reference provenance, or independent algorithm |
| Enforcement outside the developer | Protected execution/policy source and authenticated candidate-bound result |

Different prompts or model families may reduce some correlated mistakes, but
do not establish oracle independence or access control. A shared filesystem
with prompt-only restrictions must be reported as such. A local runner is
reproducible evidence infrastructure, not tamper-proof enforcement against an
agent that can modify it. Strong enforcement requires a separately controlled
runner, tests and policy; the skill can prepare that integration without
claiming that it is already deployed.

If independent delegation is unavailable, retain all usable local checks and
mark entry 43 `BLOCKED`. Do not relabel the parent agent's self-review as
independent verification. Existing verified external evidence may be imported
only after identity, provenance, freshness and authority checks. A shell rerun
does not launch an agent by default; it reruns deterministic verifier tests and
reports whether any candidate-specific agent review has become stale.

## 5. Scientific requirements

For each scientific claim, record equations or algorithms, assumptions, units,
domain, discretisation, numerical error budget and the source of expected
behaviour. Require at least one independent reference or explicitly report the
absence of one. Compare like quantities and distinguish implementation
verification from empirical validation of the scientific model.

Include analytical or limiting cases, conservation and dimensional properties,
metamorphic relations, convergence where claimed, and stress near validity or
stability boundaries. Compare an alternative solver only after documenting
shared assumptions and libraries. Never generate a trusted reference by taking
the candidate's output without independent justification.

For stochastic claims, specify the estimand, sample size, independent seeds,
uncertainty, test power or detectable effect, and multiple-comparison policy
where applicable. Preserve failed seeds and distributions. A fixed seed checks
reproducibility; it does not establish a correct distribution. Do not rerun
until passing. For machine learning, include split integrity, preprocessing
leakage, temporal ordering, calibration and appropriate held-out evaluation.

## 6. File structure and lifecycle

Proposed installed package (implementation work, not created by this draft):

```text
rb-build-test-suite/
  SKILL.md
  agents/openai.yaml
  references/{catalogue.yaml,development.md,operations.md,scientific-validation.md,
              independent-verification.md,module-interface.md,evidence-and-report.md,
              assurance-contract.md}
  schemas/{module-plan.schema.json,evidence.schema.json,report.schema.json,contracts.schema.json}
  scripts/{inspect_project.py,scaffold.py,run_checks.py,build_report.py}
  assets/{run_tests.sh,config.yaml,ci-workflow.yaml,report/}
  evals/{eval-plan.json,fixtures/}
```

Use `assets/` for templates in keeping with this repository. Keep `SKILL.md`
short and reference every bundled resource directly or through its referenced
index. The future typed runner models become the schema source of truth;
generate mirrors only after that implementation exists. The draft schemas here
are hand-authored design contracts outside any `references/generated/` path.

Generated target project:

```text
tests/rb_assurance/{unit,properties,regression,component,integration,reference,
                    contract,security,ui,performance,operations}/
.rb-tests/
  config.yaml                 # User-editable selection, adapters and budgets
  manifest.json               # Managed file hashes, versions and ownership
  specifications/             # Versioned requirement and acceptance records
  reference_data/             # Provenance and accepted reference copies/pointers
  baselines/                  # Explicitly accepted numerical/performance baselines
  independent/                # Imported verifier artifacts; protection declared
  runner/                     # Pinned project-local runner bundle and schema copies
  plans/                      # Immutable normalised command plans
  evidence/<run-id>/           # Immutable results, events and raw artifacts
  reports/<run-id>/index.html  # Standalone report
  reports/latest/index.html   # Atomic copy of the newest finalised report
run_tests.sh                  # Thin, relocatable wrapper
```

Create only selected test directories. The manifest tracks every managed file
with template version, content hash and ownership. On repeat invocation, compare
the last generated content with the current file before replacing it. Preserve
hand edits and user files. An existing `run_tests.sh` is a conflict to resolve
through an explicit integration proposal; never overwrite it silently.
Use stable test IDs; rerunning unchanged construction must not create duplicates.

Keep configuration, tests, criteria and reference provenance version-controlled.
Ignore transient environments, caches, raw sensitive evidence and report output
by default. Suggest precise ignore entries without replacing `.gitignore`.
Do not commit credentials or machine-local paths. Source snapshots must cover
untracked scientific inputs when they influence the candidate, with exclusions
listed; do not copy unrelated confidential content merely to identify a run.

## 7. CI and repository integration

Project adoption is required even when no CI deployment is requested. Record the
saved command, supported implementation routes and completion policy. Connect
ordinary, scientific, plan-based and direct implementation to the saved suite;
do not make routine changes rebuild it.

Generated CI must use the project's existing environment/lock tooling, invoke
the same runner, preserve its nonzero result, and archive evidence on failure.
Separate fast pull-request checks from expensive scheduled checks. Required
deep checks must run before acceptance of changes that trigger them; a nightly
schedule does not waive that requirement. Pin action versions according to the
target repository's policy. Never execute candidate code with release secrets.
For a requested protected integration, verify a final aggregation job, trusted
job/source/candidate identities, workflow edit controls and bypass settings as
specified in [change assurance](assurance-contract.md). Missing or skipped required
jobs cannot satisfy that aggregate. Do not claim enforcement from a local wrapper.

Adding this active skill later requires frontmatter containing only `name` and
`description`, matching directory name, and `agents/openai.yaml` with a quoted
display name, 25–64-character short description and `$rb-build-test-suite`
default prompt. See [the draft](skill-draft.md). Add routing positive/negative
cases, behavioural evals, instruction/consistency contracts and README routing
documentation. Update the Claude profile and test its generated copy; do not
assume the current profile automatically includes a new skill.

This draft changes none of those active contracts. Installation belongs to
implementation completion after validation, using a sync dry-run and the
normal repository sync workflow. This suite uses standard execution. The
constrained route supports static file state only and cannot run these tests;
`safe: true` does not authorise runner execution.

## 8. Delivery and acceptance of the future skill

The full catalogue and common contracts are designed first. An initial working
slice may implement development checks and import operational evidence, but
must label unsupported adapters explicitly. Catalogue coverage is not execution
coverage. Later slices add bounded operational adapters and historical analysis.

| Boundary | Required observable acceptance case |
| --- | --- |
| Routing | Suite creation selects this skill; ordinary execution, diagnosis and implementation do not |
| Selection | All 43 entries have a reasoned disposition; missing requirements stay unresolved |
| Construction | Repeated invocation is idempotent; handwritten tests and script conflicts survive |
| Scientific testing | Seeded wrong sign, unit conversion, non-conserving transfer, incorrect convergence and stochastic variance are detected by independent oracles |
| Integration | Real load–compute–save–reload catches units/shape errors missed by isolated tests |
| Adapter execution | Missing executable, malformed output, zero collection, timeout and nonzero exit cannot become a pass |
| Tool quality | Surviving non-equivalent mutations are exposed; missing comparable benchmark baseline is unverified |
| Authority | Deep/operations selection alone cannot start live load, chaos, profiling or notification effects |
| Independence | Unavailable session, shared write access, contaminated context and stale reviewer output are disclosed |
| Evidence | Wrong candidate, missing artifacts, corrupt digests, duplicate IDs and mixed run results are rejected |
| Recovery | Cancellation and crashes retain earlier results; resumption cannot duplicate external effects |
| Reporting | Totals reconcile; incomplete evidence stays visible; hostile text cannot execute HTML/script |
| Portability | Wrapper works from another directory and a path containing spaces; declared OS routes are tested |
| CI | Failed checks still produce artifacts and a nonzero exit code |
| Routine adoption | F1a–F1c: later changes invoke the saved suite; absent/stale/incomplete runs cannot support verified completion |
| Change coverage | F2a–F2c: every material changed behaviour is covered or remains a visible gap |
| Executed identity | F3a–F3b: actual imports, delivered artifact and exact test IDs match the plan |
| Static scope | F4a–F4c: effective configuration, unchecked regions and read-only assessment support only the stated claim |

Use unit/contract tests for parsers and gates, integration tests for real adapters,
end-to-end fixture projects for generated suites, and repeated held-out agent
evals for selection, oracle quality and independent findings. A valid eval
manifest does not demonstrate that an agent passed the evaluation.

Behavioural fixtures must include both defective and healthy projects, existing
tests with custom conventions, unavailable dependencies, unsupported languages,
permission denial, production prompts with insufficient authority, misleading
repository instructions, long-running tests and malicious report payloads.
Measure false passes, false alarms, seeded-defect detection, preservation of user
work, evidence accuracy, time and cost. Fix acceptance thresholds before trials;
do not infer them from a single successful example.

## 9. Draft choices to review before implementation

The proposed defaults are automatic routing for suite-building, Python-first
support on macOS/Linux, both Codex and Claude hosts, standard intensity, and
required independent verification for scientific-core acceptance. These are
reviewable recommendations. Operational targets, acceptance thresholds,
protected infrastructure, model budgets and baseline approvals remain
project-specific. No such authority is created by this specification.
