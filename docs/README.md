# Documentation guide

Use the active `SKILL.md` files for current agent instructions and the repository
[README](../README.md) for installation, selection and validation commands. This
index distinguishes current guides from design proposals and dated observations.
A report of a passing run applies to the candidate and environment it records;
it does not certify every later change or currently installed host.

## Current guides

| Topic | Start here |
| --- | --- |
| Claude installation, refresh, model choices and exclusions | [Claude compatibility](claude-code-compatibility.md) |
| Build tests, independently audit them and repair from one invocation | [Two-part test-suite system](test-suite-system/README.md) |
| Test coordinator commands, states and evidence checks | [Coordinator contract](../rb-audit-test-suite/references/coordinator.md) |
| A complete numerical build/audit/repair example | [Periodic heat example](../examples/periodic-heat/README.md) |
| Standard versus constrained execution | [Repository route guide](../README.md#safe-execution-standard-and-constrained-routes) |
| Constrained setup, source identity, schemas and launcher | [Runtime contract](../rb-safe-operation/references/runtime-contract.md) |
| Current fixed-policy/schema-3 migration | [Runtime 0.3 migration](project-policy-runtime-0.3-migration.md) |
| Visual explanation of the constrained workflow | [Safe-operation process](safe-operation-process.html) |
| Static phase conversion and its checks | [Converter explanation](safe-operation-converter.html) and [test explanation](safe-operation-converter-tests.html) |

The test coordinator is a small cooperative local command/state gate. It is not
the deferred general assurance runner, an LLM-dispatch service or the constrained
static-file runtime. The builder's host agent manages the audit and repair loop.

## Test-suite design and delivery history

- [Full assurance specification](rb-build-test-suite-specification/README.md)
  and [implementation plan](rb-build-test-suite-specification/IMPLEMENTATION_PLAN.md)
  describe the broader deferred runner, adapters and report engine. The delivered
  instruction edition and narrow audit coordinator do not complete that plan.
- [Specification review corrections](rb-build-test-suite-specification/review-resolution.md)
  and [independent recheck](rb-build-test-suite-specification/review-resolution-check.md)
  record the design review; [implementation evidence](rb-build-test-suite-specification/implementation-evidence/README.md)
  records the prototype's limited checks.
- [Instruction-edition validation](rb-build-test-suite-specification/instruction-edition-validation.md)
  and [review](rb-build-test-suite-specification/instruction-edition-review.md)
  record the initial skill delivery.
- [Original numerical trial](rb-build-test-suite-specification/numerical-trial.md),
  [first repeat](rb-build-test-suite-specification/repeat-trial/COMPARISON.md) and
  [second repeat](rb-build-test-suite-specification/repeat-trial-2/COMPARISON.md)
  explain supporting-code costs and historical regressions missed by regenerated
  suites. They are evidence for subsequent design changes, not current acceptance.
- [Lighter project-workflow revision](rb-build-test-suite-specification/proportionate-workflow-validation.md)
  records the move to native tools, compact notes and static reports.
- [Two-skill creation record](test-suite-system/validation.md),
  [log-evidence fixes](test-suite-system/fresh-review.md) and
  [single-invocation revision](test-suite-system/single-entry-workflow.md)
  record successive changes. Older sessions without command-log hashes cannot
  pass the current coordinator's acceptance gate.

## Other dated records

- [Documentation review, 15 November 2026](documentation-review-2026-11-15.md)

- [Discussion/interview changes, 8 October 2026](discussion-interviews-2026-10-08.md)
- [Skill refinement, 29 September 2026](skill-refinement-2026-09-29.md)
- [Codex-native provider acceptance](live-provider-acceptance.md), including the
  exact qualified runtime identity and limits; current service compatibility
  needs its own verification.
- [Runtime 0.2 migration](proposal-first-runtime-0.2-migration.md), retained as
  historical schema-1/schema-2 migration guidance and superseded for current runs.

Generated HTML explanations and trial reports are readable documentation, not
execution authority. Raw trial evidence may be local and ignored by Git; each
trial's README identifies its evidence and rerun commands. A source checkout
alone does not imply that every linked raw receipt was published with it.
