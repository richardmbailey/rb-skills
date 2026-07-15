"""Load a routing manifest and its optional family case files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")

    inline = data.get("cases", [])
    if not isinstance(inline, list):
        raise ValueError("cases must be a list")
    cases = list(inline)

    case_files = data.get("case_files", [])
    if not isinstance(case_files, list) or not all(
        isinstance(item, str) and item.strip() for item in case_files
    ):
        raise ValueError("case_files must be a list of non-empty paths")
    for relative in case_files:
        case_path = path.parent / relative
        extra = json.loads(case_path.read_text(encoding="utf-8"))
        if not isinstance(extra, list):
            raise ValueError(f"case file must contain a list: {case_path}")
        cases.extend(extra)

    loaded = dict(data)
    loaded["cases"] = cases
    return loaded
