# Phase 3 Deterministic Verification

Date: 2026-07-19

Verdict: PASS

The assessor fails closed across deterministic identity, policy merge, capability, executable, concrete path, effect target, evidence, verification, instruction, approval, and snapshot gates. Project requirements that name an unsupported enforcement, observation, evidence, or verification control are blocking rather than ignored. The first release rejects bounded executable forms because that vocabulary does not carry executable hashes.

The final wheelhouse-enabled 113-test run passed the policy and assessment matrix, including target mismatch, narrowed-policy requirements, strict-profile capability rejection, exact current approval binding, stale approval, environmental and network widening, missing semantic evidence, forged Pydantic copy, omitted instructions, detrimental-effect cases, closed finding/invariant registries, evidence provenance, derived approval classes, and malformed semantic-output handling. Three fresh-context assessor trials and three without-skill baselines retain their raw FALSE outputs.

Result: no deterministic or semantic assessment test failed.
