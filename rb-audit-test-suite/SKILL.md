---
name: "rb-audit-test-suite"
description: "Use when independently testing whether a project's tests detect specified defects, preserve regressions and propagate failures. Pair with rb-build-test-suite for reliable test-suite construction. Exclude routine test runs, general diff review and agent-skill evaluations."
---

# RB Audit Test Suite

Assess the tests by running them against known behaviours and deliberate faults.
Produce executable evidence of gaps and retain the resulting regression cases.
A passing suite alone does not establish that its assertions detect wrong results.

## Selection and ownership

Use this skill for a direct test-suite audit or the paired workflow requested
through `$rb-build-test-suite`. A direct audit returns findings and executable
challenges; it does not authorize repairs to application code or developer tests.
If the user requests construction or repair of the suite, follow the bounded
[build-and-audit loop](references/paired-workflow.md). Do not create a third LLM
orchestrator merely to repeat the builder's and auditor's judgements.

The host invokes a separate auditor through the platform's documented delegation
tool. Give it a fresh task packet rather than the builder's conversation. The host
may act as builder; it must not claim to be its own independent auditor. Reuse an
existing distinct auditor for repair rounds, retaining its original challenge
plan. If delegation is unavailable, report the required audit as incomplete.
Codex and Claude Code use their own documented agent tools and delegation policy;
this skill does not provide an agent API or authorize new paid services.

The builder owns production tests. The auditor owns challenge tests and findings.
Both use disposable copies for intentional defects. The host owns dispatch and
scope; deterministic commands own execution outcomes and loop state. Shared files
and different agent names do not establish enforced write or oracle isolation.

## Inputs

Read requirements, interfaces, numerical bounds, known failures and saved test
commands. Obtain the candidate source/test/configuration identity and current
policy. Identify required fault classes and historical regressions before running
challenges. Missing scientific criteria or disputed requirements remain explicit
gaps; do not infer expected values from the implementation under test.

Read [challenge design](references/challenge-design.md). For numerical code, also
use the builder's scientific guidance and independently derived reference values.
The [numerical example](examples/numerical/README.md) supplies an executable
healthy/weak/repaired demonstration; its model-specific values are not universal
numerical tolerances.

## Procedure

1. Before reading the builder's tests, derive a bounded challenge plan from
   requirements and historical failures. Record requirement IDs, fault classes,
   independent oracles and expected observations. Then inspect the code, tests,
   fixtures, mocks, exclusions and execution entry point. Label later discoveries.
2. Review actual test collection and execution. Check exact IDs and imported/build
   origins, nonempty selection, skipped/xfail outcomes, assertions, tolerances,
   randomness controls and real integration boundaries. Identify tests that pass
   without exercising or checking the claimed behaviour.
3. Write deterministic audit tests. Each challenge establishes that the healthy
   control passes and the targeted defect fails for a relevant assertion. Keep
   exact expected test identities and raw native results. A crash, import error,
   missing test or timeout is an invalid experiment, not successful detection.
   Audit tests themselves return zero only when those expectations are satisfied.
4. Run all required historical regression challenges. Keep an explicit disposition
   for each inherited failure, including why a case does not apply to a changed
   interface. Do not replace an exact known failing input with a nearby example.
   Reject removal or weakening of a required historical test to obtain a pass.
5. Exercise the saved completion command with an early failed test, failed lint or
   type check, unavailable required tool and timeout, where those components exist.
   A later successful command cannot erase an earlier failure. Use a fresh owned
   temporary directory and retain partial output. Do not alter the real candidate
   to simulate these failures.
6. Return a candidate-bound review with requirement, counterexample, raw evidence,
   proposed correction and blocking status for each finding. Distinguish a test
   defect, application defect, invalid challenge and unresolved requirement.
   The builder repairs authorized tests; the auditor reruns affected challenges
   and any previously required controls the repair could invalidate.
7. For a paired run, use the bundled [local coordinator](references/coordinator.md)
   and [script](scripts/test_loop.py), or existing CI that demonstrably enforces
   the same conditions. A recorded tool exit is not enforced failure propagation.
   Neither a semantic review nor a green report can override a required failure.
8. Freeze the final candidate, run all required project and audit commands, and
   review that exact result. Any later change invalidates affected evidence.
   Missing or altered command logs block acceptance. Keep raw audit evidence in
   retained CI artifacts when using an ephemeral runner.
   Report verified scope, unresolved findings, surviving faults, invalid cases,
   unrun checks and the coordinator's actual terminal state.

## Completion and limits

The default paired limit is three total assessment rounds, including the initial
assessment. Exhaustion, cancellation, unavailable expertise or stale evidence
ends the run without verified acceptance. Preserve failures across all rounds.
Do not repeatedly run an unchanged failing candidate until it happens to pass.

A local `verified_local` result means the declared commands and host-attested
independent review met the frozen local policy. It is not proof of exhaustive
correctness, authenticated reviewer identity, a sandbox or protected CI approval.
The host must actually observe the independent invocation; typing a reviewer ID
into JSON does not create independence. Retain any limitations of shared access.

Deliver the executable audit tests, challenge/requirement map, findings, receipts
and exact rerun commands. Reuse the builder's evidence note and HTML report for a
paired task rather than creating a second report application. The standalone
[behavioural evaluation plan](evals/eval-plan.json) tests this skill's routing and
judgements; its definitions are not evidence that those agent trials ran.

Invoke `$rb-audit-test-suite` in Codex or `/rb-audit-test-suite` in Claude Code.
