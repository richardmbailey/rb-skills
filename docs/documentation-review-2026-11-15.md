# Documentation review — 15 November 2026

The README and current supporting guides were checked against the repository's
active skills, installer/exporter implementations, Claude profile and authoritative
CI workflow. Dated trial and qualification results were preserved as historical
observations rather than rewritten as fresh verification.

## Corrections

- The README now leads with the builder/auditor system, explains one-invocation
  construction and repair, includes the research and test-suite routing entries,
  and links the periodic heat example and new documentation/example indexes.
- Current counts match the sources: 36 active top-level skills; 31 Claude editions
  from 30 shared skills and one Claude-specific override. The five exclusions and
  historical September counts retain their original meaning.
- Installation, sync and setup-repair instructions distinguish Codex symlinks from
  Claude generated copies. They document explicit host selection, automatic
  missing Claude project bridges, content verification, refresh conflicts and
  backups. Existing permissions and replacement safeguards are preserved.
- README validation commands now include Claude manifests, skill regressions,
  reference-schema checks, coordinator tests and native numerical audit evidence.
  Local checks are explicitly a CI subset; manifest validation is distinguished
  from executed agent trials. The periodic heat trial is not claimed as a CI job.
- AGENTS.md now lists all four generated-schema mirrors, matching the owning
  runtime contract. No generated schema or runtime source was edited.
- The test-system index now states the universal builder entry point and links
  the evidence-integrity repairs, current workflow and heat example. The broader
  specification, implementation plan, draft skill and prototype index distinguish
  deferred full-system work from delivered instructions and the local coordinator.
- Added indexes under docs/ and examples/, plus an entry README for the second
  historical numerical repeat. Recorded missed historical defects remain visible.

The documented routing validator exposed an existing gap: the auditor had only
two positive routing cases against the required minimum of three. The original
failure is retained in the local publication-check evidence, outside the Git tree. Added an explicit
failure-propagation audit case; validation then passed without relaxing its rule.

## Independent checks and validation

Two fresh GPT-6 Astra medium reviewers checked platform/install documentation and
workflow/runtime documentation separately. The platform reviewer corrected its
bounded source instructions and applied the rb-write-skill post-draft language
review. The workflow reviewer rechecked the integrated README, indexes and status
headers and found no remaining material issue within that scope.

- 46 repository regression tests passed; the platform reviewer also ran the
  relevant 34 exporter/setup tests as a subset, not 34 additional distinct tests.
- Instruction, consistency and routing validators, all top-level and Claude eval
  manifests, metadata, publication hygiene and diff whitespace checks passed.
- Markdown/HTML link checks parsed local targets and section anchors. The final
  scan totals are recorded below; external web destinations were not network-tested.
- All 36 active skills appear in the README catalogue. A full Claude generation
  dry-run produced the expected 31 editions. Codex source symlinks were already
  current; the three changed setup skills' Claude copies were refreshed and checked.
- Read-only identity verification found the current constrained runtime source
  still matches the exact July-qualified hash recorded in README, and the four
  generated mirrors are byte-identical. This is source comparison, not a fresh
  runtime, remote-provider or hosted-CI qualification.

Not run for these documentation/instruction changes: the full constrained-runtime
or numerical suites, hosted CI, current external host-service compatibility,
live Claude agent trials or repeated semantic skill evaluations. No executable
implementation changed. Existing unrelated working-tree changes were preserved;
no commit or push was made.

Final local scan: 155 Markdown/HTML documents, 362 relative file/directory links and 21 section anchors; no unresolved target or anchor.
