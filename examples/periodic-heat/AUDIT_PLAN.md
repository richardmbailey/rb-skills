# Independent challenge plan

This plan was derived from REQUIREMENTS.md before inspecting heat.py or the developer tests. The auditor has separate ownership but shared filesystem access; this is not enforced isolation.

## Predetermined risks and oracles

- R1/R2: dropped last step or updating a cell before its neighbours are read. Use initial (4,0,0,0), r=1/4: one step is (2,1,0,1), two steps (1.5,1,0.5,1). Challenge step count and simultaneous stencil.
- R2/R5/R6: wrong diffusion coefficient, wrong sign or missing periodic wrapping. Challenge coefficient and periodic neighbour. A discrete Fourier mode has eigenvalue 1-4r sin²(pi k/n); this oracle follows by substituting exp(i 2 pi k j/n) into the specified stencil, independently of implementation.
- R3/R4: omitted finite/domain/type validation and stability comparator. Challenge the representable value immediately above r=0.5, rejection at zero steps, and NaN validation. Values exactly at and immediately below the limit must pass.
- R5: constant field, mean, extremum and shift invariants supplement exact values. They alone cannot detect a wrong diffusion speed.
- R6: independently check k=2 on n=32 with r=0.2 for 19 steps, mean=280 K and amplitude=7 K. Maximum pointwise absolute tolerance 2e-12 K allows accumulated double rounding while remaining far below a changed coefficient. Continuum convergence uses L=1 m, D=1 m²/s, k=1, t=1/64 s, r=1/4, n=16,32,64, giving integer steps n²/16. Expected amplitude error is second order in dx; require successive error ratios 3.8..4.2 and fine-grid pointwise error <0.002 K for unit amplitude. These bounds are set before execution.
- R7: corrupted exported time or spatial scale and swallowed CLI write failure. Native CSV reading and subprocess exit must expose them.
- R8: exact collection, import origin and substantive failures are required. Timeout, broken import, missing test and malformed evidence are invalid challenges. The existing numerical helper's inspect_result and replace_once will be reused via an explicit import; a small run adapter is needed for this example's filenames and assertion-specific evidence.

## History and execution

The previous transfer-model duration/dt-underflow and subtraction-of-rounded-timestamps cases are inapplicable because this API takes bounded integer steps and calculates no shortened timestep. This decision does not waive float stability neighbours, zero steps, final time or last-step tests. No inherited bug for this new API is known.

Fault anchors and exact native target IDs will be mapped only after this plan is saved, retaining the pre-inspection risks above. Each selected fault gets a healthy control, a bounded subprocess against a disposable copy, raw command/log/JUnit and mutated source. No production test or model edits are authorized to the auditor. Any survivor is retained and reported, never reclassified by weakening the audit.

The unchanged coordinator's existing executable failure-propagation tests will be reused rather than duplicating its runner: early failure followed by success, lint/type-like nonzero command, unavailable executable, timeout, empty/skipped evidence and altered receipts require exact scope review. Parent owns the frozen coordinator declaration and acceptance. Default limit is three assessments.

## Implementation-informed mapping and qualification

After the initial plan was saved, the auditor read the final developer tests and model. `audit_suite.py::FAULTS` records all ten exact source replacements and native detecting test IDs: sequential updates, omitted final step, half diffusion speed, reversed sign, omitted periodic wrap, omitted stability check, accepted NaN, spatial unit corruption, time corruption, and swallowed CLI write failure. Each selected test runs with the import-origin assertion on an untouched copy first, then on its faulty copy. This bounded selection does not estimate universal mutation coverage.

The existing helper is imported explicitly from `rb-audit-test-suite/examples/numerical/audit/support.py`; `replace_once` and `inspect_result` are reused unchanged. Its project runner is intentionally not reused because filenames, selection and retained evidence locations differ. A narrow validation-receipt adapter handles pytest 9's exact `Failed: DID NOT RAISE ValueError` outcome. Seven fixtures qualify that adapter against healthy, empty, duplicate, error, skipped, wrong-failure and wrong-exit native receipts. Existing shared-helper qualification remains a separate parent command.

Initial evidence `evidence/audit/attempt-q48uyzyj` and `audit-initial.xml` records two invalid adapter expectations for pytest's message spelling. Second evidence `attempt-00kwk1kb` and `audit-corrected.xml` records an invalid sequential-update anchor after builder formatting, plus unrelated default-temp cleanup warnings. Neither was a survivor or a production failure. Corrected exact message and anchor preserve the intended requirements. The final local run uses an owned outer basetemp; each child always had its own retained location.

Six coordinator fixtures invoke the unchanged actual `test_loop.py`, retaining plans, state, commands and stdout/stderr. Healthy commands end pending independent review. Early failure, generic lint-like/type-like nonzero commands, missing executable and timeout end needs_repair even though a later audit command succeeds; `status --require-verified` refuses all these incomplete states. These are exit-propagation tests, not claims that synthetic exits exercise Ruff or mypy semantics. Actual Ruff/mypy commands belong to the frozen parent assessment.

Exact audit collection is in `expected-audit-tests.json`, derived from native `--collect-only` output retained at `evidence/audit-collection.txt`. Command (from this directory): `python -m pytest audit_suite.py audit_science.py -q -s --basetemp=evidence/audit-final-tmp --junitxml=evidence/audit-final.xml`. For coordinator rounds the parent must give each outer JUnit and basetemp a fresh owned location; child evidence automatically creates a fresh `evidence/audit/attempt-*` directory and prints it.

## Scientific review scope

The explicit periodic second-difference stencil has dimensions K, and its update uses simultaneous previous-step values. Its coefficient r is dimensionless. For 0<=r<=1/2, each exact update is a convex combination of the centre and two neighbours, establishing the maximum principle; periodic indexing telescopes the sum and commutes with cyclic shifts. The Fourier eigenvalue follows from the stencil, and dt proportional to dx² gives second-order fixed-time convergence here. Code inspection agrees with these derivations and the public bounded domain. Executable checks independently assess one/two hand steps, a different discrete mode, and continuum refinement with predetermined tolerances. The prior transfer-model timestamp defects do not occur in this integer-step control flow. No empirical material or physical forecasting validation is claimed.
