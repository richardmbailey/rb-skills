---
name: "rb-implement-with-tests"
description: "Use to implement ordinary software/product changes with focused tests and executable checks after requirements are clear. Use for non-scientific feature work, refactors, bug fixes with an agreed fix, and implementation plans that need small verified increments."
---

# /rb:implement - implement with tests

## Purpose

Implement agreed changes in small verified increments.

Use `$rb-clarify` first when material behaviour, interface, edge cases, compatibility, or test expectations are unclear. Use `$rb-tdd-scientific-code` instead when the change is scientific, numerical, modelling, simulation, or domain-sensitive enough to need scientific invariants.

## Procedure

1. Confirm the agreed requirement, plan, or issue.
2. Read `AGENTS.md`, `CONTEXT.md`, relevant docs, surrounding code, and existing tests that define local conventions.
3. Check current worktree state. Preserve user changes and avoid touching unrelated files.
4. Identify the smallest useful behaviour to change.
5. If the change handles text, classify the text operation before designing the code:
   - Use deterministic parsing for syntax-bound tasks with stable structure, such as JSON/YAML/XML/CSV parsing, frontmatter fields, exact delimiters, known IDs, line-oriented logs, file paths, URLs, or protocol formats.
   - Use structured parsers or existing libraries for structured formats before considering regex.
   - Invoke an LLM for semantic tasks that require meaning, intent, relevance, classification, summarisation, ambiguity resolution, rubric judgment, natural-language extraction, entity/claim matching, or deciding whether two differently worded passages mean the same thing.
   - Do not replace semantic understanding with elaborate regexes, keyword lists, brittle heuristics, or ad hoc string scoring unless the human explicitly accepts that limitation.
   - When using an LLM, keep deterministic pre/post-processing around it: bounded input selection, typed output schema, validation, retries/fallbacks, fixtures/evals where practical, and visible failure if the LLM path is unavailable.
6. Add or update a focused test/check where practical. If no automated test is practical, define the explicit manual or executable check before editing.
7. Run the relevant failing or baseline check before editing when possible.
8. Implement the smallest change that should pass the check, following existing patterns and helper APIs.
9. Run the focused check again.
10. Run broader relevant checks when the change touches shared behavior, public interfaces, migrations, build configuration, or user-facing workflows.
11. Refactor only while keeping checks green and only within the requested scope.
12. Update `$rb-working-diary` at meaningful checkpoints with decisions, checks run, failures, and next steps.
13. Repeat in small increments until the requested change is complete.

## Required Behaviour

- Do not skip clarification when behaviour is still ambiguous.
- Do not claim success without running or explicitly naming the check that could not be run.
- Keep edits scoped to the requested behaviour unless a wider change is necessary and explained.
- Do not introduce dependencies, migrations, destructive operations, secret handling changes, or broad architecture changes without explicit approval.
- Do not rewrite working user changes; work with them or ask if they block the task.
- Prefer the repository's existing style, tests, frameworks, and abstractions over new patterns.
- For text-heavy code, keep a clear boundary between deterministic structure handling and semantic LLM judgment.
- Do not build complex regex/string heuristics for tasks whose acceptance criteria depend on understanding the text.

## Output

- what changed
- checks run and exact outcome
- checks not run and why
- residual risks or follow-up work
