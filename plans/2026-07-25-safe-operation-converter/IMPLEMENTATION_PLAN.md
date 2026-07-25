# Safe-Operation Converter Pilot Implementation Plan

## Summary

Build a dependency-free temperature-converter web application as a controlled pilot of the RB constrained execution workflow. The application will live in prefixed files under `docs/`, remain completely local, and avoid modifying existing documentation or user changes.

## Execution Route

`constrained`

Richard selected the constrained route on 2026-07-25. Each phase must be compiled by `$rb-create-low-level-plan`, assessed by `$rb-assess-plan-safety`, and executed only from an unchanged `safe: true` bundle through `$rb-safe-operation`.

## Goals

- Produce a small browser application that converts temperatures between Celsius, Fahrenheit, and Kelvin.
- Exercise canonical low-level planning, safety assessment, exact patch execution, audit recording, and separated verification.
- Use two independently assessed phases so the phase handoff and continuity mechanism are exercised.
- Provide deterministic browser-native self-tests without adding dependencies or a build system.

## Non-goals

- Do not modify `README.md` or any existing skill, runtime, evaluation, or plan file outside this plan directory.
- Do not add packages, network access, analytics, storage, service workers, or a backend.
- Do not run shell commands, subprocesses, browser automation, or delegated work inside a safe-operation run.
- Do not claim that source inspection proves browser execution; manual browser evidence remains separate from constrained verification in this first release.
- Do not commit or push changes.

## Users

- Richard, evaluating whether the constrained workflow is understandable and operationally useful.
- Maintainers inspecting the resulting audit artifacts and phase handoffs.

## Requirements

- The application must accept one finite numeric temperature and explicit source and target units.
- It must convert all Celsius, Fahrenheit, and Kelvin pairs, including identity conversions.
- It must reject empty, non-finite, and below-absolute-zero inputs with clear visible feedback.
- It must display successful results to two decimal places and identify both units.
- Controls and feedback must be keyboard accessible and labelled for assistive technology.
- All assets must be local files under `docs/` with the prefix `safe-operation-converter`.
- Browser self-tests must cover canonical conversions, identity conversion, absolute-zero boundaries, invalid input, and round-trip tolerance.

## Assumptions

- A modern browser can open the HTML files directly from disk.
- The installed safe-operation runtime remains version `0.1.0` with schema `1.0` and permits only read/patch operations.
- Existing uncommitted repository changes are intentional user work and must remain unchanged.
- The browser-native tests will be run manually after constrained verification because command and browser execution are disabled inside the first-release constrained policy.

## Constraints

- Preserve the current repository snapshot and stop on relevant drift.
- Use only existing directories so safe execution does not require directory-creation commands.
- Confine product changes to the exact files declared by the current phase.
- Keep application logic deterministic and free of external data.
- Process one constrained phase at a time and stop after its verified handoff.

## Proposed Approach

Use a small global browser API for pure conversion and validation functions, a separate DOM controller, a dedicated stylesheet, and semantic HTML. Phase 1 supplies the complete runnable vertical slice. Phase 2 adds a deterministic in-browser test harness and a link from the application to that harness.

## Implementation Phases

### Phase 1: Runnable Converter Walking Skeleton

- [ ] Implement the complete local converter described in [the Phase 1 checklist](phase-1-runnable-converter.md).
- Target only the four new `docs/safe-operation-converter` application files.
- Exit only after constrained verification records a locally openable conversion workflow.

### Phase 2: Browser Self-Tests And Test Entry Point

- [ ] Implement the deterministic test harness described in [the Phase 2 checklist](phase-2-browser-self-tests.md).
- Add one new prefixed test page and its declared local link from the application.
- Exit only after constrained verification records complete deterministic test coverage in source.

The repository checkboxes remain unchanged during constrained execution. Verified phase status is maintained in the canonical external working-diary overlay.

## Validation Plan

- Each phase must pass deterministic preflight and fresh semantic assessment.
- Each `safe: true` bundle must be revalidated immediately before every mutation.
- The coordinator must compare the final product snapshot with every phase success criterion.
- A context-separated verifier must inspect all declared outputs and forbidden effects.
- After a terminal verified handoff, open the relevant local HTML file manually and record browser results separately from constrained verification.
- After the successful build, optionally run a newly identified drift experiment in which a target preimage changes after assessment; the expected result is a stop before mutation and preservation of the user change.

## Risks

- The current constrained runtime cannot execute the browser tests. Mitigation: keep formulas and cases explicit, verify source state in the constrained run, and record a separate manual browser smoke test.
- Existing user changes could invalidate a repository snapshot. Mitigation: target only new prefixed files and stop rather than overwrite any changed preimage.
- Workflow ceremony may dominate such a small application. This is intentional: the pilot evaluates the control workflow, not delivery speed.
- Instruction-only assessor/verifier separation is weaker than host-proven isolation. Report this limitation in every handoff.

## Success Criteria

- Both phases reach the runtime lifecycle state `verified` from unchanged `safe: true` bundles.
- Only the declared `docs/safe-operation-converter*` product files are created or modified by safe-operation execution.
- Existing modified files, especially `README.md`, remain byte-for-byte untouched by the product operations.
- The application works from a local browser with no network requests or installation.
- The browser self-test page visibly reports all declared cases passing when run manually.
- Canonical artifacts, audit event heads, phase-status overlays, enforcement limitations, and exact next actions are preserved in the external diary.

## Open Questions

- Whether to perform the optional deliberate repository-drift experiment after the successful two-phase build. This is intentionally deferred until the application itself is complete.
