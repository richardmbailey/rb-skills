# P1 implementation contracts and checks

The first implementation slice validates records and evaluates available local
artifact evidence. It does not run project code, invoke a verifier, construct a
suite or render a report. Missing authentication, live observations, protected
CI verification and reused evidence remain insufficient until their owning
integrations are qualified.

## Source and schema compatibility

Typed models in `rb-build-test-suite/src/rb_test_suite/models.py` generate the
schemas. `scripts/export_schemas.py --check` detects export drift. Schema version
is 1.0.0; package/evaluator version is 0.1.0. No published consumer exists.

[The compatibility record](p1-schema-compatibility.json) records added roots and
public field differences. The original 15 schema tests also pass against the
generated schemas. They retain the original fixture definitions while replacing
the validation registry; this avoids mistaking generated reference organization
for a changed public data shape.

`EvidenceRun.evaluation` is optional for a producer's initial record. Evaluation
emits provenance identifying the original input, evaluated content, policy,
evaluator version and evaluation timestamp. Revalidation rejects mismatched
content, decisions, version or policy and preserves an existing valid evaluation
timestamp. The input object is not mutated. Unsupported versions/migrations are
rejected; a future migration must preserve original evidence and identify its
new derivation. The runner must retain original observations before finalisation.

## Authoring configuration and candidate identity

Configuration contains `ModuleRequest`, `ExecutionRequest`, `StaticRequest` and
`AdoptionRequest`, plus paths to reviewed change-impact and imported operational
records. These requests have no candidate digest, run ID or finished assessment.
The runner compiles requests into the public candidate-bound `ModulePlan` and
`Adoption` records after all source, test, configuration and policy edits finish.

This avoids making the configuration hash depend on a candidate digest stored
inside that same configuration. The source snapshot includes authoring config,
tests and relevant source/data. Derived plans, receipts, reports and reviewed
change-impact control records are kept outside that source hash, with their
exclusions explicit. Their own content hashes remain part of the run evidence.
Finalisation and completion must compare both the source snapshot and the frozen
control-record identities. Exclusion from the source snapshot is not permission
to change a review, policy, test or decision without invalidating its evidence.

P2 owns containment, snapshots and configuration compilation; P3 owns persisted
observations, finalisation and completion checks. No claim of actual execution
identity follows from a correctly shaped authoring request.

## Independent checks and repaired defects

The first implementation review found false acceptance when test counts contained
a failure and when a plan referenced an absent input. It also found that a stored
gate's policy identity could be silently replaced. Regression tests now reject
these cases while retaining healthy controls. Artifact hashes are streamed;
verified frozen-plan bytes must match the supplied plan.

Parent-authored cross-record tests use literal outcomes from the public independent
oracle packet. They cover complete and omitted results, required deep omissions,
failures with gaps, blocked/timeout/cancelled execution, optional failures,
repeated attempts and blocking findings. These exercise the evaluator with real
local synthetic artifact files; they do not claim real pytest or agent receipts.

The original independent review and focused repair verdict are preserved in
[p1-review.md](p1-review.md). All later phases remain subject to their own gates.
