# Independent follow-up review — 15 November 2026

A fresh reviewer examined `rb-build-test-suite`, `rb-audit-test-suite`, the local
coordinator and the numerical example. It found two defects in evidence
preservation. Both have been repaired. This review addresses the implemented
local workflow; it does not establish that every project test suite will detect
every defect.

The reviewer was `/root/fresh_test_skills_review`, running GPT-6 Astra with medium
reasoning in a fresh context. It received the task and file locations without the
builder's conversation or previous review conclusions. It inspected the files,
ran the original 18 coordinator tests and 24 numerical audit tests, and reproduced
the missing-log defect independently.

## Findings and repairs

1. **P2: acceptance survived missing command evidence.** Deleting all four
   stdout/stderr logs after approval still allowed `status --require-verified`
   to exit zero. The coordinator now records each log's SHA-256 hash after its
   file closes. Every subsequent operation checks all recorded command logs from
   every round for the expected path, regular-file status, absence of symlink
   components and matching content. Lost or changed logs reject the operation.
   Five new test methods cover deletion before review, modification after
   approval, deletion after approval, symlink substitution, redirected paths and
   legacy records without hashes. The first three tests failed against the old
   implementation; all five pass after the repair.
2. **P2: CI discarded the numerical audit's raw child evidence.** The workflow
   wrote child commands, logs and native reports outside its uploaded artifact
   directory. It now writes them under
   `validation-output/test-audit-evidence/`, with the parent JUnit report at
   `validation-output/test-audit.xml`. The existing always-run upload includes
   both, including artifacts produced before a failed validation step.

The skill's instructions and coordinator reference now state these requirements.
Two behavioural evaluation definitions cover lost command evidence and ephemeral
CI artifact retention. A consistency contract protects the reference's log-hash,
legacy-record and retained-artifact rules. These definitions are not completed
semantic agent trials.

Older coordinator sessions without saved log hashes fail the updated acceptance
check. Their files remain historical evidence; hashes must not be added later and
represented as observations made during execution. The earlier two-round demo
and its saved result remain historical records of the earlier implementation.
They are not a current accepted session under this repair.

## Validation

| Check | Observed result |
| --- | --- |
| Initial regression run against old coordinator | Expected failure: 21 tests, seven failed assertions |
| Repaired coordinator | 23 passed |
| Numerical audit and invalid-evidence controls | 24 passed |
| Repository routing/skill regressions | 46 passed |
| Schema-reference tests | 15 passed |
| Instruction and consistency contracts | Passed |
| Skill metadata and workflow YAML parsing | Passed |
| All top-level skill eval manifests and publication-hygiene check | Passed |
| Diff whitespace check | Passed |

The same independent reviewer checked the repairs and reran the coordinator
suite: 23 tests passed. Its original deleted-log reproducer now returns exit 2,
rejecting acceptance. It confirmed the CI artifact paths by source inspection
and found no new actionable issue. Its `rb-simplify-language` review found no
material ambiguity in the changed instructions.

Both Codex symlinks resolve to the repository source. The normal Claude sync
refreshed the auditor's generated copy after a clean dry-run; the builder's copy
was already current. No commit or push was performed.

Raw red/green outputs and the independent missing-log reproducer results are
retained locally under ignored `evidence/fresh-review/`. The numerical audit's
raw child evidence was also preserved in an external temporary directory.

Not run: hosted Linux CI and its remote artifact upload, live Claude agent
execution, repeated semantic skill trials, or the constrained-runtime and schema
export suites. The latter are outside this change: no constrained-runtime code
or schema changed. Local execution and workflow inspection support the fixes;
they do not prove remote artifact delivery. The coordinator remains a cooperative
local tool, with the existing limits on identity authentication, concurrent
writes, detached descendants and dependencies outside declared inputs.
