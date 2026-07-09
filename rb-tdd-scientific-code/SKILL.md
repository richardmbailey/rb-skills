---
name: "rb-tdd-scientific-code"
description: "Use for test-driven implementation of scientific, numerical, modelling, simulation, or domain-sensitive code with tight verification loops over units, invariants, reproducibility, benchmark fixtures, stochastic behaviour, and numerical tolerances. For ordinary product/software changes, use $rb-implement-with-tests."
---

# /rb:tdd - test-driven implementation for scientific code

## Purpose

Implement scientific, numerical, modelling, simulation, or domain-sensitive changes with a tight feedback loop. For ordinary product/software changes, use `$rb-implement-with-tests`.

## Procedure

1. Confirm requirements from the human, a PRD, or an implementation plan. If material ambiguity remains, use `$rb-discuss` first.
2. Read `CONTEXT.md`, relevant docs, benchmark fixtures, tests, and source code for units, assumptions, invariants, tolerances, and trusted outputs. If these are missing or unclear, ask before implementing.
3. If the change implements multi-LLM-agent behaviour, also use `$rb-multi-agent-systems` to define testable agent contracts, tool boundaries, traces, evals, and reproducibility expectations.
4. Identify the smallest meaningful behaviour to test.
5. Define expected units, numerical tolerance, seed/reproducibility policy, and benchmark/provenance before writing the test.
6. Write or describe a failing test first.
7. Run the test where possible.
8. Implement the minimal code to pass.
9. Run the test again.
10. Add broader invariant, regression, or stochastic checks when the change could pass one fixture while violating the model.
11. Refactor while keeping tests green.
12. Update `$rb-working-diary` at meaningful checkpoints with decisions, checks run, failures, and next steps.
13. Repeat in small increments.

## Scientific test types

- units and dimensional consistency
- conservation or mass balance
- monotonicity
- limiting cases
- deterministic behaviour under fixed seeds
- statistical properties under stochastic components
- regression against benchmark fixtures
- numerical tolerance
- boundary behaviour
- data provenance and trusted-output comparison

## Required Behaviour

- Do not loosen tolerances merely to make a test pass; justify tolerance changes from numerical scale, domain knowledge, or benchmark uncertainty.
- Do not overfit to a single benchmark fixture when an invariant or property should hold more broadly.
- Do not silently change units, coordinate systems, sign conventions, random seeds, or calibration assumptions.
- Do not claim scientific validity beyond the checks actually run.
- Preserve existing validated outputs unless the human agrees they should change and the reason is documented.

## Output

- behaviour implemented
- scientific assumptions, units, tolerances, seeds, and fixtures used
- tests/checks added or run
- benchmark or invariant results
- remaining scientific uncertainty or validation gaps
