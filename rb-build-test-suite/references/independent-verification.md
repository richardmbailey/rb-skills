# Independent verification

Use an independent check when a shared assumption or developer-written oracle
could conceal an important defect. Independence has several dimensions; a
separate model name or session does not establish all of them.

The builder skill always requires a separate test-suite auditor. This reference
also governs additional domain or scientific verification; its non-selection
rules cannot waive the required suite audit. The same auditor may fulfil both
roles when its actual expertise, oracles and reviewed scope meet both needs.

Apply this procedure when additional independent verification is selected or required by
the project policy. Scientific-core acceptance requires it by default. Other
claims may have a justified non-selection; record its reason and continue the
required change-impact review. The independent method may be a reviewer,
reference implementation, dataset or analytical method. Delegate only when the
selected method requires a reviewer; do not invent an additional agent gate beyond
the required test-suite auditor.

## Prepare the handoff

For a delegated review, use the host's documented delegation mechanism. Give the
verifier a bounded packet with requirements, candidate/policy identities, permitted reads and
writes, tool/turn/time budget, oracle sources and expected output structure.
Do not invent a host API, session ID or authentication receipt. No paid calls or
external data sharing are authorized merely by invoking this skill.

Where feasible, first request test design from requirements without developer
code or tests. Preserve that packet and its proposed checks. A later review may
inspect the implementation and developer evidence to localize disagreements.
Use `$rb-multi-agent-systems` for the runner/agent boundary; keep the workflow a
simple pipeline or dependency graph unless more control is actually needed.

Record separately:

- session and context separation, including what the verifier saw;
- filesystem/tool permissions and whether isolation is enforced or instruction-only;
- oracle origins and dependencies shared with the candidate;
- actual host invocation receipts and attributable findings;
- unavailable controls, budget stops and incomplete outcomes.

For cooperative project checks, preserve the host's actual tool/session result
and attributable review artifact. A custom host adapter or external signature is
not required unless the accepted policy or trust boundary requires it. Do not
label a real local review unavailable merely because a generalized adapter has
not been built. Conversely, a self-authored provenance note without an observed
invocation cannot establish that a separate review occurred.

A shared workspace is not write isolation. Require enforceable controls when the
project policy requires them; otherwise disclose the limitation. Do not label
prompt instructions as a sandbox.

## Evaluate the result

The verifier supplies proposed tests, counterexamples and findings, not an
unconditional pass. The runner validates inputs, executes accepted tests within
authority, and evaluates frozen criteria. The host agent inspects actual artifacts
and evidence rather than trusting a completion sentence.

Required disagreements remain unresolved until supported evidence reconciles
them. A stale review, unavailable delegate, missing receipt or required domain
expertise cannot become self-review. Continue unrelated checks and show the
required gap. A shell rerun does not silently start paid agents or reuse a review
whose candidate/policy identities no longer match.

When building or changing a reusable host adapter, qualify the handoff with a
wrong implementation that passes developer tests but
fails an independently derived check, plus a healthy control. Test unavailable
hosts, malformed and wrong-candidate returns, cancellation and budget exhaustion.
Synthetic host receipts test record handling only; actual host qualification
requires an observed invocation. Keep model confidence advisory and distinguish
local cooperative evidence from externally enforced acceptance.
An ordinary project using an existing host does not need to implement and qualify
a new host adapter. It still needs actual independent evidence for every claim
whose policy requires it, and must preserve unresolved findings.
