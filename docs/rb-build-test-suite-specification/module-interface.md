# Module interface

A module represents one bounded check and the evidence it must produce. Tools
may differ, but each module declares its inputs, permitted effects, limits and
acceptance criteria before it runs. The runner applies the same validation and
reporting rules to every module.

## 1. Catalogue and selection contract

The future `references/catalogue.yaml` contains exactly 43 stable entries from
[the catalogue](capabilities.md), ordered by original number. Each entry has:

| Field | Type and meaning |
| --- | --- |
| `number`, `id`, `name` | Original integer 1–43, stable identifier, readable name |
| `original_phase`, `original_phase_note` | Verified historical group (`pre_production`, `deployment`, `release`, `post_release`, `cross_cutting`), or null with a note when the source grouping is unavailable; never used for acceptance |
| `focuses` | Nonempty subset of `development`, `operations`, `full` |
| `kinds` | Subset of `executable`, `observation`, `procedure`, `human_review`, `agent_review` |
| `purpose`, `applicability` | Meaning of the claim and semantic selection guidance |
| `construction` | Ordered instructions for substantive checks |
| `tools` | Candidate tools; installed versions and output formats require adapter validation |
| `evidence`, `acceptance` | Required artifacts, interpretation and decision rules |
| `cost`, `profile_hint` | Relative cost and suggested profile; never permission or a gate override |
| `effects`, `authority` | Possible effects and required existing authority |
| `subtypes` | Extensions such as `analytical_reference`, `convergence`, `metamorphic`, `empirical_validation` |

The source text establishes all 43 capabilities but does not establish every
original diagram group. Preserve unknown historical labels as null with an
explanation; do not infer them from current applicability or invent source facts.

These prose fields guide agent judgement. They are not code executed by the
runner. Exactly one disposition record per capability is retained in every
run. Dispositions are `selected`, `deferred`, `not_applicable` or `unresolved`,
each with a reason and whether acceptance requires it. Excluding a capability
from a profile produces `deferred`, not `not_applicable`.

One capability may have several modules, such as a benchmark on CPU and GPU.
A physical check may support several claims, but it has one execution ID and
one primary capability. Secondary claims cite that evidence explicitly; they
do not double-count execution or infer identical acceptance rules.

## 2. Project configuration

`config.yaml` is parsed with a safe YAML parser into a validated object. Reject
duplicate keys, unknown fields and unsupported schema versions. It records:

| Section | Required content |
| --- | --- |
| Identity | Config version, project-relative root, focus and default profile |
| Environment | Existing environment command, lock digest, supported OS, runner version |
| Profiles | Explicit check selections and finite resource budgets |
| Requirements | Specification/policy paths, digests, criteria IDs and authorised owner |
| Modules | Stable IDs, adapter IDs, test paths, expected collection and parameters |
| Capabilities | All 43 dispositions with reasons and required flags |
| References | Baseline and oracle provenance, digests, accepted tolerances |
| Operations | Environment identities, scoped authority references, observation windows |
| Adoption and impact | Saved completion workflow, supported routes, versioned change-impact inventory and reviewed requirement/check mapping |
| Execution identity | Intended import/build mode, artifact manifests and exact selected test IDs |
| Static scope | Intended checked paths, effective configuration references and type/suppression policy |
| Reporting | Retention, redaction, raw-artifact inclusion and local report location |

The implementation must publish a configuration schema before accepting config
files. This draft supplies schemas for the normalised module plan, evidence and
report; configuration is an authoring layer that compiles to those contracts.
The implementation authoring schema uses unbound module/adoption requests and
paths to reviewed control records. Compile these into candidate-bound plans after
freezing inputs; do not embed a candidate hash inside the configuration being
hashed. See [P1 contract notes](implementation-evidence/p1-contract-notes.md).
Environment commands are arrays, not shell strings. Credentials are referenced
through the host's secret facility; never embed secret values in config or JSON.
An authority reference locates a trusted receipt; a string in an editable file
does not itself grant permission.

## 3. Module protocol

Adapters are versioned, registered implementations. The runner selects them
from an allow-list; it does not import a module path supplied by test output.
Use typed in-process calls first. External tools run as child processes, while
agent/human review uses the host adapter and an imported evidence record.

```python
describe() -> AdapterDescriptor
probe(context: ReadOnlyContext) -> Availability
plan(request: CheckRequest) -> ModulePlanProposal
collect(receipt: ExecutionReceipt, artifacts: ArtifactSet) -> ResultProposal
```

`describe` identifies adapter and supported versions, capability/kind, input
parameters and output format. `probe` checks executable presence and declared
compatibility without installing packages or running project hooks. `plan`
does not launch processes. The runner validates the proposal, freezes its
digest, executes its command and gives the adapter a receipt. `collect` parses
bounded structured output and proposes observations; the runner validates and
evaluates them. Adapters cannot author their own trusted process receipts.

For reviews, procedures and observations, the plan uses `command: null` and a
non-null `evidence_import`. Executable modules require a command and a null
import. A capability that needs both uses separate linked modules. The runner
validates imported provenance and requested
identity before evaluation. Human review additionally requires a reviewer
identity and attestation artifact. An agent review requires a host invocation
receipt and the independence record. Do not manufacture human or agent receipts.

The import contract identifies source artifacts, producer identity, receipt,
expected candidate/policy digests and target. Human imports require
`reviewer_identity`; agent imports require `host_invocation_ref`. Observation
imports require start/end timestamps, minimum sample count, maximum permitted
age and evaluation time. Compare these constraints with the raw receipt and
observations, including target configuration; a producer's declared identity or
window alone is not evidence that the constraint was met. The independent
verifier may produce executable modules as well as its review import.

The exact structural input is [module-plan.schema.json](schemas/module-plan.schema.json).
Its principal fields are:

| Field | Meaning |
| --- | --- |
| `plan_id`, `run_id`, `module_id` | Immutable plan, run and stable logical check identities |
| `capability_id`, `kind`, `adapter` | Catalogue ID, execution class, adapter name/version |
| `candidate_digest`, `policy_digest` | Exact inspected source/input snapshot and acceptance policy |
| `requirement_ids`, `subtypes` | Claims assessed, including scientific/reference roles |
| `required`, `profile` | Acceptance obligation independent of execution intensity |
| `inputs`, `depends_on` | Hashed input artifacts and required successful module results |
| `command` | Executable argv, relative working directory and environment variable names; nullable |
| `evidence_import` | Alternative typed import binding producer, receipt, target, identity and observation constraints |
| `target` | Local/sandbox/staging/production identity and its configuration digest |
| `effects`, `authority_refs` | Declared access/effects and trusted authorisation receipts |
| `limits` | Timeout, termination grace, output bytes, concurrency, model/tool calls and optional spend |
| `execution_contract`, `static_contract` | Typed execution identity and static scope expectations; null only when inapplicable |
| `criteria` | Predetermined metric/assertion/attestation predicates, units and justification |

Predicate semantics are fixed: `at_most` and `at_least` are inclusive numeric
comparisons; `between` includes both bounds and requires lower ≤ upper;
`equals` compares like scalar types; `is_true` requires boolean true;
`attested` requires the named authorised review and its receipt. Validate the
criterion type, predicate and expected value together. Numerical tolerance is
expressed as a justified bound on an error metric, not approximate equality
chosen by the adapter. Reject unit mismatches unless the plan explicitly
declares and justifies the conversion. Missing observations produce `unknown`.

Schema validation is followed by semantic validation. Resolve relative paths
under the assigned root and reject escapes, symlink escapes and unexpected
devices. Validate executable location, adapter compatibility, dependency DAG,
unique IDs, nonempty expected test selection, criterion references and matching
candidate/policy identities. Hash the exact bytes being executed, including
tests, configuration and relevant untracked inputs. Record Git commit plus
dirty state when available; a commit SHA alone does not identify a dirty tree.

[Change assurance](assurance-contract.md) defines the required `ChangeImpact`,
`Adoption`, execution identity and static-scope records. Validate those contracts
before accepting a run. Imports must match the intended candidate or distribution,
and exact collected/executed test identities must match the frozen selection.
Candidate hashes and matching test totals alone cannot establish these facts.

## 4. Execution and failure behaviour

Spawn commands with argument arrays and `shell=False`. The shell wrapper only
locates the project and invokes its pinned runner. Preserve the project's
environment manager and lock; do not impose a global environment or run
automatic dependency updates. Installation is a separate, disclosed setup step
within the user's authority. Missing packages make the affected module blocked.

Run arbitrary candidate code without unnecessary credentials. Use temporary
directories, process/resource limits and denied network access where enforced
by the selected host. Declare which isolation controls actually exist. An argv
array prevents shell expansion but does not sandbox Python or test hooks.
If a required control is unavailable, block that check. Mutation tools operate
on disposable source copies. Never apply mutations to the user's working tree.

Runner scheduling follows the validated dependency graph and declared shared
resources. A required failed dependency blocks its dependants; independent
checks continue within budget. Limit concurrent benchmark jobs to avoid
resource interference. Honour cancellation by terminating the process group,
waiting the specified grace period, then force-stopping remaining children.
Write the termination receipt and partial artifacts.

No automatic retries of failed assertions, stochastic tests, or externally
visible actions. A transient read-only adapter transport failure may have at
most one configured retry within the original budget, preserving both attempts.
Do not combine a retry's passing subset with an earlier failing run. Crashes
mark in-flight work interrupted. Resume only after checking identities and
receipts. An uncertain external effect requires reconciliation; never replay
it merely because its completion receipt is missing.

Persist a run manifest, append-only lifecycle events, artifact hashes and final
record using atomic writes. Maintain one local writer lock per run; reject a
second writer. Each event includes sequence, UTC timestamp, actor, module,
state transition and receipt/artifact references. Corrupt/incomplete records
remain visible and cannot supply a pass. Durable remote workflow services are
outside the initial scope.

If any declared effect exceeds existing authority, do not dispatch it. In
particular, live load/chaos/security tests, traffic changes, process attachment,
notifications and production writes require a named target, bounded effects,
time window, stop conditions and recovery owner where effects are reversible.
Preparing a procedure does not execute it or test its result.

## 5. CLI contract

```bash
./run_tests.sh --profile quick
./run_tests.sh --profile standard
./run_tests.sh --profile deep --category property_based
./run_tests.sh --list
./run_tests.sh --report-only --run-id RUN_ID
```

No flags defaults to the saved `standard` profile unless configured otherwise.
`--category` accepts stable catalogue IDs and limits execution, not acceptance
requirements. Unknown IDs/options fail before dispatch. `--list` is read-only.
`--report-only` validates saved evidence, executes no tests or agents, and cannot
update evidence dates to make stale results appear fresh. Without `--run-id`,
it uses the latest finalised run, not a mixture of results. No `--force-pass`,
`--ignore-required` or implicit production-authorisation flag is provided.

| Exit | Meaning |
| --- | --- |
| `0` | All required criteria for the recorded scope are accepted; or successful `--list` |
| `1` | Required criterion failed or a blocking defect was demonstrated |
| `2` | Evidence insufficient: required blocked, unrun, stale, skipped or review-needed check |
| `3` | Invalid configuration/record, runner failure or inability to produce a valid report |
| `130` | User cancellation, with partial evidence/report where storage remains usable |

Precedence is cancellation, runner/configuration error, demonstrated required
failure, insufficient evidence, accepted. Preserve lower-priority outcomes in
the report. `--report-only` returns the underlying gate outcome after a
successful render. Partial profile runs may therefore exit `2` despite all
executed checks passing. CI must not mask these exits with a successful report
command or shell pipeline.

## 6. Tool adapter acceptance

Initial adapters should use structured output where available: pytest JUnit
XML, coverage JSON/XML, Ruff JSON, type-checker diagnostics, mutation records and
benchmark samples. Preserve raw output and parser version. Do not infer results
by searching stdout for words such as “passed”. Bound input size, disable XML
external entity resolution, reject duplicate JSON keys and reject NaN/infinity.
An unsupported output version is an adapter error, not a pass.

A pytest adapter must capture actual first-party import origins in the test process
and reconcile exact selected, collected and executed IDs, including custom and
parameterized discovery. Qualify checkout, editable, distribution and standalone
script routes with the cases in [change assurance](assurance-contract.md). It must
also reconcile collected, executed, failed, skipped, expected
failure and unexpected pass counts with its selected required tests. Zero tests
is not success. Known expected failures remain visible; they cannot satisfy a
required acceptance assertion. Mutation adapters distinguish killed, survived,
equivalent-reviewed, timeout and invalid mutants. Benchmark adapters preserve
hardware, repetitions, uncertainty and baseline identity. Report unsupported
platforms, including a tool's need for fork or process-attachment permissions.

Static adapters must preserve effective nested configuration, actual checked
paths and justified excluded/unchecked regions. Ruff assessment disables fixes
and fix-only behaviour explicitly and verifies source bytes remain unchanged.
Type-checking claims must disclose untyped functions, Any, skipped imports and
suppressions. These requirements and healthy/defective fixtures are specified
in [change assurance](assurance-contract.md). Formatting, when required, has a
separate read-only check under the existing lint capability.

Current primary documentation supports these starting choices:
[pytest output](https://docs.pytest.org/en/stable/how-to/output.html),
[Hypothesis](https://hypothesis.readthedocs.io/en/latest/),
[Ruff](https://docs.astral.sh/ruff/), and
[mutmut requirements](https://mutmut.readthedocs.io/en/latest/).
Exact versions, CLI options and parser fixtures must be pinned and tested during
implementation; this draft does not claim tool compatibility has been tested.
