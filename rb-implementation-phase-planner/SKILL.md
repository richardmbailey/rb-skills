---
name: "rb-implementation-phase-planner"
description: "Use when creating, updating, executing, or reviewing implementation plans, coding phases, phase checklists, MVP/walking-skeleton plans, or verification gates. Emphasizes vertical-slice planning, fail-fast diagnostics, repo-appropriate stack choices, and [ ] -> [x] -> [v] task verification."
---

# RB Implementation Phase Planner

Use this skill for explicit implementation planning and phase execution.

## Core Defaults

- Prefer a walking-skeleton approach: build the thinnest runnable vertical slice first, then deepen it.
- Prefer vertical slices over horizontal/layer-first phases.
- Each implementation increment should preserve a runnable path through user input, core processing, output, validation, and persistence/audit when those concerns apply.
- Avoid silent fallbacks. Prefer fail-fast or fail-closed behavior with clear diagnostics.
- Only include degraded modes or fallback-like behavior when the human explicitly asks for them or when they are deliberate, visible, and auditable product states.
- Preserve the repository's existing language, framework, validation, test, and deployment conventions unless there is a clear reason to change them.
- For greenfield Python projects, or when the repo has no structured-data convention, consider Pydantic for structured data, validation, settings, and API contracts.
- For greenfield LLM-backed Python workflows, consider PydanticAI for LLM interfaces and typed agent/tool outputs, but verify this against project constraints and current official docs before implementation.
- For multi-LLM-agent systems, also use `$rb-multi-agent-systems` to define agent boundaries, tools, handoffs, state, observability, evals, retrieval, provider routing, and durability.
- For local LLM use, prefer the repository's existing provider/runtime. If the work is greenfield and the human has no preference, Ollama is a reasonable local default to propose rather than assume silently.

## Phase Checklist Convention

Every explicit implementation phase plan must use task checkboxes:

- `[ ]` planned
- `[x]` implemented
- `[v]` verified

Rules:

1. Mark a task `[x]` only after completing the implementation work.
2. After all tasks in the phase are `[x]`, run a second verification pass over every task.
3. Mark a task `[v]` only after confirming its behavior with a relevant automated test or explicit verification check.
4. If a task has no verification path, add a test/check or document why the best available check is manual before marking it `[v]`.
5. Do not declare the phase complete until every task is `[v]`.
6. For multi-phase work, create a separate implementation file for each phase.
7. Keep the main implementation plan as an overview; put the granular task list, verification notes, and phase-specific test plan in the phase file.
8. Granular tasks should be small enough that completion and verification are unambiguous.

## Planning Requirements

When drafting or revising an implementation plan:

1. Identify the walking skeleton before detailed phase planning.
2. Make Phase 1 a runnable end-to-end slice, even if some internals are minimal.
3. Keep horizontal foundation work only as large as the first vertical slice requires.
4. State exit criteria in terms of user-observable workflow and validation checks.
5. Include fail-fast diagnostics for missing dependencies, provider failures, validation errors, unsupported states, and policy blocks.
6. Record the existing stack and project conventions first. For greenfield Python/LLM systems, propose structured/LLM stack choices such as Pydantic, PydanticAI, and Ollama only as defaults to confirm, not as mandatory replacements.
7. For multi-LLM-agent systems, record the stack choice, agent/tool boundaries, handoffs, state, tracing/evals, retrieval, provider routing, and durability plan from `$rb-multi-agent-systems`.
8. Include tests or verification checks for every task.
9. For each phase, create or reference a dedicated phase implementation file with:
   - phase goal
   - scope and non-scope
   - dependencies
   - granular `[ ]` task checklist
   - verification checklist
   - tests to add or run
   - phase exit criteria

## Execution Requirements

When executing a phase:

1. Work through `[ ]` tasks in order unless a dependency requires reordering.
2. Update each completed task from `[ ]` to `[x]`.
3. Run the relevant test/check loop as tasks are completed.
4. When all tasks are `[x]`, verify every task again with recorded tests or checks.
5. Add missing tests/checks before marking unverified work verified.
6. Update verified tasks from `[x]` to `[v]`.
7. Report any task that cannot be verified, with the diagnostic and next fix.

## Review Requirements

When reviewing an existing implementation plan:

- Check whether Phase 1 is truly vertical and runnable.
- Flag horizontal phases that build isolated layers without user-visible workflow progress.
- Flag fallback paths that may hide defects.
- Flag stack or dependency changes that ignore existing repo conventions.
- For multi-LLM-agent plans, confirm `$rb-multi-agent-systems` concerns are addressed explicitly.
- Flag tasks without test or verification coverage.
- Check whether task status uses `[ ]`, `[x]`, and `[v]` correctly.
- Confirm no phase is marked complete unless all tasks are `[v]`.

## Output

- walking skeleton summary
- proposed phases with `[ ]` task lists
- stack/dependency assumptions and which are existing vs proposed
- verification plan and phase exit criteria
- risks, open questions, and decisions needed from the human
