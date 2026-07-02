---
name: "rb-implement-with-tests"
description: "Use to implement ordinary software/product changes with focused tests and executable checks after requirements are clear. Use for non-scientific feature work, refactors, bug fixes with an agreed fix, and implementation plans that need small verified increments."
---

# /rb:implement - implement with tests

## Purpose

Implement agreed changes in small verified increments.

Use `$rb-grill-with-docs` first when material behaviour, interface, edge cases, compatibility, or test expectations are unclear. Use `$rb-tdd-scientific-code` instead when the change is scientific, numerical, modelling, simulation, or domain-sensitive enough to need scientific invariants.

## Procedure

1. Confirm the agreed requirement, plan, or issue.
2. Read `AGENTS.md`, `CONTEXT.md`, relevant docs, surrounding code, and existing tests that define local conventions.
3. Check current worktree state. Preserve user changes and avoid touching unrelated files.
4. Identify the smallest useful behaviour to change.
5. Add or update a focused test/check where practical. If no automated test is practical, define the explicit manual or executable check before editing.
6. Run the relevant failing or baseline check before editing when possible.
7. Implement the smallest change that should pass the check, following existing patterns and helper APIs.
8. Run the focused check again.
9. Run broader relevant checks when the change touches shared behavior, public interfaces, migrations, build configuration, or user-facing workflows.
10. Refactor only while keeping checks green and only within the requested scope.
11. Update `$rb-working-diary` at meaningful checkpoints with decisions, checks run, failures, and next steps.
12. Repeat in small increments until the requested change is complete.

## Required Behaviour

- Do not skip clarification when behaviour is still ambiguous.
- Do not claim success without running or explicitly naming the check that could not be run.
- Keep edits scoped to the requested behaviour unless a wider change is necessary and explained.
- Do not introduce dependencies, migrations, destructive operations, secret handling changes, or broad architecture changes without explicit approval.
- Do not rewrite working user changes; work with them or ask if they block the task.
- Prefer the repository's existing style, tests, frameworks, and abstractions over new patterns.

## Output

- what changed
- checks run and exact outcome
- checks not run and why
- residual risks or follow-up work
