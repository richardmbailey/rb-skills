---
name: "rb-implement-with-tests"
description: "Use for one bounded ordinary software or product change after requirements are clear, with focused tests, executable checks, and a final review+fix loop. Do not own multi-phase planning or plan-status tracking; use $rb-execute-plan for that."
---

# /rb:implement - implement with tests

## Purpose

Implement one agreed ordinary change in small verified increments. This skill owns the detailed code, test, and task-level review loop; it does not sequence multi-phase work or maintain plan-wide status.

Use `$rb-discuss` first when material behaviour, interface, edge cases, compatibility, or test expectations are unclear. Use `$rb-execute-plan` when the user asks to refine, sequence, continue, or track an existing implementation plan or phase. When `$rb-execute-plan` selects one ordinary task, use this skill to implement that task and return evidence; the plan owner updates `[ ]`, `[x]`, and `[v]` status. Use `$rb-tdd-scientific-code` instead when the selected change is scientific, numerical, modelling, simulation, or domain-sensitive enough to need scientific invariants.

## Procedure

1. Confirm the one agreed requirement, selected plan task, or issue. If the request contains several tasks that need sequencing or requires plan-state tracking, route to `$rb-execute-plan` before editing.
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
12. Update `$rb-working-diary` only when the implementation is long-running, context-heavy, or part of accumulated project work that needs cross-session continuity.
13. Repeat in small increments until the requested change is complete.
14. Run a final review over the diff, tests, docs, and behavior. Use `$rb-review-pr-or-diff` for substantial, risky, or cross-cutting changes; for small changes, perform the same review discipline inline.
15. Fix actionable review findings, rerun the relevant focused and broader checks, and re-review when findings were material.
16. Do not call the implementation complete until no blocking review findings remain, or the human explicitly accepts the residual risk.

## Required Behaviour

- Do not skip clarification when behaviour is still ambiguous.
- Do not create, resequence, or mark a multi-phase plan complete. Return implementation and verification evidence to `$rb-execute-plan` when it owns the surrounding plan.
- Do not claim success without running or explicitly naming the check that could not be run.
- Keep edits scoped to the requested behaviour unless a wider change is necessary and explained.
- Do not introduce dependencies, migrations, destructive operations, secret handling changes, or broad architecture changes without explicit approval.
- Do not rewrite working user changes; work with them or ask if they block the task.
- Prefer the repository's existing style, tests, frameworks, and abstractions over new patterns.
- For text-heavy code, keep a clear boundary between deterministic structure handling and semantic LLM judgment.
- Do not build complex regex/string heuristics for tasks whose acceptance criteria depend on understanding the text.
- Do not skip the final review+fix loop unless the human explicitly asks to stop before review.

## Output

- the selected task or requirement completed and what changed
- checks run and exact outcome
- review+fix findings, fixes applied, and checks rerun
- checks not run and why
- residual risks or follow-up work
