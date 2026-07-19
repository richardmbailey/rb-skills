# Phase 5: Workflow Integration And Release Readiness

## Phase Goal

Make the constrained route discoverable but optional, preserve ordinary execution, prove installation and behavioral claims, and refresh active skills only after source validation.

## Scope

- Existing workflow integration, routing/contract/eval coverage, installation, documentation, release review, and skill sync.

## Non-scope

- Automatic route selection, hidden dependency installation, strict-isolation advertising, or Claude compatibility claims.

## Task Checklist

- [v] Add `standard`, `constrained`, and `undecided` plan route handling and the optional reminder to `rb-create-implementation-plan`.
- [v] Update `rb-execute-plan` to sequence one constrained phase while preserving every later phase and the standard route.
- [v] Update `rb-working-diary`, README, skill metadata, and sibling boundaries for durable continuity and honest optional routing.
- [v] Add routing and instruction-contract cases, including matched positives, sibling negatives, ambiguity, and standard-route regressions.
- [v] Add release-scoped deterministic, adversarial, stale-reference, redaction, generated-drift, and packaging evaluations, with the unimplemented target-matrix cases recorded as residual coverage limits.
- [v] Run repeated fresh-context semantic and with/without-skill trials and preserve raw results and limitations.
- [v] Validate all source skill folders, runtime schemas, manifests, requirements, and references.
- [v] Prove disposable symlink and copy installs select all three skills and one manifest-pinned runtime with no handwritten duplication or auto-install.
- [v] Sync the three skills into the active Codex skill root and explicitly provision/smoke-test the runtime only after every source gate passes.
- [v] Run independent diff, safety-claim, multi-agent, portability, hidden-fallback, record-integrity, and final plan-completion reviews; fix every actionable finding.

## Verification Checklist

- [v] The reminder never selects constrained mode automatically and the ordinary route still behaves as before.
- [v] Metadata, routing, instruction contracts, deterministic tests, adversarial tests, semantic trials, and install smoke tests pass.
- [v] Active skill discovery resolves to the versioned repository and all three invoke the same verified runtime manifest.
- [v] Release evidence distinguishes deterministic proof, coordinator/host observation, agent report, and manual conclusion.
- [v] No blocking review finding, stale reference, schema drift, secret canary, or undeclared fallback remains.
- [v] Every Phase 1 to 5 task is `[v]`, `git diff --check` passes, and the top-level success criteria are rechecked.

## Evidence

Record eval manifests and raw results, install manifests/logs, source/runtime/schema hashes, ordinary-route regressions, final review, and release limitations under `evidence/phase-5/`.

## Phase Exit Criteria

The route is optional and usable, ordinary execution remains intact, evidence supports every release claim at its stated enforcement level, all tasks are `[v]`, and the final review is clear.
