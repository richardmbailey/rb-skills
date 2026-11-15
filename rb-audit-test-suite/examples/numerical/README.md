# Demonstration: can the tests expose plausible numerical defects?

The project tests check a small numerical model. The audit runs those same tests
against healthy and deliberately faulty copies, and checks that the relevant
assertion actually fails. A passing model suite alone cannot show that its tests
would notice a plausible error.

- `project/model.py`: fixed two-store Euler model and CSV export.
- `project/test_model.py`: eight substantive tests with independently specified
  oracles in [REQUIREMENTS.md](REQUIREMENTS.md).
- `audit/test_effectiveness.py`: eight fault challenges and two controls proving
  the deliberately weak suite is rejected.
- `audit/test_evidence.py`: rejection tests for invalid execution and report evidence.
- `audit/support.py`: the narrow adapter needed to copy projects, launch pytest,
  and reconcile exact native JUnit identities. It does not schedule a project-wide
  tool chain or produce a second report schema.

For each fault the adapter copies a healthy project twice. The test/config files
are identical in each pair; only one declared source replacement differs. The
healthy copy must pass all eight expected identities. The faulty copy must exit 1
and fail the predeclared test by assertion. Missing, extra, duplicate, skipped or
empty test collections, import/collection errors, non-assertion failures, missing
or malformed reports, inconsistent exit codes and timeouts cannot count as a kill.
Every copy checks its actual model import path during collection. A fresh child
config and `--confcutdir` prevent unrelated ancestor configuration from leaking in.
The example deliberately uses no third-party plugins; adapting a real project
requires preserving that project's necessary plugins and discovery configuration.

## Run it

Use Python 3.14.2 and the pytest version pinned in `requirements.txt` to reproduce
the recorded environment. No model, API, network call or LLM verdict is used while
the numerical tests or audit execute. From this directory, with that environment's
Python active:

```bash
python -m pip install -r requirements.txt
python -m pytest -c pytest.ini --confcutdir=project project/test_model.py -q
run=$(mktemp -d "${TMPDIR:-/tmp}/rb-audit-example.XXXXXX")
python -m pytest audit -q --basetemp="$run/tmp" --evidence="$run/children" --junitxml="$run/audit.xml"
```

The first pytest command runs the project suite (eight tests). The second runs
the audit and its negative controls (24 tests). Its output is native pytest/JUnit;
child logs, exact commands, exits and native JUnit are retained under `children`.
Use a new run directory each time. Pytest may clear `--basetemp`, so supply only a
fresh directory owned by this run. Without `--evidence`, child artifacts live in
pytest's temporary directory and are subject to normal cleanup.

To see the deliberately weak suite fail its audit:

```bash
weak=$(mktemp -d "${TMPDIR:-/tmp}/rb-audit-weak.XXXXXX")
python -m pytest audit/test_effectiveness.py -q --suite=weak --basetemp="$weak/tmp" --evidence="$weak/children" --junitxml="$weak/audit.xml"
```

That command is deliberately **red (exit 1)**: two challenges fail because the
historical faults survive. Eight other audit tests pass, including the two checks
that explicitly expect rejection. The weak project suite itself passes all eight
tests on the healthy model and passes on both historical faulty versions. The
strengthened suite retains the test identities but checks the real requirements;
it exposes all eight seeded faults. No failing test is deleted or marked xfail.

## Recorded results

On 15 November 2026 with Python 3.14.2 / pytest 9.2.0:

| Command scope | Observed result | Retained evidence (local, ignored) |
| --- | --- | --- |
| Full strengthened audit and evidence rejection tests | 24 passed; exit 0 | `evidence/final-audit.log`, `evidence/final-audit.xml`, `evidence/final/` |
| Weak suite audit | 2 failed, 8 passed; exit 1 | `evidence/weak-audit.log`, `evidence/weak-audit.xml`, `evidence/weak/` |

Each strengthened fault has a healthy eight-test pass and faulty assertion XML at
`evidence/final/<fault>/healthy/` and `faulty/`. The weak historical runs under
`evidence/weak/rounded_step/` and `quotient_underflow/` each show the faulty suite
passing, explaining the audit failures. Raw failed evidence is retained alongside
the successful run. The evidence directory is intentionally excluded from Git.

The adapter and pytest option fixture total 139 lines, including blank lines and
comments. Substantive project tests total 70 lines; audit tests total 78 lines;
the example model totals 68 lines. There is no custom runner, report application,
report schema, plugin framework or copied legacy support package.

## Adapt it to another project

1. Start from that project's requirements and native test command. Choose a small
   set of plausible faults and an exact intended test identity for each one.
2. Replace the example project, fault anchors and expected identity set. Keep a
   healthy control and identical tests/configuration for each fault pair. Use
   stable native IDs, not a count or a substring match in a log.
3. Preserve raw output and failure exits. Add a narrow native-report adapter only
   where the project's tools do not already provide the required reconciliation.
   This adapter supports pytest's ordinary assertion format, not every framework
   or plugin; test any format change explicitly.
4. Include a weak-suite negative control that should miss a known defect, and
   show that the audit rejects it. Validate malformed, missing, skipped, errored
   and timed-out outcomes without treating them as detections.

The two historical input tuples apply to this Euler implementation only. Other
models need their own boundary analysis and independent scientific oracles. Eight
seeded faults do not establish exhaustive mutation coverage, model validity,
general test-suite adequacy or an improvement attributable to using a skill.

Validation artifacts from skill development are retained outside the installed skill,
under `docs/test-suite-system/evidence/example/` in the source repository. The
relative evidence paths in the recorded-results table describe that archived
directory. New runs should use the external temporary directories above.
