# Independent Runtime Review And Fix Record

## Review Outcome Before Fixes

A fresh independent reviewer found release-blocking defects despite the then-green 44-test suite: assessment/plan mismatch could authorise mutation; rejected assessments could be reported verified; policy/source/snapshot identities and approval scope were not fully re-derived; Git status maps were omitted from snapshot comparison; setup reuse and installed-package identity were under-validated; duplicate-key audit records were accepted; nested suspension was ambiguous; and release evidence was incomplete.

## Resolution

| Finding | Resolution |
| --- | --- |
| Unrelated assessment could mutate another plan | Removed public mutation CLI; coordinator and private dispatcher require exact plan/assessment identity. |
| Rejected or caller-asserted verification | Removed public verification CLI; added typed `VerificationProposal` and one-use coordinator-issued context. |
| Missing policy/source/snapshot re-derivation | Assessment reselects the authoritative phase, verifies continuity and both policy hashes, and compares the current full snapshot. |
| Approval scope incomplete | Approval binds plan, operation, policy, snapshot, effect ID/class, approval class, exact target, expiry, one-use state, and idempotency when required. |
| Git status drift ignored | Snapshot comparison covers staged, unstaged, untracked, rename, selected, instruction, index, link, branch, head, root, and device state, excluding only declared outputs/control roots. |
| Coordinator controls disconnected | Execution coordinator owns lease, lifecycle, audit, pre/post operation checks, approval consumption, bounded-agent packets, repair, pause, resume, and verification handoff. |
| Setup/invocation identity weak | Targets use full source and combined-lock hashes; builds use sanitized source copies; reuse is validated; every invocation verifies source, lock, and installed-package hashes. |
| Duplicate-key audit accepted | Reload uses strict parsing and requires exact canonical persisted bytes plus one newline. |
| Nested suspension ambiguous | Generic resumable-to-resumable transition is rejected; one explicit evidence-bearing pause-drift escalation preserves the original suspended state. |
| Patch metadata under-modelled | Exact patch actions reject binary, mode, symlink-mode, rename, copy, and combined-diff metadata. |
| Release evidence incomplete | Added repeated planner/operator trials, 36-case routing evidence, final disposable installs, active runtime smoke checks, phase reports, and a second independent review gate. |

All fixes are covered by focused regression tests or retained behavioral/install evidence. Residual limitations remain explicit: semi-formal role restrictions, incomplete child trace, first-platform lock, and no claim of malicious-tamper resistance.

## Final Hardening Passes

The release review continued after the earlier record above. Subsequent findings and fixes included:

- closed invariant and finding-category vocabularies, exact operation/effect/evidence references, and author-provenance validation for semantic findings;
- canonical coordinator sanitisation of semantic proposals, including an immutable false bundle for malformed assessor output;
- mandatory effect evidence and observation-source consistency, explicit `security_sensitive`, conservative detectability, and approval classes derived from destructive, external, privacy, security, cost, and irreversibility dimensions;
- rejection of duplicate IDs, path aliases, cross-operation patch targets, unsupported observation claims, and plan evidence whose locators do not match the captured snapshot or `agent-report:<id>` convention;
- snapshot comparison of platform, case sensitivity, and Unicode normalisation, plus protected control-root component and symlink checks;
- fail-closed handling of control-state drift without attempting another audit write into the changed control plane;
- removal of the public launcher control-root override, stronger installed-source/package identity checks, and removal of stale source-tree identity residue;
- documentation of the manual instruction-only approval channel, context-separated verification, unsupported executable containment, and the precise first-release provenance rules.

The final source suite grew from the earlier 44 and 69-test checkpoints to 113 tests. The final independent release gate is recorded separately in `final-independent-review.md`.
