# Independent review of the instruction edition

Reviewed the active `rb-build-test-suite/` instructions, references, schemas,
metadata, eval manifest and relevant repository validation integration. This
review was derived from those sources before consulting any earlier verdict.
The deferred implementation under `development/` was excluded.

## Findings

1. **[P2] Make verifier dispatch conditional on the selected acceptance policy.**
   `rb-build-test-suite/SKILL.md:56-60` and `:84-85` unconditionally instruct the
   agent to obtain a separate verifier and treat unavailable delegation as a gap.
   The catalogue permits reasoned non-selection, and scientific validation
   explicitly establishes independent verification as the scientific-core default.
   On a non-scientific project with justified independent-verification exclusion,
   these competing instructions can cause unnecessary delegation or prevent
   completion despite satisfying the accepted policy. Condition dispatch and
   required-gap treatment on selected/required independence, retaining the
   scientific-core rule. Distinguish this from mandatory change-impact review.
   Add an outcome case for justified non-scientific non-selection alongside the
   existing missing scientific verifier case.

2. **[P2] Define how a permitted retry determines the logical module outcome.**
   `references/module-interface.md:181-187` allows one transient read-only
   transport retry and retains both attempts. `references/evidence-and-report.md:47`
   records every attempt, while `:106-110` aggregates module assessments without
   defining how attempts produce one module assessment. An error then successful
   complete retry can therefore remain inconclusive under one implementation and
   pass under another. A careless last-attempt rule could hide contradictory
   evidence. Define an effective logical-module result before capability
   aggregation: a qualifying transport-only failure may be superseded by a
   complete validated retry with unchanged inputs, criteria and authority, but
   demonstrated violations and uncertain external effects cannot be superseded.
   Retain all attempt records and expose their history. Add healthy retry,
   contradictory-result and identity-change evaluation cases.

3. **[P2] Run schema contract checks against the active distributed files.**
   `docs/rb-build-test-suite-specification/checks/test_schemas.py:15-16` loads the
   design-directory schema copies. Its catalogue check also reads the design
   catalogue. `.github/workflows/validate-skills.yml` does not execute this test
   module. Consequently the active closed records and references can break while
   repository CI remains green. Parameterize the check paths or make the active
   skill package their default; wire those small schema tests into CI with format
   assertion dependencies. This checks the supplied contracts without introducing
   an executable test-suite runner. A separate check of archived design copies is
   optional, and must be named distinctly.

## Checks and limits

- Applied the review and skill-authoring guidance, including the authorized
  simplify-language audit and the agent-boundary guidance. The findings above
  concern observable workflow consequences, rather than stylistic preference.
- Independently ran the existing 14 non-catalogue schema tests against the active
  schema package using a local registry and format checker: all passed. Separately
  compared the active catalogue headings to the exact ordered schema enum: all
  43 IDs matched, with no added scientific pseudo-capabilities.
- Reviewed all capability entries for construction, evidence, applicability and
  authority boundaries. Found no additional actionable catalogue defect.
- No active schema/prose incompatibility was demonstrated by the shape checks.
  Cross-record truth, reference integrity, identity matching and gate computation
  are explicitly semantic obligations, not claims that JSON Schema enforces them.
- The eval manifest is a plan, not completed behavioural evidence. No live skill
  trials, target-project construction, operational observations, browser report
  validation, or protected CI deployment were run. Those remain qualification
  risks and are already disclosed by this edition.
- Did not rerun unrelated constrained-runtime tests or inspect the deferred runtime.
  Missing bundled executables are an intentional boundary, not a finding. The
  instructions correctly require generated target-project tools to be qualified
  before their results can support acceptance.

The edition is coherent enough to construct a project-local workflow once the
three issues above are repaired. This review does not establish that any such
workflow has already been built or run successfully.

## Focused recheck after repairs

All three findings are resolved in the current instruction edition.

- Steps 5 and 10 now condition independent verification on the selected project
  policy, preserve its scientific-core default and retain change-impact review
  after justified non-selection. The reference distinguishes independent methods
  from methods that require reviewer delegation. The new non-selection decision
  probe tests the consequential distinction without claiming a live outcome.
- The module and reporting contracts now derive one logical-module outcome before
  capability aggregation. Only the qualified, complete, unchanged transport retry
  may determine that outcome. Earlier violations, uncertain effects and changed
  bindings cannot be superseded; both attempts remain visible. The two new retry
  decision probes cover permitted recovery and forbidden hiding of a failed
  assertion. They are correctly identified as decision probes, not execution
  evidence. The instruction contract protects the operative aggregation language.
- The schema tests now default to `rb-build-test-suite/schemas/` and its active
  reference catalogue. `RB_TEST_SUITE_PACKAGE_ROOT` provides an explicit override.
  The CI step installs the dedicated pinned schema-validation requirement, runs
  those tests with failure-preserving pipe handling, and contributes its outcome
  to the final validation gate. It does not add a target-project runtime.

Reviewed the changed control text using the authorized simplify-language audit;
no remaining material ambiguity was found within these repairs. Reused the
parent's reported passing 15 packaged-schema checks after confirming their
current default targets and CI wiring. Did not rerun that unchanged passing
suite or expand into the deferred implementation. The original limitations on
behavioural trials and target-project qualification remain. No blocking finding
or material unanswered question remains within this review's scope.
