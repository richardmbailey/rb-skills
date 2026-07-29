# Implementation Plan Template

## Title

## Summary

## Execution Route

`standard` | `constrained` | `undecided`

The constrained route is optional. In the first release it is Codex-only and compiles, assesses, executes, and verifies one phase at a time with context separation that is instruction-only rather than host-proven. Its current capability set cannot execute tests, builds, linting, typing, or application commands. Do not select it automatically or use it for phases whose acceptance depends on runtime behaviour.

The fixed project policy is also optional. If repository-owned path restrictions are wanted, use `$rb-create-safe-operation-policy` to translate the human's ordinary-language rules into a deterministic preview and proposal-bound confirmation. Do not invent a policy merely because a plan concerns safety or sensitive work.

For every constrained phase, write each success criterion and verifier check using the closed form:

```text
<mode>::<description>
```

The first-release constrained runtime accepts only `static_file_state::<description>`. Untyped strings and the modes `executable_test`, `runtime_observation`, and `external_observation` fail deterministic preflight and require the standard route.

## Goals

## Non-goals

## Users

## Requirements

## Assumptions

## Constraints

## Proposed Approach

## Implementation Phases

## Testing Strategy

### Unit and Property Tests

### Component and Integration Tests

### API, Schema, Event, and Tool Contracts

### Migration, Existing-Data, and Rollback Tests

### Critical End-to-End Workflows

### Negative, Boundary, Failure, Concurrency, and Recovery Cases

### Scientific, Stochastic, Performance, and Security Checks

### Fixtures, Test Data, Mocks, and External-Service Simulation

### Coverage Expectations

Use existing project thresholds and changed-behaviour or diff coverage where available. Do not introduce an arbitrary universal percentage target.

### Canonical CI-Equivalent Command

Record the repository command or workflow that combines the relevant tests, linting, formatting, typing, build/package, migration, and critical workflow checks. State any parts that cannot be run locally.

## Validation and Release Plan

Include release, rollback, smoke, monitoring, and post-deployment validation where relevant.

## Risks

## Success Criteria

## Open Questions
