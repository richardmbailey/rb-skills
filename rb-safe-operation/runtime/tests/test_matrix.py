from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from rb_safe_operation.audit import AuditError, AuditLog, redact
from rb_safe_operation.canonical import artifact_hash
from rb_safe_operation.fakes import (
    FakeApprovalStore,
    FakeCapabilityViolation,
    FakeClockResourceHost,
    FakeExternalService,
    FakeNetwork,
    FakeSecretStore,
    Ledger,
)
from rb_safe_operation.models import EventPayload, ExecutionReport, HostCapabilities, INVARIANT_IDS, RunManifest
from rb_safe_operation.paths import PathViolation, resolve_contained
from rb_safe_operation.policy import default_global_policy
from rb_safe_operation.state import StateError, capture_snapshot, snapshot_materially_equal, validate_resume_identity
from rb_safe_operation.workflow import WorkflowError, assess_plan as runtime_assess_plan, begin_verification_context, verify_reports

from helpers import capabilities, current_snapshot, safe_plan, semantic, verification_proposal


def assess_plan(plan, policy, host_capabilities, semantic_proposal, approvals):
    return runtime_assess_plan(
        plan,
        default_global_policy(plan.snapshot.project_root),
        policy,
        current_snapshot(plan),
        host_capabilities,
        semantic_proposal,
        approvals,
    )


class CapabilityLedgerTests(unittest.TestCase):
    def test_network_allow_and_redirect_denial(self):
        ledger = Ledger()
        network = FakeNetwork(ledger, {("docs.example", 443, "https", "GET")})
        self.assertEqual(network.request("docs.example", 443, "https", "GET")["status"], 200)
        with self.assertRaises(FakeCapabilityViolation):
            network.request("redirect.example", 443, "https", "GET")
        self.assertEqual(len(ledger.entries), 1)

    def test_secret_handle_never_records_value(self):
        ledger = Ledger()
        store = FakeSecretStore(ledger, {"deploy-token": "CANARY-SECRET"})
        self.assertEqual(store.resolve("deploy-token", "example"), "CANARY-SECRET")
        self.assertNotIn("CANARY-SECRET", json.dumps(ledger.entries))

    def test_one_use_approval_and_external_idempotency(self):
        ledger = Ledger()
        approvals = FakeApprovalStore(ledger, {"a": {"artifact_hash": "h", "consumed": False}})
        approvals.consume("a", "h")
        with self.assertRaises(FakeCapabilityViolation):
            approvals.consume("a", "h")
        service = FakeExternalService(ledger)
        service.write("fake-target", "key-1")
        with self.assertRaises(FakeCapabilityViolation):
            service.write("fake-target", "key-1")

    def test_unbounded_work_still_pauses_at_host_budget(self):
        ledger = Ledger()
        host = FakeClockResourceHost(ledger, remaining_steps=5)
        for index in range(5):
            host.consume(f"repair-{index}")
        with self.assertRaises(FakeCapabilityViolation):
            host.consume("repair-5")
        self.assertEqual([entry["action"] for entry in ledger.entries].count("consume"), 5)
        self.assertEqual(ledger.entries[-1]["action"], "pause")


class StateAuditMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "input.txt").write_text("hello", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_snapshot_is_observational_and_detects_change(self):
        before_paths = sorted(path.name for path in self.root.iterdir())
        first = capture_snapshot(str(self.root), ["input.txt"], [], [])
        self.assertEqual(before_paths, sorted(path.name for path in self.root.iterdir()))
        (self.root / "input.txt").write_text("changed", encoding="utf-8")
        second = capture_snapshot(str(self.root), ["input.txt"], [], [])
        equal, differences = snapshot_materially_equal(first, second)
        self.assertFalse(equal)
        self.assertTrue(any(item.startswith("selected_file:") for item in differences))

    def test_hardlink_mutation_denied(self):
        linked = self.root / "linked.txt"
        linked.hardlink_to(self.root / "input.txt")
        with self.assertRaises(PathViolation):
            resolve_contained(str(linked), [str(self.root)], [], mutation=True)

    def test_audit_partial_file_quarantines(self):
        audit = self.root / "audit"
        log = AuditLog(str(audit), "r")
        (audit / ".event-interrupted.tmp").write_text("partial", encoding="utf-8")
        with self.assertRaises(AuditError):
            log.validate_chain()
        self.assertTrue((audit / "quarantine" / ".event-interrupted.tmp").exists())

    def test_recovery_report_preserves_corruption(self):
        audit = self.root / "audit-recovery"
        log = AuditLog(str(audit), "r")
        (audit / ".event-interrupted.tmp").write_text("partial", encoding="utf-8")
        report = log.recover()
        self.assertEqual(report["status"], "human_required")
        self.assertEqual(len(list(audit.glob("recovery-*.json"))), 1)
        self.assertTrue((audit / "quarantine" / ".event-interrupted.tmp").exists())

    def test_redaction_omits_uncertain_free_text(self):
        value = redact({"message": "CANARY-SECRET", "api_key": "SECOND-CANARY", "status": "ok"})
        serialized = json.dumps(value)
        self.assertNotIn("CANARY", serialized)
        self.assertEqual(value["status"], "ok")

    def test_resume_identity_requires_every_hash(self):
        manifest = RunManifest(schema_version="1.0", run_id="r", state="paused_resource", suspended_from="executing", plan_hash=None, assessment_hash=None, policy_hash=None, snapshot_hash=None, event_head_hash="head")
        validate_resume_identity(manifest, plan_hash=None, assessment_hash=None, policy_hash=None, snapshot_hash=None, event_head_hash="head")
        with self.assertRaises(StateError):
            validate_resume_identity(manifest, plan_hash=None, assessment_hash=None, policy_hash=None, snapshot_hash=None, event_head_hash="changed")


class AssessmentVerificationMatrixTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "input.txt").write_text("hello", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_environment_widening_is_false(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["operations"][0]["environment"] = [{"name": "API_TOKEN", "literal_value": None, "value_hash": None, "secret_handle": "token"}]
        plan = plan.__class__.model_validate(data)
        result = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [])
        self.assertFalse(result.safe)
        self.assertIn("environment_widening", {item.category for item in result.findings})

    def test_network_widening_is_false(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["operations"][0]["network_grants"] = [{
            "grant_id": "g", "destinations": ["example.com"], "ports": [443], "protocols": ["https"],
            "methods": ["GET"], "semantics": ["read"], "request_data_classes": ["public"],
            "response_data_classes": ["public"], "credential_audiences": [], "redirect_destinations": [],
            "max_calls": 1, "max_bytes": 100, "max_seconds": 5, "retry_limit": 0,
            "idempotency_required": False, "approval_classes": [],
        }]
        plan = plan.__class__.model_validate(data)
        result = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [])
        self.assertFalse(result.safe)
        self.assertIn("network_widening", {item.category for item in result.findings})

    def test_missing_semantic_evidence_is_false(self):
        proposal = semantic().model_copy(update={"covered_evidence_ids": []})
        result = assess_plan(safe_plan(self.root), default_global_policy(str(self.root)), capabilities(), proposal, [])
        self.assertFalse(result.safe)
        self.assertEqual(result.missing_evidence_ids, ["evidence-source"])

    def test_malformed_agent_report_is_rejected(self):
        with self.assertRaises(ValidationError):
            TypeAdapter(ExecutionReport).validate_python({"schema_version": "1.0", "operation_id": "x", "success": "yes"})

    def test_verification_requires_independent_context(self):
        plan = safe_plan(self.root)
        assessment = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [])
        report = ExecutionReport(schema_version="1.0", operation_id="read-1", success=True, evidence=[], expected_effect_ids_observed=["effect-read"], unexpected_effects=[], next_strategy=None)
        context = begin_verification_context(plan, assessment, "fresh-context", current_snapshot(plan))
        proposal = verification_proposal(plan, assessment, context).model_copy(update={"verifier_context_id": "caller-claimed-context"})
        with self.assertRaises(WorkflowError):
            verify_reports(plan, assessment, [report], proposal, context)

    def test_volatile_observation_does_not_change_payload_identity(self):
        payload = {"safe": False, "findings": ["x"]}
        first = {"payload": payload, "observation": {"time": "one"}}
        second = {"payload": payload, "observation": {"time": "two"}}
        self.assertEqual(artifact_hash("assessment", "1.0", first["payload"]), artifact_hash("assessment", "1.0", second["payload"]))


class PackagingDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.skill_root = Path(__file__).resolve().parents[2]

    def tearDown(self):
        self.temporary.cleanup()

    def test_missing_manifest_is_named_and_does_not_install(self):
        environment = {**os.environ, "CODEX_HOME": str(self.root)}
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(self.skill_root / "scripts/run_runtime.py"), "runtime-info"],
            check=False, capture_output=True, text=True, env=environment,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing_runtime_manifest", result.stderr)
        self.assertEqual(list(self.root.iterdir()), [])

    def test_normative_invariant_headings_equal_closed_runtime_registry(self):
        reference_root = self.skill_root.parent / "plans" / "2026-07-18-constrained-plan-execution" / "references"
        observed: set[str] = set()
        for name in (
            "assurance-and-threat-model.md", "operation-and-policy-contract.md", "execution-audit-state-model.md",
        ):
            observed.update(re.findall(r"^### `([A-Z]-[0-9]{3})`", (reference_root / name).read_text(encoding="utf-8"), re.MULTILINE))
        self.assertEqual(observed, INVARIANT_IDS)

    def test_launcher_requires_isolated_no_site_no_bytecode_bootstrap(self):
        environment = {**os.environ, "CODEX_HOME": str(self.root)}
        result = subprocess.run(
            [sys.executable, str(self.skill_root / "scripts/run_runtime.py"), "runtime-info"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsafe_runtime_bootstrap", result.stderr)

    def test_isolated_launcher_does_not_import_pythonpath_sitecustomize(self):
        canary_root = self.root / "canary"
        canary_root.mkdir()
        marker = self.root / "sitecustomize-ran"
        (canary_root / "sitecustomize.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran', encoding='utf-8')\n",
            encoding="utf-8",
        )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(canary_root)
        environment["CODEX_HOME"] = str(self.root / "missing-codex-home")
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(self.skill_root / "scripts/run_runtime.py"), "runtime-info"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing_runtime_manifest", result.stderr)
        self.assertFalse(marker.exists(), "PYTHONPATH sitecustomize executed before launcher validation")

    def test_legacy_environment_redirects_are_ignored(self):
        codex_home = self.root / "canonical-codex-home"
        redirected_control = self.root / "redirected-control"
        redirected_control.mkdir()
        redirected_manifest = self.root / "redirected-manifest.json"
        redirected_manifest.write_text("{}\n", encoding="utf-8")
        environment = os.environ.copy()
        environment.update(
            {
                "CODEX_HOME": str(codex_home),
                "RB_SAFE_OPERATION_CONTROL_ROOT": str(redirected_control),
                "RB_SAFE_OPERATION_MANIFEST": str(redirected_manifest),
            }
        )
        result = subprocess.run(
            [sys.executable, "-I", "-S", "-B", str(self.skill_root / "scripts/run_runtime.py"), "runtime-info"],
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        expected = codex_home / "rb-safe-operation" / "current.json"
        self.assertEqual(result.returncode, 2)
        self.assertIn(f"missing_runtime_manifest: expected {expected}", result.stderr)
        self.assertNotIn(str(redirected_control), result.stderr)
        self.assertNotIn(str(redirected_manifest), result.stderr)

    def test_missing_runtime_source_is_named(self):
        wheelhouse = self.root / "wheels"
        wheelhouse.mkdir()
        result = subprocess.run(
            [sys.executable, str(self.skill_root / "scripts/setup_runtime.py"), "--control-root", str(self.root / "control"), "--wheelhouse", str(wheelhouse), "--runtime-root", str(self.root / "missing")],
            check=False, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("missing_runtime_skill", result.stderr)

    def test_unsupported_artifact_version_is_named(self):
        artifact = self.root / "artifact.json"
        artifact.write_text('{"schema_version":"2.0"}\n', encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "-m", "rb_safe_operation.cli", "validate", "--artifact-type", "active-policy", "--input", str(artifact)],
            check=False, capture_output=True, text=True, env=os.environ.copy(),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unsupported_artifact_version", result.stderr)

    def test_disposable_setup_reuse_and_identity_tamper_gates(self):
        wheelhouse_value = os.environ.get("RB_SAFE_OPERATION_TEST_WHEELHOUSE")
        if not wheelhouse_value or not Path(wheelhouse_value).is_dir():
            self.skipTest("RB_SAFE_OPERATION_TEST_WHEELHOUSE is not an available wheelhouse")
        copied_skill = self.root / "skill"
        shutil.copytree(
            self.skill_root,
            copied_skill,
            ignore=shutil.ignore_patterns("build", "*.egg-info", "__pycache__", "*.pyc", ".pytest_cache", "_source_identity.json"),
        )
        runtime = copied_skill / "runtime"
        before = self._tree_snapshot(runtime)
        codex_home = self.root / "codex-home"
        control = codex_home / "rb-safe-operation"
        setup = [
            sys.executable,
            str(copied_skill / "scripts/setup_runtime.py"),
            "--control-root",
            str(control),
            "--wheelhouse",
            wheelhouse_value,
            "--python",
            sys.executable,
        ]
        first = subprocess.run(setup, check=False, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(before, self._tree_snapshot(runtime), "setup polluted runtime source")
        manifest_path = control / "current.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        target = Path(manifest["interpreter_path"]).parents[2]
        self.assertEqual(target.name, f"0.1.0-{manifest['installed_source_hash']}-{manifest['lock_hash']}")
        self.assertRegex(manifest["installed_package_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(manifest["installed_package_hash"], manifest["expected_source_package_hash"])
        self.assertRegex(manifest["interpreter_hash"], r"^[0-9a-f]{64}$")
        self.assertEqual(manifest["launcher_bootstrap_interpreter_path"], str(Path(sys.executable).resolve(strict=True)))
        self.assertRegex(manifest["launcher_bootstrap_interpreter_hash"], r"^[0-9a-f]{64}$")
        interpreter_stat = Path(manifest["interpreter_path"]).stat()

        run = [sys.executable, "-I", "-S", "-B", str(copied_skill / "scripts/run_runtime.py"), "runtime-info"]
        run_environment = {**os.environ, "CODEX_HOME": str(codex_home)}
        invoked = subprocess.run(run, check=False, capture_output=True, text=True, env=run_environment)
        self.assertEqual(invoked.returncode, 0, invoked.stderr)
        info = json.loads(invoked.stdout)
        self.assertEqual(info["runtime_source_hash"], manifest["installed_source_hash"])
        self.assertEqual(info["runtime_lock_hash"], manifest["lock_hash"])
        self.assertEqual(info["installed_package_hash"], manifest["installed_package_hash"])
        self.assertEqual(info["recorded_installed_package_hash"], manifest["installed_package_hash"])

        forged_bootstrap_manifest = dict(manifest)
        forged_bootstrap_manifest["launcher_bootstrap_interpreter_hash"] = "0" * 64
        manifest_path.write_text(
            json.dumps(forged_bootstrap_manifest, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        bootstrap_mismatch = subprocess.run(run, check=False, capture_output=True, text=True, env=run_environment)
        self.assertEqual(bootstrap_mismatch.returncode, 2)
        self.assertIn("unsafe_runtime_bootstrap", bootstrap_mismatch.stderr)
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

        reused = subprocess.run(setup, check=False, capture_output=True, text=True)
        self.assertEqual(reused.returncode, 0, reused.stderr)
        self.assertEqual(interpreter_stat.st_ino, Path(manifest["interpreter_path"]).stat().st_ino)
        self.assertEqual(before, self._tree_snapshot(runtime), "reuse polluted runtime source")

        sentinel = self.root / "fake-interpreter-ran"
        fake_interpreter = self.root / "fake-python"
        fake_interpreter.write_text(f"#!/bin/sh\ntouch '{sentinel}'\n", encoding="utf-8")
        fake_interpreter.chmod(0o700)
        forged_manifest = dict(manifest)
        forged_manifest["interpreter_path"] = str(fake_interpreter)
        manifest_path.write_text(json.dumps(forged_manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
        swapped = subprocess.run(run, check=False, capture_output=True, text=True, env=run_environment)
        self.assertEqual(swapped.returncode, 2)
        self.assertFalse(sentinel.exists(), "unbound interpreter executed before validation")
        manifest_path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

        package_file = Path(manifest["installed_package_path"]) / "__init__.py"
        original_package = package_file.read_bytes()
        package_file.write_bytes(original_package + b"\n# accidental installed-package drift\n")
        tampered_run = subprocess.run(run, check=False, capture_output=True, text=True, env=run_environment)
        self.assertEqual(tampered_run.returncode, 2)
        self.assertIn("installed environment or dependency bytes differ", tampered_run.stderr)
        invalid_reuse = subprocess.run(setup, check=False, capture_output=True, text=True)
        self.assertEqual(invalid_reuse.returncode, 2)
        self.assertIn("existing environment tree differs", invalid_reuse.stderr)

        package_file.write_bytes(original_package)
        restored_run = subprocess.run(run, check=False, capture_output=True, text=True, env=run_environment)
        self.assertEqual(restored_run.returncode, 0, restored_run.stderr)
        dependency_file = Path(manifest["installed_package_path"]).parent / "pydantic" / "__init__.py"
        original_dependency = dependency_file.read_bytes()
        dependency_file.write_bytes(original_dependency + b"\n# dependency drift\n")
        dependency_tamper = subprocess.run(run, check=False, capture_output=True, text=True, env=run_environment)
        self.assertEqual(dependency_tamper.returncode, 2)
        self.assertIn("installed environment or dependency bytes differ", dependency_tamper.stderr)
        dependency_file.write_bytes(original_dependency)
        with (runtime / "requirements.lock").open("a", encoding="utf-8") as handle:
            handle.write("\n# reviewed lock identity change\n")
        stale_lock = subprocess.run(run, check=False, capture_output=True, text=True, env=run_environment)
        self.assertEqual(stale_lock.returncode, 2)
        self.assertIn("expected lock", stale_lock.stderr)

    @staticmethod
    def _tree_snapshot(root: Path) -> dict[str, str]:
        return {
            path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }


if __name__ == "__main__":
    unittest.main()
