---
name: "rb-diagnose"
description: "Use when a bug, regression, failing test, flaky test, or surprising output needs root-cause investigation before choosing a fix. Do not use for general diff review or when the cause and requested fix are already agreed."
---

# /rb:diagnose - disciplined debugging

## Purpose

Use this for bugs, regressions, surprising outputs, failing tests, or flaky tests.

## Procedure

1. State expected behaviour.
2. State observed behaviour.
3. Identify the smallest reproducible case.
4. Build or find a feedback loop and run it when possible.
5. Capture the failing output, input, environment, seed/configuration, execution order, timing, platform, and affected version or commit when relevant.
6. Localise the failure by reading surrounding code, tests, recent changes, logs, configuration, and integration boundaries.
7. Form hypotheses.
8. For text-handling failures, test whether the bug comes from using deterministic string parsing for a semantic natural-language task:
   - Deterministic parsing is plausible for stable syntax, exact delimiters, structured formats, known IDs, URLs, logs, or protocol fields.
   - Semantic understanding likely needs an LLM when the failure involves meaning, intent, relevance, classification, summarisation, ambiguous wording, natural-language extraction, rubric judgment, entity/claim matching, or semantic equivalence.
   - Treat brittle regexes, keyword lists, and fuzzy string scoring as suspects. This approach should only be used to infer meaning in very simple predictable cases, never for free unstructured text.
9. For multi-LLM-agent systems, also use `$rb-multi-agent-systems` when localising failures across agents, tools, state, retrieval, provider routing, budgets, or recovery.
10. Test hypotheses one at a time. Use the smallest discriminating experiment rather than changing several variables together.
11. For intermittent failures, do not rerun until green. Preserve the failing seed, ordering, timing, concurrency, environment, and output; determine whether the issue is race-dependent, state-leaking, statistically unstable, resource-dependent, or externally caused.
12. Use `$rb-working-diary` only when its trigger conditions apply and the human has authorized durable continuity. Do not write diary entries for an isolated one-turn diagnosis.
13. Propose a fix only after evidence supports it.
14. A bug fix must normally include an automated regression test that fails against the defective behaviour and passes after the fix. Specify the test level where the regression escaped: unit, integration, contract, migration, workflow, stochastic, or end-to-end. Do not create or edit that test during diagnosis-only work.
15. If automated regression coverage is genuinely infeasible, document the technical reason, define the best executable or manual check, and state the remaining regression risk. Do not silently substitute a lint, build, import, or smoke check for behavioural coverage.
16. If the human asks for implementation, use `$rb-implement-with-tests` or `$rb-tdd-scientific-code` for the fix path after diagnosis.
17. Explain the root cause, why the regression escaped existing coverage, and which regression test should prevent recurrence. Report its result only when implementation was requested.

## Required Behaviour

- Do not shotgun changes.
- Do not hide the bug with a silent fallback or broader exception handling unless that is the explicit product requirement.
- Do not claim a bug is fixed without running or specifying the regression test and broader check.
- Do not delete, skip, quarantine, weaken, or repeatedly rerun a failing test merely to obtain a green result.
- Do not weaken assertions, expected errors, tolerances, seeds, coverage thresholds, or fixtures unless evidence shows the prior expectation was wrong.
- Do not make unrelated refactors while diagnosing.
- Do not edit implementation or tests during diagnosis-only work. Make those changes only when the human asks for a fix and the implementation skill owns the change.
- Preserve user changes in the worktree.
- Do not "fix" semantic text failures by adding more regex layers unless the task is truly syntax-bound. Prefer LLM comprehension of text in all but the most simple predictable cases.

## Output

- expected vs observed behaviour
- minimal repro or best available feedback loop
- hypotheses tested and results
- root cause with evidence
- why existing tests did not catch the defect
- proposed fix and automated regression-test level
- regression test result before and after the fix when implementation was requested
- checks run, checks not run, and residual risk
