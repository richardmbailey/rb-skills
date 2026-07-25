---
name: "rb-tdd-scientific-code"
description: "Use for test-driven implementation of scientific, numerical, modelling, simulation, or domain-sensitive code with tight verification and review+fix loops over units, invariants, reproducibility, benchmark fixtures, stochastic behaviour, numerical tolerances, integration boundaries, and CI-equivalent checks. For ordinary product/software changes, use $rb-implement-with-tests."
---

# /rb:tdd - test-driven implementation for scientific code

## Purpose

Implement scientific, numerical, modelling, simulation, or domain-sensitive changes with a tight feedback loop. For ordinary product/software changes, use `$rb-implement-with-tests`.

## Procedure

1. Confirm requirements from the human, a PRD, or an implementation plan. If material ambiguity remains, use `$rb-discuss` first.
2. Read `CONTEXT.md`, relevant docs, benchmark fixtures, tests, coverage configuration, canonical CI commands, and source code for units, assumptions, invariants, tolerances, trusted outputs, and integration boundaries. If these are missing or unclear, ask before implementing.
3. If the change implements multi-LLM-agent behaviour, also use `$rb-multi-agent-systems` to define testable agent contracts, tool boundaries, traces, evals, failure cases, and reproducibility expectations.
4. Identify the smallest meaningful behaviour to test and the plausible scientific failure modes.
5. Define expected units, numerical tolerance, seed/reproducibility policy, benchmark provenance, test level, and acceptance criteria before writing the test.
6. Select the required test levels:
   - unit or property tests for mathematical logic, transformations, local algorithms, and invariants;
   - component or integration tests for solvers, data loaders, databases, files, external libraries, model pipelines, and coupled modules;
   - regression tests against trusted benchmark fixtures or published results;
   - statistical tests for stochastic components, using enough seeds or replications to test distribution-level behaviour;
   - end-to-end workflow tests when the scientific result depends on several coupled stages.
7. Write or describe a failing test first. For a defect, preserve evidence that the regression test fails against the defective behaviour.
8. Run the test where possible.
9. Implement the minimal code to pass.
10. Run the test again.
11. Add broader invariant, limiting-case, boundary, regression, integration, or stochastic checks when the change could pass one fixture while violating the model.
12. Inspect coverage tooling when already present. Ensure changed scientific branches, error paths, and model regimes are exercised; use diff coverage when available and do not reduce established thresholds without explicit approval.
13. Refactor while keeping tests green.
14. Update `$rb-working-diary` at meaningful checkpoints with decisions, checks run, failures, and next steps.
15. Repeat in small increments.
16. Run the closest available repository CI-equivalent command before completion, including relevant tests, linting, typing, builds, benchmark checks, or reproducibility checks. If the complete suite is impractical, run the largest relevant affordable subset and state exactly what was omitted.
17. Run a final review over the diff, tests, scientific assumptions, units, tolerances, seeds, benchmarks, provenance, integration boundaries, and validation gaps. Use `$rb-review-pr-or-diff` for substantial, risky, or cross-cutting changes; for small changes, perform the same review discipline inline.
18. Fix actionable review findings, rerun the relevant focused checks plus any affected invariant, regression, stochastic, integration, benchmark, coverage, and CI-equivalent checks, and re-review when findings were material.
19. Do not call the implementation scientifically complete until no blocking review findings remain, or the human explicitly accepts the residual scientific or validation risk.

## Scientific Test Types

- units and dimensional consistency
- conservation or mass balance
- monotonicity and ordering
- limiting and asymptotic cases
- deterministic behaviour under fixed seeds
- statistical properties under stochastic components
- regression against benchmark fixtures or trusted published values
- numerical tolerance and stability
- boundary and invalid-input behaviour
- calibration, coordinate-system, and sign-convention checks
- data provenance and trusted-output comparison
- integration between coupled model or data-processing stages
- performance or scaling checks where computational behaviour is part of correctness

## Test Integrity Rules

- Do not loosen tolerances merely to make a test pass; justify tolerance changes from numerical scale, domain knowledge, benchmark uncertainty, or a corrected model specification.
- Do not overfit to a single benchmark fixture when an invariant or property should hold more broadly.
- Do not silently change units, coordinate systems, sign conventions, random seeds, calibration assumptions, or benchmark provenance.
- Do not delete, skip, quarantine, or weaken a failing scientific test merely to make the suite green.
- Do not repeatedly rerun a stochastic or intermittent failure until it passes. Preserve seeds, sample sizes, execution order, platform details, and failing distributions; diagnose flakiness or statistical instability.
- Do not use a single fixed seed as the only evidence for a stochastic claim when the requirement is distributional.
- Do not mock away the numerical or scientific behaviour being validated. Use stubs at external boundaries while retaining realistic integration tests for important coupled paths.
- Do not claim scientific validity beyond the checks actually run.
- Preserve existing validated outputs unless the human agrees they should change and the reason is documented.
- Do not skip the final review+fix loop unless the human explicitly asks to stop before review.

## Output

- behaviour implemented
- scientific assumptions, units, tolerances, seeds, fixtures, benchmarks, and provenance used
- selected test levels and scientific failure modes covered
- tests added or run, including integration, boundary, negative, stochastic, and regression coverage
- benchmark, invariant, coverage, and CI-equivalent results
- review+fix findings, fixes applied, checks rerun, and accepted scientific risks
- checks not run and the remaining scientific uncertainty or validation gaps
