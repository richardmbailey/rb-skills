"""Capture collection, phases and the model actually imported by pytest."""

import hashlib
import json
import os
import sys
from pathlib import Path

_CAPTURE = {"collected_ids": [], "phases": []}


def pytest_collection_finish(session):
    _CAPTURE["collected_ids"] = [item.nodeid for item in session.items]


def pytest_runtest_logreport(report):
    _CAPTURE["phases"].append(
        {
            "nodeid": report.nodeid,
            "when": report.when,
            "outcome": report.outcome,
            "wasxfail": getattr(report, "wasxfail", None),
        }
    )


def pytest_sessionfinish(session, exitstatus):
    destination = os.environ.get("RB_TRIAL_CAPTURE")
    if not destination:
        return
    module = sys.modules.get("model")
    origin = getattr(module, "__file__", None)
    if origin:
        path = Path(origin).resolve()
        root = Path(__file__).resolve().parent
        _CAPTURE["model_origin"] = (
            str(path.relative_to(root)) if path.is_relative_to(root) else str(path)
        )
        _CAPTURE["model_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    _CAPTURE["exitstatus"] = int(exitstatus)
    Path(destination).write_text(json.dumps(_CAPTURE, indent=2))
