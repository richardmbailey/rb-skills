# Build tests with little supporting code

Use this workflow for a project whose required checks and evidence can be handled
by its existing tools and the host agent. It changes the representation and amount
of infrastructure, not the requirements that must pass. Preserve an already
adopted assurance contract; simplifying it needs an explicit policy decision.

## Reuse before building

1. Inspect the existing test command, task runner, CI, logs and report tools.
   Reuse their discovery, fixtures, environment and failure exits. Do not replace
   pytest, coverage, Ruff or an existing CI job with an agent-written scheduler.
2. Put most new code in substantive tests. First use native outputs such as JUnit,
   coverage JSON/HTML and lint diagnostics. Record their locations and actual
   outcomes in one [evidence note](../assets/project-checks.md), or equivalent
   existing project documentation. Do not convert every output into a second schema.
3. Add a thin command wrapper only when needed for repeatability. It must preserve
   each required failure, missing check and partial output; a final report command
   cannot mask an earlier failure. Test success, failure and unavailable-tool paths
   when introducing such a wrapper. Existing verified orchestration needs no new one.
4. Add an adapter only for a named unmet boundary: for example exact test-ID
   reconciliation or actual import origin absent from native output. State why
   native tooling is insufficient, keep the adapter narrow and test a defective
   and healthy case. Do not promote the numerical trial's bespoke harness to a
   general implementation; its remaining qualification gaps were explicit.

A small project normally needs tests, tool configuration and perhaps one saved
command. The host can write the evidence note and static HTML summary without
adding a report application, schema packager, plugin registry or separate audit
service. Record any justified additional infrastructure and the requirement it serves.

## Evidence that must still exist

Keep this information together, linking raw files rather than duplicating them:

| Information | Minimum sufficient record |
| --- | --- |
| Acceptance | Requirements, failure cases, justified scientific bounds and required checks decided before the run |
| Capability selection | All 43 stable IDs accounted for once, with reasons and required flags; explicit IDs may share a reason |
| Change impact | Current changed paths/inputs, affected behaviours, requirement/test mapping, reviewed exclusions and unresolved gaps |
| Candidate | Commit plus dirty diff and relevant untracked inputs, or an equivalent content manifest; include tests, config and scientific data |
| Execution | Environment/tool versions, exact command and working directory, times, exits, logs and actual artifact locations |
| Identity and collection | Actual first-party import/build origin from execution; nonempty expected test IDs reconciled with actual executed outcomes, including skipped/xfail cases |
| Static scope | Checked paths, effective configuration, suppressed/excluded regions and limits of the type claim |
| Review | Actual verifier invocation/session reference when available, supplied context, reviewed candidate, oracle sources, findings and resolution |
| Completion | Final identity comparison, required failures/gaps, optional limitations and saved rerun command |

Do not accept a commit hash alone for a dirty working tree or a passing test count
in place of exact identities. A native report is sufficient only if it contains
the needed information; otherwise use a narrow capture hook or retain a gap.
The host reviews meaning and links; deterministic commands establish syntax,
hashes, collection and exits. No semantic keyword scoring is needed.

Preserve the raw logs and assertion XML behind mutation results, not only a
summary saying all mutants failed. Keep evidence in a new run directory. If raw
files cannot be bundled, link their actual location and explain access restrictions.
Never fabricate a successful receipt or erase a failed attempt.

## Scientific checks that justified their cost in the trial

- Pair invariants with independent expected values or relations. A model can
  conserve total mass while moving it in the wrong direction or at the wrong rate.
- Test the actual export/reload boundary, including units. Static lint and typing
  can pass code with scientifically wrong equations or conversions.
- Derive numerical bounds and check convergence in a stated regime. Test adjacent
  floating-point values near stability limits, cancellation in time differences,
  underflow/overflow in step counts and final-time inclusion where applicable.
- Use bounded property generation, but let independent review challenge generator
  ranges and numerical extremes. A passing sample is not exhaustive evidence.
- Start mutation checks with a few explicit plausible defects in disposable copies
  and a healthy control. Keep assertions meaningful; distinguish killed, surviving,
  invalid and timed-out cases. Use an established mutation tool for a larger campaign.
- Attribute independent design and later code inspection separately. The trial's
  two numerical bugs were found after the initial green suite, not by its original
  requirements-first tests. Do not turn this into a measured skill-lift claim.

## Keep test infrastructure from contaminating the result

Use new, owned temporary directories. Pytest can discover ancestor configuration
and conftest hooks even in a nested temporary fixture. When testing a standalone
child project, provide its own config and explicitly bound discovery, for example
with a fixture-local `-c` and `--confcutdir`; assert the expected IDs and origin.
For tests of inherited configuration, keep inheritance deliberate and test it.
Do not disable project plugins or existing discovery indiscriminately.

When using `--basetemp`, choose a fresh path owned by the current trial: pytest
may clear it. Do not clean unrelated shared caches to hide warnings. Use finite
timeouts for spawned commands and preserve partial output on interruption.

Coverage of a parent process does not automatically include child CLI processes.
Either configure supported child-process coverage or report the unmeasured paths
alongside real CLI integration results. Do not weaken a required coverage threshold
or treat separate CLI assertions as proof that measured branch coverage increased.

## Report and completion

Produce a small standalone HTML summary from the note or a suitable existing
reporter. Include scope, current candidate, required outcomes, numerical reference
results where relevant, independent findings, limitations and links to raw evidence.
No chart, filter, sort control or JavaScript is needed unless the project requires it.
Use escaped text, verify summary values and relative links, and check actual offline
rendering with JavaScript disabled. If required rendering cannot be checked, record
that report gap separately from the observed code-test results.

The project workflow does not require the full JSON schemas, generated module
plans, a custom renderer or a reusable host adapter. Their absence is not a gap
in a claim that the project's specified checks passed. Existing mandatory policies
and required checks still govern completion. Never label this lighter evidence as
full assurance-contract conformance or a protected release decision.

Record the adopted completion rule for subsequent ordinary, scientific, plan-based
and direct changes. Revisit affected capability dispositions and the current impact
map, run the required saved checks, and compare final identities before claiming
verification. A quick profile cannot waive a required deep check. Unresolved
coverage, stale evidence, missing required independent review or an actual failure
keeps that outcome incomplete or failed.

## Paired test-suite audit

Every build or extension uses [rb-audit-test-suite](../../rb-audit-test-suite/SKILL.md).
The host invokes it and manages authorized repairs within the original builder
invocation; the user does not manually alternate skills. Explicit user limits
can narrow the deliverable but cannot turn a missing audit into verified acceptance.
Retain exact known-failure fixtures, then have the auditor demonstrate that the
suite rejects their deliberate reintroduction. Ordinary tests and audit tests run
as code. The host dispatches the distinct reviewer and the local coordinator
combines native command results with the candidate-bound review. Reuse the
existing evidence note and HTML; do not build another report package.
