# Draft validation record

This record describes checks of the specification and its schemas. No target
project test suite, operational adapter, independent verification service or
HTML renderer has been implemented by this work.

Date: 2026-11-15. The working tree was clean before this draft. Changes are
limited to this specification package and a discovery link in the root README.

## Checks completed

| Check | Result and scope |
| --- | --- |
| Draft schema tests | 9 tests passed, including valid records and negative subcases |
| Catalogue consistency | Exactly 43 unique IDs in the required order, matching schema enums |
| JSON Schema metaschemas | All four schemas validated against Draft 2020-12 |
| JSON syntax | 48 repository/draft JSON files parsed successfully |
| Proposed skill metadata | Draft frontmatter and Codex metadata parsed and checked separately |
| Instruction contracts | Passed for existing active skills |
| Consistency contracts | Passed for existing active skills |
| Metadata validator | Passed for 34 existing in-scope skills |
| Behavioural eval manifests | All 32 active/Claude manifests validated; this does not mean agent trials ran |
| Skill routing regression suite | 46 tests passed |
| Publication hygiene | Existing control-state hygiene check passed; new draft also inspected for local paths and credentials |
| Independent design review | Two material interface gaps identified and corrected; reviewer confirmed both fixes |
| Language review | Applied `rb-simplify-language` under the authoring procedure; clarified import ownership, criterion semantics and invalid-report handling |
| Whitespace and local links | Tracked diff and new draft whitespace checked; local Markdown links resolve |

The review added a typed evidence-import contract and embedded criterion
definitions in the report model. Regression cases cover required reviewer and
invocation identities, observation constraints and missing report definitions.
Other negative cases cover malformed timestamps, unknown fields and capability
IDs, empty criteria, invalid hashes, missing receipts, invalid pass states and
acceptance before run finalisation.

An initial timestamp test failed because the basic JSON Schema installation did
not enforce date formats. Installing its format-validation extra and requiring
format assertions fixed the validation environment; the test was retained.
The temporary validation environment used Python 3.14 and jsonschema 4.26.0.
This is schema-check tooling, not a proposed target-project dependency lock.

Reproduce the draft checks in an isolated environment with
`jsonschema[format-nongpl]` installed:

```bash
python -m unittest discover -s docs/rb-build-test-suite-specification/checks -v
python3 evals/skill-routing/validate_instruction_contracts.py evals/skill-routing/instruction-contracts.json
python3 evals/skill-routing/validate_consistency_contracts.py evals/skill-routing/consistency-contracts.json
python3 evals/skill-routing/validate_publication_hygiene.py
ruby evals/skill-routing/validate_skill_metadata.rb
python3 -m unittest discover -s evals/skill-routing/tests -p 'test_*.py'
for manifest in rb-*/evals/eval-plan.json platforms/claude/skills/*/evals/eval-plan.json; do
  python3 rb-create-skill-evals/scripts/validate_eval_manifest.py "$manifest"
done
git diff --check
```

## Checks deliberately not performed

- Constrained-runtime unit suites, Python-version matrix, dependency wheelhouse
  preparation and generated-schema drift checks: no runtime, constrained schema,
  launcher or constrained-workflow files changed. This draft provides no new
  evidence about their runtime behaviour.
- Full existing-source compile sweep: existing executable sources were unchanged;
  the new schema test module was imported and executed by its tests.
- Live agent behavioural trials, actual tool-adapter integration, generated-suite
  end-to-end tests, operating-system matrix and HTML/browser accessibility/security
  tests: these require the implementation. Their acceptance cases are specified
  in the main document; they are not reported as passed.
- Remote CI execution/artifact upload, sync dry-run and installation: this is a
  local design draft and does not add an active skill or publish anything.

Cross-record semantic validation, authenticity checking and report escaping
remain implementation requirements. The schema tests deliberately establish
structural acceptance/rejection only; they do not claim those behaviours exist.

## Continuation

The requested specification is drafted. The next possible task is review of
the proposed defaults and implementation scope, then implementation under the
repository's planning/testing workflow if requested. The present request does
not authorise installing the skill, deploying operational controls or running
tests against a user's production systems.
