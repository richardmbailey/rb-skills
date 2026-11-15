# Independent check of assurance-review corrections

The revised requirements address the four ways the original design could report
success without assessing the intended change. They require later changes to use
the saved suite, review whether its checks cover changed behaviour, identify the
code and tests actually executed, and disclose static-tool limits. These are
specification and implementation obligations; no runner has been implemented or
qualified by this review.

Date: 2026-11-15. The reviewer did not author the reviewed corrections and wrote
only this file. Scope: this draft package and the four findings in
[the original review](independent-assurance-review.md), which remains historical.
Repository instructions, `rb-review-pr-or-diff` and `rb-multi-agent-systems` were
applied. No nested reviewer or implementation agent was used.

## Finding-by-finding assessment

| Original finding | Verdict at specification/plan level | Evidence and original failure case |
| --- | --- | --- |
| 1. Routine changes need to invoke the suite | Resolved | `assurance-contract.md:15–65` requires project adoption, ordinary/scientific/plan/direct routes, final identities and incomplete completion for absent, failed, stale or quick-only evidence. Tuesday's change cannot claim verification from Monday's run. Local cooperation remains distinct from protected enforcement; protected aggregation rejects skipped/neutral/missing/cancelled results and checks producer, candidate and workflow controls. `IMPLEMENTATION_PLAN.md:278`, `:304`, `:422`, `:451` and `:475` assign implementation and qualification. F1a–F1c are explicit at `assurance-contract.md:197–199`. |
| 2. Changed behaviour needs coverage reconciliation | Resolved | `assurance-contract.md:69–108` requires a complete change inventory, reviewed behaviour/requirement/check mappings, transitive effects and justified exclusions. The new kg-to-tonnes export cannot qualify merely by rerunning old conservation tests. Missing paths, stale records, unreviewed exclusions and unresolved material science claims prevent acceptance. F2a–F2c include documentation-only and already-covered controls (`:200–202`). P1.4/P1.5, P2.1/P2.2, P4.6, P5.4 and P8.8 own the semantic and agent checks. |
| 3. Executed Python and exact test selection need qualification | Resolved | `assurance-contract.md:112–144` requires actual in-process import evidence, source/build identities, exact selected/collected/executed test IDs and per-test outcomes. A stale healthy installation cannot qualify a defective checkout; a clean installed-artifact workflow must expose missing package data and checkout shadowing. Script projects retain an appropriate non-packaging route. F3a/F3b (`:203–204`) and P4.7/P4.8 (`IMPLEMENTATION_PLAN.md:337–338`) require defects, healthy controls and custom discovery. |
| 4. Static-tool scope and read-only assessment need qualification | Resolved | `assurance-contract.md:148–172` requires effective nested configuration, checked paths, exclusions, untyped/Any/import/suppression limitations and claim-compatible interpretation. Ruff assessment must disable fixes/fix-only, reject masked exits and verify unchanged bytes; unsupported read-only behaviour blocks dispatch. F4a–F4c (`:205–207`), P4.3 (`IMPLEMENTATION_PLAN.md:333`) and P6.1 (`:385`) require the original defect cases, healthy gradual typing/exclusion controls and distinct formatting results. |

## Structural records and semantic responsibilities

The shared schema contains closed `Adoption`, `ChangedPath`, `ChangedBehaviour`,
`ChangeImpact`, `ExecutionContract`, `ExecutionEvidence`, `StaticContract` and
`StaticEvidence` shapes (`schemas/contracts.schema.json:2699–3535`). Evidence and
report roots require adoption and impact records; module plans, receipts and
report rows carry the execution/static records. Local implications cover verified
completion requiring an accepted gate, accepted impact being reviewed, required
distribution identity, review references and unique test-ID arrays.

The shapes deliberately do not prove that referenced artifacts exist or are true,
that actual IDs equal the planned selection, that before/after digests match, or
that semantic impact review is adequate. The normative contract explicitly assigns
these duties to future validation (`assurance-contract.md:187–191`), implemented
by P1.4/P1.5 (`IMPLEMENTATION_PLAN.md:248–249`). Raw inventory, import/build and
per-test artifacts supply detail beyond the summary shapes. Schema-permitted
semantic inconsistency is therefore not evidence that these obligations vanished.

The phase dependencies put typed validation before scaffolding and execution,
real adapter qualification before core integration, and route trials before
release. The acceptance matrix is explicitly an extension of phase exit gates
(`IMPLEMENTATION_PLAN.md:494–503`); schema fixtures cannot close F1a–F4c. No phase
is marked implemented or verified by these changes.

Scientific safeguards remain intact: independent reference provenance, units,
conservation, convergence, predeclared tolerances/statistical designs, preserved
failures and separation of numerical verification from empirical validity
(`README.md:193–212`; `assurance-contract.md:103–108`). Independent-agent evidence
remains advisory and its actual context/write/oracle separation must be disclosed;
the deterministic runner owns acceptance. No new distributed orchestration is
needed to implement these corrections.

## Focused repair check and final verdict

The review found that the first revision placed adoption/impact work after
execution and optional CI edits after the final candidate check. The author
corrected the ordering. The final draft loads assurance first, adopts the suite
and prepares CI before freezing the candidate, refreshes impact after generated
edits, and reruns after verifier-added tests (`skill-draft.md:28–86`). Evidence
validation precedes reporting and the final completion comparison is last.
The proposed package now lists its assurance reference (`README.md:222–224`).
The gate also explicitly marks any required coverage/scope gap insufficient
(`evidence-and-report.md:119–125`). These repairs were inspected directly.

**PASS at specification/plan level.** All four original findings are resolved in
requirements, typed records and future acceptance obligations. No material
unresolved finding remains within this review's scope. This verdict does not
close any implementation task or demonstrate future runtime enforcement,
defect-detection performance or scientific validity.

## Checks and limits

- Read the original failure examples and revised normative contract, specification,
  catalogue, draft instructions, module/evidence/report interfaces, plan, schema
  definitions and test source. Parsed schemas for targeted inspection.
- Reused the parent agent's reported 15 passing tests from the disposable validation
  environment, using `python -m unittest discover -s docs/rb-build-test-suite-specification/checks -v`.
  Inspected the six added tests (`checks/test_schemas.py:252–354`). These test
  structural acceptance/rejection; they do not run a candidate, Ruff, a type
  checker, protected CI or an implementation agent. The unchanged suite was not
  rerun merely to obtain a second reviewer-owned result.
- Ran `git diff --check` successfully. Because this package is untracked, that
  command does not independently validate all its new files.
- No full repository CI, constrained-runtime tests, OS/tool matrix, browser,
  protected deployment, scientific fixture execution or live host trials ran.
  This review changes no runtime or active skill. Those future qualification
  obligations remain open and cannot be inferred from this document.
- No tool-version compatibility claim was independently established. The draft
  requires exact supported versions and options to be qualified in P0/P4.
