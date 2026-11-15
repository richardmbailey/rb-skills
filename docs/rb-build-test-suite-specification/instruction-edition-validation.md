# Instruction edition validation

Date: 2026-11-15. The user selected skill instructions and references first.
The active `rb-build-test-suite/` package supplies that edition, including all
43 catalogue entries, four reference schemas, host metadata and evaluation
definitions. It does not supply an executable runner, adapters or HTML renderer.

## Completed checks

| Check | Observed result |
| --- | --- |
| Repository routing regression suite | 46 tests passed |
| Reviewed schema acceptance cases against packaged reference schemas | 15 checks passed |
| Active skill evaluation manifests | 32 manifests validated; new skill has 16 cases |
| Root routing manifest | Passed, including the new routing case file |
| Instruction and consistency contracts | Passed |
| Skill metadata | Passed for 35 skills; 1100 aggregate description words |
| Publication hygiene and `git diff --check` | Passed |
| Catalogue continuity and Markdown resources | All 43 entries retained; resource links resolve |
| Independent instruction review | No remaining actionable findings in this scope |
| Codex installation | Installed symlink resolves to the repository skill |
| Claude installation | Generated installed copy reports current; manifest and resource checks passed |

The [independent review](instruction-edition-review.md) records its own scope,
three semantic decision probes and limitations. Those probes are reasoned
applications of the instructions, not measured agent trials.

Adding the skill required raising the aggregate metadata budget from 1080 to
1115 words. The regression suite exposed an obsolete overflow sample. The
repaired boundary test accepts 1115 and rejects 1116 words; its negative
assertion remains. The independent reviewer confirmed the repair, and the full
46-test regression suite subsequently passed. Existing skill descriptions and
pre-existing instruction and consistency contract entries were preserved.

Both installed editions were checked for all 43 entries and resolving Markdown
resource links. Installation checks establish file placement and generated-copy
consistency; they do not establish model routing or successful host invocation.

## Deferred work and limits

Repeated with-skill/without-skill behavioural trials have not been run. Several
eval scenarios need their own environments when trials are performed. Valid
manifests and schemas do not demonstrate reliable agent behaviour or application
correctness.

No target-project suite, live adapter, browser report, protected CI integration
or host invocation was qualified for this edition. The unrelated constrained
runtime suite was omitted because its runtime, generated schemas and launcher
were unchanged. The packaged schemas are design contracts, not proof that a
runtime enforces their semantics.

Partial executable work begun before the scope clarification is preserved under
`development/rb-build-test-suite/`, outside active skill discovery and installation.
Its earlier checks and independent reviews are historical prototype evidence;
they do not qualify a completed executable system. The
[implementation plan](IMPLEMENTATION_PLAN.md) records completed, unreviewed and
deferred work separately. Future executable work requires a new implementation
request; this instruction-edition delivery does not complete that broader plan.

No commit or push was performed.

## Fresh independent review and repairs, 2026-11-15

A new reviewer independently identified three P2 issues and confirmed their
repairs in [the follow-up review](fresh-instruction-review.md):

- Verifier dispatch now follows the selected method and project policy.
  Scientific-core acceptance still requires independent verification by default;
  justified non-selection does not waive change-impact review.
- One permitted read-only transport retry now has an explicit logical-module
  aggregation rule. Its complete evidence can determine the result only with
  unchanged bindings and no earlier violation or uncertain external effect.
  Both attempts remain visible, without combining partial results or double-counting.
- The schema checks now load the active distributed package by default, including
  its catalogue. CI runs them with format-validation dependencies and includes
  their outcome in its final failure gate.

Validation after these changes: all 46 repository regression tests and all 15
packaged-schema checks passed. A temporary copy with a deliberately broken
evidence-schema reference was rejected by the same test command. The workflow
parsed and its schema-test step was confirmed in the final gate. Instruction and
consistency contracts, the revised eval manifest, publication hygiene and
`git diff --check` passed. Three new semantic decision probes bring the skill's
manifest to 19 cases; these are definitions, not executed behavioural trials.

The existing static-tool guidance was checked against current primary
[Ruff configuration documentation](https://docs.astral.sh/ruff/configuration/),
[Ruff formatting documentation](https://docs.astral.sh/ruff/formatter/) and
[mypy guidance](https://mypy.readthedocs.io/en/stable/common_issues.html).
No additional tool-guidance correction was needed.

Codex's existing symlink exposes the corrected source. The supported generator
refreshed Claude's copy, retained a backup and confirmed it current. No runtime
implementation was added. The full GitHub-hosted workflow and unrelated
constrained-runtime suite were not run locally; the new schema step was exercised
in the existing disposable validation environment. Host invocation trials,
repeated skill evaluations and target-project qualification remain unperformed.
