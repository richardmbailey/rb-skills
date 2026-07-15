# Phase 3: Instruction-Body Cleanup

## Phase Goal

Remove duplicated, irrelevant, stale, or generic instructions from the highest-priority skill bodies while preserving the decisions, validations, and safety boundaries that make each skill useful.

## Scope

- `rb-start-project`
- `rb-execute-plan`
- `rb-multi-agent-systems`
- `rb-setup-local-agent-skills`
- `rb-working-diary`
- `rb-discuss`
- `rb-create-implementation-plan`
- targeted light cleanup in other skills only when a specific duplicate was identified during review

## Non-scope

- Rewriting healthy output contracts for stylistic consistency.
- Changing `rb-wiki` or using it as the destination for removed text.
- Removing safety or validation instructions merely to reduce line count.

## Dependencies

- Completed frontmatter routing changes from Phases 1 and 2.
- Baseline and revised routing results.
- A deletion log classifying removed instructions as duplicate, generic, obsolete, relocated, or intentionally retained.

## Task Checklist

### `rb-start-project`

- [v] Collapse repeated workflow routing into one authoritative routing table or sequence.
- [v] Keep the onboarding questions, approval boundary, and handoff output once each.
- [v] Remove repeated prose that restates the same discuss-plan-execute-implement-review chain.
- [v] Confirm the shorter body still routes bugs, scientific work, planning, orientation, architecture, and review correctly.

### `rb-execute-plan`

- [v] Retain `[ ]`, `[x]`, and `[v]` semantics, walking-skeleton guidance, phase files, verification gates, and review+fix rules.
- [v] Remove general Pydantic, PydanticAI, and Ollama defaults from the cross-domain plan-execution body.
- [v] Remove duplicated review requirements while preserving one complete phase-completion gate.
- [v] Keep multi-agent and semantic-text concerns as concise conditional routes to the appropriate skills.

### `rb-multi-agent-systems`

- [v] Keep the capability-scaling decision: deterministic tool, embedded capability, split agent, or orchestration layer.
- [v] Keep contracts, state ownership, tool permissions, failure containment, budgets, observability, evals, and durability decisions.
- [v] Move detailed framework/product selection guidance into `rb-multi-agent-systems/references/framework-selection.md` if it remains useful.
- [v] Add a direct instruction explaining exactly when to read the new reference.
- [v] Remove repeated preferred-stack statements from the main body.
- [v] Require official documentation checks before concrete version-sensitive implementation.

### `rb-setup-local-agent-skills`

- [v] Determine whether the legacy `_rb-agent-skills` layout is still used.
- [v] If unused, remove legacy routing and commands.
- [v] If still needed, move legacy details into a conditional reference and keep only the discovery decision in `SKILL.md`.
- [v] Keep current flat-repository source-of-truth and symlink verification behaviour prominent.

### `rb-working-diary`

- [v] Align the body with the narrowed durable-continuity trigger.
- [v] Keep the tiny-task exclusion, secret-handling rule, compact entry shape, and checkpoint guidance.
- [v] Remove generic prose that does not help decide whether, when, or what to write.

### `rb-discuss` and `rb-create-implementation-plan`

- [v] Replace generic instructions such as “restate” or “ask questions if needed” with material decision categories.
- [v] Keep one-question-at-a-time behaviour only where user input is genuinely required.
- [v] Ensure `rb-discuss` stops after requirements clarity and `rb-create-implementation-plan` produces the durable top-level plan.
- [v] Remove duplicate planning steps that blur the handoff between the two skills.

### Cross-cutting cleanup

- [v] Standardize the deterministic-structure versus semantic-meaning rule into a concise form in each skill that genuinely needs it.
- [v] Do not create a shared reference that breaks standalone skill portability.
- [v] Review repeated `$rb-working-diary` instructions and keep them conditional on durable continuity value.
- [v] Check `rb-continue-project` and `rb-create-skill-evals` for description/body repetition after frontmatter changes.
- [v] Review `rb-research-question-gate` decision-state repetition; trim only when stop/revise/proceed semantics remain unambiguous.
- [v] Record body line-count changes as information, not as the success metric.
- [v] Run a final semantic diff review for every deletion.

## Verification Checklist

- [v] Every deleted instruction is classified and justified.
- [v] Safety, approval, failure, and validation requirements remain represented.
- [v] Moved reference material is directly linked from the owning `SKILL.md` with a clear read condition.
- [v] Modified skills remain under 500 lines.
- [v] Routing cases still pass after body cleanup.
- [v] Outcome cases cover material body changes.
- [v] Custom validators for `rb-explain-diff`, `rb-where-are-we`, and `rb-create-skill-evals` still pass their existing checks.
- [v] `git diff --check`, metadata validation, and `rb-wiki` protections pass.
- [v] Phase review+fix is complete.

## Execution Record

- Deletions, relocations, retained contracts, and line-count changes are
  recorded in
  `evals/skill-routing/results/2026-07-15-instruction-cleanup-log.md`.
- `evals/skill-routing/validate_instruction_contracts.py` passes the revised
  skills and a known-good fixture and rejects the deliberately bad fixture.
- Version-sensitive framework guidance and legacy-layout commands now live in
  directly linked, read-on-demand references.
- Routing remains 288/288 after the body cleanup because the evaluated
  frontmatter is unchanged by those instruction-only edits.

## Phase Exit Criteria

- The high-priority skills contain one clear version of each important instruction.
- Cross-domain skills no longer impose unrelated technology defaults.
- Detailed conditional guidance uses progressive disclosure without breaking portability.
- Behavioural and deterministic checks show no lost contract.
- Every task is `[v]`, review findings are fixed, and `rb-wiki` remains unchanged.
