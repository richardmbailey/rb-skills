# Safe-operation Runtime 0.3 Migration

Runtime 0.3 adds fixed repository policy bindings and moves current action-bearing plans, assessments, run state, reports, repairs, and verification artifacts to schema 3. Proposal-cycle artifacts that already describe one exact diff remain schema 2. Schema numbers identify individual artifact contracts; they are not one global version applied to every file.

Existing schema-1 and schema-2 runs remain audit evidence. They cannot be executed, repaired, verified, or resumed by runtime 0.3. The runtime does not rewrite old records or pretend that an old run was assessed under a policy identity that did not yet exist.

For unfinished work:

1. Inspect old artifacts with `inspect-legacy` if an audit summary is needed.
2. Install and verify runtime 0.3 through the manifest-pinned launcher.
3. Decide whether the repository needs the optional `.rb-safe-operation-policy.json` file.
4. If it does, use `$rb-create-safe-operation-policy` to produce a typed proposal, deterministic preview, and proposal-bound confirmation.
5. Recompile the current source phase as a newly identified schema-3 low-level plan.
6. Capture the policy-pruned schema-3 snapshot and bind the fixed source and effective policy hashes.
7. Reassess the new plan and start a new run identity.

Do not edit `schema_version`, copy old hashes into new envelopes, or reuse an old approval. Current approvals use schema 3. Current exact and bounded execution reports use schema 3. Exact diff proposals, patch preflights, patch assessments, apply intents, and proposal-cycle records use their published schema-2 contracts within the schema-3 run.

The only project policy location is `<project-root>/.rb-safe-operation-policy.json`. Its absence has a canonical identity and preserves baseline behaviour. Adding, tightening, relaxing, or otherwise changing the file invalidates earlier current authority. Relaxation requires enhanced explicit confirmation. A denied read is prospective and does not remove information from historical artifacts, conversations, provider logs, Git history, copies, or backups.

After installation, `runtime-info` must report runtime `0.3.0`, schema `3.0`, Pydantic `2.13.4`, PydanticAI Slim `2.19.0`, and matching source, lock, environment, interpreter, launcher, and installed-package identities. Regenerate all four schema mirrors through that launcher and require byte-identical output before using the constrained route.
