from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from rb_safe_operation.canonical import artifact_hash, canonical_bytes
from rb_safe_operation.codex_cli_transport import (
    REVIEWED_CODEX_CLI_VERSION,
    CodexCliProtocolError,
    CodexCliTransport,
    _ROLE_CONTRACTS,
    _CodexVerificationDecision,
    _materialize_verifier_response,
    _output_schema_for_role,
)
from rb_safe_operation.proposal_models import PlanAssessmentResponse, VerificationRoleResponse
from rb_safe_operation.proposal_models import PatchSemanticAssessmentProposal


class FakeRunner:
    def __init__(self, result: dict[str, object] | None = None) -> None:
        self.result = result or {
            "schema_version": "1.0",
            "request_token": "request-1",
            "operation_id": "operation-1",
            "attempt_id": "attempt-1",
            "intent_summary": "Replace the bounded fixture text.",
            "unified_diff": "--- a/x.txt\n+++ b/x.txt\n@@ -1 +1 @@\n-a\n+b\n",
            "claimed_created_paths": [],
            "claimed_modified_paths": ["/tmp/x.txt"],
            "claimed_deleted_paths": [],
            "claimed_effect_ids": ["effect-1"],
            "evidence": [],
            "no_other_changes": True,
        }
        self.calls: list[tuple[list[str], dict[str, object]]] = []
        self.exec_events: list[dict[str, object]] | None = None
        self.exec_returncode = 0
        self.version = f"codex-cli {REVIEWED_CODEX_CLI_VERSION}\n"
        self.login = "Logged in using ChatGPT\n"
        self.output_schema: dict[str, object] | None = None
        self.prompt: bytes | None = None

    def __call__(self, argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        self.calls.append((list(argv), dict(kwargs)))
        if argv[-1] == "--version":
            return subprocess.CompletedProcess(argv, 0, self.version.encode(), b"")
        if argv[-2:] == ["login", "status"]:
            return subprocess.CompletedProcess(argv, 0, b"", self.login.encode())
        self.output_schema = json.loads(Path(argv[argv.index("--output-schema") + 1]).read_text())
        self.prompt = kwargs.get("input") if isinstance(kwargs.get("input"), bytes) else None
        output = Path(argv[argv.index("-o") + 1])
        output.write_bytes(canonical_bytes(self.result) + b"\n")
        events = self.exec_events or [
            {"type": "thread.started", "thread_id": "thread-test"},
            {"type": "turn.started"},
            {
                "type": "item.completed",
                "item": {
                    "id": "item-1",
                    "type": "agent_message",
                    "text": canonical_bytes(self.result).decode("utf-8"),
                },
            },
            {
                "type": "turn.completed",
                "usage": {
                    "input_tokens": 120,
                    "cached_input_tokens": 20,
                    "output_tokens": 30,
                    "reasoning_output_tokens": 5,
                },
            },
        ]
        stdout = b"".join(canonical_bytes(item) + b"\n" for item in events)
        return subprocess.CompletedProcess(argv, self.exec_returncode, stdout, b"")


class CodexCliTransportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.cli = Path(self.temporary.name) / "codex"
        self.cli.write_bytes(b"fixture executable\n")
        self.cli.chmod(0o700)
        self.request = canonical_bytes({
            "type": "role_request",
            "role": "proposer",
            "adapter": "json_line",
            "payload": {"schema_version": "1.0", "request_token": "request-1"},
        }) + b"\n"

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def transport(self, runner: FakeRunner) -> CodexCliTransport:
        return CodexCliTransport(
            cli_path=str(self.cli),
            model="gpt-5.6-sol",
            expected_cli_version=REVIEWED_CODEX_CLI_VERSION,
            max_response_bytes=20_000,
            runner=runner,
        )

    def test_structured_call_is_ephemeral_tool_disabled_and_usage_observed(self) -> None:
        runner = FakeRunner()
        transport = self.transport(runner)
        response = json.loads(transport.exchange(self.request, 20))
        self.assertEqual(response["type"], "role_response")
        self.assertEqual(response["payload"]["request_token"], "request-1")
        argv, kwargs = runner.calls[-1]
        self.assertIn("--ephemeral", argv)
        self.assertIn("--ignore-user-config", argv)
        self.assertIn("--ignore-rules", argv)
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        for capability in (
            "shell_tool", "unified_exec", "code_mode_host", "apps",
            "auth_elicitation", "computer_use", "browser_use", "goals", "hooks",
            "image_generation", "in_app_browser", "memories", "multi_agent", "personality",
            "plugin_sharing", "plugins", "remote_plugin", "request_permissions_tool",
            "shell_snapshot", "skill_mcp_dependency_install", "skill_search",
            "tool_call_mcp_elicitation", "tool_suggest", "workspace_dependencies",
        ):
            self.assertIn(["--disable", capability], [argv[i:i + 2] for i in range(len(argv) - 1)])
        self.assertNotIn(str(Path.cwd()), argv)
        self.assertEqual(kwargs["cwd"], argv[argv.index("-C") + 1])
        config_values = [argv[index + 1] for index, item in enumerate(argv[:-1]) if item == "-c"]
        self.assertTrue(any(item.startswith('sqlite_home="') for item in config_values))
        self.assertTrue(any(item.startswith('log_dir="') for item in config_values))
        self.assertEqual(transport.last_usage.input_tokens, 120)
        self.assertEqual(transport.last_usage.cached_input_tokens, 20)
        self.assertEqual(transport.last_usage.output_tokens, 30)
        self.assertEqual(transport.last_usage.tool_calls, 0)
        self.assertIn(b"never put an absolute path in a diff header", runner.prompt or b"")
        self.assertIn(b"including repository-read effects", runner.prompt or b"")
        self.assertIsNotNone(runner.output_schema)

        def assert_strict_objects(schema: object) -> None:
            if isinstance(schema, dict):
                if isinstance(schema.get("properties"), dict):
                    self.assertEqual(
                        set(schema.get("required", [])),
                        set(schema["properties"]),
                    )
                    self.assertFalse(schema.get("additionalProperties"))
                for value in schema.values():
                    assert_strict_objects(value)
            elif isinstance(schema, list):
                for value in schema:
                    assert_strict_objects(value)

        assert_strict_objects(runner.output_schema)

        def invariant_schemas(schema: object) -> list[dict[str, object]]:
            found: list[dict[str, object]] = []
            if isinstance(schema, dict):
                properties = schema.get("properties")
                if isinstance(properties, dict) and isinstance(properties.get("invariant_id"), dict):
                    found.append(properties["invariant_id"])
                for value in schema.values():
                    found.extend(invariant_schemas(value))
            elif isinstance(schema, list):
                for value in schema:
                    found.extend(invariant_schemas(value))
            return found

        for schema in invariant_schemas(runner.output_schema):
            self.assertIn("O-001", schema["enum"])
            self.assertNotIn("I-003", schema["enum"])

    def test_tool_event_is_rejected_even_when_final_output_is_valid(self) -> None:
        runner = FakeRunner()
        runner.exec_events = [
            {"type": "thread.started", "thread_id": "thread-test"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {"id": "tool-1", "type": "command_execution"}},
            {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
        ]
        with self.assertRaisesRegex(CodexCliProtocolError, "tool or unsupported item"):
            self.transport(runner).exchange(self.request, 20)

    def test_reasoning_lifecycle_events_are_not_misclassified_as_tools(self) -> None:
        runner = FakeRunner()
        result_text = canonical_bytes(runner.result).decode("utf-8")
        runner.exec_events = [
            {"type": "thread.started", "thread_id": "thread-test"},
            {"type": "turn.started"},
            {"type": "item.started", "item": {"id": "reason-1", "type": "reasoning"}},
            {"type": "item.completed", "item": {"id": "reason-1", "type": "reasoning"}},
            {"type": "item.completed", "item": {"id": "message-1", "type": "agent_message", "text": result_text}},
            {"type": "turn.completed", "usage": {"input_tokens": 2, "output_tokens": 1}},
        ]
        response = json.loads(self.transport(runner).exchange(self.request, 20))
        self.assertEqual(response["payload"]["request_token"], "request-1")

    def test_verifier_evidence_maps_are_bound_to_exact_request_keys(self) -> None:
        schema = _output_schema_for_role(
            "verifier",
            VerificationRoleResponse,
            {
                "expected_success_criteria": ["static_file_state::criterion one"],
                "expected_verifier_checks": ["static_file_state::check one"],
                "expected_effect_ids": ["effect-1"],
            },
        )
        proposal = schema["properties"]
        expected = {
            "criterion_evidence": ["static_file_state::criterion one"],
            "check_evidence": ["static_file_state::check one"],
            "effect_evidence": ["effect-1"],
        }
        for field, keys in expected.items():
            self.assertEqual(proposal[field]["required"], keys)
            self.assertEqual(set(proposal[field]["properties"]), set(keys))
            self.assertFalse(proposal[field]["additionalProperties"])
        evidence = schema["$defs"]["EvidenceRef"]["properties"]
        self.assertEqual(evidence["provenance"]["const"], "agent_reported")
        self.assertTrue(evidence["locator"]["pattern"].startswith("^agent-report:"))
        finding = schema["$defs"]["Finding"]["properties"]["finding_provenance"]
        self.assertEqual(finding["const"], "agent_reported")

    def test_plan_assessor_contract_separates_proposer_reads_from_static_verification(self) -> None:
        contract = _ROLE_CONTRACTS["plan_assessor"]
        self.assertIn("allowed_read_tools governs proposer interactive reads", contract)
        self.assertIn("read_roots must cover every deliberately selected source file", contract)
        self.assertIn("expected_product_changes", contract)
        self.assertIn("does not require the new product targets to be proposer read roots", contract)

        schema = _output_schema_for_role(
            "plan_assessor",
            PlanAssessmentResponse,
            {
                "plan": {
                    "operations": [{
                        "kind": "bounded_agent_task",
                        "required_assurance_profile": "instruction_only_proposal_host",
                    }],
                },
            },
        )
        provenance = schema["$defs"]["Finding"]["properties"]["finding_provenance"]
        self.assertEqual(provenance["const"], "agent_reported")
        self.assertNotIn("enum", provenance)
        patch_schema = _output_schema_for_role(
            "patch_assessor",
            PatchSemanticAssessmentProposal,
            {},
        )
        patch_provenance = patch_schema["$defs"]["Finding"]["properties"]["finding_provenance"]
        self.assertEqual(patch_provenance["const"], "agent_reported")
        public_schema = PlanAssessmentResponse.model_json_schema()
        public_provenance = (
            public_schema["$defs"]["Finding"]["properties"]["finding_provenance"]
        )
        self.assertEqual(
            set(public_provenance["enum"]),
            {"agent_reported", "coordinator_observed"},
        )

    def test_codex_host_factory_validates_identity_before_returning_host(self) -> None:
        from rb_safe_operation.codex_cli_adapter import build_codex_cli_role_host

        preview = SimpleNamespace(
            credential_handle="CODEX_CHATGPT_LOGIN",
            provider_grant=SimpleNamespace(
                model="gpt-5.6-sol",
                max_request_bytes=20_000,
                max_seconds=120,
            ),
            run_resource_grant=SimpleNamespace(
                max_response_bytes=10_000,
                max_elapsed_seconds=90,
            ),
        )
        with (
            patch("rb_safe_operation.codex_cli_adapter.validate_reviewed_codex_cli_profile"),
            patch("rb_safe_operation.codex_cli_adapter.CodexCliTransport") as transport_type,
            patch("rb_safe_operation.codex_cli_adapter.JsonLineProposalRoleHost") as host_type,
        ):
            built = build_codex_cli_role_host(preview)

        transport_type.return_value.validate_identity.assert_called_once_with(90)
        host_type.assert_called_once()
        self.assertIs(built, host_type.return_value)

    def test_verifier_identity_bindings_are_materialized_from_request(self) -> None:
        policy_binding = {
            "schema_version": "1.0",
            "project_root": "/tmp/project",
            "policy_path": "/tmp/project/.rb-safe-operation-policy.json",
            "presence": "absent",
            "source_policy_sha256": "0" * 64,
            "global_policy_hash": {
                "algorithm": "sha256",
                "artifact_type": "active-policy",
                "schema_version": "1.0",
                "value": "1" * 64,
            },
            "effective_policy_hash": {
                "algorithm": "sha256",
                "artifact_type": "active-policy",
                "schema_version": "2.0",
                "value": "2" * 64,
            },
        }
        payload = {
            "context": {"request_token": "request-verifier"},
            "verifier_context_id": "verifier-context",
            "plan": {"snapshot": {"marker": "pre"}, "policy_binding": policy_binding},
            "assessment": {"safe": True},
            "post_execution_snapshot": {"marker": "post"},
            "proposals": [{"proposal_id": "proposal-1"}],
            "patch_assessments": [{"assessment_id": "assessment-1"}],
            "execution_reports": [{"report_id": "report-1"}],
        }
        decision = _CodexVerificationDecision(
            schema_version="1.0",
            success_criteria_met=["criterion-1"],
            verifier_checks_passed=["check-1"],
            observed_effect_ids=["effect-1"],
            evidence=[],
            criterion_evidence={"criterion-1": []},
            check_evidence={"check-1": []},
            effect_evidence={"effect-1": []},
            findings=[],
        )

        response = _materialize_verifier_response(payload, decision)

        self.assertEqual(response.request_token, "request-verifier")
        proposal = response.verification_proposal
        self.assertEqual(proposal.verifier_context_id, "verifier-context")
        self.assertEqual(
            proposal.snapshot_hash.value,
            artifact_hash("repository-snapshot", "3.0", payload["post_execution_snapshot"]),
        )
        self.assertNotEqual(
            proposal.snapshot_hash.value,
            artifact_hash("repository-snapshot", "3.0", payload["plan"]["snapshot"]),
        )
        self.assertEqual(len(proposal.proposal_hashes), 1)
        self.assertEqual(len(proposal.patch_assessment_hashes), 1)
        self.assertEqual(len(proposal.execution_report_hashes), 1)

    def test_verifier_exchange_returns_materialized_role_response(self) -> None:
        policy_binding = {
            "schema_version": "1.0",
            "project_root": "/tmp/project",
            "policy_path": "/tmp/project/.rb-safe-operation-policy.json",
            "presence": "absent",
            "source_policy_sha256": "0" * 64,
            "global_policy_hash": {
                "algorithm": "sha256",
                "artifact_type": "active-policy",
                "schema_version": "1.0",
                "value": "1" * 64,
            },
            "effective_policy_hash": {
                "algorithm": "sha256",
                "artifact_type": "active-policy",
                "schema_version": "2.0",
                "value": "2" * 64,
            },
        }
        payload = {
            "context": {"request_token": "request-verifier"},
            "verifier_context_id": "verifier-context",
            "plan": {"snapshot": {"marker": "pre"}, "policy_binding": policy_binding},
            "assessment": {"safe": True},
            "post_execution_snapshot": {"marker": "post"},
            "proposals": [],
            "patch_assessments": [],
            "execution_reports": [],
            "expected_success_criteria": ["criterion-1"],
            "expected_verifier_checks": ["check-1"],
            "expected_effect_ids": ["effect-1"],
        }
        runner = FakeRunner({
            "schema_version": "1.0",
            "success_criteria_met": ["criterion-1"],
            "verifier_checks_passed": ["check-1"],
            "observed_effect_ids": ["effect-1"],
            "evidence": [],
            "criterion_evidence": {"criterion-1": []},
            "check_evidence": {"check-1": []},
            "effect_evidence": {"effect-1": []},
            "findings": [],
        })
        request = canonical_bytes({
            "type": "role_request",
            "role": "verifier",
            "adapter": "json_line",
            "payload": payload,
        }) + b"\n"

        response = json.loads(self.transport(runner).exchange(request, 20))["payload"]

        self.assertEqual(response["request_token"], "request-verifier")
        self.assertEqual(
            response["verification_proposal"]["snapshot_hash"]["value"],
            artifact_hash("repository-snapshot", "3.0", payload["post_execution_snapshot"]),
        )
        self.assertNotIn("request_token", runner.output_schema["properties"])
        self.assertNotIn("snapshot_hash", runner.output_schema["properties"])

    def test_plan_assessor_assurance_profiles_are_bound_to_bounded_operations(self) -> None:
        exact_schema = _output_schema_for_role(
            "plan_assessor",
            PlanAssessmentResponse,
            {"plan": {"operations": [{"kind": "exact_action"}]}},
        )
        exact = exact_schema["$defs"]["SemanticAssessmentProposalV2"]["properties"][
            "required_role_assurance_profiles"
        ]
        self.assertEqual((exact["minItems"], exact["maxItems"]), (0, 0))
        bounded_schema = _output_schema_for_role(
            "plan_assessor",
            PlanAssessmentResponse,
            {"plan": {"operations": [{
                "kind": "bounded_agent_task",
                "required_assurance_profile": "instruction_only_proposal_host",
            }]}},
        )
        bounded = bounded_schema["$defs"]["SemanticAssessmentProposalV2"]["properties"][
            "required_role_assurance_profiles"
        ]
        self.assertEqual(bounded["items"]["enum"], ["instruction_only_proposal_host"])
        self.assertEqual((bounded["minItems"], bounded["maxItems"]), (1, 1))

    def test_malformed_event_result_and_nonzero_exit_fail_closed(self) -> None:
        malformed = FakeRunner()
        malformed.exec_events = [{"type": "turn.completed"}]
        with self.assertRaises(CodexCliProtocolError):
            self.transport(malformed).exchange(self.request, 20)

        invalid_result = FakeRunner({"unexpected": True})
        with self.assertRaisesRegex(CodexCliProtocolError, "schema-invalid"):
            self.transport(invalid_result).exchange(self.request, 20)

        failed = FakeRunner()
        failed.exec_returncode = 2
        with self.assertRaisesRegex(CodexCliProtocolError, "non-zero"):
            self.transport(failed).exchange(self.request, 20)

    def test_event_lifecycle_and_stream_size_fail_closed(self) -> None:
        out_of_order = FakeRunner()
        out_of_order.exec_events = [
            {"type": "turn.started"},
            {"type": "thread.started", "thread_id": "thread-test"},
        ]
        with self.assertRaisesRegex(CodexCliProtocolError, "turn lifecycle"):
            self.transport(out_of_order).exchange(self.request, 20)

        after_completion = FakeRunner()
        result_text = canonical_bytes(after_completion.result).decode("utf-8")
        after_completion.exec_events = [
            {"type": "thread.started", "thread_id": "thread-test"},
            {"type": "turn.started"},
            {"type": "item.completed", "item": {
                "id": "message-1", "type": "agent_message", "text": result_text,
            }},
            {"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}},
            {"type": "item.completed", "item": {"id": "reason-1", "type": "reasoning"}},
        ]
        with self.assertRaisesRegex(CodexCliProtocolError, "outside the active turn"):
            self.transport(after_completion).exchange(self.request, 20)

        oversized = FakeRunner()
        with self.assertRaisesRegex(CodexCliProtocolError, "event stream exceeds"):
            CodexCliTransport(
                cli_path=str(self.cli), model="gpt-5.6-sol",
                expected_cli_version=REVIEWED_CODEX_CLI_VERSION,
                max_response_bytes=20, runner=oversized,
            ).exchange(self.request, 20)

    def test_timeout_version_login_and_executable_identity_fail_closed(self) -> None:
        class TimeoutRunner(FakeRunner):
            def __call__(self, argv: list[str], **kwargs: object):
                if "exec" in argv:
                    raise subprocess.TimeoutExpired(argv, kwargs.get("timeout", 0))
                return super().__call__(argv, **kwargs)

        with self.assertRaises(TimeoutError):
            self.transport(TimeoutRunner()).exchange(self.request, 1)

        wrong_version = FakeRunner()
        wrong_version.version = f"codex-cli {REVIEWED_CODEX_CLI_VERSION} unexpected\n"
        with self.assertRaisesRegex(CodexCliProtocolError, "version"):
            self.transport(wrong_version).exchange(self.request, 20)

        logged_out = FakeRunner()
        logged_out.login = "Not logged in\n"
        with self.assertRaisesRegex(CodexCliProtocolError, "authenticated"):
            self.transport(logged_out).exchange(self.request, 20)

        link = Path(self.temporary.name) / "codex-link"
        link.symlink_to(self.cli)
        with self.assertRaisesRegex(ValueError, "regular non-symbolic-link"):
            CodexCliTransport(
                cli_path=str(link), model="gpt-5.6-sol",
                expected_cli_version=REVIEWED_CODEX_CLI_VERSION,
                max_response_bytes=1000, runner=FakeRunner(),
            )

        drift_runner = FakeRunner()
        drifted = self.transport(drift_runner)
        self.cli.write_bytes(b"changed fixture executable\n")
        self.cli.chmod(0o700)
        with self.assertRaisesRegex(CodexCliProtocolError, "identity changed"):
            drifted.exchange(self.request, 20)


if __name__ == "__main__":
    unittest.main()
