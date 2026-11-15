"""Synthetic parser fixtures; never used as trial evidence."""

import hashlib
import json

import pytest
from jsonschema import ValidationError

from tools.package_evidence import SCHEMAS, package, pytest_counts, read_json, validate


def fixture(tmp_path):
    root, run = tmp_path / "project", tmp_path / "run"
    root.mkdir()
    run.mkdir()
    (root / "model.py").write_text("# synthetic fixture, not the model\n")
    (root / "REQUIREMENTS.md").write_text("Synthetic parser acceptance fixture")
    (root / "AGENTS.md").write_text("Synthetic local policy")
    definitions = json.loads((SCHEMAS / "contracts.schema.json").read_text())["$defs"]
    capabilities = [
        {
            "id": name,
            "disposition": "selected"
            if name in {"unit", "mutation"}
            else "not_applicable",
            "required": name in {"unit", "mutation"},
            "reason": "Synthetic fixture only",
            "module_ids": ["pytest"]
            if name == "unit"
            else ["mutation"]
            if name == "mutation"
            else [],
        }
        for name in definitions["Capability"]["properties"]["id"]["enum"]
    ]
    (root / "capabilities.json").write_text(json.dumps(capabilities))
    manifest = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir()
    }
    capture = {
        "collected_ids": ["tests/test_synthetic.py::test_example"],
        "model_origin": "model.py",
        "model_sha256": manifest["model.py"],
        "phases": [
            {
                "nodeid": "tests/test_synthetic.py::test_example",
                "when": when,
                "outcome": "passed",
                "wasxfail": False,
            }
            for when in ("setup", "call", "teardown")
        ],
    }
    raw = {
        "format": "trial-raw-v1",
        "before_manifest": manifest,
        "after_manifest": manifest,
        "pytest": capture,
        "expected_test_ids": capture["collected_ids"],
        "commands": [
            {
                "name": "pytest",
                "log": "pytest.log",
                "returncode": 0,
                "timed_out": False,
                "output_limit_exceeded": False,
                "error": None,
            }
        ],
    }
    (run / "receipts.json").write_text(json.dumps(raw))
    (run / "pytest.log").write_text("synthetic")
    (run / "junit.xml").write_text(
        "<testsuites><testsuite>"
        '<testcase name="test_example"/></testsuite></testsuites>'
    )
    mutation = {
        "format": "fault-injection-v1",
        "baseline_model_sha256": manifest["model.py"],
        "cases": [
            {
                "id": key,
                "detected": True,
                "failures": ["test_example"],
                "pytest": {"returncode": 1},
            }
            for key in (
                "wrong_direction",
                "wrong_receiver",
                "wrong_rate",
                "wrong_final_step",
                "wrong_units",
                "missing_stability",
            )
        ],
    }
    mutation_path = tmp_path / "mutations.json"
    mutation_path.write_text(json.dumps(mutation))
    return root, run, raw, mutation_path


def test_schema_valid_import_retains_counts_and_incomplete_gate(tmp_path):
    root, run, _, mutation = fixture(tmp_path)
    output = tmp_path / "out"
    evidence = package(run, mutation, output, root)
    validate(evidence, "evidence")
    report = json.loads((output / "report.json").read_text())
    validate(report, "report")
    assert sum(report["summary"]["capability_counts"].values()) == 43
    assert report["summary"]["test_counts"]["passed"] == 1
    assert report["summary"]["logical_checks"] == 7
    assert evidence["gate"]["outcome"] == "INSUFFICIENT_EVIDENCE"
    assert all(
        p["kind"] == "procedure"
        for p in [json.loads(path.read_text()) for path in output.glob("*.plan.json")]
    )


def test_survivor_rejects_despite_claimed_all_detected(tmp_path):
    root, run, _, mutations = fixture(tmp_path)
    value = json.loads(mutations.read_text())
    value["all_detected"] = True
    value["cases"][0]["pytest"]["returncode"] = 0
    mutations.write_text(json.dumps(value))
    result = package(run, mutations, tmp_path / "out", root)
    assert result["gate"]["outcome"] == "REJECTED"
    assert "mutation" in result["gate"]["required_failures"]


def test_mutation_assertion_artifacts_are_retained_and_missing_is_visible(tmp_path):
    root, run, _, mutations = fixture(tmp_path)
    value = json.loads(mutations.read_text())
    value["cases"][0]["pytest"]["log"] = "wrong_direction-pytest.log"
    mutations.write_text(json.dumps(value))
    (tmp_path / "wrong_direction-pytest.log").write_text("synthetic assertion failure")
    (tmp_path / "wrong_direction.xml").write_text("<testsuite/>")
    result = package(run, mutations, tmp_path / "retained", root)
    indexed = {a["id"]: a for a in result["artifacts"]}
    assert "mutations/wrong_direction-pytest.log" in indexed
    assert "mutations/wrong_direction.xml" in indexed
    (tmp_path / "wrong_direction-pytest.log").unlink()
    incomplete = package(run, mutations, tmp_path / "missing", root)
    assert "mutation_raw_artifacts" in incomplete["gate"]["required_gaps"]


def test_missing_required_phases_and_junit_cannot_pass(tmp_path):
    root, run, raw, mutations = fixture(tmp_path)
    raw["pytest"]["phases"].pop()
    (run / "receipts.json").write_text(json.dumps(raw))
    (run / "junit.xml").unlink()
    result = package(run, mutations, tmp_path / "out", root)
    assert (
        next(row for row in result["results"] if row["module_id"] == "pytest")[
            "assessment"
        ]
        == "REQUIRES_REVIEW"
    )
    assert result["gate"]["outcome"] != "ACCEPTED"


@pytest.mark.parametrize("timestamp", ["2026-02-30T12:00:00Z", "not-a-timestamp"])
def test_offline_schema_checks_dates(tmp_path, timestamp):
    root, run, _, mutations = fixture(tmp_path)
    evidence = package(run, mutations, tmp_path / "out", root)
    evidence["started_at"] = timestamp
    with pytest.raises(ValidationError):
        validate(evidence, "evidence")


def test_xml_entities_rejected(tmp_path):
    _, run, raw, _ = fixture(tmp_path)
    (run / "junit.xml").write_text(
        '<!DOCTYPE x [<!ENTITY x SYSTEM "file:///etc/passwd">]><testsuites/>'
    )
    _, issues = pytest_counts(raw, run / "junit.xml")
    assert any("Unsafe" in issue for issue in issues)


@pytest.mark.parametrize("text", ['{"a": 1, "a": 2}', '{"a": NaN}'])
def test_malformed_json_rejected(tmp_path, text):
    path = tmp_path / "data.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        read_json(path)


def test_stale_candidate_visible(tmp_path):
    root, run, _, mutations = fixture(tmp_path)
    (root / "model.py").write_text("changed")
    evidence = package(run, mutations, tmp_path / "out", root)
    assert "stale_candidate" in evidence["gate"]["required_gaps"]
