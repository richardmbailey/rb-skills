from __future__ import annotations

from importlib.metadata import PackageNotFoundError
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import ValidationError

from rb_safe_operation.canonical import parse_json_strict
from rb_safe_operation.proposal_models import RunResourceGrant
from rb_safe_operation.readiness import (
    CONFIRMATION_PREFIX,
    confirm_run_preparation,
    load_confirmed_run_preparation,
    prepare_run_authority,
    run_doctor,
)
from rb_safe_operation.readiness_models import (
    DoctorRequest,
    RunPreparationConfirmation,
    RunPreparationRequest,
)
from rb_safe_operation.cli import cmd_codex_resume, cmd_codex_run
from rb_safe_operation.patches import capture_file_metadata


ZERO = "0" * 64


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class ReadinessContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "README.md").write_text("fixture\n", encoding="utf-8")
        self.mirrors = []
        for skill in ("rb-create-low-level-plan", "rb-assess-plan-safety", "rb-safe-operation", "rb-create-safe-operation-policy"):
            mirror = self.root / "installed" / skill / "references" / "generated"
            mirror.mkdir(parents=True)
            (mirror / "fixture.schema.json").write_text('{"schema":"same"}\n', encoding="utf-8")
            self.mirrors.append(str(mirror))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def doctor_request(self, **updates: object) -> DoctorRequest:
        payload = {
            "schema_version": "1.0",
            "request_id": "doctor-1",
            "observed_at": "2026-07-28T10:00:00Z",
            "project_root": str(self.root),
            "requested_profile": "exact_static",
            "adapter": "pydantic_ai",
            "requested_verification_modes": ["static_file_state"],
            "credential_handle": None,
            "credential_status": "not_required",
            "provider_grant_path": None,
            "run_resource_grant_path": None,
            "schema_mirror_roots": self.mirrors,
        }
        payload.update(updates)
        return DoctorRequest.model_validate(payload)

    def test_doctor_is_read_only_and_exact_static_can_be_ready(self) -> None:
        before = tree_bytes(self.root)
        result = run_doctor(self.doctor_request())
        self.assertEqual(result.status, "ready_exact_static")
        self.assertEqual(tree_bytes(self.root), before)
        self.assertEqual(result.requested_profile, "exact_static")
        self.assertEqual(result.observed_at, "2026-07-28T10:00:00Z")
        self.assertEqual(result.request_hash.artifact_type, "doctor-request")
        self.assertFalse(any(item.blocking for item in result.diagnostics))
        policy_status = next(item for item in result.diagnostics if item.code == "project_policy_status")
        self.assertIn("status is absent", policy_status.summary)

    def test_malformed_fixed_project_policy_is_not_ready(self) -> None:
        (self.root / ".rb-safe-operation-policy.json").write_text("{}\n", encoding="utf-8")
        result = run_doctor(self.doctor_request())
        self.assertEqual(result.status, "not_ready")
        self.assertIn(
            "invalid_project_policy",
            {item.code for item in result.diagnostics if item.blocking},
        )

    def test_framework_profile_requires_explicit_grants_and_credential_status(self) -> None:
        result = run_doctor(self.doctor_request(
            requested_profile="framework_proposal",
            credential_handle="OPENAI_API_KEY",
            credential_status="unknown",
        ))
        self.assertEqual(result.status, "not_ready")
        codes = {item.code for item in result.diagnostics if item.blocking}
        self.assertEqual(codes, {
            "credential_status_unknown",
            "missing_provider_grant",
            "missing_run_resource_grant",
        })
        self.assertNotIn("CANARY", result.model_dump_json())

    def test_instruction_only_profile_requires_its_explicit_adapter_and_grants(self) -> None:
        result = run_doctor(self.doctor_request(
            requested_profile="instruction_only_compatibility",
            adapter="json_line",
            credential_handle="HOST_CREDENTIAL",
            credential_status="available",
        ))
        self.assertEqual(result.status, "not_ready")
        self.assertEqual(
            {item.code for item in result.diagnostics if item.blocking},
            {"missing_provider_grant", "missing_run_resource_grant"},
        )
        self.assertIn("role and context restriction is instruction-only", result.omitted_capabilities)

    def test_framework_profile_checks_the_required_pydantic_ai_distribution(self) -> None:
        with patch("rb_safe_operation.readiness.package_version", side_effect=PackageNotFoundError):
            result = run_doctor(self.doctor_request(
                requested_profile="framework_proposal",
                credential_handle="OPENAI_API_KEY",
                credential_status="available",
            ))
        self.assertEqual(result.status, "not_ready")
        self.assertIn("missing_pydantic_ai", {item.code for item in result.diagnostics})

    def test_unsupported_verification_mode_stops_without_fallback(self) -> None:
        result = run_doctor(self.doctor_request(
            requested_verification_modes=["static_file_state", "executable_test"],
        ))
        self.assertEqual(result.status, "not_ready")
        self.assertIn("unsupported_verification_mode", {item.code for item in result.diagnostics})

    def test_schema_drift_and_lease_are_blocking_without_mutation(self) -> None:
        Path(self.mirrors[1], "fixture.schema.json").write_text('{"schema":"changed"}\n', encoding="utf-8")
        control = self.root / ".rb-safe-operation"
        control.mkdir()
        (control / "execution.lease").write_text("opaque lease\n", encoding="utf-8")
        before = tree_bytes(self.root)
        result = run_doctor(self.doctor_request())
        self.assertEqual(result.status, "not_ready")
        self.assertEqual(tree_bytes(self.root), before)
        self.assertTrue({"generated_schema_drift", "execution_lease_present"}.issubset(
            {item.code for item in result.diagnostics}
        ))

    def test_absent_or_empty_schema_mirror_is_not_ready(self) -> None:
        for mirror in self.mirrors:
            Path(mirror, "fixture.schema.json").unlink()
        result = run_doctor(self.doctor_request())
        self.assertEqual(result.status, "not_ready")
        self.assertIn("generated_schema_drift", {item.code for item in result.diagnostics})

    def test_unsafe_control_root_and_symlinked_schema_are_not_ready(self) -> None:
        (self.root / ".rb-safe-operation").write_text("not a directory\n", encoding="utf-8")
        schema = Path(self.mirrors[0], "fixture.schema.json")
        schema.unlink()
        schema.symlink_to(Path(self.mirrors[1], "fixture.schema.json"))
        result = run_doctor(self.doctor_request())
        self.assertEqual(result.status, "not_ready")
        self.assertTrue({"unsafe_control_root", "generated_schema_drift"}.issubset(
            {item.code for item in result.diagnostics}
        ))

    def test_paused_run_is_visible_but_nonblocking_and_active_run_blocks(self) -> None:
        runs = self.root / ".rb-safe-operation" / "runs"
        paused = runs / "paused-run"
        paused.mkdir(parents=True)
        (paused / "coordinator-bundle.json").write_text(
            json.dumps({"manifest": {"state": "paused_resource"}}), encoding="utf-8"
        )
        result = run_doctor(self.doctor_request())
        self.assertEqual(result.status, "ready_exact_static")
        self.assertIn("paused_run_present", {item.code for item in result.diagnostics})
        active = runs / "active-run"
        active.mkdir()
        (active / "coordinator-bundle.json").write_text(
            json.dumps({"manifest": {"state": "executing"}}), encoding="utf-8"
        )
        result = run_doctor(self.doctor_request())
        self.assertEqual(result.status, "not_ready")
        self.assertIn("unfinished_run_state", {item.code for item in result.diagnostics})

    def test_strict_doctor_contract_rejects_unknown_fields(self) -> None:
        payload = self.doctor_request().model_dump(mode="json") | {"ambient_discovery": True}
        with self.assertRaises(ValidationError):
            DoctorRequest.model_validate(payload)


class RunPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def request(self, **updates: object) -> RunPreparationRequest:
        payload = {
            "schema_version": "1.0",
            "preparation_id": "prep-1",
            "run_id": "run-1",
            "project_root": str(self.root),
            "adapter": "pydantic_ai",
            "provider": "openai",
            "endpoint": "https://api.openai.com/v1/responses",
            "model": "gpt-5-mini-2025-08-07",
            "model_revision": "2025-08-07",
            "credential_handle": "OPENAI_API_KEY",
            "credential_status": "available",
            "credential_audience": "api.openai.com",
            "roles": ["plan_assessor", "proposer", "patch_assessor", "verifier"],
            "request_data_classes": ["internal_source"],
            "response_data_classes": ["patch_proposal", "patch_assessment"],
            "maximum_data_classification": "internal",
            "retention_disclosure": "up to 30 days abuse monitoring; store=false",
            "training_use": "disallowed",
            "issued_at": "2026-07-28T10:00:00Z",
            "expires_at": "2026-07-28T12:00:00Z",
            "max_provider_calls": 8,
            "max_proposer_calls": 4,
            "max_assessor_calls": 4,
            "max_model_requests": 8,
            "max_read_tool_calls": 4,
            "max_read_tool_bytes": 100000,
            "max_patch_bytes": 100000,
            "max_request_bytes": 200000,
            "max_response_bytes": 100000,
            "max_input_tokens": 50000,
            "max_output_tokens": 20000,
            "max_elapsed_seconds": 600,
            "max_cost_decimal": "0.25",
            "cost_accounting": "observed",
            "temperature_decimal": "0",
            "seed": None,
            "structured_output_mode": "tool",
            "redirect_endpoints": [],
            "authorization_hash": {
                "artifact_type": "human-authorization",
                "schema_version": "1.0",
                "algorithm": "sha256",
                "value": ZERO,
            },
        }
        payload.update(updates)
        return RunPreparationRequest.model_validate(payload)

    def test_preview_constructs_exact_artifacts_and_never_contains_secret_value(self) -> None:
        request = self.request()
        preview = prepare_run_authority(request)
        dumped = preview.model_dump_json()
        self.assertEqual(preview.provider_grant.model, request.model)
        self.assertEqual(preview.run_resource_grant.max_model_requests, 8)
        self.assertEqual(preview.host_capabilities.role_tool_allocation, "framework_enforced")
        self.assertIn("OPENAI_API_KEY", dumped)
        self.assertNotIn("CANARY-SECRET-VALUE", dumped)
        self.assertTrue(any("finite" in line for line in preview.assurance_statements))
        self.assertTrue(any("external handle" in line for line in preview.assurance_statements))
        self.assertTrue(any("not an OS sandbox" in line for line in preview.assurance_statements))
        self.assertIn("Automatic retries are disabled.", preview.assurance_statements)

    def test_preview_binds_unbounded_format_retries_to_finite_aggregate_resources(self) -> None:
        request = self.request(
            automatic_retry_attempt_limit="unbounded",
            automatic_retry_classes=["proposal_format_error"],
        )
        preview = prepare_run_authority(request)
        resource = preview.run_resource_grant
        self.assertEqual(resource.automatic_retry_attempt_limit, "unbounded")
        self.assertEqual(resource.automatic_retry_classes, ["proposal_format_error"])
        self.assertEqual(resource.max_model_requests, 8)
        self.assertIn("bounded by aggregate resources", preview.assurance_statements[-1])
        statement = preview.exact_confirmation_statement
        confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-retry-envelope",
            preview_hash=preview.confirmation_binding_hash.value,
            statement=statement,
            confirmed_at="2026-07-28T10:05:00Z",
        )
        paths = confirm_run_preparation(preview, confirmation, statement)
        persisted = RunResourceGrant.model_validate(
            parse_json_strict(Path(paths["run_resource_grant"]).read_bytes())
        )
        self.assertEqual(persisted, resource)

    def test_codex_cli_preparation_uses_the_reviewed_codex_native_profile(self) -> None:
        request = self.request(
            adapter="json_line",
            provider="codex-cli",
            endpoint="host-mediated://codex-cli/exec",
            model="gpt-5.6-sol",
            model_revision=None,
            host_revision="0.146.0-alpha.3.1",
            credential_handle="CODEX_CHATGPT_LOGIN",
            credential_audience="chatgpt-local-auth",
            retention_disclosure=(
                "ephemeral local Codex thread; service retention follows the authenticated ChatGPT account"
            ),
            training_use="unknown",
            max_cost_decimal="0",
            cost_accounting="declared_zero",
            seed=None,
            structured_output_mode="native",
        )
        preview = prepare_run_authority(request)
        self.assertEqual(preview.provider_grant.provider, "codex-cli")
        self.assertEqual(preview.provider_grant.adapter, "json_line")
        self.assertEqual(preview.credential_handle, "CODEX_CHATGPT_LOGIN")
        with self.assertRaisesRegex(ValueError, "Codex CLI profile mismatch"):
            prepare_run_authority(request.model_copy(update={"model": "different-model"}))

    def test_doctor_reports_exact_codex_cli_readiness_and_login_failure(self) -> None:
        request = self.request(
            adapter="json_line", provider="codex-cli",
            endpoint="host-mediated://codex-cli/exec", model="gpt-5.6-sol",
            model_revision=None, host_revision="0.146.0-alpha.3.1",
            credential_handle="CODEX_CHATGPT_LOGIN",
            credential_audience="chatgpt-local-auth",
            retention_disclosure=(
                "ephemeral local Codex thread; service retention follows the authenticated ChatGPT account"
            ),
            training_use="unknown", max_cost_decimal="0",
            cost_accounting="declared_zero", seed=None, structured_output_mode="native",
        )
        preview = prepare_run_authority(request)
        statement = preview.exact_confirmation_statement
        confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-codex",
            preview_hash=preview.confirmation_binding_hash.value,
            statement=statement,
            confirmed_at="2026-07-28T10:05:00Z",
        )
        paths = confirm_run_preparation(preview, confirmation, statement)
        mirrors = []
        for skill in (
            "rb-create-low-level-plan", "rb-assess-plan-safety",
            "rb-safe-operation", "rb-create-safe-operation-policy",
        ):
            mirror = self.root / "installed" / skill / "references" / "generated"
            mirror.mkdir(parents=True)
            (mirror / "fixture.schema.json").write_text('{"schema":"same"}\n', encoding="utf-8")
            mirrors.append(str(mirror))
        doctor = DoctorRequest(
            schema_version="1.0", request_id="doctor-codex",
            observed_at="2026-07-28T11:00:00Z", project_root=str(self.root),
            requested_profile="codex_cli", adapter="json_line",
            requested_verification_modes=["static_file_state"],
            credential_handle="CODEX_CHATGPT_LOGIN", credential_status="available",
            provider_grant_path=paths["provider_grant"],
            run_resource_grant_path=paths["run_resource_grant"],
            schema_mirror_roots=mirrors,
        )
        with patch("rb_safe_operation.readiness._probe_codex_cli", return_value=None):
            ready = run_doctor(doctor)
        self.assertEqual(ready.status, "ready_codex_cli")
        self.assertEqual(ready.effective_assurance_profile, "instruction_only_proposal_host")
        with patch("rb_safe_operation.readiness._probe_codex_cli", side_effect=ValueError("logged out")):
            unavailable = run_doctor(doctor)
        self.assertEqual(unavailable.status, "not_ready")
        self.assertIn("unavailable_codex_cli", {item.code for item in unavailable.diagnostics})

    def test_confirmation_is_bound_to_preview_and_persists_create_only(self) -> None:
        preview = prepare_run_authority(self.request())
        preview_hash = preview.confirmation_binding_hash.value
        statement = preview.exact_confirmation_statement
        self.assertEqual(statement, f"{CONFIRMATION_PREFIX}{preview_hash}")
        confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-1",
            preview_hash=preview_hash,
            statement=statement,
            confirmed_at="2026-07-28T10:05:00Z",
        )
        result = confirm_run_preparation(preview, confirmation, statement)
        self.assertEqual(set(result), {
            "host_capabilities", "provider_grant", "run_preparation_confirmation",
            "run_preparation_preview", "run_resource_grant",
        })
        for path in result.values():
            self.assertTrue(Path(path).is_file())
        with self.assertRaises(FileExistsError):
            confirm_run_preparation(preview, confirmation, statement)

    def test_stale_or_wrong_confirmation_leaves_control_state_unchanged(self) -> None:
        preview = prepare_run_authority(self.request())
        preview_hash = preview.confirmation_binding_hash.value
        confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-1",
            preview_hash=preview_hash,
            statement=f"{CONFIRMATION_PREFIX}{preview_hash}",
            confirmed_at="2026-07-28T10:05:00Z",
        )
        with self.assertRaises(ValueError):
            confirm_run_preparation(preview, confirmation, "CONFIRM SOMETHING ELSE")
        self.assertFalse((self.root / ".rb-safe-operation").exists())

        expired_confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-expired",
            preview_hash=preview_hash,
            statement=preview.exact_confirmation_statement,
            confirmed_at="2026-07-28T12:00:00Z",
        )
        with self.assertRaisesRegex(ValueError, "confirmation_outside_authority_window"):
            confirm_run_preparation(
                preview,
                expired_confirmation,
                preview.exact_confirmation_statement,
            )
        self.assertFalse((self.root / ".rb-safe-operation").exists())

    def test_lease_appearing_after_preview_blocks_persistence(self) -> None:
        preview = prepare_run_authority(self.request())
        control = self.root / ".rb-safe-operation"
        control.mkdir()
        (control / "execution.lease").write_text("new lease\n", encoding="utf-8")
        statement = preview.exact_confirmation_statement
        confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-1",
            preview_hash=preview.confirmation_binding_hash.value,
            statement=statement,
            confirmed_at="2026-07-28T10:05:00Z",
        )
        with self.assertRaisesRegex(ValueError, "execution_lease_present"):
            confirm_run_preparation(preview, confirmation, statement)
        self.assertFalse((control / "preparations").exists())

    def test_preparation_rejects_unknown_credential_and_infinite_or_contradictory_limits(self) -> None:
        with self.assertRaises(ValidationError):
            self.request(credential_status="unknown")
        with self.assertRaises(ValidationError):
            self.request(max_model_requests=7, max_provider_calls=8)
        with self.assertRaises(ValidationError):
            self.request(max_cost_decimal="NaN")
        with self.assertRaises(ValidationError):
            self.request(roles=["proposer"])
        with self.assertRaises(ValidationError):
            self.request(automatic_retry_attempt_limit="unbounded")
        with self.assertRaises(ValidationError):
            self.request(automatic_retry_classes=["proposal_format_error"])

    def test_confirmed_grants_drive_framework_readiness_and_expiry(self) -> None:
        preview = prepare_run_authority(self.request())
        statement = preview.exact_confirmation_statement
        confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-1",
            preview_hash=preview.confirmation_binding_hash.value,
            statement=statement,
            confirmed_at="2026-07-28T10:05:00Z",
        )
        paths = confirm_run_preparation(preview, confirmation, statement)
        mirrors = []
        for skill in ("rb-create-low-level-plan", "rb-assess-plan-safety", "rb-safe-operation", "rb-create-safe-operation-policy"):
            mirror = self.root / "installed" / skill / "references" / "generated"
            mirror.mkdir(parents=True)
            (mirror / "fixture.schema.json").write_text('{"schema":"same"}\n', encoding="utf-8")
            mirrors.append(str(mirror))
        request = DoctorRequest(
            schema_version="1.0",
            request_id="doctor-framework",
            observed_at="2026-07-28T11:00:00Z",
            project_root=str(self.root),
            requested_profile="framework_proposal",
            adapter="pydantic_ai",
            requested_verification_modes=["static_file_state"],
            credential_handle="OPENAI_API_KEY",
            credential_status="available",
            provider_grant_path=paths["provider_grant"],
            run_resource_grant_path=paths["run_resource_grant"],
            schema_mirror_roots=mirrors,
        )
        supported_versions = {
            "pydantic-ai-slim": "2.19.0",
            "openai": "2.45.0",
            "tiktoken": "0.12.0",
        }
        with patch(
            "rb_safe_operation.readiness.package_version",
            side_effect=supported_versions.__getitem__,
        ), patch(
            "rb_safe_operation.readiness._import_openai_provider_adapter"
        ):
            self.assertEqual(run_doctor(request).status, "ready_framework_proposal")

        def missing_openai(name: str) -> str:
            if name == "openai":
                raise PackageNotFoundError(name)
            return supported_versions[name]

        with patch(
            "rb_safe_operation.readiness.package_version", side_effect=missing_openai
        ), patch(
            "rb_safe_operation.readiness._import_openai_provider_adapter"
        ):
            missing_transport = run_doctor(request)
        self.assertEqual(missing_transport.status, "not_ready")
        self.assertIn(
            "missing_openai_provider_dependency",
            {item.code for item in missing_transport.diagnostics if item.blocking},
        )

        with patch(
            "rb_safe_operation.readiness.package_version",
            side_effect=supported_versions.__getitem__,
        ), patch(
            "rb_safe_operation.readiness._import_openai_provider_adapter",
            side_effect=ImportError("provider import failed"),
        ):
            unavailable_transport = run_doctor(request)
        self.assertEqual(unavailable_transport.status, "not_ready")
        self.assertIn(
            "unavailable_openai_provider_adapter",
            {item.code for item in unavailable_transport.diagnostics if item.blocking},
        )
        expired = DoctorRequest.model_validate(request.model_dump(mode="json") | {
            "observed_at": "2026-07-28T12:00:00Z"
        })
        with patch(
            "rb_safe_operation.readiness.package_version",
            side_effect=supported_versions.__getitem__,
        ), patch(
            "rb_safe_operation.readiness._import_openai_provider_adapter"
        ):
            result = run_doctor(expired)
        self.assertEqual(result.status, "not_ready")
        self.assertEqual(
            {item.code for item in result.diagnostics if item.blocking},
            {"invalid_provider_grant", "invalid_run_resource_grant"},
        )
        provider_path = Path(paths["provider_grant"])
        tampered = json.loads(provider_path.read_text(encoding="utf-8"))
        tampered["model"] = "different-model"
        provider_path.write_text(
            json.dumps(tampered, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        tampered_result = run_doctor(request)
        self.assertEqual(tampered_result.status, "not_ready")
        self.assertIn(
            "invalid_preparation_bundle",
            {item.code for item in tampered_result.diagnostics if item.blocking},
        )

    def test_live_loader_requires_one_unchanged_confirmed_preparation_bundle(self) -> None:
        preview = prepare_run_authority(self.request())
        statement = preview.exact_confirmation_statement
        confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-live-loader",
            preview_hash=preview.confirmation_binding_hash.value,
            statement=statement,
            confirmed_at="2026-07-28T10:05:00Z",
        )
        paths = confirm_run_preparation(preview, confirmation, statement)
        loaded = load_confirmed_run_preparation(
            paths["run_preparation_preview"],
            project_root=str(self.root),
            run_id="run-1",
            observed_at="2026-07-28T11:00:00Z",
        )
        self.assertEqual(loaded, preview)

        with self.assertRaisesRegex(ValueError, "run identity"):
            load_confirmed_run_preparation(
                paths["run_preparation_preview"],
                project_root=str(self.root),
                run_id="other-run",
                observed_at="2026-07-28T11:00:00Z",
            )
        with self.assertRaisesRegex(ValueError, "expired"):
            load_confirmed_run_preparation(
                paths["run_preparation_preview"],
                project_root=str(self.root),
                run_id="run-1",
                observed_at="2026-07-28T12:00:00Z",
            )

    def test_confirmed_grants_drive_instruction_only_readiness(self) -> None:
        preview = prepare_run_authority(self.request(
            adapter="json_line",
            provider="operator-host",
            endpoint="host-mediated://json-line",
            model="operator-selected-model",
            model_revision=None,
            credential_handle="HOST_CREDENTIAL",
            credential_audience="operator-host",
            structured_output_mode="prompted",
        ))
        statement = preview.exact_confirmation_statement
        confirmation = RunPreparationConfirmation.from_statement(
            confirmation_id="confirmation-json-line",
            preview_hash=preview.confirmation_binding_hash.value,
            statement=statement,
            confirmed_at="2026-07-28T10:05:00Z",
        )
        paths = confirm_run_preparation(preview, confirmation, statement)
        mirrors = []
        for skill in ("rb-create-low-level-plan", "rb-assess-plan-safety", "rb-safe-operation", "rb-create-safe-operation-policy"):
            mirror = self.root / "installed" / skill / "references" / "generated"
            mirror.mkdir(parents=True)
            (mirror / "fixture.schema.json").write_text('{"schema":"same"}\n', encoding="utf-8")
            mirrors.append(str(mirror))
        request = DoctorRequest(
            schema_version="1.0",
            request_id="doctor-json-line",
            observed_at="2026-07-28T11:00:00Z",
            project_root=str(self.root),
            requested_profile="instruction_only_compatibility",
            adapter="json_line",
            requested_verification_modes=["static_file_state"],
            credential_handle="HOST_CREDENTIAL",
            credential_status="available",
            provider_grant_path=paths["provider_grant"],
            run_resource_grant_path=paths["run_resource_grant"],
            schema_mirror_roots=mirrors,
        )
        self.assertEqual(run_doctor(request).status, "ready_instruction_only_compatibility")


class ReadinessCliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.mirrors: list[str] = []
        for skill in ("rb-create-low-level-plan", "rb-assess-plan-safety", "rb-safe-operation", "rb-create-safe-operation-policy"):
            mirror = self.root / "installed" / skill / "references" / "generated"
            mirror.mkdir(parents=True)
            (mirror / "fixture.schema.json").write_text('{"schema":"same"}\n', encoding="utf-8")
            self.mirrors.append(str(mirror))
        self.environment = os.environ.copy()
        source = Path(__file__).resolve().parents[1] / "src"
        self.environment["PYTHONPATH"] = str(source)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "rb_safe_operation.cli", *arguments],
            check=False,
            capture_output=True,
            text=True,
            env=self.environment,
        )

    def test_doctor_plain_cli_is_read_only_and_names_the_profile(self) -> None:
        before = tree_bytes(self.root)
        arguments = [
            "doctor", "--request-id", "doctor-cli", "--observed-at", "2026-07-28T10:00:00Z",
            "--project-root", str(self.root), "--profile", "exact_static",
            "--adapter", "pydantic_ai", "--verification-mode", "static_file_state",
            "--credential-status", "not_required", "--format", "plain",
        ]
        for mirror in self.mirrors:
            arguments.extend(["--schema-mirror-root", mirror])
        result = self.run_cli(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ready for exact static operations", result.stdout)
        self.assertIn("Status code: ready_exact_static", result.stdout)
        self.assertIn("deterministic_coordinator_exact_static", result.stdout)
        self.assertEqual(tree_bytes(self.root), before)

    def test_framework_run_requires_an_explicit_live_provider_switch_before_loading_inputs(self) -> None:
        result = self.run_cli(
            "framework-run",
            "--plan", str(self.root / "absent-plan.json"),
            "--run-preparation-preview", str(self.root / "absent-preview.json"),
            "--verifier-context-id", "verifier-live-test",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("live provider execution is disabled", result.stderr)
        self.assertNotIn("absent-plan", result.stderr)

    def test_codex_run_requires_an_explicit_switch_before_loading_inputs(self) -> None:
        result = self.run_cli(
            "codex-run",
            "--plan", str(self.root / "absent-plan.json"),
            "--run-preparation-preview", str(self.root / "absent-preview.json"),
            "--verifier-context-id", "verifier-codex-test",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Codex CLI execution is disabled", result.stderr)
        self.assertNotIn("absent-plan", result.stderr)

    def test_codex_run_does_not_accept_an_executable_override(self) -> None:
        result = self.run_cli(
            "codex-run",
            "--plan", str(self.root / "absent-plan.json"),
            "--run-preparation-preview", str(self.root / "absent-preview.json"),
            "--verifier-context-id", "verifier-codex-fixed-executable",
            "--enable-codex-cli",
            "--codex-cli-path", str(self.root / "different-codex"),
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("unrecognized arguments: --codex-cli-path", result.stderr)
        self.assertFalse((self.root / ".rb-safe-operation").exists())

    def test_codex_run_builds_only_the_codex_host_from_confirmed_authority(self) -> None:
        plan = SimpleNamespace(
            snapshot=SimpleNamespace(project_root=str(self.root)),
            run_id="run-codex-driver",
        )
        preview = object()
        host = object()
        args = SimpleNamespace(
            enable_codex_cli=True,
            plan=str(self.root / "plan.json"),
            run_preparation_preview=str(self.root / "preview.json"),
        )
        with patch("rb_safe_operation.cli._load_fixed_plan", return_value=plan), patch(
            "rb_safe_operation.cli.load_confirmed_run_preparation", return_value=preview
        ) as load_preparation, patch(
            "rb_safe_operation.codex_cli_adapter.build_codex_cli_role_host", return_value=host
        ) as build_host, patch(
            "rb_safe_operation.cli._execute_confirmed_role_host"
        ) as execute:
            cmd_codex_run(args)
        load_preparation.assert_called_once()
        build_host.assert_called_once_with(preview)
        execute.assert_called_once_with(
            args, plan, preview, host, rejection_type="codex_assessment_rejected"
        )

    def test_codex_resume_reloads_usage_into_only_the_codex_host(self) -> None:
        preview = SimpleNamespace(
            host_capabilities=object(), provider_grant=object(), run_resource_grant=object()
        )
        host = object()
        coordinator = SimpleNamespace(
            manifest=SimpleNamespace(suspended_from=None, state="paused_resource"),
            lease=None,
            resume_after_pause=Mock(),
        )
        args = SimpleNamespace(
            enable_codex_cli=True,
            project_root=str(self.root),
            run_id="run-codex-resume",
            run_preparation_preview=str(self.root / "preview.json"),
            resume_evidence_id="resume-evidence",
            repair_attempt=None,
            verifier_context_id="verifier-resume",
        )
        with patch(
            "rb_safe_operation.cli.load_confirmed_run_preparation", return_value=preview
        ), patch(
            "rb_safe_operation.codex_cli_adapter.build_codex_cli_role_host", return_value=host
        ) as build_host, patch(
            "rb_safe_operation.cli.ExecutionCoordinator.reload", return_value=coordinator
        ) as reload_coordinator, patch(
            "rb_safe_operation.cli._drive_coordinate"
        ) as drive:
            cmd_codex_resume(args)
        build_host.assert_called_once_with(preview)
        reload_coordinator.assert_called_once_with(
            str(self.root), "run-codex-resume", preview.host_capabilities,
            agent_host=host, provider_grant=preview.provider_grant,
            run_resource_grant=preview.run_resource_grant,
            metadata_loader=capture_file_metadata,
        )
        coordinator.resume_after_pause.assert_called_once_with("resume-evidence")
        drive.assert_called_once_with(coordinator, args, preview.host_capabilities)

    def test_prepare_and_confirm_cli_use_exact_bound_preview(self) -> None:
        arguments = [
            "prepare-run-authority", "--preparation-id", "prep-cli", "--run-id", "run-cli",
            "--project-root", str(self.root), "--adapter", "pydantic_ai",
            "--provider", "openai", "--endpoint", "https://api.openai.com/v1/responses",
            "--model", "gpt-5-mini-2025-08-07", "--model-revision", "2025-08-07",
            "--credential-handle", "OPENAI_API_KEY", "--credential-status", "available",
            "--credential-audience", "api.openai.com", "--role", "plan_assessor",
            "--role", "proposer", "--role", "patch_assessor", "--role", "verifier",
            "--request-data-class", "internal_source",
            "--response-data-class", "patch_proposal", "--maximum-data-classification", "internal",
            "--retention-disclosure", "up to 30 days abuse monitoring; store=false",
            "--training-use", "disallowed", "--issued-at", "2026-07-28T10:00:00Z",
            "--expires-at", "2026-07-28T12:00:00Z", "--max-provider-calls", "8",
            "--max-proposer-calls", "4", "--max-assessor-calls", "4",
            "--max-model-requests", "8", "--max-read-tool-calls", "4",
            "--max-read-tool-bytes", "100000", "--max-patch-bytes", "100000",
            "--max-request-bytes", "200000", "--max-response-bytes", "100000",
            "--max-input-tokens", "50000", "--max-output-tokens", "20000",
            "--max-elapsed-seconds", "600", "--max-cost-decimal", "0.25",
            "--automatic-retry-attempt-limit", "unbounded",
            "--automatic-retry-class", "proposal_format_error",
            "--cost-accounting", "observed", "--temperature-decimal", "0",
            "--structured-output-mode", "tool", "--authorization-hash", ZERO,
            "--format", "json",
        ]
        result = self.run_cli(*arguments)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("CANARY-SECRET-VALUE", result.stdout + result.stderr)
        preview = json.loads(result.stdout)
        self.assertEqual(preview["provider_grant"]["max_calls"], 8)
        self.assertEqual(
            preview["run_resource_grant"]["automatic_retry_attempt_limit"], "unbounded"
        )
        self.assertEqual(
            preview["run_resource_grant"]["automatic_retry_classes"],
            ["proposal_format_error"],
        )
        preview_path = self.root / "preview.json"
        preview_path.write_text(result.stdout, encoding="utf-8")

        wrong = self.run_cli(
            "confirm-run-authority", "--preview", str(preview_path),
            "--confirmation-id", "confirmation-wrong", "--statement", "CONFIRM WRONG",
            "--confirmed-at", "2026-07-28T10:05:00Z",
        )
        self.assertEqual(wrong.returncode, 2)
        self.assertFalse((self.root / ".rb-safe-operation").exists())

        confirmed = self.run_cli(
            "confirm-run-authority", "--preview", str(preview_path),
            "--confirmation-id", "confirmation-cli",
            "--statement", preview["exact_confirmation_statement"],
            "--confirmed-at", "2026-07-28T10:05:00Z",
        )
        self.assertEqual(confirmed.returncode, 0, confirmed.stderr)
        payload = json.loads(confirmed.stdout)
        self.assertEqual(set(payload["artifact_paths"]), {
            "host_capabilities", "provider_grant", "run_preparation_confirmation",
            "run_preparation_preview", "run_resource_grant",
        })


if __name__ == "__main__":
    unittest.main()
