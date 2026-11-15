# Worked examples

These examples illustrate different workflows and record the limits of their
verification. Use each example's own requirements and commands; passing one
example does not qualify a general runner or guarantee another project's code.

| Example | Purpose and status |
| --- | --- |
| [Periodic heat](periodic-heat/README.md) | Current builder/auditor workflow: a new numerical model, deterministic tests, ten selected fault experiments, preserved failed first assessment and independent approval after repair. See its [report](periodic-heat/report.html). |
| [Two-store audit demonstration](../rb-audit-test-suite/examples/numerical/README.md) | Executable weak/strong suite demonstration, preserving exact historical floating-point regressions. Bundled with the auditor skill and checked by repository CI. |
| [Original numerical assurance trial](numerical-assurance/README.md) | Historical first trial and broader assurance-style supporting code. Its qualification limits remain; later delivery uses a lighter project workflow. |
| [First independent repeat](numerical-assurance-repeat/README.md) | Historical reconstruction using less supporting code; the [comparison](../docs/rb-build-test-suite-specification/repeat-trial/COMPARISON.md) records missed historical regressions. |
| [Second independent repeat](numerical-assurance-repeat-2/README.md) | Historical second reconstruction; selected planned faults were detected, but exact historical regression protection was again incomplete. |
| [Safe sandpile](safe-sandpile/README.md) | Constrained static-file example; read its recorded execution and behavioural-validation limits. |
| [Safe Space Invaders](safe-space-invaders/README.md) | WebGL example distinguishing constrained file edits from standard behavioural verification. |

The periodic heat report records 78 developer tests, 27 audit checks and 14 reused
helper checks passing in its final local assessment. Those are observations for
its frozen candidate, not an automatic pass for a later edit. Run its saved checks
and obtain current independent review after relevant changes.

Raw logs, temporary fault copies and native reports are generally retained locally
under ignored evidence directories. Their presence in a local report does not
mean they are distributed in a Git clone. Requirements, source, tests and rerun
instructions remain versionable; do not fabricate or relabel missing receipts.
