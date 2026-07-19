# Phase 1 Verification Report

## Outcome

The supported Codex `semi_formal` walking skeleton is implemented. A strict plan can be assessed, an unsafe plan cannot reach a product adapter, and a safe plan can pass through a lease-owning coordinator to a coordinator-bound fresh verifier context. The workflow continues to disclose instruction-only role separation and incomplete child tracing.

## Deterministic Evidence

- The final wheelhouse-enabled source regression run passed 113/113 tests on 2026-07-19.
- The runtime suite covers strict JSON, domain-separated hashing, typed models, policy narrowing, effects, snapshots, paths, leases, lifecycle, audit recovery, fake capability ledgers, safe/unsafe workflows, and schema drift.
- The unsafe fake workflow raises before filesystem or subprocess ledger entries.
- The safe workflow keeps executor, coordinator, and verifier evidence distinct and reaches `verified` only from a typed proposal bound to the exact plan, assessment, snapshot, and coordinator-issued verifier context.
- Unknown fields, stale identities, unsupported versions, missing runtime state, and schema drift fail closed.
- Disposable setup tests use an approved local wheelhouse; normal invocation never installs.

## Review Fixes

The independent runtime review exposed artifact-only execution and verification bypasses. Public `execute` and `verify` CLI commands were removed. Execution now sits below `ExecutionCoordinator`, which revalidates identities and approvals, holds the project lease, advances lifecycle, writes the audit chain, checks snapshots before and after operations, and atomically consumes approval records. Verification requires a one-use coordinator-issued context and complete typed evidence.

## Limits

- The committed wheel lock is the probed CPython 3.12 macOS ARM64 release lock.
- Strict role isolation and complete child tracing are not claimed.
- Project-local audit hashes detect inconsistency relative to a retained head; they do not prevent equivalent-authority tampering.
