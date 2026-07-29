from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pydantic_ai import ModelResponse, ToolCallPart, models
from pydantic_ai.models.function import FunctionModel

from rb_safe_operation.canonical import artifact_hash, canonical_bytes
from rb_safe_operation.proposal_models import (
    AgentPatchProposal,
    BoundedAgentTaskV2,
    BoundedPatchProposal,
    ExactProposedChange,
    ExactTextInput,
    PatchAssessmentRequest,
    PatchProposalPreflight,
    PatchSemanticAssessmentProposal,
    PlanAssessmentResponse,
    ProposalContext,
    ProposalRequest,
    ProviderGrant,
    RunResourceGrant,
    ReadToolResult,
    SourceObservation,
    VerificationRoleResponse,
)
from rb_safe_operation.policy_models import (
    PathPolicyDecision,
    PolicyBinding,
    PolicyTranslationRequest,
    ProjectPolicyProposal,
    ProjectPolicyV2,
)
from rb_safe_operation.role_hosts import (
    JsonLineProposalRoleHost,
    PydanticAIProposalRoleHost,
    RoleHostProtocolError,
    RoleHostResourceExhausted,
    RoleHostTimeout,
)
from rb_safe_operation.workflow import hash_ref

from helpers import common, effect


ZERO = "0" * 64
ONE = "1" * 64


class FakeTransport:
    def __init__(self, response: bytes | Exception):
        self.response = response
        self.requests: list[tuple[bytes, float]] = []

    def exchange(self, request: bytes, timeout_seconds: float) -> bytes:
        self.requests.append((request, timeout_seconds))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class ProposalRoleHostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.target = self.root / "input.txt"
        self.target.write_text("a\n", encoding="utf-8")
        self.instructions_path = self.root / "AGENTS.md"
        self.instructions_text = "Change only the approved file."
        self.instructions_path.write_text(self.instructions_text, encoding="utf-8")
        operation = {
            **common(self.root, "op-1", effect("effect-1", targets=[str(self.target)])),
            "kind": "bounded_agent_task",
            "proposal_protocol": "unified_diff_v1",
            "goal": "replace a with b",
            "non_goals": ["do not touch other files"],
            "evidence_ids": ["evidence-source"],
            "source_data_classification": "internal",
            "allowed_read_tools": [],
            "allowed_patch_actions": ["modify"],
            "created_file_mode": 0o600,
            "forbidden_actions": ["direct writes", "shell", "network"],
            "permitted_adaptations": ["revise_local_code"],
            "diagnostic_checkpoint_rules": ["record a changed strategy"],
            "completion_evidence": ["completion-op-1"],
            "escalation_conditions": ["scope change"],
            "required_adapter": "pydantic_ai",
            "required_assurance_profile": "framework_tool_enforced_proposer",
            "provider_grant_id": "provider-grant-1",
            "run_resource_grant_id": "resource-grant-1",
        }
        operation["path_contract"]["modify_roots"] = [str(self.root)]
        self.operation = BoundedAgentTaskV2.model_validate(operation)
        self.provider_grant = ProviderGrant(
            schema_version="1.0",
            grant_id="provider-grant-1",
            issued_at="2026-07-28T10:00:00Z",
            expires_at="2026-07-28T11:00:00Z",
            roles=["plan_assessor", "proposer", "patch_assessor", "verifier"],
            adapter="pydantic_ai",
            provider="test-provider",
            endpoint="in-memory://function-model",
            model="role-model",
            model_revision="test-1",
            credential_audience="none:test-only",
            request_data_classes=["internal_source"],
            response_data_classes=["patch_proposal", "patch_assessment"],
            maximum_data_classification="internal",
            retention_disclosure="in-memory deterministic test",
            training_use="disallowed",
            max_calls=4,
            max_request_bytes=100_000,
            max_input_tokens=10_000,
            max_output_tokens=10_000,
            max_seconds=5,
            max_cost_decimal="0",
            cost_accounting="declared_zero",
            temperature_decimal="0",
            seed=7,
            structured_output_mode="tool",
            redirect_endpoints=[],
            approval_hash=None,
        )
        self.resource_grant = RunResourceGrant(
            schema_version="1.0",
            grant_id="resource-grant-1",
            issued_at="2026-07-28T10:00:00Z",
            expires_at="2026-07-28T11:00:00Z",
            max_proposer_calls=2,
            max_assessor_calls=2,
            max_model_requests=4,
            max_read_tool_calls=2,
            max_read_tool_bytes=100_000,
            max_patch_bytes=100_000,
            max_input_tokens=10_000,
            max_output_tokens=10_000,
            max_request_bytes=100_000,
            max_response_bytes=100_000,
            max_elapsed_seconds=10,
            max_cost_decimal="0",
            replenishes_grant_id=None,
            authorization_hash=hash_ref("human-authorization", {}, "1.0"),
        )
        self.policy_binding = PolicyBinding(
            schema_version="1.0", project_root=str(self.root),
            policy_path=str(self.root / ".rb-safe-operation-policy.json"),
            presence="absent",
            global_policy_hash=hash_ref("active-policy", {}, "1.0"),
            source_policy_sha256=ZERO,
            effective_policy_hash=hash_ref("active-policy", {}, "2.0"),
        )

    def allowed_read(self, path: Path) -> PathPolicyDecision:
        return PathPolicyDecision(
            schema_version="1.0", capability="read", requested_path=str(path),
            allowed=True, matched_rule_ids=[], component_identity_hash=ZERO,
            uncertainty=None,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def context(self, role: str, adapter: str = "pydantic_ai") -> ProposalContext:
        assurance = (
            ("framework_tool_enforced_proposer" if role == "proposer" else "framework_tool_enforced_no_tools")
            if adapter == "pydantic_ai" else "instruction_only_proposal_host"
        )
        source = self.target.read_text(encoding="utf-8")
        return ProposalContext(
            schema_version="2.0",
            context_id=f"context-{role}",
            request_token=f"request-{role}",
            operation_id="op-1",
            attempt_id="attempt-initial",
            role=role,
            adapter=adapter,
            assurance_profile=assurance,
            plan_hash=hash_ref("low-level-plan", {}, "3.0"),
            plan_assessment_hash=hash_ref("assessment", {}, "3.0"),
            operation_hash=hash_ref("operation", self.operation.model_dump(mode="json"), "2.0"),
            active_policy_hash=self.policy_binding.effective_policy_hash,
            policy_binding=self.policy_binding,
            base_snapshot_hash=hash_ref("repository-snapshot", {}, "3.0"),
            provider_grant_hash=hash_ref("provider-grant", self.provider_grant.model_dump(mode="json"), "1.0"),
            run_resource_grant_hash=hash_ref("run-resource-grant", self.resource_grant.model_dump(mode="json"), "1.0"),
            repair_attempt_hash=None,
            input_artifact_hashes=[],
            instruction_hashes={str(self.instructions_path): hashlib.sha256(self.instructions_text.encode()).hexdigest()},
            source_observations=[] if role == "patch_assessor" else [
                SourceObservation(
                    observation_id="source-1",
                    path=str(self.target),
                    byte_start=0,
                    byte_end=len(source.encode()),
                    content_hash=hashlib.sha256(source.encode()).hexdigest(),
                    metadata_hash=ZERO,
                    data_classification="internal",
                    policy_decision=self.allowed_read(self.target),
                )
            ],
            prompt_packet_hash=ZERO,
            toolset_hash=ZERO,
            created_at="2026-07-28T10:00:00Z",
        )

    def proposal_request(self, adapter: str = "pydantic_ai") -> ProposalRequest:
        context = self.context("proposer", adapter)
        source = self.target.read_text(encoding="utf-8")
        operation = self.operation
        if adapter == "json_line":
            operation = operation.model_copy(
                update={
                    "required_adapter": "json_line",
                    "required_assurance_profile": "instruction_only_proposal_host",
                }
            )
        context = context.model_copy(update={
            "operation_hash": hash_ref("operation", operation.model_dump(mode="json"), "2.0")
        })
        return ProposalRequest(
            schema_version="2.0",
            context=context,
            operation=operation,
            plan_evidence=[],
            applicable_instructions={str(self.instructions_path): self.instructions_text},
            source_inputs=[
                ExactTextInput(
                    input_id="input-1",
                    observation_id="source-1",
                    path=str(self.target),
                    byte_start=0,
                    byte_end=len(source.encode()),
                    content=source,
                    content_hash=hashlib.sha256(source.encode()).hexdigest(),
                    metadata_hash=ZERO,
                    data_classification="internal",
                )
            ],
        )

    def proposal_payload(self, token: str = "request-proposer") -> dict:
        return {
            "schema_version": "1.0",
            "request_token": token,
            "operation_id": "op-1",
            "attempt_id": "attempt-initial",
            "intent_summary": "replace a with b",
            "unified_diff": "--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-a\n+b\n",
            "claimed_created_paths": [],
            "claimed_modified_paths": [str(self.target)],
            "claimed_deleted_paths": [],
            "claimed_effect_ids": ["effect-1"],
            "evidence": [],
            "no_other_changes": True,
        }

    def json_line_host(self, response, *, timeout_seconds=2):
        grant = ProviderGrant.model_validate(self.provider_grant.model_dump(mode="json") | {
            "adapter": "json_line",
            "endpoint": "host-mediated://stdio",
        })
        return JsonLineProposalRoleHost(
            FakeTransport(response), timeout_seconds=timeout_seconds,
            provider_grant=grant, run_resource_grant=self.resource_grant,
            now=lambda: datetime(2026, 7, 28, 10, 30, tzinfo=timezone.utc),
        )

    def assessment_request(self, adapter: str = "pydantic_ai") -> PatchAssessmentRequest:
        context = self.context("patch_assessor", adapter)
        proposal = BoundedPatchProposal(
            schema_version="2.0",
            proposal_id="proposal-1",
            context_hash=hash_ref("proposal-context", {}, "2.0"),
            agent_proposal_hash=hash_ref("agent-patch-proposal", {}, "1.0"),
            plan_hash=context.plan_hash,
            plan_assessment_hash=context.plan_assessment_hash,
            operation_hash=context.operation_hash,
            active_policy_hash=context.active_policy_hash,
            policy_binding=context.policy_binding,
            base_snapshot_hash=context.base_snapshot_hash,
            repair_attempt_hash=None,
            patch_hash=ZERO,
            created_paths=[],
            modified_paths=[str(self.target)],
            deleted_paths=[],
            preimage_hashes={str(self.target): hashlib.sha256(b"a\n").hexdigest()},
            postimage_hashes={str(self.target): hashlib.sha256(b"b\n").hexdigest()},
            metadata_hashes={str(self.target): ZERO},
            expected_effect_ids=["effect-1"],
            proposer_role="proposer",
            assurance_profile=context.assurance_profile,
            evidence=[],
        )
        proposal_hash = hash_ref("bounded-patch-proposal", proposal.model_dump(mode="json"), "2.0")
        preflight = PatchProposalPreflight(
            schema_version="2.0",
            preflight_id="preflight-1",
            proposal_hash=proposal_hash,
            plan_hash=context.plan_hash,
            policy_hash=context.active_policy_hash,
            snapshot_hash=context.base_snapshot_hash,
            policy_binding=context.policy_binding,
            deterministic_pass=True,
            semantic_assessment_required=True,
            findings=[],
        )
        operation = self.operation
        if adapter == "json_line":
            operation = operation.model_copy(
                update={
                    "required_adapter": "json_line",
                    "required_assurance_profile": "instruction_only_proposal_host",
                }
            )
        context = context.model_copy(update={
            "operation_hash": hash_ref("operation", operation.model_dump(mode="json"), "2.0")
        })
        proposal = proposal.model_copy(update={
            "operation_hash": context.operation_hash,
            "assurance_profile": context.assurance_profile,
        })
        preflight = preflight.model_copy(update={
            "proposal_hash": hash_ref("bounded-patch-proposal", proposal.model_dump(mode="json"), "2.0")
        })
        return PatchAssessmentRequest(
            schema_version="2.0",
            context=context,
            operation=operation,
            proposal=proposal,
            preflight=preflight,
            exact_changes=[
                ExactProposedChange(
                    path=str(self.target),
                    action="modify",
                    preimage="a\n",
                    postimage="b\n",
                    preimage_hash=hashlib.sha256(b"a\n").hexdigest(),
                    postimage_hash=hashlib.sha256(b"b\n").hexdigest(),
                    metadata_hash=ZERO,
                )
            ],
            source_inputs=[],
            applicable_instructions={str(self.instructions_path): self.instructions_text},
        )

    def test_json_line_host_returns_strict_proposals_for_both_roles(self):
        proposal_response = canonical_bytes(
            {"type": "role_response", "role": "proposer", "adapter": "json_line", "payload": self.proposal_payload()}
        ) + b"\n"
        proposal_transport = FakeTransport(proposal_response)
        proposal_transport.last_usage = SimpleNamespace(
            requests=1, tool_calls=0, input_tokens=120, output_tokens=30,
        )
        grant = ProviderGrant.model_validate(self.provider_grant.model_dump(mode="json") | {
            "adapter": "json_line", "endpoint": "host-mediated://stdio",
        })
        host = JsonLineProposalRoleHost(
            proposal_transport, timeout_seconds=2, provider_grant=grant,
            run_resource_grant=self.resource_grant,
            now=lambda: datetime(2026, 7, 28, 10, 30, tzinfo=timezone.utc),
        )
        proposal = host.propose_patch(self.proposal_request("json_line"))
        self.assertIsInstance(proposal, AgentPatchProposal)
        emitted = json.loads(proposal_transport.requests[0][0])
        self.assertEqual(emitted["role"], "proposer")
        self.assertEqual(emitted["adapter"], "json_line")
        self.assertEqual(host.call_records[0].input_tokens, 120)
        self.assertEqual(host.call_records[0].output_tokens, 30)

        assessment_payload = {
            "schema_version": "2.0",
            "request_token": "request-patch_assessor",
            "proposal_hash": self.assessment_request("json_line").preflight.proposal_hash.model_dump(mode="json"),
            "semantic_pass": True,
            "findings": [],
            "covered_paths": [str(self.target)],
            "covered_effect_ids": ["effect-1"],
            "no_uncontrolled_detrimental_side_effects": True,
            "policy_binding": self.policy_binding.model_dump(mode="json"),
        }
        assessment_response = canonical_bytes(
            {"type": "role_response", "role": "patch_assessor", "adapter": "json_line", "payload": assessment_payload}
        ) + b"\n"
        assessment_host = self.json_line_host(assessment_response)
        self.assertIsInstance(
            assessment_host.assess_patch(self.assessment_request("json_line")),
            PatchSemanticAssessmentProposal,
        )

    def test_json_line_host_dispatches_owned_plan_assessor_and_verifier_roles(self):
        host = self.json_line_host(b"")
        request = SimpleNamespace(context=SimpleNamespace(adapter="json_line"))
        plan_result = object()
        with patch.object(host, "_exchange", return_value=plan_result) as exchange:
            self.assertIs(host.assess_plan(request), plan_result)
            exchange.assert_called_once_with(
                "plan_assessor", request, PlanAssessmentResponse
            )
        verifier_result = object()
        with patch.object(host, "_exchange", return_value=verifier_result) as exchange:
            self.assertIs(host.verify(request), verifier_result)
            exchange.assert_called_once_with(
                "verifier", request, VerificationRoleResponse
            )

    def test_json_line_host_rejects_eof_malformed_timeout_and_token_mismatch(self):
        request = self.proposal_request("json_line")
        eof_host = self.json_line_host(b"", timeout_seconds=1)
        with self.assertRaisesRegex(RoleHostProtocolError, "ended"):
            eof_host.propose_patch(request)
        self.assertEqual(eof_host.call_records[0].outcome, "protocol_error")
        self.assertFalse(eof_host.call_records[0].usage_complete)
        with self.assertRaisesRegex(RoleHostResourceExhausted, "incomplete usage"):
            eof_host.propose_patch(request)
        self.assertEqual(len(eof_host.transport.requests), 1)
        with self.assertRaises(RoleHostProtocolError):
            self.json_line_host(b"not json\n", timeout_seconds=1).propose_patch(request)
        with self.assertRaises(RoleHostTimeout):
            self.json_line_host(TimeoutError(), timeout_seconds=1).propose_patch(request)
        mismatched = canonical_bytes(
            {"type": "role_response", "role": "proposer", "adapter": "json_line", "payload": self.proposal_payload("wrong-token")}
        ) + b"\n"
        with self.assertRaisesRegex(RoleHostProtocolError, "request token"):
            self.json_line_host(mismatched, timeout_seconds=1).propose_patch(request)

    def test_pydantic_ai_host_exposes_no_function_tools_and_records_usage(self):
        seen: list[list[str]] = []
        seen_settings: list[dict[str, object]] = []

        def response(messages, info):
            seen.append([item.name for item in info.function_tools])
            seen_settings.append(dict(info.model_settings or {}))
            output = info.output_tools[0]
            return ModelResponse(parts=[ToolCallPart(tool_name=output.name, args=self.proposal_payload())])

        models.ALLOW_MODEL_REQUESTS = False
        os.environ["OPENAI_API_KEY"] = "AMBIENT-CANARY-MUST-NOT-BE-USED"
        host = PydanticAIProposalRoleHost(
            model=FunctionModel(response, model_name="role-model"),
            provider_grant=self.provider_grant,
            run_resource_grant=self.resource_grant,
            observed_provider="test-provider",
            observed_endpoint="in-memory://function-model",
            observed_credential_audience="none:test-only",
            observed_model_revision="test-1",
            now=lambda: "2026-07-28T10:30:00Z",
        )
        proposal = host.propose_patch(self.proposal_request())
        self.assertEqual(proposal.request_token, "request-proposer")
        self.assertEqual(seen, [[]])
        self.assertEqual(seen_settings[0]["openai_store"], False)
        self.assertEqual(seen_settings[0]["parallel_tool_calls"], False)
        self.assertEqual(seen_settings[0]["openai_native_tools"], ())
        self.assertEqual(host.call_records[0].tool_calls, 0)
        self.assertEqual(host.call_records[0].requests, 1)
        self.assertNotIn("AMBIENT-CANARY", canonical_bytes(host.call_records[0].model_dump()).decode())

    def test_pydantic_ai_patch_assessor_is_a_separate_no_tool_call(self):
        seen: list[list[str]] = []

        def response(messages, info):
            seen.append([item.name for item in info.function_tools])
            request = self.assessment_request()
            output = info.output_tools[0]
            payload = {
                "schema_version": "2.0",
                "request_token": request.context.request_token,
                "proposal_hash": request.preflight.proposal_hash.model_dump(mode="json"),
                "semantic_pass": True,
                "findings": [],
                "covered_paths": [str(self.target)],
                "covered_effect_ids": ["effect-1"],
                "no_uncontrolled_detrimental_side_effects": True,
                "policy_binding": self.policy_binding.model_dump(mode="json"),
            }
            return ModelResponse(parts=[ToolCallPart(tool_name=output.name, args=payload)])

        models.ALLOW_MODEL_REQUESTS = False
        host = PydanticAIProposalRoleHost(
            model=FunctionModel(response, model_name="role-model"),
            provider_grant=self.provider_grant, run_resource_grant=self.resource_grant,
            observed_provider="test-provider", observed_endpoint="in-memory://function-model",
            observed_credential_audience="none:test-only",
            observed_model_revision="test-1",
            now=lambda: "2026-07-28T10:30:00Z",
        )
        result = host.assess_patch(self.assessment_request())
        self.assertTrue(result.semantic_pass)
        self.assertEqual(seen, [[]])
        self.assertEqual(host.call_records[0].role, "patch_assessor")

    def test_pydantic_ai_proposer_receives_only_the_granted_mediated_read_tool(self):
        seen_tools: list[list[str]] = []
        calls = 0

        def response(messages, info):
            nonlocal calls
            calls += 1
            seen_tools.append([item.name for item in info.function_tools])
            if calls == 1:
                return ModelResponse(parts=[ToolCallPart(
                    tool_name="read_file",
                    args={"path": str(self.target), "byte_start": 0, "byte_end": 2},
                )])
            output = info.output_tools[0]
            return ModelResponse(parts=[ToolCallPart(tool_name=output.name, args=self.proposal_payload())])

        operation = self.operation.model_copy(update={"allowed_read_tools": ["read_file"]})
        base = self.proposal_request()
        context = base.context.model_copy(update={
            "operation_hash": hash_ref("operation", operation.model_dump(mode="json"), "2.0")
        })
        request = ProposalRequest.model_validate(base.model_dump(mode="json") | {
            "context": context.model_dump(mode="json"),
            "operation": operation.model_dump(mode="json"),
        })

        def mediated(path: str, byte_start: int, byte_end: int | None) -> ReadToolResult:
            self.assertEqual(path, str(self.target))
            self.assertEqual((byte_start, byte_end), (0, 2))
            return ReadToolResult(
                schema_version="2.0", request_token=context.request_token,
                observation_id="tool-read-1", path=path,
                byte_start=0, byte_end=2, content="a\n",
                content_hash=hashlib.sha256(b"a\n").hexdigest(), metadata_hash=ZERO,
                data_classification="internal",
                policy_decision=self.allowed_read(self.target),
            )

        models.ALLOW_MODEL_REQUESTS = False
        host = PydanticAIProposalRoleHost(
            model=FunctionModel(response, model_name="role-model"),
            provider_grant=self.provider_grant, run_resource_grant=self.resource_grant,
            observed_provider="test-provider", observed_endpoint="in-memory://function-model",
            observed_credential_audience="none:test-only",
            observed_model_revision="test-1",
            now=lambda: "2026-07-28T10:30:00Z",
        )
        proposal = host.propose_patch(request, read_file=mediated)
        reads = host.drain_read_results(context.request_token)
        self.assertEqual(proposal.operation_id, operation.operation_id)
        self.assertEqual(seen_tools, [["read_file"], ["read_file"]])
        self.assertEqual([item.observation_id for item in reads], ["tool-read-1"])
        self.assertEqual(host.call_records[0].tool_calls, 1)

    def test_role_hosts_fail_closed_on_expired_or_mismatched_grants(self):
        expired = ProviderGrant.model_validate(self.provider_grant.model_dump(mode="json") | {
            "expires_at": "2026-07-28T10:15:00Z",
        })
        host = PydanticAIProposalRoleHost(
            model=FunctionModel(lambda messages, info: ModelResponse(), model_name="role-model"),
            provider_grant=expired, run_resource_grant=self.resource_grant,
            observed_provider="test-provider", observed_endpoint="in-memory://function-model",
            observed_credential_audience="none:test-only",
            observed_model_revision="test-1",
            now=lambda: "2026-07-28T10:30:00Z",
        )
        from rb_safe_operation.role_hosts import RoleHostResourceExhausted
        with self.assertRaises(RoleHostResourceExhausted):
            host.propose_patch(self.proposal_request())
        with self.assertRaisesRegex(ValueError, "model"):
            PydanticAIProposalRoleHost(
                model=FunctionModel(lambda messages, info: ModelResponse(), model_name="wrong-model"),
                provider_grant=self.provider_grant, run_resource_grant=self.resource_grant,
                observed_provider="test-provider", observed_endpoint="in-memory://function-model",
                observed_credential_audience="none:test-only",
                observed_model_revision="test-1",
            )

    def test_adopted_role_record_preserves_aggregate_resource_use_across_hosts(self):
        provider = ProviderGrant.model_validate(self.provider_grant.model_dump(mode="json") | {
            "max_calls": 1,
        })
        resource = RunResourceGrant.model_validate(self.resource_grant.model_dump(mode="json") | {
            "max_model_requests": 1,
        })

        def response(messages, info):
            output = info.output_tools[0]
            return ModelResponse(parts=[ToolCallPart(tool_name=output.name, args=self.proposal_payload())])

        first = PydanticAIProposalRoleHost(
            model=FunctionModel(response, model_name="role-model"),
            provider_grant=provider, run_resource_grant=resource,
            observed_provider="test-provider", observed_endpoint="in-memory://function-model",
            observed_credential_audience="none:test-only", observed_model_revision="test-1",
            now=lambda: "2026-07-28T10:30:00Z",
        )
        first.propose_patch(self.proposal_request())

        resumed = PydanticAIProposalRoleHost(
            model=FunctionModel(response, model_name="role-model"),
            provider_grant=provider, run_resource_grant=resource,
            observed_provider="test-provider", observed_endpoint="in-memory://function-model",
            observed_credential_audience="none:test-only", observed_model_revision="test-1",
            now=lambda: "2026-07-28T10:30:00Z",
        )
        resumed.adopt_call_record(first.call_records[0])
        resumed.adopt_call_record(first.call_records[0])
        self.assertEqual(len(resumed.call_records), 1)
        with self.assertRaisesRegex(RoleHostResourceExhausted, "model-request grant"):
            resumed.propose_patch(self.proposal_request())

        mismatched = first.call_records[0].model_copy(update={"endpoint": "in-memory://other"})
        with self.assertRaisesRegex(RoleHostProtocolError, "provider identity"):
            resumed.adopt_call_record(mismatched)

    def test_policy_translator_is_typed_and_receives_no_tools_in_both_profiles(self):
        policy_payload = {
            "schema_version": "2.0", "policy_version": "fixture-1",
            "path_rules": [{
                "rule_id": "deny-x", "path": "x.txt", "scope": "exact",
                "deny": ["create", "delete", "modify", "read"], "reason": "user restriction",
            }],
            "deny_operations": [], "deny_adapters": [], "deny_effect_classes": [],
            "deny_command_forms": [], "intersect_path_roots": None,
            "intersect_executable_hashes": None, "intersect_network_grants": None,
            "intersect_environment_names": None, "lower_maximums": {},
            "require_approvals": [], "require_minimum_enforcement": {},
            "require_minimum_observation": {}, "require_evidence_sources": [],
            "require_verification": [],
        }
        proposal_payload = {
            "schema_version": "1.0", "request_token": "policy-request",
            "proposed_policy": policy_payload, "ambiguity_questions": [],
            "interpretation_summary": "Deny reading and all writes to x.txt.",
            "no_protected_content_observed": True,
        }
        pyd_grant = ProviderGrant.model_validate(self.provider_grant.model_dump(mode="json") | {
            "roles": ["policy_translator"],
            "request_data_classes": ["policy_request"],
            "response_data_classes": ["project_policy_proposal"],
            "max_calls": 1,
        })
        pyd_request = PolicyTranslationRequest(
            schema_version="1.0", request_token="policy-request", adapter="pydantic_ai",
            assurance_profile="framework_tool_enforced_authoring",
            provider_grant_hash=hash_ref("provider-grant", pyd_grant.model_dump(mode="json"), "1.0"),
            run_resource_grant_hash=hash_ref("run-resource-grant", self.resource_grant.model_dump(mode="json"), "1.0"),
            project_root_identity_hash=ZERO, source_policy_sha256=ONE,
            policy_binding=self.policy_binding.model_copy(update={"source_policy_sha256": ONE}),
            current_policy=None, bounded_user_request="Do not read or write x.txt.",
            named_project_relative_paths=["x.txt"], created_at="2026-07-28T10:00:00Z",
        )
        observed_tools = []

        def response(messages, info):
            observed_tools.append([item.name for item in info.function_tools])
            output = info.output_tools[0]
            return ModelResponse(parts=[ToolCallPart(tool_name=output.name, args=proposal_payload)])

        pyd_host = PydanticAIProposalRoleHost(
            model=FunctionModel(response, model_name="role-model"), provider_grant=pyd_grant,
            run_resource_grant=self.resource_grant, observed_provider="test-provider",
            observed_endpoint="in-memory://function-model", observed_credential_audience="none:test-only",
            observed_model_revision="test-1", now=lambda: "2026-07-28T10:30:00Z",
        )
        self.assertEqual(pyd_host.translate_policy(pyd_request).proposed_policy.path_rules[0].rule_id, "deny-x")
        self.assertEqual(observed_tools, [[]])
        self.assertEqual(pyd_host.call_records[0].role, "policy_translator")
        self.assertEqual(pyd_host.call_records[0].tool_calls, 0)

        json_grant = ProviderGrant.model_validate(pyd_grant.model_dump(mode="json") | {
            "adapter": "json_line", "endpoint": "host-mediated://stdio",
        })
        json_request = PolicyTranslationRequest.model_validate(pyd_request.model_dump(mode="json") | {
            "adapter": "json_line", "assurance_profile": "instruction_only_authoring",
            "provider_grant_hash": hash_ref("provider-grant", json_grant.model_dump(mode="json"), "1.0").model_dump(mode="json"),
        })
        response_bytes = canonical_bytes({
            "type": "role_response", "role": "policy_translator", "adapter": "json_line",
            "payload": proposal_payload,
        }) + b"\n"
        json_host = JsonLineProposalRoleHost(
            FakeTransport(response_bytes), timeout_seconds=2, provider_grant=json_grant,
            run_resource_grant=self.resource_grant,
            now=lambda: datetime(2026, 7, 28, 10, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(json_host.translate_policy(json_request).proposed_policy, ProjectPolicyV2.model_validate(policy_payload))
        self.assertEqual(json_host.call_records[0].role, "policy_translator")


if __name__ == "__main__":
    unittest.main()
