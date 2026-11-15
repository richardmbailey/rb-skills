# Assurance for every project change

A saved suite must be used on later changes, and its report must explain whether
those changes were actually assessed. A clean command exit is insufficient when
tests imported an old package, omitted a new behaviour, or left changed code
outside a static tool's checking scope.

This contract resolves the four findings in the
[independent assurance review](independent-assurance-review.md). It is normative
for the specification, module interface, evidence/report contract and plan.
It adds no catalogue entries. The original review remains historical evidence.

## 1. Adopt the suite in ordinary development

On suite construction, the host agent must save the runner command and acceptance
policy in the project's existing implementation and completion instructions.
Preserve unrelated instructions and managed-file ownership. Record the locations
and hashes in `Adoption.instruction_artifact_ids`. The adoption record names the
supported workflows: ordinary implementation, scientific implementation and
plan execution. A project that does not use one of these workflows records that
boundary in its policy; it does not claim that route is integrated.

For each subsequent generated code, configuration or scientific-data change,
the implementation agent must update the change-impact record, invoke the saved
runner with the required selections, and inspect its evidence before claiming
verification. Invoke the existing suite; suite construction is selected again
only when tests or infrastructure need extension. Completion instructions must
also apply when an agent works directly without a named implementation skill.

The runner evaluates the full required policy, even when a quick profile executes
only part of it. The completion workflow must compare the final working candidate,
tests, configuration, policy and change-impact identities with the accepted run.
A missing run, subsequent edit, required failed check, missing deep result or
unresolved material coverage means `completion: incomplete`. Report the specific
gap; do not claim the change is verified. A later edit requires a new run record.
Reuse of unaffected check evidence is allowed only after dependency identities
are validated and the reuse is explicitly recorded under the existing rules.
Documentation-only changes can use a justified limited policy after impact review.

`Adoption` is a versioned record embedded in evidence and the report. Its
`candidate_digest`, `policy_digest` and `run_id` must match the enclosing run.
`completion: verified` requires a finalised `ACCEPTED` run and no completion gaps.
The completion agent rechecks current identities when reporting completion; a
saved record cannot establish that the working tree has remained unchanged.

Local instructions and a locally editable runner are cooperative controls.
They cannot force a user or agent to run the suite, or protect against someone
who controls the checks. Label them `cooperative`. Do not describe them as
merge or release enforcement.

If protected CI is requested, prepare an integration that invokes the same runner.
Its final aggregation job must run even after dependency failure and reject
missing, skipped, cancelled, neutral, insufficient or failed required jobs.
Check the exact required job set, authenticated producer and designated candidate
(for example the tested merge candidate), rather than accepting any success with
the same display name. Bind policy/workflow identities to the trusted version.
Candidate changes to the policy, required job set or workflow cannot silently
weaken the gate; require the repository's authorized review path and reevaluation.

Before recording `protected_ci_verified`, inspect protection rules, required
check source, bypass permissions and workflow edit controls. Retain authenticated
receipts and state the identities to which protection applies. Missing permission
to inspect these controls leaves `protected_ci_requested`; local success is still
only cooperative evidence. Applying branch settings or deployment controls needs
separate existing or explicit authority. Fixture tests do not prove deployment.

## 2. Reconcile the change with requirements and checks

The runner must require a versioned `ChangeImpact` record before evaluating a
change for acceptance. Its baseline identifies the previously assessed snapshot;
a first adoption has a null baseline and assesses the full declared project scope.
The candidate and requirement-inventory digests bind the record to current inputs.

Use deterministic diffs and structured parsers to inventory added, modified,
deleted and renamed source, configuration, tests, data and documentation. Store
the complete inventory artifact, including before/after content identities. A
rename records the previous path. The semantic reviewer maps that inventory and
affected public/internal interfaces to behaviours, requirement IDs and module IDs.
Each changed path must be accounted for by at least one behaviour record, including
a justified exclusion for a change with no relevant behavioural effect. Account
for transitive callers, data interpretation and build/configuration effects where
the change can affect them. A path list alone cannot establish this judgement.

Each behaviour has a description, affected paths/interfaces, scientific effects,
review evidence and one disposition:

- `covered`: existing or new required checks discriminate the behaviour's important
  failure cases. Link requirement IDs and module IDs and explain the oracle.
- `excluded`: explain why the change is outside a stated acceptance claim or has
  no behavioural effect. Cite the policy and review evidence; an exclusion cannot
  remove an existing required claim without an attributable policy revision.
- `unresolved`: the behaviour, requirement, oracle or coverage remains uncertain.
  Record it in `unresolved_behavior_ids` and keep acceptance insufficient.

The runner validates references, exact path accounting, identities, required-check
links and unresolved status. Semantic adequacy remains a bounded agent/domain
review, with a receipt and evidence; never replace it with keyword scoring or a
one-test-per-line rule. A reviewed record must not contain unreviewed exclusions.
Missing review, missing paths, stale identity or unresolved material behaviour
produces a required gap. Structurally invalid records still follow exit `3`.
A demonstrated required defect retains `REJECTED` even if other coverage is absent.

For science, record separately whether the change affects implementation,
assumptions, numerical tolerances or empirical validity. Numerical agreement does
not establish empirical validity. Reassess the relevant reference, units, domain,
tolerance or validation data; unresolved domain decisions remain visible. Existing
adequate tests may be reused without generating redundant tests. Keep original
criteria frozen during evaluation; a justified policy update starts a new run.

## 3. Verify executed code and selected tests

Every executable module has an `execution_contract`; imports use null. The plan
states `checkout`, `editable`, `distribution`, `script` or `not_applicable` mode.
The last mode is for tools that do not execute candidate code, such as lint.
Freeze expected test identities in `expected_test_ids`, including parameter IDs
and custom discovery conventions. Empty selection is valid only for a module
that does not collect tests. Required test modules cannot plan an empty selection.

The runner records `execution_evidence` in the process receipt, independent of
an adapter's assessment. For Python, capture first-party package/module import
origins from the actual test execution, not from a separate interpreter probe.
Resolve namespace packages, editable mappings, symlinks, subprocesses and native
extensions against the intended candidate or build manifest where applicable.
Preserve origin and manifest artifacts. Unsupported origin capture blocks the
claimed execution mode; it is not evidence that the checkout was tested.

`source_digest` must match the planned candidate. Distribution mode additionally
requires a non-null `distribution_digest` and a build manifest linking the exact
artifact to the source, configuration, build tool and dependency identities.
Compare actual imported first-party content digests and origins with that manifest.
Third-party dependencies may originate in the environment if they match the
recorded lock/environment; they cannot stand in for the first-party package.
Detect stale installed copies and unintended checkout shadowing.

When a package is the deliverable, test clean installation of the built artifact
in a disposable environment with the checkout excluded from import resolution.
Exercise a representative delivered workflow, including required package data.
Healthy editable and installed-package modes must both work. A standalone script
does not acquire a packaging obligation merely because it is Python.

Reconcile exact collected/executed test IDs and per-test outcomes with the frozen
selection and raw artifacts. A same-count substitution cannot qualify a selection.
Missing, duplicate or unexpected IDs require review; a skip/xfail cannot satisfy
a required assertion. Preserve aggregate counts for display, not as identity proof.

## 4. Record static-tool scope and prevent assessment edits

Static modules have a `static_contract` with tool, intended paths, claim, policy
artifact and configuration artifacts. Receipts add `static_evidence`: effective
configuration artifacts, actually checked paths, exclusions, unchecked regions,
suppressions, before/after candidate digests and assessment-only status. Discover
nested configuration and preserve the project's intended hierarchy. Resolve each
changed path relevant to the claimed scope as checked or explicitly limited.
An unexplained omission is a required gap, not a clean result.

For a selected type checker, the policy must state treatment of untyped functions,
dynamic `Any`, missing/skipped imports and suppressions. Preserve justified gradual
typing. A clean run over annotated code cannot imply that unannotated bodies were
checked. Record unchecked regions with path, symbol/region, reason and policy
reference. A limitation is acceptable only when compatible with the frozen claim;
a required full-checking claim remains insufficient if those regions are unchecked.

For Ruff lint assessment, explicitly disable both fixes and fix-only behaviour
using the qualified version's `--no-fix --no-fix-only` options. Reject options such
as `--exit-zero` that mask required violations. Preserve selected rules; do not
enable every rule by default. Verify effective settings and source bytes before
and after assessment. An unexpected edit invalidates affected evidence and is
reported as an unauthorized effect; do not silently restore user files. An
unsupported version that cannot guarantee read-only assessment is blocked before
execution. If formatting is required, use a separate `ruff format --check` module
under `lint`, with its own result. Repairs require separate authority, a new
candidate and rerun checks.

## 5. Report and semantic validation

Evidence and report roots embed `adoption` and `change_impact`. Every report module
includes the plan's `execution_contract` and `static_contract`, and the receipt's
`execution_evidence` and `static_evidence` (null when unavailable or inapplicable).
The renderer must copy these from validated source records, never invent them.

Show adoption/completion and impact coverage in `overview`; show behaviour-to-
requirement/check mappings and import/test identity in `checks`; show static scope,
configuration and manifests in `provenance`. Show excluded/unchecked regions and
unresolved coverage in `limitations`. Keep the existing nine report sections and
43 capabilities. A report must explain the claimed scope without opening raw logs.

The shared draft schema now supplies these closed typed records. Cross-record
comparisons, path accounting, authentication and semantic adequacy remain future
validator responsibilities. Schema acceptance alone proves none of those facts.
This is an unreleased revision of draft schema version 1.0.0; no deployed consumer
or migration is claimed. P1 must record this draft compatibility change.

## 6. Required discriminating acceptance cases

| ID | Case and required result | Owning plan tasks |
| --- | --- | --- |
| F1a | Adopt once, then healthy changes through ordinary/scientific/plan/direct completion routes invoke saved suite and allow verified completion | P2.7, P8.8 |
| F1b | Failed change, absent run, later edit and quick-only omission of required deep check each prevent verified completion | P1.5, P3.5, P8.8 |
| F1c | Protected integration rejects skipped/neutral/missing/cancelled required jobs, wrong producer/candidate and unauthorized workflow weakening; healthy protected fixture accepts | P7.8, P9.1 |
| F2a | Passing old suite plus newly exported kg-to-tonnes result with seeded units defect is uncovered or fails a discriminating new assertion; old tests alone cannot qualify the change | P2.1, P4.6, P8.8 |
| F2b | Documentation-only change and behaviour already covered receive justified dispositions without unnecessary new tests; deleted/renamed/config/data changes are accounted for | P1.4, P2.1, P2.2 |
| F2c | Missing path, stale inventory, unresolved science assumption/tolerance/validation claim or unreviewed exclusion prevents acceptance | P1.4, P1.5, P5.4 |
| F3a | Healthy stale installed package cannot qualify defective checkout; missing package data fails a clean installed-artifact workflow | P4.8 |
| F3b | Healthy editable, distribution and standalone-script modes pass their policy; custom discovery survives; same-count different test IDs cannot qualify | P4.1, P4.7, P4.8 |
| F4a | Untyped defective function, missing-import Any and suppressed error are caught or explicitly outside the type claim; compatible gradual typing remains usable | P4.3 |
| F4b | Ruff fix=true and fix-only=true cannot edit source or hide remaining required violations; nested config and excluded changed paths are visible | P4.3 |
| F4c | Formatting-only violation fails its formatting criterion while clean lint stays clean; justified exclusions remain usable | P4.3, P6.1 |

These are future integration, agent-evaluation and semantic-validator tests, not
outcomes established by the draft schema tests. Independent phase reviewers must
inspect real discrimination evidence and healthy controls before closing tasks.

## Primary documentation

The tool-specific requirements follow [pytest integration guidance](https://docs.pytest.org/en/stable/explanation/goodpractices.html),
[Ruff configuration](https://docs.astral.sh/ruff/configuration/),
[Ruff formatting](https://docs.astral.sh/ruff/formatter/) and
[mypy limitations](https://mypy.readthedocs.io/en/stable/common_issues.html).
The distinction between local policy and protected enforcement follows
[GitHub protection rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).
Coverage limits and scientific claim boundaries are explained by
[Coverage.py branch coverage](https://coverage.readthedocs.io/en/latest/branch.html),
[NASA verification](https://www.grc.nasa.gov/www/wind/valid/tutorial/verassess.html) and
[NASA validation](https://www.grc.nasa.gov/www/wind/valid/tutorial/valassess.html).
Exact tool versions and supported options must be qualified in P0/P4.
