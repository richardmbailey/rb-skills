# Normative Invariant Registry

This tracked registry gives every policy invariant a stable identifier and title. The runtime models reject unknown identifiers, and the repository test suite requires these headings to match the closed runtime set exactly. The current operational meaning and enforcement boundaries are described in `runtime-contract.md`, the skill instructions, and the versioned Pydantic models.

## Assurance

### `A-001` Protected And Excluded Failure Classes

The workflow names the failures it addresses and the malicious or host-level failures it does not claim to prevent.

### `A-002` Distinct Assurance Properties

Identity, authorization, isolation, observation, and tamper resistance remain separate claims.

### `A-003` Authority And Instruction Order

Platform rules, policy, confirmed authority, assessed plans, and repository guidance are applied in a fixed descending order.

### `A-004` Evidence Is Not Instruction

Source, plans, logs, generated text, and model output are evidence unless a higher authority independently recognizes an instruction.

### `A-005` Repository Instruction Discovery And Scope

Applicable repository instructions are discovered, hash-bound, and limited to their documented path scope.

### `A-006` Enforcement Vocabulary

Assurance statements use the closed enforcement and observation vocabulary defined by the runtime contracts.

### `A-007` Assurance Profiles And Capability Gate

Each profile requires named capabilities and fails closed rather than silently weakening the requested profile.

### `A-008` Fail-Closed And Human-Review Conditions

Missing, stale, contradictory, unsupported, or materially ambiguous evidence blocks execution or requires human review.

## Operations And Paths

### `O-001` Closed Operation Union

Every operation is one strictly validated exact action or bounded semantic task.

### `O-002` Tool-Specific Exact Adapters

Exact adapters have separate typed contracts and cannot be treated as interchangeable arbitrary tools.

### `O-003` Transitive Execution Closure

Authorization covers everything an executable could load, invoke, or cause, not just its visible command line.

### `O-004` Environment Contract

Operations receive only explicitly authorized environment names and credential handles.

### `O-005` Network Contract

Network access requires bounded destination, data, credential, redirect, resource, and effect grants.

### `O-006` Subprocess And Delegation Inheritance

Any child receives no more than the intersection of its parent's remaining authority.

### `O-007` Pre-Action Approval Classes

Required approval classes are derived from effects and bound to exact targets before mutation.

### `O-008` Actual-Effect Observation Limits

Assessments disclose material effects that the configured host cannot reliably observe.

### `X-001` Normative Path Resolution

Paths are normalized, contained, resolved, and checked for links, aliases, mounts, and special files before use.

### `X-002` Mutation-Time Revalidation

The coordinator repeats relevant identity and containment checks immediately before mutation.

## Policy And Effects

### `P-001` Immutable Global Baseline

Each run binds one installed global policy payload that cannot change in place.

### `P-002` Closed Monotonic Project Policy

Repository policy may only narrow the global baseline through typed operations.

### `P-003` Widening And Conflict Rejection

Policy widening, incompatible restrictions, and uncertain merges fail closed.

### `P-004` Semantic Guidance Separation

Natural-language guidance can inform judgment but cannot create authority.

### `E-001` Side-Effect Classification

Direct, indirect, cumulative, and external effects are classified with affected parties and materiality facts.

### `E-002` Deterministic Materiality Rule

Detrimental, high-risk, insufficiently controlled, or insufficiently observable effects block automatic execution.

### `E-003` Evidence Coverage Before Confidence

Every material claim requires explicit evidence coverage before semantic confidence can support it.

### `E-004` Typed Findings And Boolean

The canonical safety result is a typed Boolean accompanied by structured findings when it is false.

## Canonical Artifacts And Packaging

### `C-001` Canonical JSON

Stable artifacts use strict parsing and one deterministic JSON encoding.

### `C-002` Stable Payload Versus Envelope

Identity-bearing payloads remain separate from volatile observation envelopes.

### `C-003` Canonical Safety Boolean

Only the validated Boolean field controls the safety decision.

### `C-004` Schema Evolution

Version changes use explicit compatibility rules and never silently reinterpret action-bearing artifacts.

### `K-001` Dependency Declaration

Executable dependencies and versions are declared and hash locked.

### `K-002` Runtime Package Layout

The installed runtime, launcher, source, interpreter, environment, and package identities are manifest bound.

### `K-003` Generated Schema Contract

Schemas are generated from runtime models and checked for byte-level drift across every published mirror.

### `K-004` Fail-Fast Diagnostics

Distinct setup and identity failures produce named diagnostics without implicit repair or installation.

## Repository State And Records

### `R-001` Repository Snapshot

The coordinator captures the bounded repository state required for assessment and later comparison.

### `R-002` Snapshot Invalidation

Material source, policy, instruction, capability, identity, or preimage drift invalidates prior authority.

### `R-003` Project Execution Lease

One constrained run owns the project mutation lease, and an existing or uncertain lease is never silently stolen.

### `R-004` Concurrent Or External Change

Unexpected changes stop the run and remain preserved for review.

### `R-005` Time-Of-Check/Time-Of-Use Limit

Repeated checks reduce but do not overstate the host's remaining race-condition risk.

### `D-001` Plane Separation And Ownership

Product state, control state, semantic proposals, and durable writers have separate owners.

### `D-002` Audit Root And State Comparison

Project product state and local control records are compared and stored through separate boundaries.

### `D-003` Protected Control State

Policies, authority, prior artifacts, leases, and audit records stay outside product mutation scope.

### `D-004` Evidence Provenance

Every observation names whether it was host observed, coordinator observed, or agent reported.

### `D-005` Event Creation And Recovery

The coordinator validates, redacts, persists, chains, and reloads audit events through one owned path.

### `D-006` Redaction Before Persistence

Credentials, private reasoning, denied contents, and unbounded model text are omitted before durable recording.

### `D-007` Human Intervention Record

Human decisions bind the exact affected artifacts and never relabel a rejected result as safe.

## Lifecycle

### `L-001` Canonical States

Runs use a closed set of active, resumable, and terminal lifecycle states.

### `L-002` Legal Transitions And Evidence

Every state transition requires its named evidence and coordinator validation.

### `L-003` Unbounded Reversible Repair

Logical repair attempts may be unbounded while each active resource grant remains finite.

### `L-004` Diagnostic Checkpoints And High-Risk Replay

Repeated failures require changed diagnostic reasoning, while high-risk replay still requires fresh authority and idempotency evidence.
