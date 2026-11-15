# Test-suite auditing

Invoke `$rb-build-test-suite` once to construct deterministic project tests,
automatically obtain independent `$rb-audit-test-suite` challenges, and handle
authorized repairs and reassessment. Invoke `$rb-audit-test-suite` directly when
you want an audit of existing tests without implicitly authorizing repairs. The host dispatches two reasoning roles. A small local coordinator enforces
command results, candidate identity, review state and a finite assessment limit;
no third LLM orchestrator is required.

Start with [SKILL.md](SKILL.md), the [paired workflow](references/paired-workflow.md)
and [coordinator contract](references/coordinator.md). The coordinator does not
call agent services, authenticate reviewer identity, enforce a sandbox or implement
the builder's deferred full assurance runner. Host observations of actual reviewer
invocation and scientific judgements remain necessary.

The [numerical example](examples/numerical/README.md) runs ordinary tests and tests
of those tests. It preserves the two historical floating-point failure cases that
both earlier independent reconstructions missed. A weak suite must fail the audit;
the strengthened suite must pass it. These are executable software checks, separate
from the [skill eval definitions](evals/eval-plan.json).
