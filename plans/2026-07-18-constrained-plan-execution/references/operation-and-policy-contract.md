# Operation And Policy Contract

## Purpose

This document defines what a low-level plan may ask an executor to do and how deterministic policy decides whether that request is admissible. The runtime Pydantic models implement these rules; this document and the machine-checked invariant registry remain the normative contract.

## Operation Vocabulary

### `O-001` Closed Operation Union

Every operation is exactly one of `exact_action` or `bounded_agent_task`, has a stable operation ID, declared dependencies, preconditions, success criteria, verification, stop conditions, effects, and policy references, and rejects unknown fields. No operation contains free-form shell programs.

A `bounded_agent_task` contains a goal, non-goals, bounded evidence references, allowed read/create/modify/delete roots, protected roots, allowed tool adapters, allowed executable identities and argument-form schemas, working-directory set, environment/secret/network contracts, subprocess/delegation contract, permitted effect ceilings, approval requirements, resource maxima, forbidden actions, permitted adaptation dimensions, diagnostic checkpoint rules, success criteria, completion evidence, verifier checks, and escalation/stop conditions. Permitted adaptation is a closed list such as choosing among approved files within a root, selecting an approved test command form, or revising local code while preserving goal/non-goals; it never adds a root, tool, executable form, permission, effect class, objective, or external target. The deterministic validator must prove every field is at least as narrow as active policy before semantic assessment.

In the first-release global policy, bounded tasks may use only `read` and `apply_patch`; `allowed_executables`, subprocesses, and delegation must be empty. The broader fields above reserve typed schema space and do not confer permission. Build/test command selection is therefore unavailable until a later reviewed release provides host-enforced filesystem, process, environment, and network containment.

### `O-002` Tool-Specific Exact Adapters

`exact_action` is a discriminated union with the following typed adapters. The immutable first-release policy activates only `read_file` and `apply_patch`; `exec_argv` and `check` remain fail-closed schema/dispatcher forms. Every adapter also carries explicit allowed read/create/modify/delete roots, protected roots, working-directory set, environment/network/subprocess contracts, approval references, and expected/forbidden effects, even when a narrower adapter fixes some fields to empty:

- `read_file`: resolved path, byte/range bounds, expected identity when material;
- `apply_patch`: exact target roots, patch hash, expected preimage hashes, expected created/modified paths;
- `exec_argv`: resolved executable identity, literal argument vector, working directory, environment contract, transitive-capability declaration, timeout, expected effects;
- `check`: a validator-intent executable with the same capability and transitive rules as `exec_argv`; caches, coverage files, hooks, child processes, network, and external effects must be declared rather than assumed absent.

The dispatcher must not treat arbitrary executables as equivalent. Unsupported tool or adapter kinds fail validation. Patch application counts as a product-plane mutation even when represented as text.

### `O-003` Transitive Execution Closure

Safety analysis includes everything an executable can cause or load: shells; `-c` or equivalent inline interpreters; scripts; package-manager scripts; build/test targets; task runners; plugins; hooks; configuration-driven code; dynamic imports; startup files; subprocesses; child agents; and files interpreted by the executable.

Default rules:

- deny shells, inline interpreters, eval/exec forms, arbitrary plugins, remote code, and user-controlled startup hooks in `exact_action`;
- treat executable and input hashes as identity evidence, not confinement: they do not prove what code can read, write, spawn, or contact;
- deny repository scripts, build/test/debugging tools, and other code execution in the first release because no host-enforced filesystem, process, and network capability sandbox is available;
- permit such tools in a future policy only when a reviewed host capability layer enforces their complete filesystem, process, environment, and network envelope; semantic assessment alone does not create containment;
- reject “safe argv” reasoning that examines metacharacters without classifying the executable and loaded inputs.

### `O-004` Environment Contract

Each executable operation starts from an empty logical environment plus an explicit allowlist of names and either literal values, value hashes, or approved secret handles. Ambient credentials, proxy variables, startup paths, package indexes, cloud contexts, agent tokens, and task-unrelated variables are denied by default. The host may add documented minimal runtime variables, but their names and provenance must be recorded and they must not widen network, filesystem, or executable resolution. `PATH` is replaced by resolved executable paths where practical.

### `O-005` Network Contract

Network permission is a list of grants, not a Boolean. Each grant names destination host/IP constraints, port, protocol, method, read or write semantics, request and response data classifications, credential handle and audience, redirect policy, maximum calls/bytes/time, retry limit, idempotency key or proof, and expected external effect. DNS changes and redirects outside the grant stop execution. No grant means network denied. External writes always require the approval class defined by `O-007`.

### `O-006` Subprocess And Delegation Inheritance

A child process, plugin, hook, or delegated agent is authorised only for the intersection of the parent's remaining filesystem roots, environment allowlist, network grants, external-effect permissions, timeout, resource limits, and approval state. It receives no undeclared capability by policy. Representation as a bounded task and semantic review do not create containment. If the host cannot enforce the intersection, the semi-formal profile may proceed only when active policy explicitly permits instruction-only behaviour and the assessment records that limitation; a policy requiring enforcement returns `safe: false`.

### `O-007` Pre-Action Approval Classes

Before the action occurs, obtain a distinct current approval for destructive, externally visible, privacy-sensitive, security-sensitive, materially costly, or irreversible effects unless global policy prohibits the effect outright. The validator derives mandatory classes rather than trusting a planner-selected label: `repository_delete` requires `destructive`; `external_write` requires `external_write`; personal/sensitive/secret data requires `privacy_sensitive`; the closed `security_sensitive` Boolean requires that exact class; medium/high cost requires `material_cost`; and reversibility `none` requires `irreversible`. A planner-declared additional class can only add a gate, never replace one of these derived classes. Every approval-gated effect declares its exact targets. The approval record identifies the exact plan, operation, active-policy, and repository-snapshot hashes; effect ID and class; approval class; one exact target; retry/idempotency rule; expiry; mandatory one-use status; and recovery limit. One approval is required for every required approval-class and target pair. Approval cannot authorise unknown scope or a policy-prohibited action, and it is consumed atomically before the action.

### `O-008` Actual-Effect Observation Limits

Every operation declares expected effects and the sources capable of observing them. The executor records host-observed, coordinator-observed, and agent-reported evidence separately. Effects the host cannot reliably observe—such as transient reads, undisclosed subprocess behaviour, remote side effects, or secret exposure—must be disclosed in assessment coverage. If such an unobservable effect could be material and lacks a stronger control, `E-002` returns a rejected assessment with `safe: false` and records the required human decision.

## Path Identity

### `X-001` Normative Path Resolution

For every read or prospective mutation:

1. establish an absolute project root by resolving the supplied root without following an untrusted cwd;
2. reject NUL bytes, unresolved variables, globs, empty components, and relative roots;
3. normalize separators, remove `.` components, resolve `..` lexically, and reject any lexical escape before filesystem access;
4. normalize Unicode to NFC and compare using the platform's case-sensitivity rules; enumerate case aliases where the filesystem is case-insensitive;
5. resolve every existing ancestor with `realpath`, recording each symlink target and device/mount identity;
6. for a non-existent output, resolve its nearest existing ancestor and append normalized remaining components; reject a remaining component that becomes a link before mutation;
7. reject resolved paths outside every allowed root, unexpected mount crossings, special device files, and hard-link aliases to protected/out-of-scope inodes where link identity can be detected;
8. record the resolved identity, existing inode/device when available, and containment result in the precondition snapshot.

Hard links cannot always be detected portably. A mutation of an existing multiply-linked file is denied by default unless all discovered aliases are in scope and the limitation is disclosed.

### `X-002` Mutation-Time Revalidation

Immediately before each mutation, repeat containment, link, inode/device, applicable instruction, lease, and expected-preimage checks. Use descriptor-relative or no-follow host primitives where available. A symlink swap, path alias change, unexpected creation, mount change, or preimage mismatch stops before mutation and requires snapshot revalidation or reassessment. Non-atomic hosts retain the time-of-check/time-of-use risk documented by `R-005`.

## Policy Algebra

### `P-001` Immutable Global Baseline

At run creation, load the versioned global policy from the installed runtime package, validate it strictly, canonicalize it under `C-001`, and record its version and hash. That payload is immutable for the run. A runtime policy update creates a new assessment rather than silently changing an approved run.

### `P-002` Closed Monotonic Project Policy

Project policy has no free-form override map. It may contain only these typed operations:

- `deny_operation`, `deny_adapter`, `deny_effect_class`, or `deny_command_form`;
- `intersect_path_roots`, `intersect_executable_hashes`, `intersect_network_grants`, or `intersect_environment_names`;
- `lower_maximum` for time, calls, bytes, processes, or cost; reversible repair attempts use the operation's separate finite-or-`unbounded` `attempt_limit` and are not silently capped by project policy;
- `require_approval` adding one or more named approval kinds/classes;
- `require_minimum_enforcement` for a named control, using `instruction_only < host_enforced`;
- `require_minimum_observation` for a named fact, using `agent_reported < coordinator_observed < host_observed`;
- `require_evidence_source` adding one or more independently required evidence sources;
- `require_verification` adding checks without removing baseline checks.

Merge means set union for denials, named approval kinds, evidence sources, and verification checks; numerical minimum for maxima; and the maximum in the applicable explicit enforcement or observation order for each named control/fact. Requirements on different named controls are combined, not compared.

Allowlists use typed semantic intersection after canonicalization, not string comparison:

- path roots resolve under `X-001`; for every root pair keep the narrower root when one contains the other and discard disjoint pairs, then remove any redundant descendant already covered by a retained ancestor;
- executable hashes and environment names use ordinary set intersection;
- network grants intersect destination/IP sets, ports, protocols, methods, read/write permission sets, credential audiences, redirect destinations, and data classes; take minima for calls/bytes/time/retries; and union required idempotency/approval constraints. Split results when needed and discard any grant with an empty required dimension.

An empty resulting allowlist is a valid deny-all tightening, so an operation requiring that capability fails but the policy itself remains valid. Values outside the closed orders and structurally incompatible requirements are rejected under `P-003`. The merged policy and a machine-readable field-by-field merge proof, including discarded intersections, are hashed into the assessment.

### `P-003` Widening And Conflict Rejection

Reject unknown fields, unknown identifiers in closed registries, generic `allow` or `override` fields, attempts to add an allowlist member, raise a maximum, remove an approval/evidence requirement, change baseline semantics, or create contradictory requirements with no satisfiable value. Denial names and required approval-class names are intentionally project-extensible namespaces: an unmatched denial remains harmlessly restrictive, while a required class affects only a matching declared operation/effect. A rejected project policy cannot fall back silently to the global policy.

### `P-004` Semantic Guidance Separation

Natural-language project guidance may help the semantic assessor interpret domain harm, but it is stored separately from the deterministic policy payload. It can cause a denial, narrower interpretation, or human review; it cannot authorise an action denied by deterministic policy.

## Side-Effect Decision

### `E-001` Side-Effect Classification

For each direct, indirect, verification-induced, and cumulative effect, record exact targets, affected party/system, data classification, the closed `security_sensitive` Boolean, unmitigated severity, residual severity, likelihood, exposure, reversibility, detectability, mitigation status, recovery status, cost impact, availability impact, approval class/state, observation source, and cumulative interaction. Use these closed enums:

- severity: `none < low < medium < high < critical`;
- likelihood: `rare < unlikely < possible < likely < almost_certain`;
- exposure: `isolated < repository < project_external < multi_party < systemic`;
- reversibility: `full > bounded > uncertain > none`;
- detectability: `full > partial > weak > unknown`;
- mitigation: `verified`, `proposed`, or `none`;
- recovery: `tested`, `specified`, `uncertain`, or `impossible`;
- cost/availability impact: `none < low < medium < high`;
- cumulative interaction: `none`, `additive`, or `amplifying`;
- data classification: `public`, `internal`, `personal`, `sensitive`, or `secret`.

Semantic assessment supplies evidence-backed classifications. Deterministic validation permits residual severity below unmitigated severity by at most one step and only when mitigation is `verified`, recovery is `tested` or `specified`, reversibility is `full` or `bounded`, and detectability is `full` or `partial`. An `amplifying` interaction raises residual severity one step, capped at `critical`; an `additive` interaction uses at least the maximum residual severity of its members. “Material” means residual severity `medium` or above, likelihood `likely` or above, exposure `project_external` or above, data `personal` or above, cost/availability impact `medium` or above, reversibility `uncertain`/`none`, or a policy-designated review class. Prose may explain but not replace enum values or evidence.

### `E-002` Deterministic Materiality Rule

The outer verdict applies the following ordered table; the first matching row controls:

| Condition | Machine verdict | Lifecycle/status |
| --- | --- | --- |
| Effect is prohibited; evidence is missing; residual severity is `high`/`critical`; exposure is `systemic`; reversibility is `none` without policy-permitted idempotency; detectability is `unknown` for a material effect; or required enforcement is unavailable | `safe: false` | `rejected`; human decision required where remediation/exit is possible |
| At least one review condition is present—residual severity `medium`; likelihood `likely`/`almost_certain`; exposure `project_external`/`multi_party`; data `personal`/`sensitive`/`secret`; `security_sensitive: true`; reversibility `uncertain`; detectability `weak`; cost/availability impact `medium`/`high`; or a policy-named review class—and every deterministically derived and additionally declared exact current approval plus all required controls is absent from the assessment input | `safe: false` | `rejected`; exact human decision required |
| A preceding review-class condition has exact current approval bound to the plan/effect hashes, active policy permits it, residual severity is no higher than `medium`, exposure is no higher than `multi_party`, the action is reversible or proven idempotent, detectability is `full`/`partial`, and recovery is `tested`/`specified` | effect allowed and documented if every non-effect rule also passes | approval recorded; never relabel prior false |
| Residual severity is `none`/`low`, exposure is `isolated`/`repository`, reversibility is `full`/`bounded`, detectability is `full`/`partial`, recovery is `tested`/`specified`, and every other rule passes | effect allowed and documented | no effect-level block |
| No row proves allowance | `safe: false` | `rejected`; human decision required |

Review after a false verdict means a new assessment input/version, not mutation of that verdict. No numeric average may cancel a single blocking dimension.

### `E-003` Evidence Coverage Before Confidence

The assessor maintains a required-evidence checklist for every operation, transitive capability, path, effect, policy rule, and verification action. Any uncovered required item or unresolved material uncertainty makes the verdict false. Self-reported numeric confidence is supplementary metadata only until repeated evaluations demonstrate calibration; high confidence cannot cure missing evidence.

### `E-004` Typed Findings And Boolean

Every finding includes finding ID, exact controlling invariant ID, operation/effect IDs, category, severity, evidence references and provenance, concise explanation, remediation or required human decision, and blocking status. Machine output uses JSON `safe: true` or `safe: false`; uppercase `TRUE`/`FALSE` is presentation text only.

`rb_safe_operation.models.INVARIANT_IDS` is the authoritative closed machine registry. The normative `###` invariant headings in this document, `assurance-and-threat-model.md`, and `execution-audit-state-model.md` must equal that registry; a regression test rejects drift or unknown runtime finding IDs.

## Canonical Artifacts And Packaging

### `C-001` Canonical JSON

Parse strict UTF-8 without BOM; reject duplicate object keys, keys that collide after normalization, invalid Unicode, unpaired surrogates, and non-JSON numeric values before model validation. Hashable payloads normalize strings to Unicode NFC and use LF inside strings, object keys sorted by Unicode scalar value after normalization, arrays in semantic order, JSON `true`/`false`/`null`, and no insignificant whitespace. String serialization emits `\"` and `\\` for quote/backslash; `\b`, `\t`, `\n`, `\f`, and `\r` for those controls; lowercase `\u00xx` for other U+0000–U+001F controls; leaves `/` unescaped; and emits every other scalar as UTF-8. Integers remain minimal decimal integers. Floating-point values are forbidden in hashable safety fields; bounded decimal quantities use canonical decimal strings with no exponent, leading plus, insignificant trailing zeros, negative zero, NaN, or infinity. Paths use normalized absolute POSIX-style strings plus explicit platform metadata. Timestamps use UTC RFC 3339 with exactly `Z` and whole seconds. Unknown fields fail validation; nullable fields are explicit and omitted/defaulted fields are not interchangeable.

### `C-002` Stable Payload Versus Envelope

Each artifact has a stable `payload` and a volatile `observation` envelope. Artifact identity is lowercase hexadecimal SHA-256 over `b"rb-safe-operation\0" + artifact_type_ascii + b"\0" + schema_version_ascii + b"\0" + canonical_payload_bytes`; artifact type and schema version are closed ASCII tokens without NUL. Observation time, host session IDs, display text, local file location, and transport metadata remain outside that payload hash. The envelope records the payload hash and receives event-record identity when persisted under `D-005`. Policy, plan, assessment, approval, and snapshot hashes always name the payload type, schema version, algorithm, and lowercase encoding they cover.

### `C-003` Canonical Safety Boolean

The only executable assessment field is `safe: true|false`. Status codes and findings explain the Boolean but cannot contradict it. Human-facing renderers may display `TRUE` or `FALSE` and must show the underlying artifact hash.

### `C-004` Schema Evolution

Schemas use `major.minor`. Readers support an explicit allowlist of versions. A compatible minor reader may accept older minor payloads without changing their bytes or hash; migration creates a new payload, version, hash, and provenance link. Major or unsupported versions fail closed. Unknown fields never become forward-compatible authorization. Runtime and schema versions are checked at every handoff.

### `K-001` Dependency Declaration

The support runtime declares Python 3.9 or newer and `pydantic>=2.12,<3` in its `pyproject.toml`, and commits a lock or hash-pinned requirements export for the supported runtime environment. Normal planning, assessment, execution, verification, and sync helpers never install or upgrade dependencies. A separately named setup command may provision the dedicated runtime environment only when a human invokes and approves that setup action explicitly. Missing Pydantic, unsupported Python/Pydantic, or import failure produces a named diagnostic and stops before artifact interpretation.

### `K-002` Runtime Package Layout

`$rb-safe-operation` owns an internal Python project containing the one handwritten model/policy/canonicalization implementation, `pyproject.toml`, pinned dependency data, setup entrypoint, CLI, and schema generator. The sync command selects all three user-facing skill folders in both symlink and copy mode. The explicit setup command from `$rb-safe-operation` acquires a create-if-absent setup lock keyed by runtime version and the full combined dependency-lock hash, copies the package into a sanitized temporary source tree, builds and installs into a temporary directory, validates package/source/lock identities, and atomically promotes the completed dedicated environment under a configured host control root. An existing environment is reused only after the same validation. The manifest contains the interpreter path, package version, combined lock hash, installed source hash, and measured installed-package tree hash. Every normal invocation recomputes source and lock identity and queries installed `runtime-info` to compare the observed package tree with both its recorded identity and the manifest. Partial, stale, or tampered environments are never selected. Each skill locates that manifest through the host adapter and invokes the same manifest-pinned installed CLI; it neither imports another skill's private files nor assumes a skill destination is on Python's import path. A copied or updated `$rb-safe-operation` runtime source whose hash differs from the manifest fails until the explicit setup is rerun.

### `K-003` Generated Schema Contract

The runtime generator may export versioned JSON Schemas into consumer `references/generated/` directories for inspection and non-Python validation. Each export records generator version, runtime source-tree hash, schema payload hash, and model/schema version. A deterministic drift check regenerates into a temporary directory and compares bytes. Possessing a schema does not satisfy the runtime import requirement and must not be reported as executable Python availability.

### `K-004` Fail-Fast Diagnostics

Use distinct diagnostics for `missing_runtime_skill`, `missing_runtime_environment`, `missing_runtime_manifest`, `missing_pydantic`, `unsupported_python_version`, `unsupported_pydantic_version`, `runtime_source_hash_mismatch`, `runtime_schema_version_mismatch`, `generated_schema_drift`, `unsupported_artifact_version`, `unsupported_host_capability`, and `copy_install_dependency_missing`. Each diagnostic names the expected and observed versions/locations without exposing secrets and identifies the separately approved setup action; none triggers installation automatically.
