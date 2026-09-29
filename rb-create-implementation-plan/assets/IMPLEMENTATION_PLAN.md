# Implementation Plan Template

## Title

## Summary

## Execution Route

`standard` by default. Record `constrained` only when explicitly selected, or `undecided` when the human defers the choice; `undecided` does not block standard execution.

Only for an explicitly selected constrained phase: read the planning skill's `references/constrained-route.md` and use `static_file_state::<description>` for every acceptance criterion. Do not include constrained-runtime mechanics in a standard plan.

## Goals

## Non-goals

## Users

## Requirements

## Assumptions

## Constraints

## Proposed Approach

## Task Status Convention

- `[ ]` planned
- `[x]` implemented
- `[v]` verified

Prefix every actionable implementation task in every phase with exactly one state marker. Set newly planned work to `[ ]`. Use `[x]` only when implementation evidence already exists. Use `[v]` only when the selected delivery workflow's verification gate has passed. Record required independent review according to the delivery workflow, material risk, and existing project gates.

## Implementation Phases

Use this structure for every phase:

### Phase N: Phase Name

**Goal:**

**Dependencies:**

**Tasks:**

- [ ] First actionable implementation task
- [ ] Next actionable implementation task

**Verification:**

**Exit criteria:**

## Testing Strategy

Keep the applicable sections below and omit the rest. Link existing test plans rather than copying them.

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
