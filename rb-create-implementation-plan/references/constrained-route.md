# Optional constrained execution

Read this only when the user requests or compares constrained execution. Use standard execution for ordinary software behaviour and any phase requiring executable tests or runtime observations.

The constrained static-only route is Codex-only. It compiles one approved phase with `$rb-create-low-level-plan`, assesses it with `$rb-assess-plan-safety`, and permits only an unchanged `safe: true` bundle through `$rb-safe-operation`. It cannot execute tests, builds, linting, typing, or application commands. It provides controlled static operations, not proof that the resulting software behaves correctly or operating-system isolation.

Present the applicable choices:

- `standard`: linear `$rb-execute-plan` or adaptive `$rb-sprint`, including executable tests and CI-equivalent checks.
- `constrained`: only phases whose complete acceptance criteria are observable from static file state.
- `undecided`: preserve the user's deferred choice; do not enter constrained execution. Standard execution remains the default.

Constrained criteria and verifier checks must use `static_file_state::<description>`. The other modes `executable_test`, `runtime_observation`, and `external_observation`, and untyped criteria, are rejected by deterministic preflight. Do not narrow required behavioural acceptance merely to fit this route.

When repository-owned path restrictions are wanted, `$rb-create-safe-operation-policy` can translate them into a previewed, confirmed fixed policy. Do not create a policy implicitly. Existing general task authority does not replace the runtime's exact preview-bound confirmation, plan assessment, patch assessment, or verification gates.
