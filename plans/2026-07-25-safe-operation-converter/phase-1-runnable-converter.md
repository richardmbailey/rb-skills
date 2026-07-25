# Phase 1: Runnable Converter Walking Skeleton

## Phase ID

`phase-1`

## Goal

Create a complete local browser workflow in which a user enters a temperature, selects source and target units, requests conversion, and receives either a correctly formatted result or clear validation feedback.

## Scope

- Create `docs/safe-operation-converter.html`.
- Create `docs/safe-operation-converter.css`.
- Create `docs/safe-operation-converter-core.js`.
- Create `docs/safe-operation-converter.js`.
- Implement deterministic conversion, physical-bound validation, DOM interaction, accessibility, and responsive presentation.

## Non-scope

- Browser self-test page.
- Dependencies, build tooling, commands, network access, persistence, analytics, or backend services.
- Changes to any existing repository file.

## Dependencies

- The parent implementation plan is approved with `Execution Route: constrained`.
- The safe-operation runtime and schema identities pass preflight.
- All four target files are absent at planning and immediately before execution.

## Task Checklist

- [ ] Create pure conversion and validation functions for Celsius, Fahrenheit, and Kelvin.
- [ ] Create the semantic HTML form, accessible result region, and local asset references.
- [ ] Create the DOM controller for conversion, unit swapping, validation feedback, and initial focus-safe state.
- [ ] Create a responsive stylesheet with clear focus, success, and error states.

## Verification Checklist

- [ ] Confirm the four exact target files exist and no other product file changed.
- [ ] Confirm conversion formulas cover all source and target unit pairs, including identity conversion.
- [ ] Confirm empty, non-finite, unknown-unit, and below-absolute-zero inputs fail visibly without producing a result.
- [ ] Confirm successful values are displayed to two decimal places with source and target unit labels.
- [ ] Confirm every interactive control has a visible or programmatic label and feedback uses an appropriate live region.
- [ ] Confirm all references are local and there are no dependency, network, storage, analytics, or backend paths.

## Tests To Add Or Run

- Constrained verification: source and product-state inspection only.
- Separate post-verification manual check: open `docs/safe-operation-converter.html`, convert `0 °C` to Fahrenheit, and confirm `32.00 °F` is shown.
- Separate post-verification manual check: enter `-274 °C` and confirm a below-absolute-zero error is shown.

## Exit Criteria

- The safe-operation coordinator reaches `verified` for the exact Phase 1 bundle.
- The four declared files form a complete locally openable converter.
- The handoff preserves `phase-2` as the sole remaining phase ID and discloses that browser execution was not part of constrained verification.
