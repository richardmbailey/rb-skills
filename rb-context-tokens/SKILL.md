---
name: "rb-context-tokens"
description: "Use when the user types /tokens or asks how many tokens the current Codex chat window, context window, latest call, or active session is using. Reports current context input tokens from Codex session JSONL token_count events and works globally from any folder."
---

# /tokens - report current Codex context token usage

Alias: `/rb:tokens`

## Purpose

Use this skill when the human asks how many tokens the current Codex chat window is using, how much context is left, or what the last model call consumed.

## Procedure

1. Run the bundled reporter:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/rb-context-tokens/scripts/report_context_tokens.py"
   ```

   If working from this skill directory, run:

   ```bash
   python3 scripts/report_context_tokens.py
   ```

2. Prefer the nearest available bundled reporter in this order:
   - `scripts/report_context_tokens.py` relative to this skill directory
   - `rb-context-tokens/scripts/report_context_tokens.py` from the Codex skills directory
   - `${CODEX_HOME:-$HOME/.codex}/skills/rb-context-tokens/scripts/report_context_tokens.py`
3. By default the reporter finds the newest user `~/.codex/sessions/**/*.jsonl` file by modification time and uses the latest `token_count` event in it.
4. If the human gives a specific session file, pass it explicitly:

   ```bash
   python3 "${CODEX_HOME:-$HOME/.codex}/skills/rb-context-tokens/scripts/report_context_tokens.py" --session /path/to/session.jsonl
   ```

## Output

Report:

- session file used
- timestamp of the token-count event
- current context input tokens, cached input tokens, model context window, and percentage used
- last-call output, reasoning output, and total tokens

## Required behaviour

Do not estimate token counts from transcript text unless no `token_count` event exists. Use input tokens, not total tokens, as the headline context-window usage because total tokens include the model's reply and can decrease after shorter replies. If the reporter cannot find token usage, say that the session file does not contain a `token_count` event.
