"""Capture exact identities unavailable in native JUnit (including parameter IDs)."""

import hashlib
import json
import os
from pathlib import Path

import model

selected = []
outcomes = []


def pytest_collection_finish(session):
    selected.extend(item.nodeid for item in session.items)


def pytest_runtest_logreport(report):
    if report.when == "call" or report.outcome != "passed":
        outcomes.append(
            {"id": report.nodeid, "phase": report.when, "outcome": report.outcome}
        )


def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get("IDENTITY_OUTPUT")
    if destination:
        origin = Path(model.__file__).resolve()
        Path(destination).write_text(
            json.dumps(
                {
                    "selected": selected,
                    "outcomes": outcomes,
                    "model_origin": str(origin),
                    "model_sha256": hashlib.sha256(origin.read_bytes()).hexdigest(),
                    "exit": int(exitstatus),
                },
                indent=2,
            )
        )
