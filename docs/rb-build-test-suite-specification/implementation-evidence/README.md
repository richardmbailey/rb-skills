# Implementation evidence

Implementation started after the user requested the skill. Task states remain in
[the implementation plan](../IMPLEMENTATION_PLAN.md); this directory preserves
observed checks and their limits. This is evidence for the deferred full-system
prototype, not the separately delivered [builder/auditor workflow](../../test-suite-system/README.md).

- `baseline.json` identifies the preimplementation sources, observed environment,
  selected dependencies, host capabilities, rubric and bounded trial matrix.
- `baseline-requirements.lock`, `probe_dependencies.py` and
  `dependency-probe-result.json` make the dependency checks reproducible.
- `requirements.json` maps all 43 capabilities and common/scientific contracts
  to owning tasks and acceptance evidence.
- `initial-oracles.json` is an independent preimplementation decision/fixture
  packet. Its reserved cases must be omitted from implementation-agent packets;
  shared storage does not enforce secrecy.
- `oracle-checks/` demonstrates discrimination of independent analytical toy
  artifacts. These checks do not qualify the future runner or generated tests.
- `p0-review.md` preserves the independent baseline review and repair verdict.

Do not infer platform, agent, production, package or runtime qualification from
schema validity, dependency imports, a proposed case or a passing toy evaluator.

## Implementation clarification

The machine-readable catalogue permits a null `original_phase` with an
`original_phase_note` because the available source does not establish the
original diagram grouping. This historical metadata does not control selection,
requiredness or acceptance. All 43 stable IDs and their construction contracts
remain unchanged. The module interface now states this explicitly.
