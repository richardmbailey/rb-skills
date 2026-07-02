---
name: "rb-diagnose"
description: "Use for disciplined debugging of bugs, regressions, surprising outputs, or failing tests. Separates evidence gathering from fixes and preserves a reproducible check."
---

# /rb:diagnose - disciplined debugging

## Purpose

Use this for bugs, regressions, surprising outputs, or failing tests.

## Procedure

1. State expected behaviour.
2. State observed behaviour.
3. Identify the smallest reproducible case.
4. Build or find a feedback loop and run it when possible.
5. Capture the failing output, input, environment, seed/configuration, and affected version or commit when relevant.
6. Localise the failure by reading surrounding code, tests, recent changes, logs, and configuration.
7. Form hypotheses.
8. For text-handling failures, test whether the bug comes from using deterministic string parsing for a semantic natural-language task:
   - Deterministic parsing is plausible for stable syntax, exact delimiters, structured formats, known IDs, URLs, logs, or protocol fields.
   - Semantic understanding likely needs an LLM when the failure involves meaning, intent, relevance, classification, summarisation, ambiguous wording, natural-language extraction, rubric judgment, entity/claim matching, or semantic equivalence.
   - Treat brittle regexes, keyword lists, and fuzzy string scoring as suspects when they are being used to infer meaning.
9. For multi-LLM-agent systems, also use `$rb-multi-agent-systems` when localising failures across agents, tools, state, retrieval, or provider routing.
10. Test hypotheses one at a time.
11. Update `$rb-working-diary` with repro details, hypotheses tested, findings, and remaining risks when the diagnosis is non-trivial.
12. Propose a fix only after evidence supports it.
13. Add or update a regression test/check before or alongside the fix when practical.
14. If the human asks for implementation, use `$rb-implement-with-tests` or `$rb-tdd-scientific-code` for the fix path after diagnosis.
15. Explain the root cause.

## Required behaviour

- Do not shotgun changes.
- Do not hide the bug with a silent fallback or broader exception handling unless that is the explicit product requirement.
- Do not claim a bug is fixed without running or specifying a check.
- Do not make unrelated refactors while diagnosing.
- Preserve user changes in the worktree.
- Do not "fix" semantic text failures by adding more regex layers unless the task is truly syntax-bound.

## Output

- expected vs observed behaviour
- minimal repro or best available feedback loop
- hypotheses tested and results
- root cause with evidence
- proposed fix and regression check
- checks run, checks not run, and residual risk
