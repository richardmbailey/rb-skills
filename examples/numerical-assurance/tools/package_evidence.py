"""Package local trial observations; deliberately not a qualified execution adapter.

Timestamps describe this evidence-import operation, never the original checks.
The whole-skill gate cannot become ACCEPTED through this bounded packager.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SCHEMAS = ROOT / "contracts"
MODULES = {
    "pytest": "unit",
    "lint": "lint",
    "format": "lint",
    "typing": "static_analysis",
    "coverage": "coverage",
    "mutation": "mutation",
    "independent_review": "independent_verification",
}
MAX_BYTES = 8_000_000


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def read_json(path: Path) -> object:
    def pairs(rows: list) -> dict:
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError(f"Duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value: str) -> None:
        raise ValueError(f"Non-finite JSON number: {value}")

    data = path.read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("Oversized input")
    return json.loads(data, object_pairs_hook=pairs, parse_constant=invalid)


def validate(value: dict, name: str) -> None:
    contracts = json.loads((SCHEMAS / "contracts.schema.json").read_text())
    registry = Registry().with_resource(
        contracts["$id"], Resource.from_contents(contracts)
    )
    schema = json.loads((SCHEMAS / f"{name}.schema.json").read_text())
    Draft202012Validator(
        schema, registry=registry, format_checker=FormatChecker()
    ).validate(value)


def pytest_counts(raw: dict, junit: Path) -> tuple[dict | None, list[str]]:
    """Count each node once, preserving setup/teardown errors and xfail states."""
    expected = raw.get("expected_test_ids", [])
    captured = raw.get("pytest", {})
    if not expected or len(expected) != len(set(expected)):
        return None, ["Missing, empty or duplicate test selection"]
    issues = []
    if captured.get("collected_ids") != expected:
        issues.append("Collected test IDs differ from selection")
    if captured.get("model_origin") != "model.py" or captured.get(
        "model_sha256"
    ) != raw.get("before_manifest", {}).get("model.py"):
        issues.append("Model import identity mismatch")
    counts = dict.fromkeys(
        ("collected", "passed", "failed", "skipped", "xfailed", "xpassed", "errors"), 0
    )
    counts["collected"] = len(expected)
    phases = captured.get("phases", [])
    if any(row.get("nodeid") not in expected for row in phases):
        issues.append("Unexpected executed test")
    for node in expected:
        rows = [row for row in phases if row.get("nodeid") == node]
        keyed = {row.get("when"): row for row in rows}
        if len(rows) != 3 or set(keyed) != {"setup", "call", "teardown"}:
            issues.append(f"Incomplete phases: {node}")
        if any(
            row.get("outcome") == "failed" and row.get("when") != "call" for row in rows
        ):
            counts["errors"] += 1
        elif any(row.get("wasxfail") for row in rows):
            counts[
                "xpassed"
                if keyed.get("call", {}).get("outcome") == "passed"
                else "xfailed"
            ] += 1
        elif any(row.get("outcome") == "failed" for row in rows):
            counts["failed"] += 1
        elif any(row.get("outcome") == "skipped" for row in rows):
            counts["skipped"] += 1
        elif len(rows) == 3 and all(row.get("outcome") == "passed" for row in rows):
            counts["passed"] += 1
        else:
            issues.append(f"Unknown phase outcome: {node}")
    try:
        data = junit.read_bytes()
        if (
            len(data) > MAX_BYTES
            or b"<!DOCTYPE" in data.upper()
            or b"<!ENTITY" in data.upper()
        ):
            raise ValueError("Unsafe or oversized XML")
        cases = ElementTree.fromstring(data).findall(".//testcase")
        if len(cases) != len(expected):
            issues.append("JUnit testcase count mismatch")
        for tag, key in (("failure", "failed"), ("error", "errors")):
            if sum(case.find(tag) is not None for case in cases) != counts[key]:
                issues.append(f"JUnit {tag} mismatch")
        if (
            sum(case.find("skipped") is not None for case in cases)
            != counts["skipped"] + counts["xfailed"]
        ):
            issues.append("JUnit skipped mismatch")
    except (OSError, ValueError, ElementTree.ParseError) as exc:
        issues.append(f"JUnit unavailable or invalid: {exc}")
    return counts, issues


def package(run: Path, mutations: Path, output: Path, root: Path = ROOT) -> dict:
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    clock = time.monotonic()
    raw = read_json(run / "receipts.json")
    if not isinstance(raw, dict) or raw.get("format") != "trial-raw-v1":
        raise ValueError("Unsupported raw receipt format")
    before = raw.get("before_manifest")
    if not isinstance(before, dict) or not before:
        raise ValueError("Missing source manifest")
    candidate = digest(before)
    policy = digest(
        {
            k: v
            for k, v in before.items()
            if k
            in {"REQUIREMENTS.md", "capabilities.json", "adoption.json", "AGENTS.md"}
        }
    )
    run_id = (
        "import-"
        + hashlib.sha256((run / "receipts.json").read_bytes()).hexdigest()[:16]
    )
    capabilities = read_json(root / "capabilities.json")
    contracts = json.loads((SCHEMAS / "contracts.schema.json").read_text())["$defs"]
    ids = contracts["Capability"]["properties"]["id"]["enum"]
    if not isinstance(capabilities, list) or [row["id"] for row in capabilities] != ids:
        raise ValueError(
            "Capability inventory must contain all 43 IDs in catalogue order"
        )
    if any(set(row["module_ids"]) - MODULES.keys() for row in capabilities):
        raise ValueError("Unknown module reference")
    output.mkdir(parents=True, exist_ok=False)
    artifacts = []

    def retain(path: Path, name: str) -> str | None:
        if not path.is_file():
            return None
        data = path.read_bytes()
        if len(data) > MAX_BYTES:
            raise ValueError("Oversized artifact")
        destination = output / "raw" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        artifacts.append(
            {
                "id": name,
                "path": f"raw/{name}",
                "sha256": hashlib.sha256(data).hexdigest(),
                "media_type": "application/json"
                if name.endswith(".json")
                else "text/plain",
                "bytes": len(data),
                "sensitivity": "ordinary",
                "redacted": False,
                "access": "local",
            }
        )
        return name

    for name in (
        "receipts.json",
        "pytest.json",
        "junit.xml",
        "coverage.json",
        "report.html",
    ):
        retain(run / name, name)
    for row in raw.get("commands", []):
        name = row.get("log", "")
        if Path(name).name != name or not name:
            raise ValueError("Unsafe log path")
        retain(run / name, name)
    for name in (
        "REQUIREMENTS.md",
        "capabilities.json",
        "adoption.json",
        "AGENTS.md",
        "independent-review.md",
        "review-provenance.json",
        "pyproject.toml",
        "change-impact.json",
    ):
        retain(root / name, name)
    mutation_file = mutations if mutations.is_file() else mutations / "result.json"
    mutation_id = retain(mutation_file, "mutations.json")
    mutation = read_json(mutation_file) if mutation_id else {}
    mutation_raw_ids = []
    mutation_raw_missing = False
    mutation_receipts = [
        row.get(tool, {})
        for row in mutation.get("cases", [])
        for tool in ("pytest", "lint", "typing")
    ]
    mutation_receipts.extend(
        row.get("receipt", {}) for row in mutation.get("tool_controls", [])
    )
    mutation_receipts.append(mutation.get("weak_control") or {})
    names = {r["log"] for r in mutation_receipts if r.get("log")}
    names.update(f"{row['id']}.xml" for row in mutation.get("cases", []))
    for name in sorted(names):
        if not name or Path(name).name != name:
            raise ValueError("Unsafe mutation artifact path")
        retained = retain(mutation_file.parent / name, f"mutations/{name}")
        if retained:
            mutation_raw_ids.append(retained)
        else:
            mutation_raw_missing = True
    gaps = [
        "full_adapter_qualification",
        "independent_host_authentication",
        "static_scope_capture",
        "renderer_qualification",
        "change_impact_review",
    ]
    if not raw.get("started_at") or not raw.get("finished_at"):
        gaps.append("execution_timestamps")
    if mutation_raw_missing:
        gaps.append("mutation_raw_artifacts")
    limitations = [
        (
            "These are post-run procedure imports, not "
            "pre-execution plans or authenticated executable receipts."
        ),
        (
            "UTC times describe packaging only; original timestamps "
            "remain in raw receipts."
        ),
        (
            "Raw tool success does not establish full skill, host "
            "adapter, static scope or renderer qualification."
        ),
        "Local shared workspace; no enforced write isolation or empirical validation.",
    ]
    if before != raw.get("after_manifest"):
        gaps.append("candidate_changed_during_run")
    for path, expected_hash in before.items():
        current = root / path
        if not current.resolve().is_relative_to(root.resolve()):
            raise ValueError("Manifest path escape")
        if (
            not current.is_file()
            or hashlib.sha256(current.read_bytes()).hexdigest() != expected_hash
        ):
            gaps.append("stale_candidate")
            break
    counts, pytest_gaps = pytest_counts(raw, run / "junit.xml")
    gaps.extend("pytest: " + item for item in pytest_gaps)
    commands = {}
    for row in raw.get("commands", []):
        if row["name"] in commands:
            raise ValueError("Duplicate command receipt")
        commands[row["name"]] = row
    results, plans = [], []
    target = {
        "environment": "local",
        "identity": "numerical-assurance local evidence import",
        "config_digest": digest(
            {k: v for k, v in before.items() if k.endswith(".toml")}
        ),
    }
    for module, capability in MODULES.items():
        required = any(
            row["required"] and module in row["module_ids"] for row in capabilities
        )
        sources = ["receipts.json"]
        status, observed, reason = (
            "REQUIRES_REVIEW",
            None,
            "Required evidence unavailable or unqualified",
        )
        command = commands.get({"lint": "ruff", "typing": "mypy"}.get(module, module))
        if command:
            if (
                command.get("timed_out")
                or command.get("output_limit_exceeded")
                or command.get("error")
            ):
                reason = "Command was interrupted or failed to execute"
            elif command.get("returncode") is not None:
                observed = command["returncode"] == 0
                status = "PASSED" if observed else "FAILED"
                reason = (
                    "Imported command exit observation only; see qualification gaps"
                )
            if module == "pytest" and pytest_gaps:
                status, observed, reason = (
                    "REQUIRES_REVIEW",
                    None,
                    "; ".join(pytest_gaps),
                )
            if (
                module == "pytest"
                and counts
                and counts["passed"] != counts["collected"]
            ):
                status = (
                    "FAILED"
                    if counts["failed"] or counts["errors"]
                    else "REQUIRES_REVIEW"
                )
                observed = False if status == "FAILED" else None
            if module == "coverage" and not (run / "coverage.json").is_file():
                status, observed = "REQUIRES_REVIEW", None
        if module == "mutation":
            sources.extend(mutation_raw_ids)
            if mutation_id:
                sources.append(mutation_id)
            rows = mutation.get("cases", [])
            expected_mutants = {
                "wrong_direction",
                "wrong_receiver",
                "wrong_rate",
                "wrong_final_step",
                "wrong_units",
                "missing_stability",
            }
            valid_identity = mutation.get(
                "format"
            ) == "fault-injection-v1" and mutation.get(
                "baseline_model_sha256"
            ) == before.get("model.py")
            if (
                valid_identity
                and rows
                and any(row.get("pytest", {}).get("returncode") == 0 for row in rows)
            ):
                status, observed, reason = (
                    "FAILED",
                    False,
                    "A required predeclared mutant survived",
                )
            elif (
                valid_identity
                and len(rows) == 6
                and {row.get("id") for row in rows} == expected_mutants
                and all(
                    row.get("detected") is True
                    and row.get("failures")
                    and row.get("pytest", {}).get("returncode") == 1
                    and not row.get("pytest", {}).get("timed_out")
                    and not row.get("pytest", {}).get("output_limit_exceeded")
                    for row in rows
                )
            ):
                status, observed, reason = (
                    "PASSED",
                    True,
                    (
                        "Six local mutation receipts record failing behavioural "
                        "assertions; raw evidence retained"
                    ),
                )
        if module == "independent_review":
            sources.extend(
                item["id"]
                for item in artifacts
                if item["id"] in {"independent-review.md", "review-provenance.json"}
            )
            reason = (
                "Requirements-first separate-agent work recorded "
                "locally; no authenticated host invocation receipt"
            )
        criterion = {
            "id": f"{module}-observation",
            "requirement_id": "R7" if module == "mutation" else "R6",
            "type": "assertion",
            "predicate": "is_true",
            "expected": True,
            "unit": None,
            "justification": (
                "Bounded import of raw trial outcomes; this criterion "
                "does not qualify the adapter or whole skill"
            ),
        }
        plan = {
            "schema_version": "1.0.0",
            "plan_id": f"{run_id}-{module}",
            "run_id": run_id,
            "module_id": module,
            "capability_id": capability,
            "kind": "procedure",
            "adapter": {"name": "trial-local-import", "version": "1"},
            "candidate_digest": candidate,
            "policy_digest": policy,
            "requirement_ids": [criterion["requirement_id"]],
            "subtypes": ["post_run_receipt_inspection"],
            "required": required,
            "profile": "standard",
            "inputs": [a for a in artifacts if a["id"] in sources],
            "depends_on": [],
            "command": None,
            "target": target,
            "effects": ["local_read", "disposable_write"],
            "authority_refs": [],
            "limits": {
                "timeout_seconds": 60,
                "termination_grace_seconds": 0,
                "max_output_bytes": MAX_BYTES,
                "max_concurrency": 1,
                "max_model_calls": 0,
                "max_tool_calls": 0,
                "max_spend": None,
            },
            "criteria": [criterion],
            "evidence_import": {
                "source_identity": "local unauthenticated trial receipts",
                "source_artifact_ids": sources,
                "receipt_artifact_id": "receipts.json",
                "expected_candidate_digest": candidate,
                "expected_policy_digest": policy,
                "target": target,
                "reviewer_identity": None,
                "host_invocation_ref": None,
                "observation": None,
            },
            "execution_contract": None,
            "static_contract": None,
        }
        validate(plan, "module-plan")
        plans.append(plan)
        result = {
            "module_id": module,
            "plan_id": plan["plan_id"],
            "attempt": 1,
            "execution": "completed",
            "assessment": status,
            "reason": reason,
            "receipt": {
                "id": f"import-{module}",
                "producer": "package_evidence.py",
                "authentication": "local",
                "started_at": started,
                "finished_at": datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
                "duration_seconds": time.monotonic() - clock,
                "exit_code": None,
                "tool": {
                    "name": "trial-local-import",
                    "version": "1",
                    "parser_version": "1",
                },
                "command": None,
                "termination": "normal",
                "artifact_ids": sources,
                "authority_refs": [],
                "execution_evidence": None,
                "static_evidence": None,
            },
            "criteria": [
                {
                    "criterion_id": criterion["id"],
                    "outcome": "unknown"
                    if observed is None
                    else "satisfied"
                    if observed
                    else "violated",
                    "observed": observed,
                    "unit": None,
                    "artifact_ids": sources,
                    "rationale": reason,
                }
            ],
            "counts": counts if module == "pytest" else None,
            "artifact_ids": sources,
            "reused_from": None,
        }
        results.append(result)
        if required and status == "REQUIRES_REVIEW":
            gaps.append(module)
    for row in capabilities:
        outcomes = [
            r["assessment"] for r in results if r["module_id"] in row["module_ids"]
        ]
        row["assessment"] = (
            "NOT_APPLICABLE"
            if row["disposition"] == "not_applicable"
            else "NOT_RUN"
            if row["disposition"] == "deferred"
            else "FAILED"
            if "FAILED" in outcomes
            else "PASSED"
            if outcomes
            and set(outcomes) == {"PASSED"}
            and row["disposition"] == "selected"
            else "REQUIRES_REVIEW"
        )
    gaps.extend(
        row["id"]
        for row in capabilities
        if row["required"]
        and row["assessment"] in {"NOT_RUN", "REQUIRES_REVIEW", "BLOCKED"}
    )
    failures = [
        r["module_id"]
        for r, p in zip(results, plans, strict=True)
        if p["required"] and r["assessment"] == "FAILED"
    ]
    gate = {
        "outcome": "REJECTED" if failures else "INSUFFICIENT_EVIDENCE",
        "policy_digest": policy,
        "required_failures": failures,
        "required_gaps": list(dict.fromkeys(gaps)),
        "blocking_finding_ids": [],
        "rationale": (
            "Imported observed failures take precedence; "
            "qualification and provenance gaps prevent full acceptance"
        ),
    }
    plan_artifacts = []
    for plan in plans:
        path = output / f"{plan['module_id']}.plan.json"
        path.write_text(json.dumps(plan, indent=2) + "\n")
        plan_artifacts.append(
            {
                "id": plan["plan_id"],
                "path": path.name,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "media_type": "application/json",
                "bytes": path.stat().st_size,
                "sensitivity": "ordinary",
                "redacted": False,
                "access": "local",
            }
        )
    adoption_input = (
        read_json(root / "adoption.json") if (root / "adoption.json").is_file() else {}
    )
    adoption = {
        "schema_version": "1.0.0",
        "candidate_digest": candidate,
        "policy_digest": policy,
        "run_id": run_id,
        "instruction_artifact_ids": [
            a["id"] for a in artifacts if a["id"] in {"AGENTS.md", "adoption.json"}
        ]
        or ["REQUIREMENTS.md"],
        "runner_argv": adoption_input.get(
            "runner_argv", ["python", "tools/run_suite.py"]
        ),
        "supported_workflows": adoption_input.get(
            "supported_workflows",
            [
                "ordinary_implementation",
                "scientific_implementation",
                "plan_execution",
                "direct_completion",
            ],
        ),
        "enforcement": "cooperative",
        "protection_receipt_ids": [],
        "completion": "incomplete",
        "required_gap_ids": gate["required_gaps"],
    }
    evidence = {
        "schema_version": "1.0.0",
        "run_id": run_id,
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "state": "finalised",
        "focus": "development",
        "profile": "standard",
        "candidate": {
            "snapshot_digest": candidate,
            "git_commit": None,
            "dirty": None,
            "scope": sorted(before),
            "excluded_inputs": ["artifacts", "tool caches"],
        },
        "provenance": {
            "specification_digest": digest(
                {k: v for k, v in before.items() if k == "REQUIREMENTS.md"}
            ),
            "policy_digest": policy,
            "tests_digest": digest(
                {k: v for k, v in before.items() if k.startswith("tests/")}
            ),
            "config_digest": target["config_digest"],
            "catalogue_digest": digest(capabilities),
            "runner_digest": digest(
                {k: v for k, v in before.items() if k.startswith("tools/")}
            ),
            "environment_digest": digest(
                {k: raw.get(k) for k in ("python", "platform", "tool_versions")}
            ),
        },
        "environment": {
            "os": raw.get("platform", "not captured"),
            "architecture": "not separately captured",
            "runtime_versions": [
                {"name": "python", "version": raw.get("python", "not captured")}
            ],
            "lock_digest": digest(
                {k: v for k, v in before.items() if "requirements" in k or "lock" in k}
            ),
            "isolation_requested": [],
            "isolation_enforced": [],
            "hardware": None,
            "limitations": [
                (
                    "Import describes raw environment; host isolation and "
                    "hardware were not verified"
                )
            ],
        },
        "capabilities": capabilities,
        "plans": plan_artifacts,
        "results": results,
        "artifacts": artifacts,
        "findings": [],
        "independence": {
            "status": "partial",
            "session_ref": None,
            "packet_digest": None,
            "context_separation": (
                "Local review notes describe requirements-first "
                "separate agent; consult retained note"
            ),
            "write_isolation": "Shared workspace, prompt-only boundaries",
            "enforcement": "prompt_only",
            "oracle_refs": ["REQUIREMENTS.md"],
            "receipt_artifact_ids": [
                a["id"]
                for a in artifacts
                if a["id"] in {"independent-review.md", "review-provenance.json"}
            ],
            "limitations": ["No authenticated host invocation receipt"],
            "recommendation": "escalate",
        },
        "gate": gate,
        "limitations": limitations,
        "adoption": adoption,
        "change_impact": {
            "schema_version": "1.0.0",
            "baseline_digest": None,
            "candidate_digest": candidate,
            "inventory_artifact_id": "receipts.json",
            "requirement_inventory_digest": digest(
                {k: v for k, v in before.items() if k == "REQUIREMENTS.md"}
            ),
            "status": "pending",
            "review_artifact_id": None,
            "changes": [],
            "behaviours": [],
            "unresolved_behavior_ids": ["complete_change_impact_mapping"],
        },
    }
    validate(evidence, "evidence")
    evidence_path = output / "evidence.json"
    evidence_path.write_text(json.dumps(evidence, indent=2) + "\n")
    report = {
        k: evidence[k]
        for k in (
            "schema_version",
            "run_id",
            "candidate",
            "focus",
            "profile",
            "gate",
            "capabilities",
            "findings",
            "independence",
            "provenance",
            "environment",
            "limitations",
            "adoption",
            "change_impact",
        )
    }
    report.update(
        {
            "evidence_digest": hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
            "rendered_at": evidence["finished_at"],
            "run_started_at": started,
            "run_finished_at": evidence["finished_at"],
            "summary": {
                "capability_counts": {
                    state: sum(c["assessment"] == state for c in capabilities)
                    for state in contracts["Summary"]["properties"][
                        "capability_counts"
                    ]["required"]
                },
                "logical_checks": len(results),
                "attempts": len(results),
                "test_counts": counts,
                "required_failed": len(failures),
                "optional_failed": sum(
                    r["assessment"] == "FAILED" and not p["required"]
                    for r, p in zip(results, plans, strict=True)
                ),
            },
            "sections": [
                {
                    "id": section,
                    "title": section.replace("_", " ").title(),
                    "availability": "unavailable"
                    if section in {"performance", "scientific"}
                    else "present",
                    "explanation": (
                        "Raw evidence import only; consult source receipts and "
                        "explicit limitations"
                    ),
                }
                for section in contracts["Section"]["properties"]["id"]["enum"]
            ],
            "modules": [
                {
                    **{
                        k: r[k]
                        for k in (
                            "module_id",
                            "attempt",
                            "execution",
                            "assessment",
                            "reason",
                            "criteria",
                            "artifact_ids",
                        )
                    },
                    "capability_id": p["capability_id"],
                    "required": p["required"],
                    "tool": r["receipt"]["tool"],
                    "duration_seconds": r["receipt"]["duration_seconds"],
                    "criterion_definitions": p["criteria"],
                    "execution_contract": None,
                    "static_contract": None,
                    "execution_evidence": None,
                    "static_evidence": None,
                }
                for r, p in zip(results, plans, strict=True)
            ],
            "scientific_checks": [],
            "charts": [],
            "artifact_links": artifacts + plan_artifacts,
        }
    )
    validate(report, "report")
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    if (run / "report.html").is_file():
        shutil.copyfile(run / "report.html", output / "raw-report.html")
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--mutations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    evidence = package(args.run, args.mutations, args.output)
    print(evidence["gate"]["outcome"])
    return 1 if evidence["gate"]["outcome"] == "REJECTED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
