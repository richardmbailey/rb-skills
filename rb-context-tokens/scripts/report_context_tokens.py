#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def session_meta(path: Path) -> dict[str, Any]:
    try:
        first_line = path.open("r", encoding="utf-8").readline()
    except OSError:
        return {}
    if not first_line.strip():
        return {}
    try:
        item = json.loads(first_line)
    except json.JSONDecodeError:
        return {}
    if item.get("type") != "session_meta":
        return {}
    payload = item.get("payload", {})
    return payload if isinstance(payload, dict) else {}


def is_user_session(path: Path) -> bool:
    meta = session_meta(path)
    return meta.get("thread_source") == "user"


def latest_session(root: Path) -> Path:
    files = sorted(
        (p for p in root.rglob("*.jsonl") if p.is_file()),
        key=lambda p: (p.stat().st_mtime, str(p)),
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No .jsonl session files found under {root}")
    for path in files:
        if is_user_session(path):
            return path
    return files[0]


def iter_jsonl(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield line_number, json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}: {exc}") from exc


def token_count_events(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line_number, item in iter_jsonl(path):
        payload = item.get("payload", {})
        if item.get("type") == "event_msg" and payload.get("type") == "token_count":
            events.append(
                {
                    "line": line_number,
                    "timestamp": item.get("timestamp"),
                    "info": payload.get("info", {}),
                }
            )
    return events


def format_int(value: Any) -> str:
    return f"{value:,}" if isinstance(value, int) else "unknown"


def percent(numerator: Any, denominator: Any) -> str:
    if not isinstance(numerator, int) or not isinstance(denominator, int) or denominator <= 0:
        return "unknown"
    return f"{(numerator / denominator) * 100:.2f}%"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report the latest Codex token_count event from a session JSONL file."
    )
    parser.add_argument("--session", help="Specific Codex session .jsonl file to inspect")
    parser.add_argument(
        "--sessions-root",
        default="~/.codex/sessions",
        help="Root used to find the newest session when --session is omitted",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args()

    session = Path(args.session).expanduser() if args.session else latest_session(Path(args.sessions_root).expanduser())
    session = session.resolve()
    events = token_count_events(session)
    if not events:
        print(f"No token_count events found in {session}")
        return 1

    latest = events[-1]
    info = latest["info"]
    last = info.get("last_token_usage", {})
    total = info.get("total_token_usage", {})
    window = info.get("model_context_window")
    input_tokens = last.get("input_tokens")
    last_total = last.get("total_tokens")

    report = {
        "session": str(session),
        "event_timestamp": latest["timestamp"],
        "event_line": latest["line"],
        "current_context_tokens": input_tokens,
        "current_context_window_percent": (input_tokens / window) * 100
        if isinstance(input_tokens, int) and isinstance(window, int) and window > 0
        else None,
        "last_call_total_tokens": last_total,
        "last_token_usage": last,
        "total_token_usage": total,
        "model_context_window": window,
        "last_call_context_window_percent": (last_total / window) * 100
        if isinstance(last_total, int) and isinstance(window, int) and window > 0
        else None,
    }

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    print(f"Session: {session}")
    print(f"Token event: {latest['timestamp']} (line {latest['line']})")
    print()
    print("Current context:")
    print(f"  input tokens:             {format_int(input_tokens)}")
    print(f"  cached input tokens:      {format_int(last.get('cached_input_tokens'))}")
    print(f"  context window:           {format_int(window)}")
    print(f"  context usage:            {percent(input_tokens, window)}")
    print()
    print("Last call:")
    print(f"  output tokens:            {format_int(last.get('output_tokens'))}")
    print(f"  reasoning output tokens:  {format_int(last.get('reasoning_output_tokens'))}")
    print(f"  total tokens:             {format_int(last_total)}")
    print(f"  total/window usage:       {percent(last_total, window)}")
    print()
    print("Cumulative session usage:")
    print(f"  input tokens:             {format_int(total.get('input_tokens'))}")
    print(f"  cached input tokens:      {format_int(total.get('cached_input_tokens'))}")
    print(f"  output tokens:            {format_int(total.get('output_tokens'))}")
    print(f"  reasoning output tokens:  {format_int(total.get('reasoning_output_tokens'))}")
    print(f"  total tokens:             {format_int(total.get('total_tokens'))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
