# v0.1.5 publication check

The final check covers the new builder/auditor skills, deterministic coordinator,
numerical examples, deferred prototype, documentation and repository integration.
The independent code review found no actionable release blocker within that scope.

| Executed local check | Result |
| --- | --- |
| Repository skill/exporter/setup regressions | 46 passed |
| Coordinator behavioural tests | 23 passed |
| Bundled numerical audit and receipt controls | 24 passed |
| Reference-schema tests | 15 passed |
| Deferred prototype tests | 59 passed; prototype remains unqualified for general use |
| Original numerical trial tests | 99 passed |
| First numerical repeat tests | 87 passed |
| Second numerical repeat tests | 80 passed |
| Periodic heat publication assessment | All 10 required commands passed: 78 project tests, 27 audit checks, 14 reused helper controls, lint, format, typing, coverage and exact ID reconciliation |
| Contracts, routing, metadata and all eval manifests | Passed |
| Publication, JSON/Python syntax, workflow YAML and local documentation links | Passed |

Counts are per executed suite; reused helper cases overlap and are not summed
into a claimed unique test total. Structural eval validation does not execute
semantic model trials.

Publication review found machine-local paths in raw receipts. Originals were
preserved locally and excluded using explicit ignore entries. A labelled portable
summary retains the second repeat's outcomes and hashes. Authored interpreter
commands were made portable. No credential values or confidential project data
were found in the staged scope.

Making the heat audit-plan command portable changed a declared input, so its
previous acceptance was not silently reused. A new final assessment retained the
original completed trial history and obtained approval from the same independent
auditor. Its gate returned `verified_local`, exit zero. See the
[portable publication result](../../examples/periodic-heat/PUBLICATION_RESULT.json).
The original report remains a record of the earlier two-round trial.

Local raw final-check logs are retained under ignored `evidence/release-final/`.
The full unchanged constrained-runtime/wheelhouse suite, hosted Linux CI and live
provider/Claude trials were not run locally. Those omissions do not become passes;
the configured hosted workflow runs after publication. Runtime source and schema
mirrors were unchanged. No claim of full assurance-runner qualification or
exhaustive numerical correctness is made.
