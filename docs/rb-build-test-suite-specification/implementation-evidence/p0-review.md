# P0 baseline review

The baseline preserves the specification and makes the intended local environment explicit. It is suitable for continuing preparation, but the current artifacts do not yet establish every P0 exit condition. No runtime or host compatibility beyond the recorded observations is qualified by this review.

Reviewer: `/root/initial_oracles`, a separate preimplementation session with shared filesystem access and instruction-only write restrictions. Verdict: **CHANGES_REQUIRED for closing P0**, not a request to halt unrelated preparation. The parent owns task states and completion.

## Evidence inspected

Read `baseline.json`, `baseline-requirements.lock`, `requirements.json`, the five governing specification documents and `AGENTS.md`. Authored the independently derived `initial-oracles.json` before implementation exposure. Recomputed all 17 baseline file hashes: all match. The requirement map contains 43 unique capability IDs. All 25 dependency freeze entries match the recorded versions; the separately recorded pip version is absent from the freeze. That omission does not undermine the library pins, but the freeze is an observed environment snapshot rather than a reproducible, hash-locked installation test.

The parent reports successful strict-model positive/negative tests, schema generation, unsafe YAML-tag rejection and invalid-calendar-date rejection in a disposable environment. These results are not independently reproduced here. The inspected artifacts contain a prose probe summary, but no executable probe or raw result receipt to inspect. CLI help establishes documented options, not successful agent invocation.

## Required corrections before closing P0

1. **P0.2 — Preserve inspectable compatibility evidence.** Save the probe commands or executable probe, interpreter/environment identity, output and exit status. Distinguish the observed environment freeze from clean installation qualification. No new platform run is required merely to document the current macOS readiness; Linux must remain a target until tested.
2. **P0.4 — Complete the common-requirement mapping.** The capability map is useful, but scientific subtypes currently have names without task/evidence links, and common boundaries such as preservation/rollback, process cancellation and authority, parser rejection, report correctness and host separation have no explicit requirement records. Add their owning task IDs and observable acceptance cases, referencing the existing plan rather than duplicating prose. Include ML leakage, which is explicitly required by P4.6 but absent from the science list.
3. **P0.5/P0 verification — Demonstrate fixture evaluator discrimination.** The oracle packet defines literal healthy/defective outcomes and its convergence values were checked with exact rational quadrature sums. It does not execute an evaluator against a good and bad artifact. Preserve a small independent checker plus positive and deliberately bad artifact results before claiming the P0 verification requirement passed. Product gate tests remain future work.
4. **P0.6 — Fix the finite trial scope.** The updated baseline now records explicit critical-outcome, construction, comparison and release rubrics, which resolve the initial rubric omission. Counts per condition are recorded, but the trial condition set, designated reliability-critical cases and total budget ceiling are still not enumerated. Record these before trials; the existing matched baseline and unavailable-host rules are appropriate. The three reviewer-only oracle cases are reserved by instructions only; do not expose them in generated-test prompts. If a coding agent has read them, record contamination and reserve fresh cases.

## Task-specific assessment

| Task | Assessment of current evidence |
| --- | --- |
| P0.1 | Baseline hashes and pre-existing changes recorded and checked. Selection defaults such as standard profile and automatic suite-building routing remain in the hashed specification; copying those references into the manifest would improve clarity. |
| P0.2 | Concrete libraries and local interpreter selected; pins consistent. Probe preservation gap above prevents independent verification. |
| P0.3 | Honest distinction between actual Codex delegation/shared access and untested Claude invocation. No Linux, native Windows, WSL or live Claude qualification established. |
| P0.4 | All capabilities mapped; common requirement/task/evidence coverage needs correction above. |
| P0.5 | Independent 28-case design exists and was structurally checked. The updated baseline records its matching hash; evaluator discrimination still needed. |
| P0.6 | Initial trial caps, outcome rubric and zero live-production/API-spend limits recorded; total bounded condition set needs correction. |

## Limits

No production inputs are required for these corrections. No application, runtime, adapter, browser, paid API or live host trial was run in this review. No platform support or installed skill claim follows from P0. Current scientific cases establish analytical fixture expectations, not empirical validity, stochastic reliability or all scientific subtype coverage. This review introduces no task-state edits.

## Focused repair review

The initial verdict above is retained as the review history. After the parent saved the repairs, I inspected `probe_dependencies.py`, `dependency-probe-result.json`, the extended requirement mappings and the enumerated trial matrix. I also implemented the separately requested independent analytical checker in `oracle-checks/`; the parent must inspect that checker and its results rather than treating my authorship as an independent review of my own code.

The four recorded gaps are addressed at the P0 preparation boundary:

- The preserved dependency probe has positive and negative strict-model checks, schema generation, safe-YAML acceptance and unsafe-tag rejection, and valid/invalid timestamp checks. Its result identifies Python 3.14.2, macOS arm64 and the selected library versions. I inspected the code and result; I did not independently reinstall dependencies or rerun this environment probe. The result supplies local API-readiness evidence, not runtime or platform qualification.
- The extended requirement records map common boundaries and scientific subtypes to named tasks and observable evidence. Leakage appears under empirical validation, with P4.6 already owning the actual leakage fixture in the plan. These remain future evidence obligations, not completed validations.
- `oracle-checks/result.json` records a successful stdlib unittest run: three test methods, nine saved artifacts comprising three healthy and six defective cases, plus malformed and non-finite numeric cases. O22 rejects wrong units and conversion values; O23 rejects loss and reversed transfer; O24 rejects first-order and nonconverging results while accepting second-order trapezoidal results. These checks establish analytical artifact discrimination only. They do not test generated projects, product gate code, adapters or the held-out cases.
- The trial matrix defines six cases, two conditions and two hosts. Three critical cases receive six trials per condition/host and three others receive three. I recomputed the total as 108 trials, bounded by 64,800 seconds at 600 seconds each, with no trial retries and no direct API-spend authority. The existing outcome rubric and unavailable-host limitations remain explicit. These are ceilings, not permission to launch new paid services or claims that trials ran.

I checked the oracle digest against the baseline and the presence of task/evidence links in both mapping arrays. `git diff --check` passed for the evidence directory after the new checker files were written.

**Updated verdict: PASS for P0 preparation, with the stated limits.** No remaining blocking gap in the inspected P0 artifacts. Final P0 closure remains the parent's decision after inspecting the independently authored checker. The earlier requirement that future qualification gates actually run remains unchanged; P0 establishes neither Linux/Claude support nor a functioning suite runner.
