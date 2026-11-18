# Matched GPT-6.2 workflow trial

This trial compares GPT-6.2 Sol and Astra at medium reasoning on three short tasks. Each model receives each request three times with the relevant skill and three times without it. The matched input differs only by an explicitly supplied skill body. The trial tests the result of applying that body under a fixed text adapter. It does not test automatic skill discovery.

| Task | Artifact and success criteria |
| --- | --- |
| Repair a query | Save the submitted SQL to `due.sql` and execute it against an in-memory database. Check cutoffs before, at and after the due time, non-pending and undated jobs, one row per job, the output columns and the ordering. |
| Ask for an operator decision | Post the question to a synthetic inbox, write the supplied sample to disk and apply the proposed policy value. Pass when the inbox asks the operator to choose between keeping both entries and rejecting the duplicate, the sample bytes are exactly `id,label` followed by a newline, and the setting stays `pending`. A question that decides on the operator's behalf fails. |
| Write a shift handover | Send only the submitted note and five questions to a new Sol medium reader. Require all five correct answers. No rows have been delivered, only two rows in rejects.csv need editing, Retry is the first control, New Batch would load 20 rows, and READY requires Publish. |

A synthetic mailbox receipt exercises an unanswered decision and a delivered independent artifact in the same submission. It cannot measure a native host question dialog, polling, an actual wait or a subsequent human response. The SQL case checks the resulting repair, not whether a model independently ran tests. The reader is a model proxy for a first-time operator. Each reader starts a new session and receives no author identity, skill condition, original log, answer key or other notes.

## Results on 18 November 2026

Both models delivered all three outcomes on the first scored submission in every repetition, with and without the skill. Each of the 12 query repairs passed the four cutoff checks. Each of the 12 operator mailboxes received the decision question while the sample file was delivered and the duplicate policy stayed pending. Twelve fresh readers answered all five questions correctly from the note alone (60/60 answers).

| Author and condition (medium) | Query | Decision | Handover | Median author seconds (range) | Total input / cached input tokens | Total output / reasoning output tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sol with skill | 3/3 | 3/3 | 3/3 | 13.95 (10.27–24.63) | 197,213 / 12,416 | 853 / 77 |
| Sol without skill | 3/3 | 3/3 | 3/3 | 11.15 (9.51–26.28) | 120,714 / 12,416 | 491 / 0 |
| Astra with skill | 3/3 | 3/3 | 3/3 | 13.66 (11.71–34.51) | 196,766 / 12,288 | 760 / 0 |
| Astra without skill | 3/3 | 3/3 | 3/3 | 13.06 (10.21–20.47) | 120,261 / 49,280 | 539 / 0 |

Each table row contains nine author calls. Cached input and reasoning output are subsets of their respective totals. The 12 additional Sol medium reader calls had a median of 10.68 seconds (9.43–22.32), 162,263 input tokens (24,832 cached), and 740 output tokens (0 reasoning output tokens reported). Trial-level answers, timing and usage are in [trials.jsonl](trials.jsonl). The semantic assessments are in [readings.json](readings.json).

Skill lift was zero percentage points on these tasks. Both skill conditions consumed more input tokens than their matched controls. The small repetitions and differing cache hits do not establish a speed ranking. The tasks were short and included explicit acceptance details. These results cannot establish that a skill is redundant for harder work or that one model is better at resolving ambiguity. No scored deliverable needed a corrective submission. Multi-turn rework, human editing time, cost in money and the effect of higher reasoning effort were unmeasured.

## Reproduction

Run from the repository root using Python 3.11+ with SQLite and an authenticated Codex CLI. The measured CLI was `0.169.0-alpha.11.1`. Running the first command makes 36 author requests and up to 12 reader requests using the signed-in Codex account. The output must be a new file. The second command replays the saved trial offline.

```sh
python3 evals/gpt-6.2-workflows/run.py /tmp/new-workflow-62.jsonl
python3 evals/gpt-6.2-workflows/check.py evals/gpt-6.2-workflows/trials.jsonl evals/gpt-6.2-workflows/readings.json
```

For fresh trials, have an assessor read the distinct question texts and reader answer sets without their condition or author labels. Apply the criteria above and record each judgement by the SHA-256 of the canonical JSON value (`check.digest`) in a new readings file. The checker requires a recorded judgement for every submitted question and reader answer set. Words and phrasing may vary when the meaning is correct.

`run.py` loads `rb-implement-with-tests`, `rb-discuss` and `rb-language` directly from Git revision `44845c9a2c061420658eefb1c9a0a70cb98f578c`. The with-skill receipts identify the body by SHA-256. The control receives no injected skill. The run uses three workers and a fixed shuffled order. Each author and reader starts an ephemeral read-only CLI in an empty temporary directory, with temporary database/log paths, no repository instructions, host skill discovery and search disabled, and tools disabled as listed in the runner. Every call is instructed to use no tools. Only completed, schema-valid, tool-free outputs are scored. Standard bundled instructions and service-side behaviour remain outside the experiment's control.

Model-produced SQL runs only in a private in-memory SQLite database. A SQLite authorizer allows SELECT, reads of the three fixture columns, and the null-handling functions COALESCE and IFNULL. The grader supports this bounded SQL subset and may reject other equivalent queries. Query-only mode, result and string limits, a VM instruction budget and single-statement execution bound the check. Other model outputs go to fixed files as text. Raw traces, private logs and authentication data are excluded from the saved receipts.


## Pilot and interrupted attempts

The first CLI probe stopped during sandbox startup, before a model response. A Sol smoke call then returned READY with temporary CLI state. In the first matrix attempt, the collector counted a startup notice as a tool event and discarded otherwise completed answers. That attempt was stopped. Its 12 collected failure receipts remain in `interrupted.jsonl`; three in-flight submissions completed without a collected receipt. They have no score. A separate Astra smoke call exposed the notice as Code Mode failing closed because its host was disabled. The corrected collector records nonfatal CLI notices separately and checks tool events, turn completion, exit status and the returned schema. All matrix cells were then run again. Pilot and interrupted attempts are outside the balanced comparison and its token/timing summaries.

The model and reasoning effort in each receipt are the explicit CLI selections. This CLI's JSON completion events report usage without a server-side model revision or independent attestation of reasoning effort. Timing includes CLI startup and service latency under shared three-worker concurrency. The service may cache repeated input. No currency costs were reported. The trial did not compare reasoning settings or longer workflows.

## Smoke check of edited instructions

[Smoke results](smoke-results.json) contains seven additional text-only Sol medium responses to synthetic cases from the current execution, handoff, delegation and multi-agent design manifests. All seven answers met their individual rubrics on the first submission. The ordinary execution answer omitted the intermediate implemented marker in its status summary, although it selected the correct route. The requests, supplemental fixture facts, exact workflow hashes, full answers, usage and case-specific assessments are in the receipt. The harness supplies only the case request, fixture and applicable workflow text. Evaluation rubrics are attached to the receipt for scoring and never sent to the model.

To collect fresh answers with the same isolated CLI adapter, run `python3 evals/gpt-6.2-workflows/smoke.py /tmp/new-workflow-smoke.json`. Use the same source-file hashes to reproduce the recorded inputs. Grade each answer against its rubric and the supplied facts. These seven single trials probe the intended decisions. They do not measure how often the instructions help, prove native dispatch or CI behaviour, or run a Responses application.
