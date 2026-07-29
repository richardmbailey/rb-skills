# Policy Authoring Runtime Contract

Use only the installed manifest-pinned launcher and interpreter described by `rb-safe-operation/references/runtime-contract.md`. Normal policy authoring does not install dependencies, discover credentials, select a provider, or fall back between adapters.

The public deterministic commands are:

```text
run_runtime.py policy-explain --project-root <absolute-root> --format plain
run_runtime.py policy-preview --project-root <absolute-root> --proposal <canonical-proposal.json> --assurance-profile instruction_only_authoring --output <preview.json>
run_runtime.py policy-confirm --proposal <canonical-proposal.json> --preview <preview.json> --statement <exact-human-statement> --confirmed-at <UTC> --output <confirmation.json>
run_runtime.py policy-apply --project-root <absolute-root> --proposal <canonical-proposal.json> --preview <preview.json> --confirmation <confirmation.json>
```

Add `--confirm-relaxation` to `policy-confirm` only when the displayed deterministic classification is `relaxation` or `mixed` and the human has explicitly confirmed that loss of restriction.

The statement must exactly equal `CONFIRM SAFE OPERATION POLICY <confirmation-token>` for creation, tightening, and reason-only changes, or `CONFIRM SAFE OPERATION POLICY RELAXATION <confirmation-token>` for relaxation and mixed changes. The runtime recomputes this statement hash again during apply; arbitrary confirmation prose is not accepted.

The proposal, preview, and confirmation are transient control inputs. Keep them outside the product tree or under `.rb-safe-operation/`; never stage or publish them unless the human explicitly names those exact records. `policy-apply` writes only the fixed product configuration file and create-only records beneath `.rb-safe-operation/artifacts/policy-authoring/`.

The runtime accepts only canonical JSON with one trailing newline. `ProjectPolicyProposal` is schema 1.0 and contains a `ProjectPolicy` schema 2.0. The policy writer uses the shared `.rb-safe-operation/execution.lease`, a compare-and-swap source identity, a same-directory temporary file at mode 0600, `fsync`, atomic replacement, reread verification, and durable intent/commit records.

The fixed absence identity is deterministic. A missing policy therefore remains distinguishable from an unobserved, unreadable, malformed, or stale policy.
