# Phase 2: Browser Self-Tests And Test Entry Point

## Phase ID

`phase-2`

## Goal

Add a deterministic browser-native test page for the converter core and make that test page discoverable from the application without adding dependencies or command execution.

## Scope

- Create `docs/safe-operation-converter-tests.html`.
- Modify `docs/safe-operation-converter.html` to add a local link to the self-test page.
- Exercise the public pure-function API created in Phase 1.

## Non-scope

- Changes to conversion formulas unless Phase 1 verification identifies an in-envelope repair before its terminal state.
- Test frameworks, package managers, browser automation, network access, storage, or backend services.
- Changes to any file without the `docs/safe-operation-converter` prefix.

## Dependencies

- Phase 1 has reached `verified` and its external diary handoff identifies this phase as next.
- The Phase 1 product files match the new Phase 2 repository snapshot.

## Task Checklist

- [ ] Create a self-contained HTML test runner that loads the local core script and reports individual and aggregate results.
- [ ] Add deterministic cases for freezing, boiling, cross-unit absolute zero, identity conversion, invalid values, unknown units, and round-trip tolerance.
- [ ] Add a local self-test link to the application without changing its conversion workflow.
- [ ] Present pass and fail states accessibly and without external assets.

## Verification Checklist

- [ ] Confirm the exact new test page and declared application link are the only product changes.
- [ ] Confirm every required case has an explicit expected value or expected error.
- [ ] Confirm tolerance comparisons are finite and explicit.
- [ ] Confirm the test runner catches individual failures, continues through all cases, and displays totals.
- [ ] Confirm all scripts and links are local and no command, package, network, storage, analytics, or backend path was introduced.

## Tests To Add Or Run

- Constrained verification: test-source and product-state inspection only.
- Separate post-verification manual check: open `docs/safe-operation-converter-tests.html` and confirm all cases visibly pass.
- Separate post-verification manual check: follow the test link from the application and return to the converter.

## Exit Criteria

- The safe-operation coordinator reaches `verified` for the exact Phase 2 bundle.
- The test page covers every required deterministic case and is discoverable from the application.
- The final handoff records no remaining phase IDs and accurately distinguishes constrained source verification from the separate browser result.
