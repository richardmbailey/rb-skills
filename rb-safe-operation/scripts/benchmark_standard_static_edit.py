#!/usr/bin/env python3
"""Measure the local file-operation floor for the matched standard edit.

This is not a benchmark of an LLM implementation session. It deliberately
measures only the direct local edit and hash verification so the constrained
pipeline's orchestration overhead has an honest lower-bound comparison.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import time


EXPECTED = b"b\n"
EXPECTED_SHA256 = hashlib.sha256(EXPECTED).hexdigest()


def run_comparison() -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="rb-safe-standard-comparison-") as temporary:
        target = Path(temporary) / "input.txt"
        target.write_bytes(b"a\n")
        started = time.monotonic_ns()
        if target.read_bytes() != b"a\n":
            raise RuntimeError("matched standard fixture preimage changed")
        target.write_bytes(EXPECTED)
        observed_hash = hashlib.sha256(target.read_bytes()).hexdigest()
        elapsed_nanoseconds = time.monotonic_ns() - started
        if observed_hash != EXPECTED_SHA256:
            raise RuntimeError("matched standard fixture postimage is incorrect")
        return {
            "type": "matched_standard_static_edit",
            "scope": "direct local edit and hash verification only; excludes model deliberation",
            "elapsed_nanoseconds": elapsed_nanoseconds,
            "expected_target_sha256": EXPECTED_SHA256,
            "verified": True,
        }


def main() -> int:
    print(json.dumps(run_comparison(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
