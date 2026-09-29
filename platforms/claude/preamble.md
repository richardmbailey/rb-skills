## Claude Code host rules

This is a generated Claude edition. These host rules adapt the shared procedure below; they do not change its acceptance criteria or grant permissions.

- Use `/rb-name` when shared text says `$rb-name`. Keep literal commands, paths, schemas, and code unchanged unless the host-specific rule below applies.
- Read the project's `CLAUDE.md` and shared `AGENTS.md` when present, preserving existing user authority. The repository's Codex model choices and Codex-only controls do not apply to Claude.
- Use standard execution. The constrained-runtime skills and Codex context-token reporter are not supported here; use Claude's own context display for Claude usage.
- For delegation, follow the installed Claude `/rb-delegate` procedure: obtain a user-selected model or explicit permission to inherit before launching a subagent, then reuse the choice within its authorised scope. Do not map GPT model names to Claude models. Keep required independent review gates.
- Keep the existing RB diary at `${CODEX_HOME:-$HOME/.codex}/diary/` as shared Markdown unless the user has explicitly chosen another canonical root. Apply that choice consistently to onboarding, continuation, and handoff. Do not change `CODEX_HOME` or create a second history to accommodate this host.
- Run setup and sync scripts from the source repository with `--agent claude`. Recover its path from this edition's `.rb-claude-install.json` marker or an explicit `--pack-root`; the source profile, not an installed generated copy, owns refreshes. The generated-copy check replaces shared instructions that require symlinks. Preserve local edits and use the installer's backup option only for an authorised replacement.
- In skill authoring, keep shared source frontmatter and Codex metadata unchanged. The Claude exporter supplies native invocation metadata. Use the generated post-draft reference for the authoring workflow; do not enable automatic discovery of the manual-only language skill.
- Use available Claude tools for files, terminal work, review, and browser checks. Codex desktop APIs are optional host facilities, not Claude requirements. Report checks that could not run and preserve any gate they block.
