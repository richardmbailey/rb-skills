# Local builder and auditor coordinator

The coordinator preserves each assessment and accepts a candidate only after every required command succeeds and a separate auditor approves the exact files assessed. The host dispatches the builder and auditor as two LLM agent invocations. Python never dispatches or calls an LLM. The host must actually obtain the independent review; inventing an identity or invocation reference defeats the workflow.

This is a cooperative local workflow, not protected CI, authenticated agent isolation, a security boundary, or a general execution sandbox. Commands run with the caller's permissions. Builder and auditor identities and `host_invocation_ref` are host attestations, not cryptographically authenticated evidence. File hashes detect changes within the declared scope. They do not prove that the declared scope is complete or prevent a malicious process from rewriting both evidence and state. The host must inspect scope, command intent, and audit quality before initialization. The auditor should use a fresh context and inspect the requirements, changes, logs, and executable audit evidence independently.

## Commands

Run with Python 3; no third-party packages are required:

```bash
python3 rb-audit-test-suite/scripts/test_loop.py init --project /absolute/project --plan /absolute/plan.json --state-dir /absolute/new-state
python3 rb-audit-test-suite/scripts/test_loop.py run --state-dir /absolute/new-state
python3 rb-audit-test-suite/scripts/test_loop.py review --state-dir /absolute/new-state --review /absolute/review.json
python3 rb-audit-test-suite/scripts/test_loop.py status --state-dir /absolute/new-state --require-verified
python3 rb-audit-test-suite/scripts/test_loop.py cancel --state-dir /absolute/new-state
```

The state directory must be new and its parent must already exist. Keep it out of version control. It can be inside the project; snapshots exclude that directory and its contents. Inputs cannot directly name the state directory or any file inside it. Prefer an external state directory and explicitly scoped source/test directories. Snapshotting an entire project may include caches and test-generated outputs; any such changes prevent acceptance. Configure commands to keep generated outputs outside scoped inputs, rather than ignoring unexpected changes after the fact.

Every command prints the complete state JSON on a valid operation. Exit codes:

For `status --require-verified`, exit zero means only `verified_local` with current candidate, protected files, policy and command logs still matching; every other state returns nonzero. Use this command as the saved acceptance gate. Without that flag, the operational exit codes are:

- `0`: an operational acknowledgement for `init`/`cancel`, successful review, or inspection of `ready`, `awaiting_review`, `verified_local`, or `cancelled`. This is **not** a universal acceptance signal: callers must inspect `status == "verified_local"`.
- `1`: state is `needs_repair`, `exhausted`, or stale `running`.
- `3`: `run` completed checks and is awaiting independent review; it is pending, not accepted.
- `2`: invalid schema, forbidden transition, changed protection/policy, stale review, lock conflict, filesystem failure, or other rejected operation.

## Exact version 1 plan schema

JSON objects reject unknown fields and duplicate keys. All listed fields are required except `max_rounds`.

```json
{
  "version": 1,
  "builder_id": "host-builder-invocation-001",
  "max_rounds": 3,
  "input_paths": ["src", "tests", "audit_tests", "pyproject.toml"],
  "protected_paths": ["requirements.md", "tests/historical_regression_criteria.json"],
  "checks": [
    {"id": "project-tests", "kind": "project", "argv": ["python3", "-m", "unittest", "discover", "-s", "tests"], "timeout_seconds": 120},
    {"id": "audit-controls", "kind": "audit", "argv": ["python3", "-m", "unittest", "discover", "-s", "audit_tests"], "timeout_seconds": 120}
  ]
}
```

- `version`: integer exactly `1` (booleans are rejected).
- `builder_id`: nonempty string, no NUL.
- `max_rounds`: integer from 1 through 100; default 3. This bounds total command assessments, including the first assessment.
- `input_paths`, `protected_paths`: nonempty arrays of unique, nonempty strings. Paths must be existing project-relative files or directories, with no absolute paths, `..`, or symlink components. Recursive traversal rejects symlinks and special files. Protected paths are checked separately even if not included in `input_paths`. Include requirements and historical regression criteria in protection.
- `checks`: nonempty array, with at least one `project` and one `audit` check. Every check has exactly `id`, `kind`, `argv`, and `timeout_seconds`.
- `id`: nonempty unique string, no NUL. `kind`: `project` or `audit`.
- `argv`: nonempty array of nonempty strings, no NUL. No shell-command strings are accepted; the coordinator invokes argument arrays without a shell. Host review must still reject an explicit shell interpreter or other inappropriate command if project policy forbids it.
- `timeout_seconds`: finite positive number at most 86400. Boolean, zero, negative, NaN, and infinity are rejected.

The frozen plan must list all required project tests, static checks, and executable audit/meta-tests. Every listed command must exit zero. An audit command must itself assert that healthy controls pass and deliberately faulty candidates fail for the expected substantive reason. An arbitrary nonzero exit, missing executable, timeout, or broken import is never treated as a successful mutation test by the coordinator. The coordinator does not infer these semantic audit requirements from exit codes; the auditor inspects whether the executable meta-tests establish them.

Initialization copies the plan and the protected-input manifest into the state directory. Each run records a manifest of directories and files, SHA-256 content hashes and file permission bits, before and after execution. Changing scoped inputs during commands or changing protected inputs fails the round. Each command record includes its argument vector, working directory, timestamps, exit code/outcome, and paths to stdout/stderr logs. All checks run even if an earlier check fails; success requires every check, not the final check alone.

Each command record also includes `stdout_sha256` and `stderr_sha256`, calculated after the log files close. Before loading a saved session for review, status or another operation, the coordinator checks every recorded command log from every round. Each log must remain at its expected numbered path, be a regular file without symlink components, and match its saved hash. Missing, moved or altered logs reject the operation with exit 2. Hashing reads bounded blocks; it does not load an entire log into memory.

Older sessions without these log hashes are rejected. Preserve their historical evidence; do not add hashes retrospectively and present them as evidence recorded during execution. A new assessment needs a new session and an explicit decision about the previous evidence and round budget. Public plan and review schemas remain version 1.

When running in CI, save raw audit outputs, child command records and native reports under a directory uploaded even when validation fails. A summary log alone does not preserve the evidence needed to assess a deliberate-fault experiment. This repository saves numerical audit evidence under `validation-output/test-audit-evidence/` and its parent JUnit report at `validation-output/test-audit.xml`; the always-run artifact upload includes both. The coordinator hashes its stdout/stderr logs only. Projects must separately retain any native artifacts referenced by those logs.

## Exact version 1 review schema

```json
{
  "version": 1,
  "round": 1,
  "candidate_digest": "copy-the-candidate_digest-from-the-assessed-round",
  "reviewer_id": "host-auditor-invocation-002",
  "host_invocation_ref": "host-record-of-the-real-independent-auditor-invocation",
  "decision": "approve",
  "findings": []
}
```

All fields are required; unknown fields and duplicate keys are rejected.

- `version`: integer exactly 1.
- `round`: positive integer matching the latest assessment.
- `candidate_digest`: nonempty string matching that assessment's manifest digest.
- `reviewer_id`: nonempty string different from the frozen builder identity.
- `host_invocation_ref`: nonempty string pointing to the real independent invocation in host evidence. The host supplies and verifies this reference; the coordinator cannot authenticate it.
- `decision`: `approve`, `revise`, or `incomplete`.
- `findings`: array of objects, each with exactly `id`, `severity`, `message`, and `evidence`. `id`, `message`, and `evidence` must be nonempty strings. `severity` is `blocking` or `nonblocking`. Approval with a blocking finding is rejected. An empty list is allowed when the auditor found no issue.

Submission validates the current candidate and protected inputs again. Stale round numbers, wrong digests, the builder reviewing their own work, missing invocation references, malformed reviews, and changed policy cannot produce acceptance. `revise` and `incomplete` consume the assessment and return to repair or exhaustion. Reviews submitted against already changed inputs are rejected rather than silently re-bound.

## Transitions, interruption and evidence

The ordinary path is `ready → running → awaiting_review → verified_local`. Failed commands, input changes, or valid `revise`/`incomplete` decisions lead to `needs_repair`, or `exhausted` when the round limit is reached. A new assessment requires changed scoped inputs; rerunning an unchanged failed or rejected candidate is forbidden. Do not alter an irrelevant file simply to rerun a flaky check: diagnose and repair the cause. Exhausted sessions must be reported as incomplete; do not silently create a fresh session to reset the bound.

An exclusive filesystem lock prevents concurrent operations. State updates are atomic, and numbered round directories preserve all completed assessments and logs. Evidence files are not overwritten. A crash can leave a stale lock, a `running` state, or an incomplete evidence write. None is resumed automatically. Preserve it and diagnose the interruption. After confirming the owning process and its descendants have stopped, a human may remove the stale lock and cancel the session. A new session requires an explicit decision about the unresolved evidence and budget; it must not disguise the previous failure.

`cancel` is available between commands when the lock can be acquired, including for a stale `running` record after stale-lock recovery. It is not an asynchronous process control command. To interrupt a live foreground run, use the host's process interruption mechanism; a caught interrupt kills the current process group and records a failed assessment. An abrupt coordinator kill may leave descendants running, so the host must verify process termination before recovery. Timeout handling kills the process group on POSIX and preserves partial logs. On other platforms it kills the direct process only; descendant containment is not guaranteed. Descendants that deliberately detach from the POSIX group are also outside this guarantee.

Terminal accepted/cancelled sessions cannot run again. `status` rechecks current inputs before reporting `verified_local`. All acceptance is local to the declared inputs, environment, commands and time of verification. External dependencies, executables outside scope, remote services, and changes outside declared paths are not pinned. Hashing is observational and does not provide filesystem isolation or eliminate concurrent-write races.

## Validation

```bash
python3 -m unittest discover -s rb-audit-test-suite/tests -p 'test_*.py'
```

The tests execute real subprocess fixtures and cover aggregation of all checks, missing tools, timeout descendant containment on POSIX, logs, independent-review binding, changed inputs/protection/policy, malformed schemas/state, symlink/traversal refusal, locks/concurrency, cancellation, exhaustion and preserved attempts. A focused acceptance assertion also runs against deliberately defective “last check wins” and “any check passes” implementations. Both are rejected with the expected aggregation assertion while the healthy implementation passes. This demonstrates that the aggregation acceptance case can expose those faults; it is not a claim of comprehensive mutation coverage for every coordinator behavior.
