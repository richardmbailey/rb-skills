# Two-part system for reliable project tests

The builder writes executable project tests. A separate auditor writes and runs
challenges to determine whether those tests expose specified defects. A small
local coordinator preserves failures, verifies the current candidate and review,
and limits the number of assessments. Two reasoning roles are sufficient; the
coordinator does not call an LLM or act as a third reasoning agent.

- [Builder](../../rb-build-test-suite/SKILL.md)
- [Auditor](../../rb-audit-test-suite/SKILL.md)
- [Paired workflow](../../rb-audit-test-suite/references/paired-workflow.md)
- [Coordinator CLI and exact contracts](../../rb-audit-test-suite/references/coordinator.md)
- [Executable numerical demonstration](../../rb-audit-test-suite/examples/numerical/README.md)
- [Original creation validation](validation.md)
- [Evidence-integrity review and repairs](fresh-review.md)
- [Single-invocation workflow and validation](single-entry-workflow.md)
- [v0.1.5 final publication checks](release-check.md)
- [New periodic heat model and saved commands](../../examples/periodic-heat/README.md)
- [Heat trial report](../../examples/periodic-heat/report.html) and [evidence](../../examples/periodic-heat/EVIDENCE.md)

Invoke `$rb-build-test-suite` once in Codex, or `/rb-build-test-suite` in Claude
Code, for any suite build or extension. The host automatically builds the tests,
dispatches the independent auditor, manages authorized repairs and obtains final
verification. This includes non-scientific projects; the user need not alternate
skills or request each cycle. Invoke `$rb-audit-test-suite` for an audit of existing tests; audit-only requests do not authorize repairs. Native host agent
controls dispatch the roles. There is no unattended agent service or third agent.

The default is three total assessment rounds, including the initial assessment.
The acceptance command is `status --require-verified`; zero means only a current
`verified_local` result. Other command exits can acknowledge an operation without
accepting the suite. Requirements and historical regression criteria remain
protected across repair attempts. Existing full assurance policies are preserved.

This is cooperative local acceptance. The coordinator cannot authenticate agent
identity, verify scientific truth from a JSON field, provide a sandbox or guarantee
that a declared candidate scope includes every dependency. The host must observe
actual independent review and check the scope and oracles. Accepted evidence
covers declared requirements and fault classes, not all possible defects.

The original creation record predates log-hash enforcement and the universal
builder entry point. Keep its observations historical. Older coordinator sessions
without log hashes are rejected by the current gate. The periodic heat trial
records an actual two-round build/audit/repair run under the current coordinator;
it does not measure skill lift or exhaustive test adequacy. Raw evidence linked
from trial reports is local and ignored by Git unless explicitly bundled.
