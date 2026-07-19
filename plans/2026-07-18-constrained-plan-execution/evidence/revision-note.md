# Phase 0 Revision Note

The original 498-line overview was reorganised into a shorter top-level plan and four authoritative references. This note records where each review finding was resolved and what Phase 0 evidence verifies the resolution.

| Finding | Resolution | Authoritative location | Phase 0 verification |
| --- | --- | --- | --- |
| F-01 | Split fresh context from read-only isolation; added semi-formal and strict profiles | `A-006`, `A-007`, `D-003` | Codex probe found shared mutation-capable tools/workspace; strict unavailable |
| F-02 | Classified executable and all transitive capabilities, not argv syntax alone | `O-002` to `O-006` | Validation matrix includes shells, inline interpreters, scripts, build hooks, plugins, configs, children, env and network |
| F-03 | Added canonical path identity, containment, mutation-time recheck, and race disclosure | `X-001`, `X-002`, `R-005` | Traversal, link, alias, mount, hard-link and swap canaries specified |
| F-04 | Separated provenance sources and limited local hash-chain claims | `D-003` to `D-005`, `A-002` | Probe established agent-reported child trace; corruption/recovery fixtures specified |
| F-05 | Separated product/control planes and corrected the unsafe-path criterion | `D-001`, `D-002` | Phase 1 now allows declared control records but no product mutation |
| F-06 | Replaced prose-only tightening with a closed monotonic algebra | `P-001` to `P-004` | Union/intersection/minimum/stronger-order rules and widening failures specified |
| F-07 | Added repository snapshots, invalidation, lease, concurrent-change stop, and TOCTOU limit | `R-001` to `R-005` | Snapshot and lifecycle fixture rows cover all cases |
| F-08 | Defined authority order and made repository/tool text evidence, not instructions | `A-003` to `A-005` | Role-specific injection fixtures cover plan/source/instructions/log/test/generated/retrieved text |
| F-09 | Added typed effect dimensions, deterministic materiality, and evidence-first gate | `E-001` to `E-004` | Decision table blocks any single material dimension; confidence cannot cure gaps |
| F-10 | Added complete lifecycle, legal transitions, resumable resource pause, and high-risk replay gate | `L-001` to `L-004`, `D-007` | Transition, repeated-diagnosis, five-cycle repair, pause/resume and intervention cases specified |
| F-11 | Defined threat limits, canonical bytes, stable payload/envelope, versions, and hash limits | `A-001`, `A-002`, `C-001` to `C-004`, `D-005` | Golden/counterexample, migration, identity and corruption checks specified |
| F-12 | Selected explicit runtime environment/CLI and declared dependency; tested current sync mechanics | `K-001` to `K-004` | Copy probe showed selected folder only; approved setup and four-folder Phase 1 proof gate added; no automatic install |
| F-13 | Added ledgered fake capabilities and prohibited-operation canaries | validation matrix adapters and fixtures | Every prohibited capability has a fake; real dangerous operations are forbidden |
| F-14 | Canonicalised Boolean, intervention records, and normative authority | `C-003`, `D-007`, all unique invariant definitions | Documentation validator checks IDs, links, F coverage, stale phrases and reduced overview size |

Residual risks are deliberate and visible: no per-role host isolation on the probed Codex host, no complete child trace, non-atomic TOCTOU on weaker hosts, and Claude runtime capabilities unknown because its installed CLI was unauthenticated.
