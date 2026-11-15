# P1 independent implementation review

The repaired evaluator rejects the false acceptances found in the first review, and the remaining P1 evidence has been supplied. The focused repair verdict is **PASS for P1.1–P1.7**, within the contract-only scope described below. The original findings and results are retained as historical evidence.

Reviewer: independent agent session `/root/contracts_review`, 2026-11-15. Scope: P1.1–P1.7. Review-only source access; the reviewer wrote only this file. Separation is instruction-based on a shared filesystem, not enforced isolation. The reviewer read public oracle cases, but did not read `initial-oracles.json` or its reserved cases.

## Findings

1. **[P1] Failed collected tests can produce ACCEPTED.** `rb-build-test-suite/src/rb_test_suite/policy.py:125–132` checks totals, skips, expected failures and errors, but does not reject a positive `counts.failed`. Starting with `test_contracts.fixture`, change `results[0].counts` from one passed test to `passed=0, failed=1`, keeping `collected=1`, the criterion observation true and the receipt exit zero. `validate_run` returns `ACCEPTED` with no gaps. This contradictory record cannot establish a successful required test module. Validate failed outcomes against the criteria/receipt and make the record invalid or nonaccepted; preserve any demonstrated required violation. Add a regression with the healthy control. This blocks P1.4/P1.5's false-pass exit criterion.

2. **[P1] Frozen module inputs are outside artifact validation.** `validation.py:227` builds its artifact set from evidence artifacts and plans only; `policy.py:68–78` discovers fields named `*_artifact_id(s)` and ignores the full Artifact records in `ModulePlan.inputs`. Add a declared input copied from existing artifact metadata but with `id='missing-input'` and `path='absent.txt'`, and update the frozen plan file and its hash. `validate_run` still returns `ACCEPTED`. An unavailable or differently hashed required input therefore does not prevent acceptance. Reconcile every plan input against the canonical artifact identity and verify availability/bytes, including duplicate or conflicting metadata. This blocks P1.4's input/digest boundary.

3. **[P2] Evaluation policy mismatches are silently replaced.** `policy.py:294` rewrites the gate policy digest without validating its prior binding. Set only `evidence.gate.policy_digest` to another valid digest in the healthy fixture: the run accepts and the differing value disappears. P1.6 requires immutable evaluation provenance and explicit rejection or derivation when rules change. Validate cross-record policy consistency and document the API's immutable evaluation rule; retain original evidence and explicit derivation provenance if reevaluation is supported. Unsupported versions are already rejected, but that alone does not close P1.6.

## Phase verdict

| Task | Verdict on initial reviewed candidate | Evidence or concrete remainder |
| --- | --- | --- |
| P1.1 | Implemented; verification incomplete | Typed public records and schema exports exist and draft fixtures are accepted. Preserve the promised compatibility diff against all four draft schemas, including intentional structural changes. A single representative fixture is not that diff. |
| P1.2 | PASS within P1 | Configuration/catalogue/managed-file/event/verifier contracts exist; all 43 canonical IDs are ordered and routes are explicitly unsupported. Document compilation/reference ownership alongside compatibility evidence. No claim of operational qualification. |
| P1.3 | PASS within P1 | Bounded byte parsing, duplicate JSON/YAML rejection, alias rejection, finite values, XML DTD/entity rejection, local schema registry, date format assertions and unsupported version rejection are implemented. |
| P1.4 | CHANGES_REQUIRED | Findings 1 and 2 permit false acceptance; finding 3 exposes a cross-record policy mismatch. Other inspected checks cover candidate, frozen plan, exact test IDs, import manifests, change inventory and static limitations. Authentication integrations conservatively remain insufficient pending their owning later phases. |
| P1.5 | CHANGES_REQUIRED | Finding 1. Required failure/gap aggregation and exit precedence otherwise follow the stated approach. Add independent cross-record cases, especially optional failure, capability-required checks and multiple attempts. |
| P1.6 | CHANGES_REQUIRED | Finding 3; immutable evaluation/provenance and rejection/derivation rules need explicit evidence. No live report-only command is demanded in P1. |
| P1.7 | Implemented in part; verification incomplete | Schema drift check exists. `test_policy_independent.py` supplies literal expectations for predicates and exits, but no independent cross-record evaluator table. P0 analytical toy checks do not test this run evaluator. Materialize a bounded public decision table with expected outcomes fixed independently of production functions. |

**Overall initial verdict: CHANGES_REQUIRED.** This is a P1 contract/evaluator verdict, not a review of future runner, agent host, adapter or production integrations.

## Checks and reproducibility

The parent reported 23 passing unit tests using `PYTHONPATH=rb-build-test-suite/src python -m unittest discover -s rb-build-test-suite/tests -v`, schema drift and instruction/consistency checks. The reviewer inspected the tests and reused that evidence rather than repeating the unchanged suite. Focused checks used the same interpreter and imported `fixture` with `PYTHONPATH=rb-build-test-suite/src:rb-build-test-suite/tests`.

Each check created a temporary directory, called `plan,evidence=fixture(root)`, applied exactly one mutation above, and called `validate_run(evidence,[plan],root)`. For the input case only, the plan was serialized with `json.dumps(plan).encode()`, written to `plan1.json`, and `evidence.plans[0].bytes/sha256` updated. Results:

| Case | Actual gate | Required gaps |
| --- | --- | --- |
| Unchanged healthy control | ACCEPTED | none |
| Failed collected test | ACCEPTED | none |
| Absent declared module input | ACCEPTED | none |
| Differing stored gate policy | ACCEPTED | none |

No implementation tests were deleted, skipped or weakened during this review. Tests at this boundary are synthetic contract tests; they do not establish truthful process capture or scientific/empirical validity. Full repository CI, runtime process checks, browser/report execution, installed-package routes and live host trials were not run by this reviewer because they are outside this phase or already assigned to their owning later phases. The existing constrained runtime is unchanged.

## Reviewed identities

SHA-256 of the initial reviewed sources:

- `models.py`: `fed01762f0ea5d0a4a1dda845728768bafc85baee61012a5ed4f45666a6db8ce`
- `validation.py`: `cc7f803ede0c14ba8e7767a02767c804b00c8b054ed4c5ae7b517f5c575eef90`
- `policy.py`: `7b87e593109de3c513fa151b63de57954541a951eebdf527b6572a4af733b4d3`

Requirement identities:

- `module-interface.md`: `b9f7b3ffd762e4537b943716b759e5cfbd2368c34ae25bb30a9ea7361897c96e`
- `evidence-and-report.md`: `4b8ffd7bce8b16abd987da5bec0846c5c4708bc5fe5ef19c0c100fced4ac2513`
- `assurance-contract.md`: `f9b7563d25249b7adb8e5a52ebfd1a4c97a3974156c86bdc508ad13c07e3a342`
- `IMPLEMENTATION_PLAN.md`: `e6199e9ccd5e906adc9d4d1a4ec966433f3c87b8ae0cd88f4e008984080918cd`


## Focused repair review

The parent requested a bounded follow-up after repairing the three findings and supplying the missing phase evidence. This review inspected those repairs, the added evaluation derivation and unbound configuration records, the independent cross-record cases, and the schema compatibility harness. It did not reopen unrelated future integrations.

**Verdict: PASS for P1.1–P1.7.** No actionable blocking issue remains in the reviewed P1 changes. This supersedes the initial CHANGES_REQUIRED verdict while preserving its evidence above. Final phase-state ownership remains with the parent.

### Finding closure

- **Finding 1 resolved:** a positive failed-test count now retains FAILED and rejects a required module even when an asserted criterion says satisfied. The regression preserves an accepted healthy control.
- **Finding 2 resolved:** input IDs must be unique within a plan; conflicting full metadata is rejected against the canonical artifact registry and across plans. Missing/unavailable inputs produce a gap, while registered inputs undergo the existing byte/hash checks. Tests include healthy, missing, differing-hash and duplicate variants.
- **Finding 3 resolved:** gate and evaluation policy digests must agree with run provenance. A differing stored gate digest now raises ContractError. Evaluation returns a copy, binds original input and assessed content digests, fixes the evaluator/schema versions, and preserves its timestamp on unchanged revalidation. Changed assessed content, decisions, unsupported versions or changed artifact availability cannot silently refresh the saved evaluation. Original observation persistence and actual report-only execution remain P3/P6 work, explicitly described in the contract notes.

The reviewer repeated only the original discriminating reproductions against the repaired code. The healthy control returned ACCEPTED; a failed test count returned REJECTED; an absent input returned INSUFFICIENT_EVIDENCE; and a differing gate policy raised `ContractError: gate/provenance policy mismatch`.

### Added contract evidence

`p1-schema-compatibility.json` preserves the four original schema roots, generated roots, public field changes and intentional optional evaluation extension. `check_schema_compatibility.py` retains the original fixture construction and substitutes only the generated validation registry. Its reported 15 passing original structural cases support compatibility without claiming exhaustive equivalence of all possible records.

`test_cross_record_independent.py` materializes literal expected outcomes from the independent public decision table. It covers healthy and missing results, required deep omissions, required failure with and without gaps, blocked/timeout/cancelled cases, optional failure visibility, preservation of a failure across a later successful attempt, and blocking findings. The fixture helper writes synthetic artifacts; production decision functions do not calculate expected outcomes. This closes P1.7's missing cross-record evidence. These are parent-authored materializations of independent oracle decisions, not separately executed host-agent trials.

The new authoring configuration separates unbound requests from candidate-bound execution records. Command/import exclusivity, expected test identity, distribution-path requirements, referenced criteria, module uniqueness and dependency cycles are checked. Lexical path checks include the added request fields. Configuration compilation, filesystem containment against the real project, current-source snapshots and finalisation remain explicitly assigned to P2/P3; the new configuration schema does not claim those functions are already operational.

### Verification and identity

The reviewer inspected the parent-produced `p1-test-result.json` and verified every recorded source/schema/test/dependency hash against the current files: **no mismatches**. That receipt reports 32 passing tests, including the repair and derivation/configuration cases. The reviewer reused that unchanged full-suite evidence and performed the focused reproductions described above. The prior schema export and repository instruction/consistency checks remain supplied parent evidence.

Repaired principal source SHA-256 values:

- `models.py`: `0934103f33e5a760973b0b0184c931212916fcbaa34a8d77cb63ae98be5a34d8`
- `validation.py`: `3303dc74dafe9a181938416d481cd96e7159430edc12de1577701d7602879d1b`
- `policy.py`: `e69549445ea2491e637e17f05da2cbc6d405c935df91c007492c8cda831b0cc1`

P1 now has typed contracts, bounded parsing, conservative semantic evaluation, immutable evaluation derivation rules, generated schema checks and independently specified cross-record expectations. The unchanged verification limits above still apply: these checks do not qualify a live runner, imported authentication, scientific empirical claims, production controls, adapters, installed packages, browser reporting or host delegation. No claim of full skill completion follows from this phase verdict.
