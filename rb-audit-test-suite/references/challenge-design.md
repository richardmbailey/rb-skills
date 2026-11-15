# Design executable challenges to the tests

Derive expected behaviour independently from requirements, analytical results,
trusted reference data or an independently implemented algorithm. First establish
that the proposed healthy control meets those expectations. A baseline labelled
healthy is not proof that its complete implementation is correct.

## Select challenges before measuring success

For each required risk, record its requirement, fault, expected detecting test,
independent reference, allowed side effects and finite timeout. Prioritize known
failures, business/scientific invariants, boundary conditions and real integration
paths. Do not maximize a mutation percentage by selecting only easy faults.

A challenge can alter an equation, omit a receiving update, change units, corrupt
an output, remove validation, suppress test discovery or make a required command
fail. Apply defects only to disposable copies. Keep the candidate/test hashes and
exact mutation or fixture. Do not permit a mutation to edit the oracle or its own
expected result. Equivalent mutations are not defects: require a reasoned,
reviewed disposition rather than weakening an assertion to classify them as killed.

## Use native testing tools

A pytest audit test can launch the saved project test command in a temporary
project, request JUnit and parse it with an XML parser. It asserts:

- the healthy run passed a nonempty intended selection;
- the faulty run executed the intended tests against the intended candidate;
- the expected test failed its relevant assertion;
- collection/import/setup failures, unexpected skips and timeouts did not supply
  the claimed detection;
- raw logs, XML and changed source remain available.

Return normal test failure when any of these conditions is false. Missing or
malformed output is an invalid challenge. Checking only `returncode != 0` or
searching for the word `error` does not establish defect detection. Native report
parsing establishes structure; a bounded review establishes that the failure
matches the intended defect. Validate new parsing/helpers with both valid and
invalid cases. Reuse a suitable existing mutation tool for broader campaigns.

Keep child pytest discovery bounded with explicit config and `--confcutdir` for
standalone copies. Use fresh owned `--basetemp` paths. Do not disable production
plugins merely to simplify a test or clear unrelated caches to remove warnings.

## Preserve historical evidence

Inventory confirmed failures before writing new tests. Preserve exact failing
inputs, expected results or relations, numerical tolerances and the failure mode.
Keep the fixed healthy version and a minimal reintroduction where practical.
The check must demonstrate failure before repair and success after repair.

The numerical trials taught two specific lessons for the two-store Euler example:

- `simulate(1, 0, nextafter(10, 0), 0.5, 0.1)` must retain nonnegative stores when
  floating timestamps are subtracted near the stability boundary.
- `simulate(1, 0, 0, 1e-308, 1e308)` must retain the positive final timestamp even
  though the floating quotient duration/dt underflows.

These inputs apply to that interface and model, not every scientific application.
For another project, derive corresponding boundaries from its arithmetic and
requirements. Preserve the original failure until its replacement demonstrably
exercises the same defect. Random examples or a nearby floating value do not
establish that an exact historical failure is covered.

## Audit the execution path too

Check that a failed early test, lint/type command, absent executable or timeout
makes the saved completion command fail. Include missing/empty collection,
skipped required tests, stale candidate identity and a healthy control. Preserve
partial logs. Audit tests should not rely on the same untested helper they are
supposed to validate; use direct observable exits, native receipts and fixtures.

An auditor can find a production defect while testing the tests. Keep that finding
separate. Do not change product behaviour unless authorized, and never change the
expected answer merely to match existing output. If the requirement itself is
wrong or ambiguous, stop the affected acceptance claim and record the decision
needed from its owner.
