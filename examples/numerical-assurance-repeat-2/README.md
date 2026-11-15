# Second independent numerical repeat

This is a historical reconstruction of the two-store numerical trial using the
lighter project workflow. It predates the current builder/auditor system. The
selected planned faults were detected, but the reconstructed tests missed both
exact historical floating-point regressions when they were reintroduced.

Read the [comparison and limitations](../../docs/rb-build-test-suite-specification/repeat-trial-2/COMPARISON.md),
[requirements](REQUIREMENTS.md), [saved checks and evidence](CHECKS.md),
[independent review](independent-review.md) and [report](report.html).
The comparison owns claims about detected faults and supporting code; passing
local tests alone does not replace that comparison.

For the current single-invocation workflow, start with the
[periodic heat example](../periodic-heat/README.md) or the
[auditor's weak/strong suite demonstration](../../rb-audit-test-suite/examples/numerical/README.md).
The historical files and outcomes here are preserved rather than rewritten to
claim acceptance under a later skill or coordinator version.
