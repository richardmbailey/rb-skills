# Phase 1: Supported End-To-End Walking Skeleton

## Phase Goal

Prove the smallest complete constrained route: one phase becomes a strict plan, an unsafe case is rejected without product mutation, and a safe case reaches separated verification through one shared runtime.

## Scope

- Three user-facing skill folders and one internal Python runtime owned by `rb-safe-operation`.
- Strict artifact identity, minimum policy and effect decisions, snapshot/capability checks, lease/audit/lifecycle basics, and safe fake adapters.
- Disposable symlink and copy installation checks.

## Non-scope

- Full adapter execution, policy algebra, repair, and resume hardening reserved for Phases 2 to 4.
- Strict-isolation or Claude support.
- Real destructive, network, credential, paid, or external-write operations.

## Engineering Decisions

- Use CLI commands `runtime-info`, `validate`, `canonicalize`, `hash`, `merge-policy`, `snapshot`, `assess-preflight`, `assess`, `persist-artifact`, `render`, `export-schemas`, and `check-schema-drift`. Public persistence creates only the fixed plan; deterministic preflight or final assessment creates the sanitized assessment bundle directly. Keep execution and verification behind the lease-owning typed coordinator; do not expose artifact-only mutation or caller-asserted verification commands.
- Discover only the canonical control manifest, obtain the recorded bootstrap interpreter, and invoke the installed launcher by absolute path with `-I -S -B`; ignore legacy manifest/control-root environment redirects and never search sibling skill imports.
- Default the control root to `${CODEX_HOME:-~/.codex}/rb-safe-operation` and require explicit setup before normal commands.
- Keep all four exact adapters typed, but activate only `read_file` and `apply_patch` in the immutable first-release policy; command adapters remain fail-closed.
- Use project-local audit roots only in the first release; external audit roots fail visibly as unsupported.
- Bind Markdown phases by absolute source path, phase heading, normalized selected text, and SHA-256 hash.
- Keep `attempt_limit: "unbounded"` separate from finite host resource ceilings.
- Capture host-presented approval identity when available and record `identity_verification: unavailable` otherwise.

## Task Checklist

- [v] Scaffold and validate `rb-create-low-level-plan`, `rb-assess-plan-safety`, and `rb-safe-operation` with metadata and procedural boundaries.
- [v] Create the internal Python project, dependency contract, pinned requirements, explicit setup command, runtime manifest, and fail-fast discovery diagnostics.
- [v] Implement strict Pydantic artifact models, JSON parsing, canonicalization, domain-separated hashing, and generated schemas.
- [v] Implement the minimum global policy, monotonic merge, side-effect/materiality gate, typed findings, and capability profile gate.
- [v] Implement repository snapshots, path containment, a project lease, lifecycle transitions, audit event hashing/redaction, and recovery validation needed by the walking skeleton.
- [v] Implement ledgered fake filesystem, subprocess, network, approval, secret, clock/resource, service, and agent adapters.
- [v] Implement CLI orchestration for artifacts and a verified synchronous coordinator driver for safe execution and context-separated verification.
- [v] Add an unsafe fixture that produces immutable `safe: false`, declared control records, and zero product-plane mutations.
- [v] Add a safe disposable-repository fixture that reaches `verified` with separately labelled executor, coordinator, and verifier evidence.
- [v] Prove temporary symlink and copy installations use the same manifest-pinned runtime/source identity and simulate the working-diary handoff.

## Verification Checklist

- [v] Unknown fields, malformed canonical JSON, hash-domain changes, unsupported versions, and unsafe policy inputs fail closed.
- [v] Every deterministic validator has a good and bad case; fake ledgers show no undeclared dangerous call.
- [v] Unsafe and safe workflows retain canonical artifacts and audit evidence with honest enforcement labels.
- [v] Generated schemas are byte-stable and the drift check detects a deliberate mismatch.
- [v] Missing, stale, copied, and source-mismatched runtime states emit distinct diagnostics without installing dependencies.
- [v] Source metadata, focused tests, broader tests, `git diff --check`, and the phase review+fix pass succeed.

## Tests And Evidence

Use the bundled Python runtime for source tests. Provision disposable dedicated environments only through the explicit setup command. Record commands and outputs in `evidence/phase-1/`.

## Phase Exit Criteria

Both safe and unsafe routes are observable end to end, identity is reproducible, scope escape is blocked or detected at the disclosed semi-formal level, all tasks are `[v]`, and the phase review has no unresolved blocking finding.
