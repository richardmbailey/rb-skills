# Review corrections and validation

The specification and implementation plan now require the saved suite to be used
for later project changes and require evidence that those changes were assessed.
This is a design correction, not an implemented testing system.

Date: 2026-11-15. Scope: all four findings in the
[original independent review](independent-assurance-review.md). That report is
preserved unchanged. The [change-assurance contract](assurance-contract.md) owns
the new requirements; the existing interface, evidence/report, capability,
draft-skill and plan documents link and incorporate them.

## Corrections

| Finding | Specification and schema changes | Implementation and verification |
| --- | --- | --- |
| F1: ordinary changes could omit the suite | Required project adoption, saved command, final-candidate completion rule, honest cooperative/protected distinction; typed `Adoption` | P2.7 creates adoption; P8.8 integrates and trials later implementation; P7.8/P9.1 qualify requested protected aggregation. F1a–F1c include absent/stale/partial runs and bypass attempts. |
| F2: new behaviour could escape an old passing suite | Versioned `ChangeImpact`, deterministic change inventory, semantic behaviour/requirement/check reconciliation, reviewed exclusions and unresolved scientific coverage | P1/P2 validate inventory and gaps; P4.6/P8.8 test the new exported units defect, documentation-only and already-covered controls. F2a–F2c govern phase review. |
| F3: tests could import the wrong package or select different tests | Typed execution contracts/evidence, first-party origins, artifact/source manifests and exact test IDs | P4.8 qualifies checkout/editable/distribution/script routes; P4.1/P4.7 preserve custom discovery and reject same-count substitutions. F3a–F3b include stale installation and missing package data. |
| F4: empty diagnostics could conceal unchecked code or edits | Typed intended/effective static scope, type-policy limitations, nested config and suppressions; Ruff fixes/fix-only disabled; separate optional formatting check | P4.3 tests real tool configurations and healthy gradual typing; P6.1 exposes limitations. F4a–F4c include untyped/Any cases, source preservation and required violations. |

The four public schema files remain in place. New shared definitions are
required by their relevant roots. This changes an unreleased draft, not a
published 1.0.0 interface. P1 must review the draft compatibility difference
when generating implementation schemas.

All 43 capability IDs and nine HTML sections are retained. The plan has ten
phases and 71 unique tasks, all planned. No active skill, installation, branch
protection or target application was changed.

## Checks performed

- All **15 schema tests passed**, including the original nine and six added
  methods for adoption/protection, impact review and coverage, documentation and
  rename records, execution identities, static scope and required closed fields.
  These are structural tests with synthetic data. They do not establish import
  capture, semantic coverage, authentication, tool compatibility or runtime gates.
- Instruction contracts and consistency contracts passed using the repository
  validators and their existing manifests.
- The catalogue/schema check confirmed exactly 43 IDs in the original order.
- A plan check confirmed ten phases and 71 unique task IDs, all marked planned.
- Local document links resolved. A direct scan of draft Markdown, Python and JSON
  found no trailing whitespace. `git diff --check` passed; the direct scan also
  covered the untracked draft package.
- Applied the `rb-write-skill` post-draft `rb-simplify-language` review: checked
  actor ownership, sequence, required versus optional controls, scientific claim
  boundaries and failure outcomes. Moved adoption/impact and execution planning
  before dispatch; kept the final candidate comparison at completion.

Schema command, using the existing temporary Python environment with
`jsonschema` 4.26.0 and format validation dependencies:

```bash
python -m unittest discover \
  -s docs/rb-build-test-suite-specification/checks -v
python3 evals/skill-routing/validate_instruction_contracts.py \
  evals/skill-routing/instruction-contracts.json
python3 evals/skill-routing/validate_consistency_contracts.py \
  evals/skill-routing/consistency-contracts.json
git diff --check
```

The environment path is local validation evidence, not a proposed project
installation dependency. This package remains an unpublished draft.

## Independent check

A fresh reviewer, who did not author these revisions, checked the original four
findings against the documents, schema fields and planned acceptance cases. The
reviewer found that the initial revised draft loaded assurance requirements too
late in its procedure and omitted the new reference from the proposed package
layout. Those issues were repaired. A focused follow-up also moved optional CI edits
before the frozen run and kept final completion last. The final
finding-by-finding verdict and limits are in the
[independent resolution check](review-resolution-check.md).

## Checks not run and remaining limits

No runtime, target-project suite, Ruff/mypy adapter, installed-artifact workflow,
HTML browser test, protected CI deployment, OS matrix, live verifier handoff or
agent behavioural trial ran. Those components are not implemented; their
required discriminating tests belong to the named future phases.

The full constrained-runtime suite and unrelated behavioural eval-manifest suite
were not rerun because no constrained-runtime, active skill, routing metadata or
eval manifest changed. Active-skill metadata validation was likewise not needed.
The focused checks cannot establish full repository CI or future release readiness.

Local adoption remains cooperative. Deployed protection needs authorized setup
and inspection. Semantic adequacy and scientific validity still require the
specified review and domain evidence; a finite passing suite gives no guarantee
outside its assessed claims.
