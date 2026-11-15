# Independent review of the instruction edition

The instructions preserve the proposed testing and evidence requirements and clearly state that no executable runner is supplied. One adjacent regression test initially failed because its sample no longer exceeded the increased metadata budget. The parent corrected that fixture, and this reviewer confirmed that the focused regression suite now passes. This review does not qualify a working runner or demonstrate that agents follow the skill reliably.

Review date: 2026-11-15. Scope: `rb-build-test-suite/` instructions, references, schemas, metadata and eval definitions; adjacent README, Claude profile, routing and contracts. The deferred implementation under `development/` was excluded. Applied the repository guidance, `rb-write-skill`, its authorised post-draft `rb-simplify-language` audit method, and relevant review and multi-agent ownership rules. Only this review file was written.

## Finding resolved during review

### [P2, resolved] Move the metadata overflow fixture across the new boundary

Location: `evals/skill-routing/tests/test_skill_repairs.py`, lines 120–154 at review time.

The fixture creates 27 descriptions of 40 words (1080 words), then adds one word. With the new 1115-word limit, both samples should pass. Only the expected diagnostic was changed; the assertion that 1081 words fails now contradicts the policy. A focused run of `python3 -m unittest discover -s evals/skill-routing/tests -p test_skill_repairs.py` ran 12 tests and failed exactly this assertion (`0 == 0`, line 153).

Construct samples at 1115 and 1116 words while keeping the separate individual-description and long-description-count constraints satisfied. Preserve the negative assertion. The budget increase itself is justified: adding one active skill warrants a bounded additional allocation, existing descriptions were preserved, and the aggregate check remains. The failing fixture, rather than the increase, requires repair. The parent repaired the fixture to accept exactly 1115 words (27 × 40 + 35) and reject 1116. This reviewer inspected the repair and reran the focused suite: all 12 tests passed. The negative assertion remains intact.

## Requirements preserved

- The catalogue retains all 43 consecutively numbered stable entries. Comparison with the accepted specification shows only its title and introductory edition wording changed. Scientific and differential checks remain cross-cutting considerations; no invented 44th capability was added.
- All four original assurance findings remain operative: routine adoption covers ordinary, scientific, plan and direct completion; change-impact review accounts for new behaviour and justified exclusions; actual import/build origins and exact test identities must match the candidate; static evidence discloses configuration and unchecked regions while assessment prevents Ruff fixes and fix-only behaviour.
- Scientific verification, numerical agreement, assumptions and empirical validity remain distinct. Independent verification records actual context, permissions, invocation and oracle separation. Required domain expertise cannot be supplied by simply naming a second model. Missing evidence remains incomplete.
- The host and runner validate agent proposals and evidence. A shared workspace is not isolation. Local instructions are explicitly cooperative; protected CI requires authenticated producer/candidate/policy evidence and inspection of protections and bypass controls.
- Existing authority is reused. Profiles and operational focus do not grant new live-action permissions. Missing decisions block affected claims, and independent work continues. The unsaved-focus question is a product choice already specified, not a new permission request.
- Instructions, README, metadata and reference introductions explicitly identify this as an instruction edition. Example runner commands describe target-project interfaces to construct and qualify. No nonexistent bundled script is represented as available execution tooling.
- Markdown resource links in the skill, README and references all resolve locally. Schema references are package-relative with stable identifiers; references explicitly require local resolution. The Claude profile includes this portable skill, and the README gives both invocation forms. This inspection is not an installed-host discovery test.
- Existing instruction and consistency contract entries were compared as parsed JSON; no pre-existing entry was removed or changed. Formatting expansion in the files does not change those constraints.

The language audit found no additional material ambiguity requiring a behaviour change. Actor ownership, failure handling, current candidate identity and the distinction between proposed contracts and implemented tools are explicit. The long references contain implementation requirements; their length alone is not a defect or a reason to remove safeguards.

## Three bounded semantic decision probes

These are this reviewer's reasoned applications of the written instructions. They are not independent agent outcome trials, executed target suites or measurements of routing reliability.

| Probe | Decision derived from the instructions | Limit |
| --- | --- | --- |
| New scientific output while old tests pass | The fixture's old conservation test does not assess the new kg-to-tonnes output. Its requirements specify 1000 kg = 1 tonne, while the conversion divides by 100. Add a discriminating conversion assertion within the suite-building scope; preserve application bytes and failed evidence. Passing conservation alone cannot verify this change. Numerical correctness still would not establish empirical validity. | Fixture source and requirements were read, not executed as an agent trial. |
| “Run our existing tests” | Do not select suite construction. Inspect and use the adopted command within existing authority, report its actual outcome, and preserve missing evidence. Rebuilding the infrastructure merely because tests were mentioned violates the trigger boundary. | Semantic routing check only; no target command executed. |
| Extend suite with Ruff fix-only settings and unchecked untyped functions | Qualify the tool version and disable both fix and fix-only, reject masked exits, capture effective nested scope and compare source bytes. Define and disclose the type-checking claim, including untyped bodies, Any, imports and suppressions. Either detect the defect under the required claim or retain the uncovered region as a limitation/gap; do not impose universal strict typing. | No real Ruff/mypy qualification or static-scope fixture trial was run. |

Each probe has an explicit rule and a discriminating failure consequence in the active references. None requires pretending that bundled execution code exists.

## Eval adequacy and verification limits

The 16-case manifest covers construction paraphrases, five neighbouring negative routes, scientific output, adoption, stale imports, static scope, missing verification and the absent-runner boundary. Ten routing cases mirror the main trigger distinctions, and their file is included in the root routing manifest’s explicit `case_files` list (verified after the parent added it). These are a useful initial definition of future trials, not completed behavioural evidence. The scientific fixture supplies a concrete defect and describes a healthy control. Several other regression cases still require their scenario-specific environment or artifacts when trials are executed; the shared mass fixture alone does not instantiate old installations, Ruff configuration or protected CI. The reference acceptance cases retain the broader obligations.

This review independently checked catalogue continuity and preservation, resource-path existence, existing contract retention, and the focused metadata regression suite. Parent-reported manifest, metadata, instruction and consistency checks were not rerun solely to duplicate their evidence. Full repository regression checks, schema execution tests, installed Codex/Claude discovery, actual tool/host qualification and all with-skill/without-skill trials were not performed by this reviewer. The parent owns the remaining repository checks and completion decision.

Verdict: the instruction edition is substantively coherent within the requested scope. The identified metadata-test defect is resolved; no actionable finding remains in the reviewed instruction scope. Repository completion remains subject to the parent’s applicable checks. No claim is made that the deferred executable system or target-project testing has been completed.
