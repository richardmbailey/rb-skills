# Validation — 15 November 2026

This creation record predates the [fresh independent review](fresh-review.md).
That review found and repaired two evidence-preservation defects. Its updated
coordinator rejects older sessions without command-log hashes, including the
historical demo recorded below; the earlier results are not current acceptance.

The two skills and narrow coordinator are implemented and installed. The evidence
shows that deliberately weak numerical tests fail the audit, repaired assertions
pass it, and acceptance remains pending until an actual independent review of the
assessed candidate. It does not establish exhaustive test adequacy or autonomous
agent-repair performance.

## Scope and architecture

`rb-build-test-suite` now invokes the paired route for reliable/independently
audited construction, new scientific-core suites and adopted requirements.
`rb-audit-test-suite` owns independent executable challenges and findings. The
host dispatches those roles through its platform tools. The bundled Python
coordinator does not call an LLM: it enforces declared command outcomes, protected
inputs, current-candidate review, a three-assessment default and terminal states.
No third reasoning agent or general assurance runner was added.

Code/tests were implemented in independently scoped tasks by `test_loop_runtime`
and `test_audit_example` (GPT-6 Astra medium). Parent integration preserved existing
working-tree work and added metadata, routing cases, eval definitions, instruction
and consistency contracts, Claude profile entry and CI checks. The description
budget increased by 40 words for the added skill; the exact-limit/one-extra-word
regression was updated and passes. No existing description was shortened to hide
the new entry.

## Executed validation

| Check | Observed result |
| --- | --- |
| Coordinator unit/component tests | 18 passed; independently rerun by reviewer |
| Numerical audit and invalid-evidence controls | 24 passed; independently rerun by reviewer |
| Deliberately weak audit | Expected exit 1: two failed, eight passed; both historical defects survived weak project tests |
| Repository routing/skill regressions | 46 passed |
| Existing schema-reference tests | 15 passed |
| Instruction and consistency contracts | Passed |
| All top-level skill eval manifests | Validated; definitions are not completed semantic agent trials |
| Skill metadata | 36 skills, 1,133 description words within 1,155-word budget |
| Workflow YAML parse and publication-hygiene check | Passed |
| `git diff --check` | Passed |
| Codex installation | Builder existing symlink resolves; auditor new symlink installed |
| Claude Code installation | Generated builder refreshed; generated auditor installed |

The coordinator tests cover early failure followed by success, missing commands,
timeouts and POSIX descendants, actual interruption with partial logs, concurrent
lock rejection, current/stale review, independent identity, protected/candidate
changes, malformed plans/reviews/state, cancellation, unchanged retry rejection
and budget exhaustion. Faulty last-check-wins and any-check-passes aggregation
controls demonstrate that the acceptance tests are discriminating.

The numerical example uses eight predeclared faults: six scientific faults plus
the two exact historical floating-point regressions missed by earlier generated
suites. Healthy controls, exact native JUnit IDs and intended assertion failures
are required. Missing/empty/skipped tests, malformed reports, collection errors,
wrong assertions and timeout outcomes are rejected. The example's values apply
to that Euler model, not arbitrary scientific code.

## Actual two-round demonstration

[prepare_demo.py](prepare_demo.py) creates an isolated example and initially
weakens only the two historical assertions. The plan protects the requirements
and challenge tests. The builder then restores the exact substantive assertions;
no policy or tolerance is relaxed.

- Round 1: project tests 8 passed; audit challenges 2 failed / 6 passed; subsequent
  evidence-validation tests 14 passed. Coordinator outcome `needs_repair`, exit 1.
- Round 2: project tests 8 passed; eight audit challenges passed; evidence tests
  14 passed. Coordinator outcome `awaiting_review`, exit 3. The acceptance gate
  returned nonzero at this stage.
- A separate live reviewer (`/root/test_system_review`, GPT-6 Astra medium)
  independently inspected the current file/mode manifest, protected inputs,
  round-1/round-2 receipts and native child assertion evidence. It confirmed that
  only the two historical assertions changed and recommended approval with no
  blocking findings for round 2 digest
  `f33ff592fcdd66b3e69f4f8bd66f647c9f5dc98eb34028c05d4cfd9364f1f8b2`.
- The parent submitted that actual review, then ran `status --require-verified`:
  outcome `verified_local`, exit 0. The original `demo-result.json` receipt is retained locally and excluded from Git because it contains machine-specific execution paths.

This is deterministic fixture repair plus actual independent review, not a
measured trial of autonomous LLM repair planning. The example's host reference is
an attestation to the observed invocation, not cryptographic authentication.

Raw source, state, command outputs and native artifacts are archived under local
ignored `evidence/completed-demo/`; the original executed locations are retained
in the receipts. Example red/green evidence is under `evidence/example/`.
Earlier integration attempts are not counted as passing end-to-end evidence: one
used reused pytest temporary paths that could erase native child artifacts;
another helper sent an audit-only option to project-only pytest. The corrected
entry uses a new artifact directory per command and sends the option only to audit
commands. Earlier temporary work and the first-layout record remain available.
The failed description-budget fixture was corrected to test the newly allocated
limit before the final 46-test pass.

## Independent and language review

`test_system_review` reviewed the two roles, authority, candidate binding, failure
handling, historical regression policy, code and numerical example. It applied
the `rb-simplify-language` method explicitly invoked by the `rb-write-skill`
post-draft procedure. It identified one trigger inconsistency: the shared paired
reference omitted the builder's new-scientific-core trigger. The parent corrected
that wording. No other blocking finding remained within the declared local scope.
The reviewer independently ran the 18 coordinator and 24 numerical audit tests,
then supplied the candidate-specific review described above.

## Installation and remaining limits

Both matching sync dry-runs were inspected. The initial Claude dry-run rejected a
generated pytest symlink inside example evidence. Generated execution evidence
was moved outside the distributable skill and example commands now put new
artifacts in external temporary directories. The corrected dry-run and install
succeeded without weakening the installer's source checks. Codex uses source
symlinks; Claude uses its normal generated copies.

Not run: the full constrained-runtime/wheelhouse/schema-export suites, remote
Linux CI, a live Claude agent trial, repeated with/without-skill semantic trials,
and a cross-language audit campaign. No constrained-runtime code/schema changed;
these omitted checks supply no evidence here. The current example exercises
Python/pytest. Other project tools need native executable audit checks with the
same healthy/faulty and failure-propagation obligations. The generic coordinator
runs command arrays; it does not prove that arbitrary commands test anything.

Commands run with caller permissions. Reviewer IDs and invocation references are
cooperative host attestations. Hashes cover declared inputs only. Cancellation is
between operations; interruption/timeouts contain process groups on POSIX, with
direct-process termination on other platforms. A stale running state is never
silently resumed. The loop stops unverified on exhausted rounds or unresolved
requirements. The full assurance runner remains deferred.

No commit, push, deployment or external publication was performed.
