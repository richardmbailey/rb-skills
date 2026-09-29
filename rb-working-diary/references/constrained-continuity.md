# Constrained continuity records

For an implementation plan using the optional constrained route, also record:

- `Execution Route: constrained` and the authoritative plan path;
- current phase ID and every remaining phase ID in order;
- constrained phase-status overlay (`[x]` while implemented but unverified, `[v]` only after terminal verification), because the repository plan remains unchanged across the post-verification handoff;
- any explicit `leave_constrained_pipeline` choice, the rejected run and assessment-bundle hash, resulting route, and exact next action; label this as instruction-only continuity evidence rather than authenticated runtime intervention;
- run ID, lifecycle state, and suspended prior state when resumable;
- canonical plan, policy, assessment, approval, snapshot, event-head, and verification hashes and locations;
- verification requirement modes and confirmation that every accepted criterion is `static_file_state` under the first-release runtime;
- enforcement and observation levels without calling instruction-only controls isolated or read-only without qualification;
- required human decision, if any, and the exact next skill/action.

Never copy secrets, raw sensitive output, or planner/executor private reasoning into the diary. A resume pointer does not authorise execution: `$rb-safe-operation` must revalidate the complete bundle, lease, approvals, capabilities, instructions, and repository snapshot.

For a constrained run, the canonical `${CODEX_HOME:-$HOME/.codex}/diary/` is external control-plane continuity state. It may be updated from the coordinator's terminal stdout handoff after the final product snapshot, with the enforcement limitations and provenance stated accurately. Do not create or change a repository-local diary or progress file after that snapshot unless the change was an explicit assessed product operation.
