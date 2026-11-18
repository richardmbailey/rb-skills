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


def object_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def token_number(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def usage_percent(tokens: int | None, window: int | None) -> float | None:
    return (tokens / window) * 100 if tokens is not None and window else None


def event_measurement(event: dict[str, Any]) -> dict[str, Any]:
    info = object_or_empty(event.get("info"))
    last = object_or_empty(info.get("last_token_usage"))
    total = object_or_empty(info.get("total_token_usage"))
    window = token_number(info.get("model_context_window"))
    input_tokens = token_number(last.get("input_tokens"))
    last_total = token_number(last.get("total_tokens"))
    return {
        "event_timestamp": event.get("timestamp"),
        "event_line": event.get("line"),
        "input_tokens": input_tokens,
        "context_window_percent": usage_percent(input_tokens, window),
        "last_call_total_tokens": last_total,
        "last_token_usage": last,
        "total_token_usage": total,
        "model_context_window": window,
        "last_call_context_window_percent": usage_percent(last_total, window),
    }


def last_recorded_measurement(events: list[dict[str, Any]]) -> dict[str, Any] | None:
    for event in reversed(events):
        measurement = event_measurement(event)
        if measurement["input_tokens"] is not None:
            return measurement
    return None


def format_int(value: Any) -> str:
    number = token_number(value)
    return f"{number:,}" if number is not None else "unknown"


def format_percent(value: float | None) -> str:
    return f"{value:.2f}%" if value is not None else "unknown"


def print_usage(measurement: dict[str, Any], *, current: bool) -> None:
    last = measurement["last_token_usage"]
    total = measurement["total_token_usage"]
    if current and measurement["input_tokens"] is None:
        print("Current context: unavailable (latest event lacks a usable input token count)")
        if not last and not total and measurement["model_context_window"] is None:
            return
    else:
        print("Current context:" if current else "Recorded context:")
    print(f"  input tokens:             {format_int(measurement['input_tokens'])}")
    print(f"  cached input tokens:      {format_int(last.get('cached_input_tokens'))}")
    print(f"  context window:           {format_int(measurement['model_context_window'])}")
    print(f"  context usage:            {format_percent(measurement['context_window_percent'])}")
    print()
    print("Last call:" if current else "Recorded call:")
    print(f"  output tokens:            {format_int(last.get('output_tokens'))}")
    print(f"  reasoning output tokens:  {format_int(last.get('reasoning_output_tokens'))}")
    print(f"  total tokens:             {format_int(measurement['last_call_total_tokens'])}")
    print(f"  total/window usage:       {format_percent(measurement['last_call_context_window_percent'])}")
    print()
    print("Cumulative session usage:" if current else "Cumulative usage at that event:")
    print(f"  input tokens:             {format_int(total.get('input_tokens'))}")
    print(f"  cached input tokens:      {format_int(total.get('cached_input_tokens'))}")
    print(f"  output tokens:            {format_int(total.get('output_tokens'))}")
    print(f"  reasoning output tokens:  {format_int(total.get('reasoning_output_tokens'))}")
    print(f"  total tokens:             {format_int(total.get('total_tokens'))}")


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
    latest = event_measurement(events[-1] if events else {})
    recorded = None
    if not events:
        status = "no_token_count_events"
    elif latest["input_tokens"] is None:
        status = "unavailable"
        recorded = last_recorded_measurement(events[:-1])
    else:
        status = "available"

    if args.json:
        report = {
            "session": str(session),
            "current_measurement_status": status,
            "last_recorded_measurement": recorded,
            **latest,
        }
        report["current_context_tokens"] = report.pop("input_tokens")
        report["current_context_window_percent"] = report.pop("context_window_percent")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if events else 1

    if not events:
        print(f"No token_count events found in {session}")
        return 1
    print(f"Session: {session}")
    print(f"Token event: {latest['event_timestamp'] or 'unknown'} (line {latest['event_line']})")
    print()
    print_usage(latest, current=True)
    if status == "available":
        return 0

    if recorded is None:
        print("No earlier token measurement is available")
    else:
        timestamp = recorded["event_timestamp"] or "unknown"
        print()
        print(f"Last recorded measurement: {timestamp} (line {recorded['event_line']})")
        print_usage(recorded, current=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
