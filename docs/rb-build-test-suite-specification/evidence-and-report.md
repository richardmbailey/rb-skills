# Evidence and HTML report contracts

The report must let a reader see what was checked, what failed, and which
claims remain unsupported. It must also let them follow a conclusion back to
the candidate, requirements, tool output and independent reference that produced
it. A good-looking report cannot turn missing evidence into successful testing.

## 1. Schema package

All JSON schemas use Draft 2020-12 and a package-local shared definitions file:

| File | Root object |
| --- | --- |
| [module-plan.schema.json](schemas/module-plan.schema.json) | Normalised check plan |
| [evidence.schema.json](schemas/evidence.schema.json) | One candidate-bound run |
| [report.schema.json](schemas/report.schema.json) | Presentation model derived from that run |
| [contracts.schema.json](schemas/contracts.schema.json) | Shared typed objects and enums |

Validators must enable date-time format assertions, not just annotations, and
resolve all schema references locally. Test an invalid calendar date and an
invalid timestamp string when configuring a validator. Timestamps use UTC `Z`.
Unknown fields are rejected on closed objects. Each record includes
`schema_version: "1.0.0"`. Unsupported major versions fail before dispatch or
import. Future migrations must preserve the original bytes and hashes and emit
a new derived record with migration provenance. Do not reinterpret old outcomes
using new rules without identifying the new policy and evaluation.

Schema validation enforces shape, types and enums. The deterministic semantic
validator also enforces path containment, unique IDs, reference integrity,
time order, digests, candidate matching and the rules below. Passing a JSON
schema alone is not proof that the record is true or internally consistent.

## 2. Evidence record

| Object | Required information |
| --- | --- |
| `candidate` | Snapshot digest; commit/dirty state if Git exists; scope and excluded inputs |
| `adoption` | Saved runner/instruction references, supported workflows, completion state and actual enforcement level |
| `change_impact` | Versioned current-change inventory, reviewed behaviour/requirement/check mapping and unresolved coverage |
| `provenance` | Specification, policy, test suite, config, catalogue, runner and environment digests |
| `environment` | OS, architecture, language/library versions, lock digest, declared/enforced isolation; hardware details when relevant |
| `capabilities` | Exactly 43 dispositions, required flags, module references and derived states |
| `plans` | Artifact references to every frozen executed or blocked module plan |
| `results` | Every module attempt, execution receipt, criteria decisions, counts and artifacts |
| `artifacts` | Unique ID, relative path, SHA-256, media type, byte length, sensitivity/redaction metadata |
| `findings` | Severity, claim, affected requirement/module, counterexample/evidence, remediation, blocking flag and resolution |
| `independence` | Session/context/write/oracle separation, receipts, limitations and advisory review outcome |
| `gate` | Deterministically calculated outcome, required gaps/failures and policy digest |

Use UTC timestamps and elapsed monotonic duration for process measurements.
Include tool name/version and parser version for each receipt. Executable receipts
also contain `execution_evidence` and, for static tools, `static_evidence`, following
[change assurance](assurance-contract.md). Import receipts use null for these fields.
Missing required capture is a gap; fabricated provenance cannot substitute for it. Commands are
stored with secret arguments redacted; preserve a non-secret execution identity
that allows replay without leaking credentials. Artifact hashes establish
integrity relative to a receipt, not authenticity of an untrusted producer.
Externally enforced gates need authenticated receipts from the trusted runner.

Raw evidence remains immutable after finalisation. Record redaction and
retention explicitly. Do not put secrets in public hashes or reports. If raw
data must stay elsewhere, record a controlled reference and access restriction;
its unavailability must be visible to the reader. Retention removes access to
evidence, not the fact that an assessment depended on it.

## 3. States and acceptance

Each module has both an execution state and an assessment:

| Execution state | Meaning |
| --- | --- |
| `completed` | Execution or evidence import completed; says nothing about acceptance |
| `not_run` | Not attempted, for a recorded selection/budget reason |
| `blocked` | Required input, dependency, permission, tool or environment unavailable |
| `timed_out` | Time budget exceeded; retain partial results |
| `cancelled` | User cancellation stopped execution |
| `error` | Tool/adapter/runner could not produce valid evidence |

| Assessment | Rule |
| --- | --- |
| `PASSED` | All module criteria satisfied by complete valid evidence |
| `FAILED` | At least one criterion demonstrably violated |
| `NOT_RUN` | No attempt and no evidence of acceptance |
| `NOT_APPLICABLE` | Capability has a justified exclusion; never a passing module shortcut |
| `BLOCKED` | Prerequisite or authority absent |
| `REQUIRES_REVIEW` | Evidence exists but is incomplete, inconclusive, stale or awaiting required judgement |

Modules cannot use `NOT_APPLICABLE`; that state belongs to capability
dispositions. A completed command may still fail or require review. A timeout
with an already demonstrated violation retains `FAILED`; other incomplete
attempts require review. `not_run` maps to `NOT_RUN`, `blocked` to `BLOCKED`,
and `error` to `REQUIRES_REVIEW`. Passing requires `completed`, at least one
criterion, all criteria `satisfied`, no unresolved blocking finding, and
validated artifacts. Test counts alone cannot satisfy a semantic claim.

Criterion types are `assertion`, `metric` and `attestation`. Each has a stable
ID, requirement ID, predicate, expected value/unit where applicable and a
justification. Assertion results require an executed test oracle; metrics
require a value and agreed comparison; attestations require an authorised
review receipt. Criterion outcomes are `satisfied`, `violated` or `unknown`.
Agents may supply interpretations, but cannot mark their own attestation trusted.

Capability assessment aggregates its selected modules: any failure is `FAILED`;
otherwise any unresolved assessment prevents `PASSED`. Use `BLOCKED` when
all unresolved modules are blocked, `NOT_RUN` when all are unrun, otherwise
`REQUIRES_REVIEW`. Only when every selected module passes can the capability
pass. A selected capability with no substantive modules requires review.
`not_applicable` requires an explicit reason and no required flag. An unresolved
capability requires review; a deferred capability is not run. Requirements
cannot disappear because the user requested a quick profile.

The overall gate is evaluated against the recorded scope, not every conceivable
software claim:

1. Reject an invalid record before evaluating it; generate a diagnostic report
   labelled invalid if possible and return exit `3`.
2. If a required criterion is violated or an unresolved blocking defect exists,
   set `REJECTED`.
3. Validate change-impact path accounting and review, execution identity, exact
   test selection and static scope under [change assurance](assurance-contract.md).
   Missing or unresolved material coverage, mismatched imports/selection and
   unexplained scope omissions are required gaps. If any required gap exists,
   or required evidence is absent, incomplete, stale, blocked, unrun, skipped
   or awaiting review, set `INSUFFICIENT_EVIDENCE`.
4. Otherwise set `ACCEPTED`, while retaining optional failures and limitations.

`NOT_EVALUATED` is used during incomplete execution or when no accepted policy
exists. It never yields exit `0` for a test run. Reject a policy with no required
criteria as an acceptance policy; it may support an explicitly informational
run only. A human's risk acceptance is a separate attributable policy revision,
not permission to relabel a failed check as passed.

Only a finalised record can receive `ACCEPTED`. An invalid-record diagnostic
page is a separate error view: show validation errors, run identity if known,
and preserved artifact locations. It must not display an accepted gate or
invent summary counts to fit the normal report schema.

An accepted run supports verified completion only when adoption and current final
candidate identities also match. The completion workflow must make that comparison
again when handing off the change; saved evidence cannot prove no later edit occurred.

The gate checks the source/environment identity again at finalisation. Changed
inputs invalidate affected evidence. Operational observations also require the
specified target/configuration, time window, sample volume and freshness limit.
There is no default rule that “today's results” are fresh enough.

## 4. HTML presentation schema

`report.schema.json` describes a structured presentation model, not arbitrary
HTML supplied by an agent. The renderer consumes validated evidence and derives
`summary`, capability rows, module rows, findings, scientific checks, provenance,
limitations and artifact links. The report model includes the source evidence
digest; it cannot revise the gate, timestamps, claims or results.

Each report module embeds `criterion_definitions` from its frozen plan as well
as criterion results. Match result IDs to those definitions exactly; show
expected predicate/value, observed result, units, requirement and justification
together. The HTML must not need an external plan file to explain acceptance. Each row also
embeds `execution_contract`, `static_contract`, `execution_evidence` and
`static_evidence`; retain null and explain missing capture. The root embeds
`adoption` and `change_impact`. Present their mappings and limitations according
to [change assurance](assurance-contract.md), without adding sections or capabilities.

| Section ID | Required display |
| --- | --- |
| `overview` | Candidate, scope, focus, profile, run time, gate, explicit incomplete/invalid banner |
| `capabilities` | All 43 rows; state, required flag, selection reason, module count and links |
| `checks` | Module/attempt, tool, execution state, assessment, duration and criterion details |
| `findings` | Prioritised defects and gaps, evidence links, remediation and resolved/open state |
| `scientific` | Claims, units, reference provenance, tolerances, comparison/convergence/stochastic results |
| `independence` | What separation existed, oracle sources, findings, limitations and recommendation |
| `performance` | Hardware/baseline/sample comparability, measurements and uncertainty |
| `provenance` | Digests, versions, configuration, authority summaries and raw-artifact references |
| `limitations` | Deferred/unavailable checks, unsupported platforms, stale evidence and residual risks |

Sections without relevant data show a short reason; they do not invent plots or
hide required gaps. Counts explicitly distinguish capability assessments,
logical checks, attempts and individual test cases. State totals for capabilities
sum to 43. Test totals deduplicate shared executions and identify skipped/xfail
counts. Required and optional failures are visible separately. Never calculate
an overall “confidence percentage” from coverage or a pass ratio.

The report model contains typed tables, finding IDs, artifact IDs and chart
series; it contains no raw HTML fields. Every chart includes title, axis labels,
units, series meaning, source artifact IDs and the exact plotted points. Display
the same values in an accessible table. Null or non-finite measurements are
missing data, never zeros. Numerical error and convergence charts state their
reference and tolerances. Performance comparisons without comparable baselines
are descriptive only. Disable a misleading chart and retain its underlying data.

## 5. Rendering and interaction

Produce a standalone `index.html` with embedded CSS, bounded data and optional
JavaScript. Core content and tables must be readable with JavaScript disabled.
Use no CDN, external fonts, telemetry or external asset fetches. Provide text
search, filters by state/capability/required flag, sortable tables and expandable
details without hiding incomplete evidence by default. A print stylesheet keeps
candidate identity and limitations visible. Use semantic headings, table
captions, keyboard controls and text labels in addition to colour.

Escape all tool output, names, file paths and agent text. Insert text as text,
never `innerHTML`. Encode embedded JSON so that `</script>` and related strings
cannot escape the data container. Validate internal artifact paths and allow
only explicit safe external source links; reject active URL schemes and remote
embeds. A report is never allowed to execute a command, upload evidence or
accept a baseline. These are separate runner/host actions.

The main summary is self-contained. Raw logs and large data may remain relative
linked files in the run bundle; label restricted or missing artifacts. If a
report is copied alone, it must still show the full outcome and limitations,
while warning that raw artifact links require the evidence bundle. Offer a
portable bundle as a separate export; publication is never automatic.

Write to a temporary report file, validate/render it, then atomically replace
the run report and latest copy. Do not replace a previous valid report with an
empty page. A failed report build returns exit `3` while preserving evidence
and the last valid report, visibly identified by its original run/date.

## 6. Required schema and renderer tests

Validate representative accepted, failed, blocked, cancelled and partial runs.
Reject additional fields, invalid enums, missing identities, negative durations,
unknown capability IDs, digest mismatch and wrong reference types. Semantic
tests must reject duplicate IDs, mismatched candidate/policy, paths outside the
bundle, stale attestations, unknown required criteria, absent artifacts, empty
required suites and a forged `PASSED` with violated/unknown criteria.

Use real browser tests for offline opening, filters, sorting, keyboard access,
long output, narrow screens, print view, missing links, JavaScript-disabled
content and script-injection payloads. Compare every summary count and chart
value with source evidence. Preserve test failures even when the report renders
successfully. These are future implementation requirements, not tests already
passed by this document.
