@AGENTS.md

# Claude Code host guidance

Use the Claude installation profile in `platforms/claude/`, not unadapted Codex-only skill directories. Interpret shared `$rb-name` references as `/rb-name` invocations. Keep source files and literal command arguments unchanged.

The Codex delegation section in `AGENTS.md` applies only to Codex. For Claude, use the Claude `rb-delegate` edition: ask the user which subagent model to use unless an applicable user choice already exists. Reuse that choice within the task. Do not silently substitute a model or infer permission to inherit.

Use standard execution. The constrained runtime and Codex token-count reporter remain Codex-only. Retain behavioural testing and required independent-review gates using available Claude tools.

The existing RB diary is shared Markdown at `${CODEX_HOME:-$HOME/.codex}/diary/`, not Claude automatic memory. Preserve its canonical location unless the user explicitly chooses another one. Do not change `CODEX_HOME` to a Claude path.

For changes here, keep the top-level skill sources and Codex metadata authoritative. Change Claude-only metadata and procedures under `platforms/claude/`, then run the installation regression tests and shared contract checks. Never edit generated installed copies as source.
