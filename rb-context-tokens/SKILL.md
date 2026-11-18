---
name: "rb-context-tokens"
description: "Use only when the user asks for /tokens, current Codex context-window usage, latest-call input tokens, or active-session token counts. Read session token-count events and report measured values."
---

# /tokens - report current Codex context token usage

Alias: `/rb:tokens`

## Purpose

Use this skill when the human asks how many tokens the current Codex chat window is using, how much context is left, or what the last model call consumed.

## Procedure

1. Resolve the reporter relative to this skill directory first; use the installed path below only as a fallback. Run it once for the selected session:

   ```bash
   python3 "$HOME/.agents/skills/rb-context-tokens/scripts/report_context_tokens.py"
   ```

   If working from this skill directory, run:

   ```bash
   python3 scripts/report_context_tokens.py
   ```

2. Prefer the nearest available bundled reporter in this order:
   - `scripts/report_context_tokens.py` relative to this skill directory
   - `rb-context-tokens/scripts/report_context_tokens.py` from the Codex skills directory
   - `$HOME/.agents/skills/rb-context-tokens/scripts/report_context_tokens.py`
3. By default the reporter finds the newest user `~/.codex/sessions/**/*.jsonl` file by modification time and checks its latest `token_count` event. Use an explicit session path if the current session identity is available. Otherwise, report how the file was selected and say whether you could verify that it belongs to this chat.
4. If the human gives a specific session file, pass it explicitly:

   ```bash
   python3 "$HOME/.agents/skills/rb-context-tokens/scripts/report_context_tokens.py" --session /path/to/session.jsonl
   ```

## Output

Report the session file. If the latest `token_count` event has a timestamp, report it.

- If the latest event has a usable input token count, report current input tokens, cached input tokens, the model context window, the percentage used, and last-call output, reasoning output, and total tokens. Mark missing fields as unknown.
- If the latest event lacks a usable input token count, say that current context usage is unavailable. Report any requested fields that the same event still provides, such as its output tokens.
- If the reporter shows a last recorded measurement, report its input token count and any other requested fields from that measurement. Include its own timestamp when available.
- If `token_count` events exist and the reporter found no usable measurement, say that no earlier measurement is available.
- If the file has no `token_count` event, report that no event was found.

## Required behaviour

Use measured input tokens for the headline context-window usage. Total tokens include the model's reply and can decrease after shorter replies. Do not estimate token counts from transcript text.
