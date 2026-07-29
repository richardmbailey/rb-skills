from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace

from pydantic_ai import ModelResponse, ToolCallPart, models
from pydantic_ai.models.function import FunctionModel

from rb_safe_operation.canonical import artifact_hash, canonical_bytes
from rb_safe_operation.cli import (
    _coordinator_handoff,
    build_parser,
    cmd_assess,
    cmd_assess_preflight,
    cmd_framework_run,
    cmd_persist_artifact,
)
from rb_safe_operation.canonical import parse_json_strict
from rb_safe_operation.compatibility import LegacyArtifactNotExecutable
from rb_safe_operation.models import HashRef
from rb_safe_operation.patches import capture_file_metadata, metadata_fingerprint_hash
from rb_safe_operation.planning import select_markdown_phase
from rb_safe_operation.policy import default_global_policy
from rb_safe_operation.proposal_cycle import ProposalCycleService, ProposalSafetyRejected
from rb_safe_operation.proposal_models import (
    AgentPatchProposal,
    ApprovalV2,
    ApplyPatchActionV2,
    AssessmentV2,
    AssessmentBundleV2,
    BoundedAgentTaskV2,
    LowLevelPlanV2,
    PatchSemanticAssessmentProposal,
    ProviderGrant,
    RepositorySnapshotV2,
    RepairAttemptV2,
    RunResourceGrant,
    HostCapabilitiesV2,
    VerificationProposalV2,
    CoordinatorBundleV2,
    SemanticAssessmentProposalV2,
    PlanAssessmentRequest,
    PlanAssessmentResponse,
    SemanticRoleContext,
    VerificationRoleRequest,
    VerificationRoleResponse,
    RoleCallRecord,
)
from rb_safe_operation.readiness_models import RunPreparationPreview
from rb_safe_operation.acceptance import summarize_acceptance_run
from rb_safe_operation.project_policy import load_project_policy
from rb_safe_operation.state import capture_policy_snapshot, capture_snapshot, release_lease
from rb_safe_operation.role_hosts import PydanticAIProposalRoleHost, RoleHostResourceExhausted
from rb_safe_operation.workflow import (
    ExecutionCoordinator,
    ResourcePause,
    WorkflowError,
    assess_plan,
    assess_plan_with_host,
    begin_verification_context,
    default_host_capabilities_v2,
    deterministic_preflight,
    verify_reports,
)

from helpers import common, effect, safe_plan


def ref(kind: str, version: str, payload) -> HashRef:
    return HashRef(
        artifact_type=kind,
        schema_version=version,
        value=artifact_hash(kind, version, payload),
    )


def complete_verification_response(request) -> VerificationRoleResponse:
    evidence_id = "verification-evidence"
    proposal = VerificationProposalV2(
        schema_version="3.0",
        plan_hash=ref("low-level-plan", "3.0", request.plan.model_dump(mode="json")),
        assessment_hash=ref("assessment", "3.0", request.assessment.model_dump(mode="json")),
        snapshot_hash=ref(
            "repository-snapshot", "3.0", request.post_execution_snapshot.model_dump(mode="json")
        ),
        verifier_context_id=request.verifier_context_id,
        success_criteria_met=request.expected_success_criteria,
        verifier_checks_passed=request.expected_verifier_checks,
        observed_effect_ids=request.expected_effect_ids,
        evidence=[{
            "evidence_id": evidence_id, "provenance": "agent_reported",
            "locator": f"agent-report:{evidence_id}", "summary": "static result checked",
        }],
        criterion_evidence={value: [evidence_id] for value in request.expected_success_criteria},
        check_evidence={value: [evidence_id] for value in request.expected_verifier_checks},
        effect_evidence={value: [evidence_id] for value in request.expected_effect_ids},
        findings=[],
        proposal_hashes=[
            ref("bounded-patch-proposal", "2.0", item.model_dump(mode="json"))
            for item in request.proposals
        ],
        patch_assessment_hashes=[
            ref("patch-assessment", "2.0", item.model_dump(mode="json"))
            for item in request.patch_assessments
        ],
        execution_report_hashes=[
            ref("execution-report", "3.0", item.model_dump(mode="json"))
            for item in request.execution_reports
        ],
        policy_binding=request.plan.policy_binding,
    )
    return VerificationRoleResponse(
        schema_version="1.0", request_token=request.context.request_token,
        verification_proposal=proposal,
    )


def successful_verifier_record(request, response, *, adapter="pydantic_ai") -> RoleCallRecord:
    request_bytes = canonical_bytes(request.model_dump(mode="json"))
    response_bytes = canonical_bytes(response.model_dump(mode="json"))
    return RoleCallRecord(
        schema_version="2.0", call_id=f"call-verifier-{request.context.request_token[-12:]}",
        role="verifier", adapter=adapter,
        assurance_profile=(
            "framework_tool_enforced_no_tools"
            if adapter == "pydantic_ai" else "instruction_only_proposal_host"
        ),
        provider_grant_hash=request.context.provider_grant_hash,
        policy_binding=request.context.policy_binding,
        request_hash=hashlib.sha256(request_bytes).hexdigest(),
        response_hash=hashlib.sha256(response_bytes).hexdigest(),
        outcome="success", usage_complete=True,
        provider=request.provider_grant.provider, endpoint=request.provider_grant.endpoint,
        model=request.provider_grant.model,
        model_revision=request.provider_grant.model_revision, requests=1,
        tool_calls=0, input_tokens=1, output_tokens=1,
        request_bytes=len(request_bytes), response_bytes=len(response_bytes),
        elapsed_milliseconds=1, cost_decimal="0",
        cost_provenance="provider_declared_zero",
    )


class FakeProposalHost:
    def __init__(self, target: Path, *, unsafe: bool = False):
        self.target = target
        self.unsafe = unsafe
        self.requests = []
        self.call_records = []

    def adopt_call_record(self, record):
        if record.call_id not in {item.call_id for item in self.call_records}:
            self.call_records.append(record)

    def propose_patch(self, request):
        self.requests.append(request)
        return AgentPatchProposal(
            schema_version="1.0",
            request_token=request.context.request_token,
            operation_id=request.operation.operation_id,
            attempt_id=request.context.attempt_id,
            intent_summary="replace a with b",
            unified_diff="--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-a\n+b\n",
            claimed_created_paths=[],
            claimed_modified_paths=[str(self.target)],
            claimed_deleted_paths=[],
            claimed_effect_ids=["effect-modify", "effect-read"],
            evidence=[],
            no_other_changes=True,
        )

    def assess_patch(self, request):
        self.requests.append(request)
        return PatchSemanticAssessmentProposal(
            schema_version="2.0",
            request_token=request.context.request_token,
            proposal_hash=request.preflight.proposal_hash,
            semantic_pass=not self.unsafe,
            findings=[] if not self.unsafe else [{
                "finding_id": "finding-unsafe",
                "invariant_id": "E-001",
                "operation_ids": [request.operation.operation_id],
                "effect_ids": ["effect-modify"],
                "category": "detrimental_effect",
                "severity": "high",
                "evidence_ids": [],
                "evidence_provenance": [],
                "finding_provenance": "agent_reported",
                "explanation": "detrimental side effect",
                "remediation_or_human_decision": "revise and reassess",
                "blocking": True,
            }],
            covered_paths=[str(self.target)],
            covered_effect_ids=["effect-modify", "effect-read"],
            no_uncontrolled_detrimental_side_effects=not self.unsafe,
            policy_binding=request.context.policy_binding,
        )


class ProposalCycleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        self.target = self.root / "input.txt"
        self.target.write_text("a\n", encoding="utf-8")
        self.plan_file = self.root / "PLAN.md"
        self.plan_file.write_text("# Plan\n\n## Phase 1: Edit\nEdit input.\n", encoding="utf-8")
        self.policy = default_global_policy(str(self.root))
        self.loaded_policy = load_project_policy(self.root, self.policy)
        self.active_policy = self.loaded_policy.effective_policy
        self.metadata_loader = lambda path: capture_file_metadata(
            path, acl_reader=lambda _: b"", xattr_reader=lambda _: {}
        )
        base_snapshot = capture_policy_snapshot(
            self.loaded_policy, [str(self.target), str(self.plan_file)], [], [str(self.target)],
            [str(self.root / ".rb-safe-operation")],
        )
        snapshot_payload = base_snapshot.model_dump(mode="json") | {
            "selected_file_metadata_hashes": {
                path: metadata_fingerprint_hash(self.metadata_loader(Path(path)))
                for path in base_snapshot.selected_file_hashes
            },
            "proposal_context_observation_hashes": {},
        }
        self.snapshot = RepositorySnapshotV2.model_validate(snapshot_payload)
        self.provider = ProviderGrant(
            schema_version="1.0", grant_id="provider-1",
            issued_at="2026-07-28T09:00:00Z", expires_at="2099-07-28T12:00:00Z",
            roles=["plan_assessor", "proposer", "patch_assessor", "verifier"], adapter="pydantic_ai", provider="test-provider",
            endpoint="in-memory://proposal-cycle", model="proposal-cycle", model_revision="test",
            credential_audience="none:test-only", request_data_classes=["internal_source"],
            response_data_classes=["patch_proposal", "patch_assessment"],
            maximum_data_classification="internal", retention_disclosure="in-memory test only",
            training_use="disallowed", max_calls=4, max_request_bytes=1_000_000,
            max_input_tokens=100_000, max_output_tokens=100_000, max_seconds=30,
            max_cost_decimal="0", temperature_decimal="0", seed=1,
            cost_accounting="declared_zero",
            structured_output_mode="tool", redirect_endpoints=[], approval_hash=None,
        )
        self.resource = RunResourceGrant(
            schema_version="1.0", grant_id="resource-1",
            issued_at="2026-07-28T09:00:00Z", expires_at="2099-07-28T12:00:00Z",
            max_proposer_calls=2, max_assessor_calls=2, max_model_requests=4,
            max_input_tokens=100_000,
            max_read_tool_calls=2, max_read_tool_bytes=100_000, max_patch_bytes=1_000_000,
            max_output_tokens=100_000, max_request_bytes=1_000_000,
            max_response_bytes=1_000_000, max_elapsed_seconds=60, max_cost_decimal="0",
            replenishes_grant_id=None, authorization_hash=ref("human-authorization", "1.0", {}),
        )
        operation_payload = {
            **common(self.root, "edit-1", effect(
                "effect-modify", "repository_modify", targets=[str(self.root)]
            )),
            "kind": "bounded_agent_task", "proposal_protocol": "unified_diff_v1",
            "goal": "replace a with b", "non_goals": ["do not edit other files"],
            "evidence_ids": ["evidence-source"], "allowed_read_tools": [],
            "source_data_classification": "internal",
            "allowed_patch_actions": ["modify"], "created_file_mode": 0o600,
            "forbidden_actions": ["direct write", "shell", "network"],
            "permitted_adaptations": ["revise_local_code"],
            "diagnostic_checkpoint_rules": ["record changed strategy"],
            "completion_evidence": ["completion-edit-1"], "escalation_conditions": ["scope change"],
            "required_adapter": "pydantic_ai",
            "required_assurance_profile": "framework_tool_enforced_proposer",
            "provider_grant_id": self.provider.grant_id,
            "run_resource_grant_id": self.resource.grant_id,
        }
        operation_payload["effects"].append(effect(
            "effect-read", "repository_read", targets=[str(self.root)]
        ))
        operation_payload["path_contract"]["modify_roots"] = [str(self.root)]
        operation = BoundedAgentTaskV2.model_validate(operation_payload)
        plan_payload = {
            "schema_version": "3.0", "plan_id": "plan-2", "run_id": "run-2",
            "source_phase": select_markdown_phase(str(self.plan_file), "phase-1").source.model_dump(mode="json"),
            "snapshot": self.snapshot.model_dump(mode="json"),
            "global_policy_hash": ref("active-policy", "1.0", self.policy.model_dump(mode="json")).model_dump(mode="json"),
            "merged_policy_hash": ref("active-policy", "2.0", self.active_policy.model_dump(mode="json")).model_dump(mode="json"),
            "operations": [operation.model_dump(mode="json")],
            "evidence": [{"evidence_id": "evidence-source", "provenance": "coordinator_observed", "locator": str(self.target), "summary": "input"}],
            "later_phase_ids": [],
            "current_artifact_locations": [str(self.root / ".rb-safe-operation/artifacts/run-2/low-level-plan.json")],
            "exact_next_action": "assess", "semantic_guidance": [],
            "provider_grant_hash": ref("provider-grant", "1.0", self.provider.model_dump(mode="json")).model_dump(mode="json"),
            "run_resource_grant_hash": ref("run-resource-grant", "1.0", self.resource.model_dump(mode="json")).model_dump(mode="json"),
            "policy_binding": self.loaded_policy.binding.model_dump(mode="json"),
        }
        self.plan = LowLevelPlanV2.model_validate(plan_payload)
        self.semantic = SemanticAssessmentProposalV2(
            schema_version="3.0", semantic_pass=True, findings=[],
            covered_evidence_ids=["evidence-source"], enforcement_disclosures=[],
            provider_grant_hash=ref("provider-grant", "1.0", self.provider.model_dump(mode="json")),
            required_role_assurance_profiles=["framework_tool_enforced_proposer"],
            policy_binding=self.loaded_policy.binding,
        )
        self.capabilities = HostCapabilitiesV2(
            schema_version="3.0", profile="semi_formal", role_read_only="host_enforced",
            role_tool_allocation="framework_enforced", product_state_observation="coordinator_observed",
            complete_child_trace=False, atomic_path_enforcement=False, atomic_lease_create=True,
            bounded_resource_enforcement="framework_enforced", fresh_context_enforcement="host_enforced",
            provider_identity_observation="coordinator_observed",
            policy_aware_role_allocation=True,
        )
        self.assessment = assess_plan(
            self.plan, self.policy, self.active_policy, self.snapshot, self.capabilities,
            self.semantic, [], now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )

    def tearDown(self):
        self.temporary.cleanup()

    def service(self, host):
        return ProposalCycleService(
            plan=self.plan, assessment=self.assessment, active_policy=self.active_policy,
            provider_grant=self.provider, resource_grant=self.resource, role_host=host,
            metadata_loader=self.metadata_loader,
            loaded_project_policy=self.loaded_policy,
            clock=lambda: datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
        )

    def test_cli_has_no_manual_plan_assessor_or_verifier_response_inputs(self):
        parser = build_parser()
        subparsers = next(
            action for action in parser._actions if hasattr(action, "choices") and action.choices
        )
        assess_options = {
            option
            for action in subparsers.choices["assess"]._actions
            for option in action.option_strings
        }
        coordinate_options = {
            option
            for action in subparsers.choices["coordinate"]._actions
            for option in action.option_strings
        }
        self.assertNotIn("--semantic-proposal", assess_options)
        self.assertNotIn("--preflight", assess_options)
        self.assertNotIn("--verification-response", coordinate_options)

    def test_framework_run_owns_plan_assessment_proposal_commit_and_verification(self):
        outer = self

        class CompleteHost:
            def __init__(inner_self):
                inner_self.call_records = []

            def record(inner_self, role, request, response):
                request_bytes = canonical_bytes(request.model_dump(mode="json"))
                response_bytes = canonical_bytes(response.model_dump(mode="json"))
                inner_self.call_records.append(RoleCallRecord(
                    schema_version="2.0", call_id=f"call-framework-{len(inner_self.call_records) + 1}",
                    role=role, adapter="pydantic_ai",
                    assurance_profile=(
                        "framework_tool_enforced_proposer"
                        if role == "proposer" else "framework_tool_enforced_no_tools"
                    ),
                    provider_grant_hash=request.context.provider_grant_hash,
                    policy_binding=request.context.policy_binding,
                    request_hash=hashlib.sha256(request_bytes).hexdigest(),
                    response_hash=hashlib.sha256(response_bytes).hexdigest(),
                    outcome="success", usage_complete=True,
                    provider=outer.provider.provider, endpoint=outer.provider.endpoint,
                    model=outer.provider.model, model_revision=outer.provider.model_revision,
                    requests=1, tool_calls=0, input_tokens=1, output_tokens=1,
                    request_bytes=len(request_bytes), response_bytes=len(response_bytes),
                    elapsed_milliseconds=1, cost_decimal="0",
                    cost_provenance="provider_declared_zero",
                ))
                return response

            def adopt_call_record(inner_self, record):
                if record.call_id not in {item.call_id for item in inner_self.call_records}:
                    inner_self.call_records.append(record)

            def assess_plan(inner_self, request):
                return inner_self.record("plan_assessor", request, PlanAssessmentResponse(
                    schema_version="1.0", request_token=request.context.request_token,
                    plan_hash=request.preflight.plan_hash,
                    preflight_hash=ref(
                        "deterministic-preflight", "3.0", request.preflight.model_dump(mode="json")
                    ),
                    policy_hash=request.preflight.policy_hash,
                    snapshot_hash=request.preflight.snapshot_hash,
                    semantic_proposal=outer.semantic,
                    policy_binding=request.context.policy_binding,
                ))

            def propose_patch(inner_self, request, read_file=None):
                response = AgentPatchProposal(
                    schema_version="1.0", request_token=request.context.request_token,
                    operation_id=request.operation.operation_id,
                    attempt_id=request.context.attempt_id,
                    intent_summary="replace a with b",
                    unified_diff="--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-a\n+b\n",
                    claimed_created_paths=[], claimed_modified_paths=[str(outer.target)],
                    claimed_deleted_paths=[], claimed_effect_ids=["effect-modify", "effect-read"],
                    evidence=[], no_other_changes=True,
                )
                return inner_self.record("proposer", request, response)

            def drain_read_results(inner_self, request_token):
                return []

            def assess_patch(inner_self, request):
                response = PatchSemanticAssessmentProposal(
                    schema_version="2.0", request_token=request.context.request_token,
                    proposal_hash=request.preflight.proposal_hash, semantic_pass=True,
                    findings=[], covered_paths=[str(outer.target)],
                    covered_effect_ids=["effect-modify", "effect-read"],
                    no_uncontrolled_detrimental_side_effects=True,
                    policy_binding=request.context.policy_binding,
                )
                return inner_self.record("patch_assessor", request, response)

            def verify(inner_self, request):
                return inner_self.record(
                    "verifier", request, complete_verification_response(request)
                )

        framework_snapshot = capture_policy_snapshot(
            self.loaded_policy,
            list(self.plan.snapshot.selected_file_hashes),
            list(self.plan.snapshot.instruction_hashes),
            self.plan.snapshot.expected_product_changes,
            self.plan.snapshot.control_plane_roots,
        )
        framework_plan = self.plan.model_copy(update={"snapshot": framework_snapshot})
        fixed_plan = Path(framework_plan.current_artifact_locations[0])
        fixed_plan.parent.mkdir(parents=True)
        fixed_plan.write_bytes(canonical_bytes(framework_plan.model_dump(mode="json")) + b"\n")
        preview = RunPreparationPreview(
            schema_version="1.0", preparation_id="prep-framework", run_id=self.plan.run_id,
            project_root=str(self.root), project_root_device=self.root.stat().st_dev,
            project_root_inode=self.root.stat().st_ino,
            request_hash=ref("run-preparation-request", "1.0", {}),
            credential_handle="TEST_KEY", credential_status="available",
            host_capabilities=self.capabilities, provider_grant=self.provider,
            run_resource_grant=self.resource,
            assurance_statements=["test"],
            confirmation_binding_hash=ref("run-preparation-preview-body", "1.0", {}),
            exact_confirmation_statement="CONFIRM RUN AUTHORITY " + "0" * 64,
        )
        host = CompleteHost()
        args = SimpleNamespace(
            enable_live_provider=True, plan=str(fixed_plan),
            run_preparation_preview=str(self.root / "unused-preview.json"),
            approvals=None, prior_assessment_bundle=None, proposal_approvals=None,
            verifier_context_id="framework-verifier-context",
        )
        with patch(
            "rb_safe_operation.cli.load_confirmed_run_preparation", return_value=preview
        ), patch(
            "rb_safe_operation.openai_adapter.build_openai_role_host", return_value=host
        ), patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_framework_run(args)

        self.assertEqual(self.target.read_text(encoding="utf-8"), "b\n")
        bundle = CoordinatorBundleV2.model_validate(parse_json_strict(
            (self.root / ".rb-safe-operation" / "runs" / self.plan.run_id / "coordinator-bundle.json").read_bytes()
        ))
        self.assertEqual(bundle.manifest.state, "verified")
        self.assertEqual(
            [record.role for record in bundle.role_call_records],
            ["plan_assessor", "proposer", "patch_assessor", "verifier"],
        )
        summary = summarize_acceptance_run(str(self.root), self.plan.run_id)
        self.assertEqual(summary.lifecycle_state, "verified")
        self.assertEqual(summary.roles, ["plan_assessor", "proposer", "patch_assessor", "verifier"])
        self.assertEqual(summary.model_requests, 4)
        self.assertEqual(summary.tool_calls, 0)
        self.assertTrue(summary.usage_complete)
        self.assertFalse(hasattr(summary, "project_root"))
        self.assertEqual(
            summary.project_root_sha256,
            hashlib.sha256(str(self.root).encode("utf-8")).hexdigest(),
        )
        self.assertNotIn("replace a with b", canonical_bytes(summary.model_dump()).decode("utf-8"))

    def plan_assessment_request(self):
        preflight = deterministic_preflight(
            self.plan, self.policy, self.active_policy, self.snapshot, self.capabilities, [],
            now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )
        input_hashes = [
            ref("low-level-plan", "3.0", self.plan.model_dump(mode="json")),
            ref("deterministic-preflight", "3.0", preflight.model_dump(mode="json")),
            ref("active-policy", "2.0", self.active_policy.model_dump(mode="json")),
            ref("host-capabilities", "3.0", self.capabilities.model_dump(mode="json")),
            ref("provider-grant", "1.0", self.provider.model_dump(mode="json")),
            ref("run-resource-grant", "1.0", self.resource.model_dump(mode="json")),
        ]
        context = SemanticRoleContext(
            schema_version="1.0", context_id="plan-assessment-context",
            request_token="plan-assessment-request", role="plan_assessor",
            adapter="pydantic_ai", assurance_profile="framework_tool_enforced_no_tools",
            provider_grant_hash=input_hashes[-2], run_resource_grant_hash=input_hashes[-1],
            policy_binding=self.loaded_policy.binding,
            input_artifact_hashes=input_hashes, prompt_packet_hash="0" * 64,
            created_at="2026-07-28T10:00:00Z",
        )
        return PlanAssessmentRequest(
            schema_version="1.0", context=context, plan=self.plan, preflight=preflight,
            active_policy=self.active_policy, capabilities=self.capabilities,
            provider_grant=self.provider, run_resource_grant=self.resource,
            approvals=[], prior_assessment_hash=None,
        )

    def test_public_execution_boundary_rejects_schema_one_plans(self):
        legacy = safe_plan(self.root)
        with self.assertRaisesRegex(LegacyArtifactNotExecutable, "recompile and reassess"):
            ExecutionCoordinator(legacy)
        with self.assertRaisesRegex(LegacyArtifactNotExecutable, "plan assessment"):
            assess_plan(legacy, None, None, None, None, None, [])
        with self.assertRaisesRegex(LegacyArtifactNotExecutable, "deterministic preflight"):
            deterministic_preflight(legacy, None, None, None, None, [])
        with self.assertRaisesRegex(LegacyArtifactNotExecutable, "audit-only"):
            begin_verification_context(None, None, "legacy", None)
        with self.assertRaisesRegex(LegacyArtifactNotExecutable, "audit-only"):
            verify_reports(None, None, [], None, None)

    def test_plan_assessor_request_and_response_are_strictly_cross_bound(self):
        request = self.plan_assessment_request()
        preflight = request.preflight
        response = PlanAssessmentResponse(
            schema_version="1.0",
            request_token=request.context.request_token,
            plan_hash=preflight.plan_hash,
            preflight_hash=ref("deterministic-preflight", "3.0", preflight.model_dump(mode="json")),
            policy_hash=preflight.policy_hash,
            snapshot_hash=preflight.snapshot_hash,
            semantic_proposal=self.semantic,
            policy_binding=self.loaded_policy.binding,
        )
        self.assertEqual(response.request_token, request.context.request_token)
        bad = request.model_dump(mode="json")
        bad["preflight"]["plan_hash"]["value"] = "f" * 64
        with self.assertRaises(ValueError):
            PlanAssessmentRequest.model_validate(bad)

    def test_pydantic_ai_plan_assessor_is_a_no_tool_typed_role(self):
        request = self.plan_assessment_request()
        seen_tools = []

        def response(messages, info):
            seen_tools.append([item.name for item in info.function_tools])
            output = info.output_tools[0]
            payload = PlanAssessmentResponse(
                schema_version="1.0", request_token=request.context.request_token,
                plan_hash=request.preflight.plan_hash,
                preflight_hash=ref(
                    "deterministic-preflight", "3.0", request.preflight.model_dump(mode="json")
                ),
                policy_hash=request.preflight.policy_hash,
                snapshot_hash=request.preflight.snapshot_hash,
                semantic_proposal=self.semantic,
                policy_binding=self.loaded_policy.binding,
            ).model_dump(mode="json")
            return ModelResponse(parts=[ToolCallPart(tool_name=output.name, args=payload)])

        models.ALLOW_MODEL_REQUESTS = False
        host = PydanticAIProposalRoleHost(
            model=FunctionModel(response, model_name="proposal-cycle"),
            provider_grant=self.provider, run_resource_grant=self.resource,
            observed_provider="test-provider", observed_endpoint="in-memory://proposal-cycle",
            observed_credential_audience="none:test-only", observed_model_revision="test",
            now=lambda: "2026-07-28T10:00:00Z",
        )
        result = host.assess_plan(request)
        self.assertEqual(result.request_token, request.context.request_token)
        self.assertEqual(seen_tools, [[]])
        self.assertEqual(host.call_records[0].role, "plan_assessor")
        self.assertEqual(host.call_records[0].assurance_profile, "framework_tool_enforced_no_tools")

    def test_owned_plan_assessment_builds_request_and_accounts_one_call(self):
        outer = self

        class PlanHost:
            def __init__(inner_self):
                inner_self.call_records = []
                inner_self.requests = []

            def assess_plan(inner_self, request):
                inner_self.requests.append(request)
                request_bytes = canonical_bytes(request.model_dump(mode="json"))
                response = PlanAssessmentResponse(
                    schema_version="1.0", request_token=request.context.request_token,
                    plan_hash=request.preflight.plan_hash,
                    preflight_hash=ref(
                        "deterministic-preflight", "3.0", request.preflight.model_dump(mode="json")
                    ),
                    policy_hash=request.preflight.policy_hash,
                    snapshot_hash=request.preflight.snapshot_hash,
                    semantic_proposal=outer.semantic,
                    policy_binding=outer.loaded_policy.binding,
                )
                response_bytes = canonical_bytes(response.model_dump(mode="json"))
                inner_self.call_records.append(RoleCallRecord(
                    schema_version="2.0", call_id="call-plan-assessor",
                    role="plan_assessor", adapter="pydantic_ai",
                    assurance_profile="framework_tool_enforced_no_tools",
                    provider_grant_hash=request.context.provider_grant_hash,
                    policy_binding=request.context.policy_binding,
                    request_hash=hashlib.sha256(request_bytes).hexdigest(),
                    response_hash=hashlib.sha256(response_bytes).hexdigest(),
                    outcome="success", usage_complete=True,
                    provider="test-provider", endpoint="in-memory://proposal-cycle",
                    model="proposal-cycle", model_revision="test",
                    requests=1, tool_calls=0, input_tokens=1, output_tokens=1,
                    request_bytes=len(request_bytes), response_bytes=len(response_bytes),
                    elapsed_milliseconds=1, cost_decimal="0",
                    cost_provenance="provider_declared_zero",
                ))
                return response

        host = PlanHost()
        guard_stages = []
        outcome = assess_plan_with_host(
            self.plan, self.policy, self.active_policy, self.snapshot, self.capabilities, [],
            provider_grant=self.provider, run_resource_grant=self.resource,
            role_host=host, now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            state_guard=guard_stages.append,
        )
        self.assertTrue(outcome.assessment.safe)
        self.assertEqual(guard_stages, ["before_plan_assessor", "after_plan_assessor"])
        self.assertEqual(outcome.role_call_record.role, "plan_assessor")
        self.assertEqual(len(host.requests), 1)

        class MutatingPlanHost(PlanHost):
            def assess_plan(inner_self, request):
                result = super().assess_plan(request)
                outer.target.write_text("unauthorised assessor mutation\n", encoding="utf-8")
                return result

        baseline = hashlib.sha256(self.target.read_bytes()).hexdigest()

        def mutation_guard(stage):
            if stage == "after_plan_assessor":
                observed = hashlib.sha256(self.target.read_bytes()).hexdigest()
                if observed != baseline:
                    raise WorkflowError("plan assessor changed product state")

        with self.assertRaisesRegex(WorkflowError, "changed product state"):
            assess_plan_with_host(
                self.plan, self.policy, self.active_policy, self.snapshot,
                self.capabilities, [], provider_grant=self.provider,
                run_resource_grant=self.resource, role_host=MutatingPlanHost(),
                state_guard=mutation_guard,
                now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            )

    def test_pydantic_ai_verifier_is_a_separate_no_tool_typed_role(self):
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=FakeProposalHost(self.target),
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        coordinator.execute()
        context = coordinator.open_verification("pydantic-verifier-context")
        verifier_request = coordinator.build_verification_request(context)
        seen_tools = []

        def response(messages, info):
            seen_tools.append([item.name for item in info.function_tools])
            output = info.output_tools[0]
            payload = complete_verification_response(verifier_request).model_dump(mode="json")
            return ModelResponse(parts=[ToolCallPart(tool_name=output.name, args=payload)])

        models.ALLOW_MODEL_REQUESTS = False
        host = PydanticAIProposalRoleHost(
            model=FunctionModel(response, model_name="proposal-cycle"),
            provider_grant=self.provider, run_resource_grant=self.resource,
            observed_provider="test-provider", observed_endpoint="in-memory://proposal-cycle",
            observed_credential_audience="none:test-only", observed_model_revision="test",
            now=lambda: "2026-07-28T10:00:00Z",
        )
        coordinator.agent_host = host
        report = coordinator.verify_with_host(context)
        self.assertTrue(report.verified)
        self.assertEqual(seen_tools, [[]])
        self.assertEqual(host.call_records[0].role, "verifier")
        self.assertEqual(
            host.call_records[0].assurance_profile,
            "framework_tool_enforced_no_tools",
        )

    def test_approved_cycle_materialises_and_assesses_without_mutating(self):
        artifacts = self.service(FakeProposalHost(self.target)).run("edit-1")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "a\n")
        self.assertEqual(artifacts.prepared_patch.targets[0].postimage, b"b\n")
        self.assertTrue(artifacts.patch_assessment.safe)
        self.assertEqual(artifacts.bounded_proposal.modified_paths, [str(self.target)])

    def test_bad_effect_claim_returns_a_typed_blocking_finding(self):
        class BadEffectHost(FakeProposalHost):
            def propose_patch(inner_self, request):
                response = super().propose_patch(request)
                return response.model_copy(update={"claimed_effect_ids": ["effect-modify"]})

        with self.assertRaises(ProposalSafetyRejected) as caught:
            self.service(BadEffectHost(self.target)).run("edit-1")
        self.assertEqual(len(caught.exception.findings), 1)
        self.assertEqual(caught.exception.findings[0].category, "effect_inventory")
        self.assertTrue(caught.exception.findings[0].blocking)
        self.assertEqual(self.target.read_text(encoding="utf-8"), "a\n")

    def test_proposal_service_rejects_an_unproved_replacement_resource_grant(self):
        replacement = self.resource.model_copy(update={
            "grant_id": "resource-unproved",
            "issued_at": "2026-07-28T11:00:00Z",
            "replenishes_grant_id": "unrelated-grant",
        })
        with self.assertRaisesRegex(Exception, "replenishment chain"):
            ProposalCycleService(
                plan=self.plan,
                assessment=self.assessment,
                active_policy=self.active_policy,
                provider_grant=self.provider,
                resource_grant=replacement,
                root_resource_grant_hash=self.plan.run_resource_grant_hash,
                authorized_resource_grants=[self.resource, replacement],
                role_host=FakeProposalHost(self.target),
                metadata_loader=self.metadata_loader,
                loaded_project_policy=self.loaded_policy,
                clock=lambda: datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc),
            )

    def test_schema_two_plan_preflight_and_assessment_bind_provider_authority(self):
        capabilities = HostCapabilitiesV2(
            schema_version="3.0", profile="semi_formal", role_read_only="host_enforced",
            role_tool_allocation="framework_enforced", product_state_observation="coordinator_observed",
            complete_child_trace=False, atomic_path_enforcement=False, atomic_lease_create=True,
            bounded_resource_enforcement="framework_enforced", fresh_context_enforcement="host_enforced",
            provider_identity_observation="coordinator_observed",
            policy_aware_role_allocation=True,
        )
        preflight = deterministic_preflight(
            self.plan, self.policy, self.active_policy, self.snapshot, capabilities, [],
            now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )
        self.assertTrue(preflight.deterministic_pass, [item.explanation for item in preflight.findings])
        semantic = SemanticAssessmentProposalV2(
            schema_version="3.0", semantic_pass=True, findings=[],
            covered_evidence_ids=["evidence-source"], enforcement_disclosures=[],
            provider_grant_hash=ref("provider-grant", "1.0", self.provider.model_dump(mode="json")),
            required_role_assurance_profiles=["framework_tool_enforced_proposer"],
            policy_binding=self.loaded_policy.binding,
        )
        assessment = assess_plan(
            self.plan, self.policy, self.active_policy, self.snapshot, capabilities, semantic, [],
            now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )
        self.assertTrue(assessment.safe, [item.explanation for item in assessment.findings])

    def test_schema_two_approval_must_match_the_declared_effect_class(self):
        operation = self.plan.operations[0]
        approved_effect = operation.effects[0].model_copy(update={
            "approval_class": "privacy_sensitive",
            "residual_severity": "medium",
        })
        operation = operation.model_copy(update={
            "approval_classes": ["privacy_sensitive"],
            "effects": [approved_effect, operation.effects[1]],
        })
        plan = self.plan.model_copy(update={"operations": [operation]})
        approval = ApprovalV2(
            schema_version="3.0",
            approval_id="approval-wrong-effect-class",
            plan_hash=ref("low-level-plan", "3.0", plan.model_dump(mode="json")),
            operation_hash=ref("operation", "2.0", operation.model_dump(mode="json")),
            policy_hash=ref("active-policy", "2.0", self.active_policy.model_dump(mode="json")),
            snapshot_hash=ref("repository-snapshot", "3.0", plan.snapshot.model_dump(mode="json")),
            proposal_hash=None, patch_assessment_hash=None,
            policy_binding=self.loaded_policy.binding,
            effect_id=approved_effect.effect_id,
            effect_class="repository_delete",
            approval_class="privacy_sensitive",
            target=str(self.root),
            expires_at="2099-07-28T12:00:00Z",
            one_use=True,
            consumed=False,
            idempotency_key="approval-key-wrong-effect-class",
            principal=None,
            identity_verification="unavailable",
        )
        result = assess_plan(
            plan, self.policy, self.active_policy, self.snapshot, self.capabilities,
            self.semantic, [approval], now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )
        self.assertFalse(result.safe)
        self.assertIn("approval-effect-modify", {item.finding_id for item in result.findings})

    def test_unsafe_semantic_assessment_rejects_without_mutating(self):
        with self.assertRaisesRegex(ProposalSafetyRejected, "semantic"):
            self.service(FakeProposalHost(self.target, unsafe=True)).run("edit-1")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "a\n")

    def test_coordinator_persists_typed_human_intervention_for_unsafe_patch(self):
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=FakeProposalHost(self.target, unsafe=True),
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        with self.assertRaisesRegex(Exception, "semantic"):
            coordinator.execute()
        bundle = CoordinatorBundleV2.model_validate(parse_json_strict(coordinator.bundle_path.read_bytes()))
        self.assertEqual(bundle.manifest.state, "human_required")
        self.assertEqual(bundle.human_interventions[0].decision_type, "revise_and_reassess")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "a\n")

    def test_direct_host_mutation_is_detectable_by_coordinator_guard(self):
        host = FakeProposalHost(self.target)
        before = hashlib.sha256(self.target.read_bytes()).hexdigest()
        calls = 0

        def guard(stage):
            nonlocal calls
            calls += 1
            if stage == "after_proposer" and hashlib.sha256(self.target.read_bytes()).hexdigest() != before:
                raise ProposalSafetyRejected("proposal host changed product state")

        original = host.propose_patch
        def mutate(request):
            result = original(request)
            self.target.write_text("host mutation\n", encoding="utf-8")
            return result
        host.propose_patch = mutate
        with self.assertRaisesRegex(ProposalSafetyRejected, "changed product state"):
            self.service(host).run("edit-1", state_guard=guard)
        self.assertEqual(calls, 2)

    def test_runtime_mediated_reads_are_typed_and_bound_into_the_final_context(self):
        operation = self.plan.operations[0].model_copy(update={"allowed_read_tools": ["read_file"]})
        plan = self.plan.model_copy(update={"operations": [operation]})
        assessment = assess_plan(
            plan, self.policy, self.active_policy, self.snapshot, self.capabilities,
            self.semantic, [], now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )

        class ReadingHost(FakeProposalHost):
            def __init__(inner_self, target):
                super().__init__(target)
                inner_self.reads = []

            def propose_patch(inner_self, request, read_file=None):
                inner_self.reads.append(read_file(str(self.target), 0, 2))
                return super().propose_patch(request)

            def drain_read_results(inner_self, request_token):
                reads, inner_self.reads = inner_self.reads, []
                return reads

        host = ReadingHost(self.target)
        artifacts = ProposalCycleService(
            plan=plan, assessment=assessment, active_policy=self.active_policy,
            provider_grant=self.provider, resource_grant=self.resource,
            role_host=host, metadata_loader=self.metadata_loader,
            loaded_project_policy=self.loaded_policy,
            clock=lambda: datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
        ).run("edit-1")
        self.assertEqual(len(artifacts.proposal_context.source_observations), 3)
        self.assertEqual(len(artifacts.source_inputs), 3)
        self.assertTrue(any(item.artifact_type == "read-tool-result" for item in artifacts.proposal_context.input_artifact_hashes))

    def test_runtime_mediated_read_drift_is_rejected_before_patch_preparation(self):
        operation = self.plan.operations[0].model_copy(update={"allowed_read_tools": ["read_file"]})
        plan = self.plan.model_copy(update={"operations": [operation]})
        assessment = assess_plan(
            plan, self.policy, self.active_policy, self.snapshot, self.capabilities,
            self.semantic, [], now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )

        class DriftingReadHost(FakeProposalHost):
            def __init__(inner_self, target):
                super().__init__(target)
                inner_self.reads = []

            def propose_patch(inner_self, request, read_file=None):
                inner_self.reads.append(read_file(str(self.target), 0, 2))
                self.target.write_text("drifted\n", encoding="utf-8")
                return super().propose_patch(request)

            def drain_read_results(inner_self, request_token):
                reads, inner_self.reads = inner_self.reads, []
                return reads

        with self.assertRaisesRegex(ProposalSafetyRejected, "runtime-mediated source changed"):
            ProposalCycleService(
                plan=plan, assessment=assessment, active_policy=self.active_policy,
                provider_grant=self.provider, resource_grant=self.resource,
                role_host=DriftingReadHost(self.target), metadata_loader=self.metadata_loader,
                loaded_project_policy=self.loaded_policy,
                clock=lambda: datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            ).run("edit-1")

    def test_runtime_mediated_patch_target_requires_a_complete_file_read(self):
        discovered = self.root / "discovered.txt"
        discovered.write_text("old\n", encoding="utf-8")
        base_snapshot = capture_policy_snapshot(
            self.loaded_policy, [str(self.target), str(self.plan_file)], [], [str(discovered)],
            [str(self.root / ".rb-safe-operation")], metadata_loader=self.metadata_loader,
        )
        snapshot = RepositorySnapshotV2.model_validate(base_snapshot.model_dump(mode="json") | {
            "selected_file_metadata_hashes": {
                path: metadata_fingerprint_hash(self.metadata_loader(Path(path)))
                for path in base_snapshot.selected_file_hashes
            },
            "proposal_context_observation_hashes": {},
        })
        operation = self.plan.operations[0].model_copy(update={"allowed_read_tools": ["read_file"]})
        plan = self.plan.model_copy(update={"snapshot": snapshot, "operations": [operation]})
        assessment = assess_plan(
            plan, self.policy, self.active_policy, snapshot, self.capabilities,
            self.semantic, [], now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )

        class DiscoveredTargetHost:
            def __init__(inner_self, complete):
                inner_self.complete = complete
                inner_self.reads = []

            def propose_patch(inner_self, request, read_file=None):
                end = None if inner_self.complete else 2
                inner_self.reads.append(read_file(str(discovered), 0, end))
                return AgentPatchProposal(
                    schema_version="1.0", request_token=request.context.request_token,
                    operation_id=request.operation.operation_id,
                    attempt_id=request.context.attempt_id,
                    intent_summary="replace old with new",
                    unified_diff="--- a/discovered.txt\n+++ b/discovered.txt\n@@ -1 +1 @@\n-old\n+new\n",
                    claimed_created_paths=[], claimed_modified_paths=[str(discovered)],
                    claimed_deleted_paths=[], claimed_effect_ids=["effect-modify", "effect-read"],
                    evidence=[], no_other_changes=True,
                )

            def drain_read_results(inner_self, request_token):
                reads, inner_self.reads = inner_self.reads, []
                return reads

            def assess_patch(inner_self, request):
                return PatchSemanticAssessmentProposal(
                    schema_version="2.0", request_token=request.context.request_token,
                    proposal_hash=request.preflight.proposal_hash, semantic_pass=True,
                    findings=[], covered_paths=[str(discovered)],
                    covered_effect_ids=["effect-modify", "effect-read"],
                    no_uncontrolled_detrimental_side_effects=True,
                    policy_binding=request.context.policy_binding,
                )

        def service(host):
            return ProposalCycleService(
                plan=plan, assessment=assessment, active_policy=self.active_policy,
                provider_grant=self.provider, resource_grant=self.resource,
                role_host=host, metadata_loader=self.metadata_loader,
                loaded_project_policy=self.loaded_policy,
                clock=lambda: datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            )

        with self.assertRaisesRegex(ProposalSafetyRejected, "complete exact"):
            service(DiscoveredTargetHost(False)).run("edit-1")
        artifacts = service(DiscoveredTargetHost(True)).run("edit-1")
        self.assertEqual(artifacts.prepared_patch.targets[0].preimage, b"old\n")
        self.assertEqual(artifacts.prepared_patch.targets[0].postimage, b"new\n")
        self.assertEqual(discovered.read_text(encoding="utf-8"), "old\n")

    def test_resumed_assessment_rejects_a_changed_prompt_packet_binding(self):
        service = self.service(FakeProposalHost(self.target))
        artifacts = service.run("edit-1")
        changed_context = artifacts.assessment_context.model_copy(update={
            "prompt_packet_hash": "0" * 64,
        })
        with self.assertRaisesRegex(Exception, "exact assessment packet"):
            service.assess_existing(
                "edit-1", context=changed_context, proposal=artifacts.bounded_proposal,
                preflight=artifacts.preflight, exact_changes=artifacts.exact_changes,
                source_inputs=artifacts.source_inputs,
            )

    def test_execution_coordinator_owns_commit_and_authoritative_report(self):
        capabilities = HostCapabilitiesV2(
            schema_version="3.0", profile="semi_formal", role_read_only="host_enforced",
            role_tool_allocation="framework_enforced", product_state_observation="coordinator_observed",
            complete_child_trace=False, atomic_path_enforcement=False, atomic_lease_create=True,
            bounded_resource_enforcement="framework_enforced", fresh_context_enforcement="host_enforced",
            provider_identity_observation="coordinator_observed",
            policy_aware_role_allocation=True,
        )
        class VerifyingHost(FakeProposalHost):
            def verify(inner_self, request):
                response = complete_verification_response(request)
                inner_self.call_records.append(successful_verifier_record(request, response))
                return response

        host = VerifyingHost(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, capabilities,
            semantic_proposal=self.semantic, agent_host=host, provider_grant=self.provider,
            run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
        )
        reports = coordinator.execute()
        self.assertEqual(self.target.read_text(encoding="utf-8"), "b\n")
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0].execution_kind, "bounded_proposal")
        self.assertEqual(reports[0].provenance, "coordinator_observed")
        self.assertEqual(coordinator.manifest.state, "verifying")
        self.assertTrue(coordinator.bundle_path.is_file())
        context = coordinator.open_verification("verification-context-1")
        verifier_request = coordinator.build_verification_request(context)
        self.assertIsInstance(verifier_request, VerificationRoleRequest)
        self.assertEqual(verifier_request.context.role, "verifier")
        observed = {item.path: item for item in verifier_request.file_states}
        self.assertEqual(observed[str(self.target)].content, "b\n")
        self.assertEqual(
            verifier_request.context.assurance_profile,
            "framework_tool_enforced_no_tools",
        )
        verified = coordinator.verify_with_host(context)
        self.assertTrue(verified.verified)
        self.assertEqual(coordinator.manifest.state, "verified")
        semantic_call = coordinator.run_root / "semantic-calls" / context.token
        self.assertTrue((semantic_call / "request.json").is_file())
        self.assertTrue((semantic_call / "response.json").is_file())

    def test_recovery_never_repeats_a_verifier_call_with_no_durable_response(self):
        class InterruptingVerifierHost(FakeProposalHost):
            def __init__(inner_self, target):
                super().__init__(target)
                inner_self.verifier_calls = 0

            def verify(inner_self, request):
                inner_self.verifier_calls += 1
                raise KeyboardInterrupt("simulated verifier transport interruption")

        host = InterruptingVerifierHost(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=host,
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        coordinator.execute()
        context = coordinator.open_verification("verification-interrupted")
        with self.assertRaises(KeyboardInterrupt):
            coordinator.verify_with_host(context)
        self.assertEqual(host.verifier_calls, 1)
        self.assertEqual(coordinator.active_semantic_request_token, context.token)
        call_root = coordinator.run_root / "semantic-calls" / context.token
        self.assertTrue((call_root / "request.json").is_file())
        self.assertFalse((call_root / "response.json").exists())
        release_lease(coordinator.lease)
        coordinator.lease = None

        with self.assertRaisesRegex(WorkflowError, "incomplete verifier call"):
            ExecutionCoordinator.reload(
                str(self.root), self.plan.run_id, self.capabilities,
                agent_host=host, provider_grant=self.provider,
                run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
            )
        self.assertEqual(host.verifier_calls, 1)
        bundle = CoordinatorBundleV2.model_validate(
            parse_json_strict(coordinator.bundle_path.read_bytes())
        )
        self.assertEqual(bundle.manifest.state, "human_required")

    def test_stale_verifier_response_is_rejected_before_persistence_or_success_transition(self):
        class StaleVerifierHost(FakeProposalHost):
            def verify(inner_self, request):
                response = complete_verification_response(request).model_copy(
                    update={"request_token": "stale-verifier-token"}
                )
                inner_self.call_records.append(successful_verifier_record(request, response))
                return response

        host = StaleVerifierHost(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=host,
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        coordinator.execute()
        context = coordinator.open_verification("verification-stale-response")
        with self.assertRaisesRegex(WorkflowError, "request token"):
            coordinator.verify_with_host(context)
        call_root = coordinator.run_root / "semantic-calls" / context.token
        self.assertTrue((call_root / "request.json").is_file())
        self.assertFalse((call_root / "response.json").exists())
        self.assertEqual(coordinator.manifest.state, "human_required")
        self.assertIsNone(coordinator.lease)
        handoff = _coordinator_handoff(coordinator, self.capabilities)
        self.assertTrue(handoff["terminal"])
        self.assertIn("cannot be resumed", handoff["status_summary"])

    def test_verifier_resource_exhaustion_before_dispatch_pauses_without_replay_marker(self):
        class ExhaustedVerifierHost(FakeProposalHost):
            def verify(inner_self, request):
                raise RoleHostResourceExhausted("finite verifier grant exhausted")

        host = ExhaustedVerifierHost(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=host,
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        coordinator.execute()
        context = coordinator.open_verification("verification-resource-pause")
        with self.assertRaises(ResourcePause):
            coordinator.verify_with_host(context)
        self.assertEqual(coordinator.manifest.state, "paused_resource")
        self.assertEqual(coordinator.manifest.suspended_from, "verifying")
        self.assertIsNone(coordinator.active_semantic_request_token)
        self.assertIsNone(coordinator.lease)
        handoff = _coordinator_handoff(coordinator, self.capabilities)
        self.assertFalse(handoff["terminal"])
        self.assertIn("not continuing in the background", handoff["status_summary"])

    def test_duplicate_verifier_response_persistence_stops_terminally(self):
        class VerifyingHost(FakeProposalHost):
            def verify(inner_self, request):
                response = complete_verification_response(request)
                inner_self.call_records.append(successful_verifier_record(request, response))
                return response

        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=VerifyingHost(self.target),
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        coordinator.execute()
        context = coordinator.open_verification("verification-duplicate-response")
        original = coordinator._persist_semantic_call_artifact

        def duplicate(token, filename, artifact):
            if filename == "response.json":
                raise FileExistsError("simulated duplicate response")
            return original(token, filename, artifact)

        with patch.object(coordinator, "_persist_semantic_call_artifact", side_effect=duplicate):
            with self.assertRaisesRegex(WorkflowError, "validation failed"):
                coordinator.verify_with_host(context)
        self.assertEqual(coordinator.manifest.state, "human_required")
        self.assertIsNone(coordinator.lease)

    def test_recovery_reuses_a_durable_verifier_response_without_provider_replay(self):
        host = FakeProposalHost(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=host,
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        coordinator.execute()
        context = coordinator.open_verification("verification-response-durable")
        request = coordinator.build_verification_request(context)
        coordinator._persist_semantic_call_artifact(context.token, "request.json", request)
        coordinator.active_semantic_request_token = context.token
        coordinator._persist_bundle_v2()
        response = complete_verification_response(request)
        coordinator._persist_semantic_call_artifact(context.token, "response.json", response)
        release_lease(coordinator.lease)
        coordinator.lease = None

        class NoVerifierReplay(FakeProposalHost):
            def verify(inner_self, request):
                raise AssertionError("recovery repeated a completed verifier call")

        recovered = ExecutionCoordinator.reload(
            str(self.root), self.plan.run_id, self.capabilities,
            agent_host=NoVerifierReplay(self.target), provider_grant=self.provider,
            run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
        )
        self.assertEqual(recovered.manifest.state, "verified")
        self.assertTrue(recovered.last_verification.verified)
        self.assertIn(context.token, recovered.completed_semantic_request_tokens)

    def test_reload_reuses_persisted_approved_proposal_without_reinvoking_model(self):
        capabilities = HostCapabilitiesV2(
            schema_version="3.0", profile="semi_formal", role_read_only="host_enforced",
            role_tool_allocation="framework_enforced", product_state_observation="coordinator_observed",
            complete_child_trace=False, atomic_path_enforcement=False, atomic_lease_create=True,
            bounded_resource_enforcement="framework_enforced", fresh_context_enforcement="host_enforced",
            provider_identity_observation="coordinator_observed",
            policy_aware_role_allocation=True,
        )
        first_host = FakeProposalHost(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, capabilities,
            semantic_proposal=self.semantic, agent_host=first_host, provider_grant=self.provider,
            run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
        )
        with patch(
            "rb_safe_operation.workflow.commit_prepared_text_patch",
            side_effect=KeyboardInterrupt("simulated crash before first product write"),
        ), self.assertRaises(KeyboardInterrupt):
            coordinator.execute()
        self.assertEqual(self.target.read_text(encoding="utf-8"), "a\n")
        self.assertEqual(coordinator.manifest.state, "applying_proposal")
        release_lease(coordinator.lease)
        coordinator.lease = None

        class NoModelCalls(FakeProposalHost):
            def propose_patch(self, request):
                raise AssertionError("recovery reinvoked proposer")
            def assess_patch(self, request):
                raise AssertionError("recovery reinvoked assessor")

        recovered = ExecutionCoordinator.reload(
            str(self.root), self.plan.run_id, capabilities,
            agent_host=NoModelCalls(self.target), provider_grant=self.provider,
            run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
        )
        reports = recovered.execute()
        self.assertEqual(self.target.read_text(encoding="utf-8"), "b\n")
        self.assertEqual(len(reports), 1)
        recovered.abandon()

    def test_interrupted_proposer_request_is_not_replayed_on_recovery(self):
        class InterruptingProposer(FakeProposalHost):
            def __init__(inner_self, target):
                super().__init__(target)
                inner_self.proposer_calls = 0

            def propose_patch(inner_self, request):
                inner_self.proposer_calls += 1
                raise KeyboardInterrupt("simulated proposer interruption")

        host = InterruptingProposer(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=host,
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        with self.assertRaises(KeyboardInterrupt):
            coordinator.execute()
        self.assertIsNotNone(coordinator.active_semantic_request_token)
        release_lease(coordinator.lease)
        coordinator.lease = None
        with self.assertRaisesRegex(WorkflowError, "incomplete proposer call"):
            ExecutionCoordinator.reload(
                str(self.root), self.plan.run_id, self.capabilities,
                agent_host=host, provider_grant=self.provider,
                run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
            )
        self.assertEqual(host.proposer_calls, 1)
        bundle = CoordinatorBundleV2.model_validate(
            parse_json_strict(coordinator.bundle_path.read_bytes())
        )
        events = coordinator.audit.validate_chain()
        self.assertEqual(bundle.manifest.state, "human_required")
        self.assertEqual(bundle.manifest.event_head_hash, events[-1].event_record_hash)

    def test_durable_proposer_response_with_interrupted_checkpoint_is_not_replayed(self):
        host = FakeProposalHost(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=host,
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        original_persist = coordinator._persist_bundle_v2

        def interrupt_after_response():
            if (
                coordinator.manifest.state == "validating_proposal"
                and coordinator.completed_semantic_request_tokens
            ):
                raise KeyboardInterrupt("simulated interruption after durable proposer response")
            return original_persist()

        with patch.object(coordinator, "_persist_bundle_v2", side_effect=interrupt_after_response):
            with self.assertRaises(KeyboardInterrupt):
                coordinator.execute()
        token = coordinator.completed_semantic_request_tokens[-1]
        self.assertTrue((coordinator.run_root / "semantic-calls" / token / "response.json").is_file())
        release_lease(coordinator.lease)
        coordinator.lease = None

        class NoReplay(FakeProposalHost):
            def propose_patch(inner_self, request):
                raise AssertionError("durable proposer response was replayed")

        with self.assertRaisesRegex(WorkflowError, "interrupted event-to-bundle checkpoint"):
            ExecutionCoordinator.reload(
                str(self.root), self.plan.run_id, self.capabilities,
                agent_host=NoReplay(self.target), provider_grant=self.provider,
                run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
            )
        bundle = CoordinatorBundleV2.model_validate(
            parse_json_strict(coordinator.bundle_path.read_bytes())
        )
        self.assertEqual(bundle.manifest.state, "human_required")
        self.assertEqual(
            bundle.manifest.event_head_hash,
            coordinator.audit.validate_chain()[-1].event_record_hash,
        )

    def test_interrupted_patch_assessor_request_is_not_replayed_on_recovery(self):
        class InterruptingAssessor(FakeProposalHost):
            def __init__(inner_self, target):
                super().__init__(target)
                inner_self.assessor_calls = 0

            def assess_patch(inner_self, request):
                inner_self.assessor_calls += 1
                raise KeyboardInterrupt("simulated patch-assessor interruption")

        host = InterruptingAssessor(self.target)
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=host,
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        with self.assertRaises(KeyboardInterrupt):
            coordinator.execute()
        self.assertEqual(coordinator.manifest.state, "assessing_proposal")
        release_lease(coordinator.lease)
        coordinator.lease = None
        with self.assertRaisesRegex(WorkflowError, "incomplete patch_assessor call"):
            ExecutionCoordinator.reload(
                str(self.root), self.plan.run_id, self.capabilities,
                agent_host=host, provider_grant=self.provider,
                run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
            )
        self.assertEqual(host.assessor_calls, 1)
        bundle = CoordinatorBundleV2.model_validate(
            parse_json_strict(coordinator.bundle_path.read_bytes())
        )
        self.assertEqual(bundle.manifest.state, "human_required")

    def test_reload_records_human_required_for_unknown_target_state(self):
        capabilities = HostCapabilitiesV2(
            schema_version="3.0", profile="semi_formal", role_read_only="host_enforced",
            role_tool_allocation="framework_enforced", product_state_observation="coordinator_observed",
            complete_child_trace=False, atomic_path_enforcement=False, atomic_lease_create=True,
            bounded_resource_enforcement="framework_enforced", fresh_context_enforcement="host_enforced",
            provider_identity_observation="coordinator_observed",
            policy_aware_role_allocation=True,
        )
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, capabilities,
            semantic_proposal=self.semantic, agent_host=FakeProposalHost(self.target), provider_grant=self.provider,
            run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
        )
        with patch(
            "rb_safe_operation.workflow.commit_prepared_text_patch",
            side_effect=KeyboardInterrupt("simulated crash"),
        ), self.assertRaises(KeyboardInterrupt):
            coordinator.execute()
        release_lease(coordinator.lease)
        coordinator.lease = None
        self.target.write_text("unrelated concurrent content\n", encoding="utf-8")
        with self.assertRaisesRegex(Exception, "unknown target state"):
            ExecutionCoordinator.reload(
                str(self.root), self.plan.run_id, capabilities,
                agent_host=FakeProposalHost(self.target), provider_grant=self.provider,
                run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
            )
        bundle_path = self.root / ".rb-safe-operation" / "runs" / self.plan.run_id / "coordinator-bundle.json"
        bundle = CoordinatorBundleV2.model_validate(parse_json_strict(bundle_path.read_bytes()))
        self.assertEqual(bundle.manifest.state, "human_required")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "unrelated concurrent content\n")

    def test_repair_uses_new_proposal_cycle_and_keeps_immutable_attempt_binding(self):
        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=FakeProposalHost(self.target),
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        initial_report = coordinator.execute()[0]
        context = coordinator.open_verification("repair-verifier-1")
        criteria = sorted({value for item in self.plan.operations for value in item.success_criteria})
        checks = sorted({value for item in self.plan.operations for value in item.verifier_checks})
        effects = sorted({value.effect_id for item in self.plan.operations for value in item.effects})
        finding = {
            "finding_id": "repair-finding-1", "invariant_id": "L-003",
            "operation_ids": ["edit-1"], "effect_ids": ["effect-modify"],
            "category": "repairable_local", "severity": "medium",
            "evidence_ids": ["verification-evidence"],
            "evidence_provenance": ["agent_reported"],
            "finding_provenance": "agent_reported", "explanation": "wording is still wrong",
            "remediation_or_human_decision": "make a narrower local correction", "blocking": True,
        }
        failed = VerificationProposalV2(
            schema_version="3.0", plan_hash=coordinator.plan_hash,
            assessment_hash=coordinator.assessment_hash, snapshot_hash=context.snapshot_hash,
            verifier_context_id=context.context_id, success_criteria_met=criteria,
            verifier_checks_passed=checks, observed_effect_ids=effects,
            evidence=[{"evidence_id": "verification-evidence", "provenance": "agent_reported", "locator": "agent-report:verification-evidence", "summary": "static result checked"}],
            criterion_evidence={value: ["verification-evidence"] for value in criteria},
            check_evidence={value: ["verification-evidence"] for value in checks},
            effect_evidence={value: ["verification-evidence"] for value in effects},
            findings=[finding], proposal_hashes=[initial_report.proposal_hash],
            patch_assessment_hashes=[initial_report.patch_assessment_hash],
            execution_report_hashes=[ref("execution-report", "3.0", initial_report.model_dump(mode="json"))],
            policy_binding=self.loaded_policy.binding,
        )
        failed_report = coordinator.verify(failed, context)
        self.assertFalse(failed_report.verified)
        repair_finding_id = failed_report.findings[0].finding_id
        attempt = RepairAttemptV2(
            schema_version="3.0", attempt_id="repair-attempt-1", finding_id=repair_finding_id,
            hypothesis="the replacement needs a narrower correction", observed_result="verification rejected b",
            reconsidered_assumption="b was sufficient", materially_different_next_strategy="replace b with c",
            strategy_code="narrow_targeted_correction", high_risk_replay=False,
            fresh_idempotency_proof=None, approval_id=None,
            prior_proposal_hash=initial_report.proposal_hash,
            resource_grant_hash=coordinator.run_resource_grant_hash, outcome="proposing",
            policy_binding=self.loaded_policy.binding,
        )
        attempt_hash = ref("repair-attempt", "3.0", attempt.model_dump(mode="json"))
        stale_binding = self.loaded_policy.binding.model_copy(update={
            "source_policy_sha256": "0" * 64,
        })
        with self.assertRaisesRegex(WorkflowError, "active project policy"):
            coordinator.resume_repair(
                attempt.model_copy(update={"policy_binding": stale_binding})
            )
        coordinator.resume_repair(attempt)

        class RepairHost(FakeProposalHost):
            def propose_patch(inner_self, request):
                return AgentPatchProposal(
                    schema_version="1.0", request_token=request.context.request_token,
                    operation_id=request.operation.operation_id, attempt_id=request.context.attempt_id,
                    intent_summary="replace b with c",
                    unified_diff="--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-b\n+c\n",
                    claimed_created_paths=[], claimed_modified_paths=[str(self.target)],
                    claimed_deleted_paths=[], claimed_effect_ids=["effect-modify", "effect-read"],
                    evidence=[], no_other_changes=True,
                )

        coordinator.agent_host = RepairHost(self.target)
        repaired_report = coordinator.execute()[0]
        self.assertEqual(self.target.read_text(encoding="utf-8"), "c\n")
        self.assertEqual(coordinator.proposal_cycle_history[-1].proposal.repair_attempt_hash, attempt_hash)
        self.assertEqual([item.outcome for item in coordinator.repair_outcomes], ["applied"])

        context = coordinator.open_verification("repair-verifier-2")
        verified = VerificationProposalV2(
            schema_version="3.0", plan_hash=coordinator.plan_hash,
            assessment_hash=coordinator.assessment_hash, snapshot_hash=context.snapshot_hash,
            verifier_context_id=context.context_id, success_criteria_met=criteria,
            verifier_checks_passed=checks, observed_effect_ids=effects,
            evidence=[{"evidence_id": "verification-evidence-2", "provenance": "agent_reported", "locator": "agent-report:verification-evidence-2", "summary": "repaired static result checked"}],
            criterion_evidence={value: ["verification-evidence-2"] for value in criteria},
            check_evidence={value: ["verification-evidence-2"] for value in checks},
            effect_evidence={value: ["verification-evidence-2"] for value in effects},
            findings=[],
            proposal_hashes=[ref("bounded-patch-proposal", "2.0", item.model_dump(mode="json")) for item in coordinator.proposal_history],
            patch_assessment_hashes=[ref("patch-assessment", "2.0", item.model_dump(mode="json")) for item in coordinator.patch_assessment_history],
            execution_report_hashes=[ref("execution-report", "3.0", item.model_dump(mode="json")) for item in coordinator.reports],
            policy_binding=self.loaded_policy.binding,
        )
        self.assertTrue(coordinator.verify(verified, context).verified)
        self.assertEqual([item.outcome for item in coordinator.repair_outcomes], ["applied", "verified"])
        self.assertEqual(len(coordinator.proposal_cycle_history), 2)
        self.assertIn("-a\n+b\n", coordinator.proposal_cycle_history[0].agent_proposal.unified_diff)
        self.assertIn("-b\n+c\n", coordinator.proposal_cycle_history[1].agent_proposal.unified_diff)
        persisted = CoordinatorBundleV2.model_validate(parse_json_strict(coordinator.bundle_path.read_bytes()))
        self.assertEqual(len(persisted.proposal_cycle_history), 2)

    def test_resource_pause_requires_a_chained_replenishment_grant(self):
        class ExhaustedHost(FakeProposalHost):
            def propose_patch(self, request):
                raise RoleHostResourceExhausted("test budget exhausted")

        coordinator = ExecutionCoordinator(
            self.plan, self.assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=self.semantic, agent_host=ExhaustedHost(self.target),
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        with self.assertRaises(ResourcePause):
            coordinator.execute()
        self.assertEqual(coordinator.manifest.state, "paused_resource")
        self.assertEqual(self.target.read_text(encoding="utf-8"), "a\n")

        invalid = self.resource.model_copy(update={"grant_id": "resource-invalid"})
        with self.assertRaisesRegex(Exception, "valid paused-run replenishment"):
            ExecutionCoordinator.reload(
                str(self.root), self.plan.run_id, self.capabilities,
                agent_host=FakeProposalHost(self.target), provider_grant=self.provider,
                run_resource_grant=invalid, metadata_loader=self.metadata_loader,
            )
        replenished = self.resource.model_copy(update={
            "grant_id": "resource-2", "issued_at": "2026-07-28T11:00:00Z",
            "expires_at": "2099-07-28T13:00:00Z", "replenishes_grant_id": self.resource.grant_id,
        })
        recovered = ExecutionCoordinator.reload(
            str(self.root), self.plan.run_id, self.capabilities,
            agent_host=FakeProposalHost(self.target), provider_grant=self.provider,
            run_resource_grant=replenished, metadata_loader=self.metadata_loader,
        )
        recovered.resume_after_pause("resource-replenishment-authorized")
        reports = recovered.execute()
        self.assertEqual(self.target.read_text(encoding="utf-8"), "b\n")
        self.assertEqual(len(reports), 1)
        recovered.abandon()

    def test_exact_patch_uses_the_same_durable_apply_intent_and_recovery_path(self):
        patch_text = "--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-a\n+b\n"
        operation_payload = {
            **common(self.root, "exact-edit-1", effect(
                "effect-exact-modify", "repository_modify", targets=[str(self.target)],
                residual_severity="medium", approval_class="privacy_sensitive",
            )),
            "kind": "exact_action", "adapter": "apply_patch", "patch": patch_text,
            "patch_hash": hashlib.sha256(patch_text.encode()).hexdigest(),
            "preimage_hashes": {str(self.target): hashlib.sha256(b"a\n").hexdigest()},
            "expected_created_paths": [], "expected_modified_paths": [str(self.target)],
            "expected_deleted_paths": [], "created_file_mode": 0o640,
        }
        operation_payload["approval_classes"] = ["privacy_sensitive"]
        operation_payload["path_contract"]["modify_roots"] = [str(self.root)]
        operation = ApplyPatchActionV2.model_validate(operation_payload)
        plan = self.plan.model_copy(update={"operations": [operation]})
        semantic = self.semantic.model_copy(update={"required_role_assurance_profiles": []})
        approval = ApprovalV2(
            schema_version="3.0",
            approval_id="approval-exact-edit",
            plan_hash=ref("low-level-plan", "3.0", plan.model_dump(mode="json")),
            operation_hash=ref("operation", "2.0", operation.model_dump(mode="json")),
            policy_hash=ref("active-policy", "2.0", self.active_policy.model_dump(mode="json")),
            snapshot_hash=ref("repository-snapshot", "3.0", plan.snapshot.model_dump(mode="json")),
            proposal_hash=None, patch_assessment_hash=None,
            policy_binding=self.loaded_policy.binding,
            effect_id="effect-exact-modify", effect_class="repository_modify",
            approval_class="privacy_sensitive", target=str(self.target),
            expires_at="2099-07-28T12:00:00Z", one_use=True, consumed=False,
            idempotency_key="exact-edit-idempotency", principal=None,
            identity_verification="unavailable",
        )
        assessment = assess_plan(
            plan, self.policy, self.active_policy, self.snapshot, self.capabilities,
            semantic, [approval], now=datetime(2026, 7, 28, 10, 0, tzinfo=timezone.utc),
            provider_grant=self.provider, run_resource_grant=self.resource,
        )
        coordinator = ExecutionCoordinator(
            plan, assessment, self.policy, self.active_policy, self.capabilities,
            semantic_proposal=semantic, agent_host=FakeProposalHost(self.target),
            provider_grant=self.provider, run_resource_grant=self.resource,
            metadata_loader=self.metadata_loader,
        )
        with patch(
            "rb_safe_operation.workflow.commit_prepared_text_patch",
            side_effect=KeyboardInterrupt("crash after exact intent"),
        ), self.assertRaises(KeyboardInterrupt):
            coordinator.execute()
        self.assertEqual(self.target.read_text(encoding="utf-8"), "a\n")
        self.assertEqual(coordinator.current_apply_intent.execution_kind, "exact")
        self.assertEqual(len(coordinator.current_apply_intent.approval_hashes), 1)
        self.assertEqual(coordinator.current_apply_intent.approval_hashes[0].schema_version, "3.0")
        self.assertTrue((
            self.root / ".rb-safe-operation" / "approvals" / plan.run_id /
            "approval-exact-edit.consumed"
        ).is_file())
        release_lease(coordinator.lease)
        coordinator.lease = None
        recovered = ExecutionCoordinator.reload(
            str(self.root), plan.run_id, self.capabilities,
            agent_host=FakeProposalHost(self.target), provider_grant=self.provider,
            run_resource_grant=self.resource, metadata_loader=self.metadata_loader,
        )
        reports = recovered.execute()
        self.assertEqual(self.target.read_text(encoding="utf-8"), "b\n")
        self.assertEqual(reports[0].execution_kind, "exact")
        self.assertEqual(recovered.apply_intent_history[0].execution_kind, "exact")
        recovered.abandon()

    def test_schema_two_cli_persists_and_assesses_only_fixed_create_only_handoffs(self):
        with tempfile.TemporaryDirectory() as input_directory:
            inputs = Path(input_directory)
            plan_input = inputs / "plan.json"
            capabilities_input = inputs / "capabilities.json"
            provider_input = inputs / "provider.json"
            resource_input = inputs / "resource.json"
            provider = self.provider.model_copy(update={
                "adapter": "json_line", "endpoint": "host-mediated://stdio",
            })
            capabilities = default_host_capabilities_v2("json_line")
            operation = self.plan.operations[0].model_copy(update={
                "required_adapter": "json_line",
                "required_assurance_profile": "instruction_only_proposal_host",
            })
            cli_snapshot = capture_policy_snapshot(
                self.loaded_policy,
                list(self.plan.snapshot.selected_file_hashes),
                list(self.plan.snapshot.instruction_hashes),
                self.plan.snapshot.expected_product_changes,
                self.plan.snapshot.control_plane_roots,
            )
            plan = self.plan.model_copy(update={
                "snapshot": cli_snapshot,
                "operations": [operation],
                "provider_grant_hash": ref(
                    "provider-grant", "1.0", provider.model_dump(mode="json")
                ),
            })
            for path, value in (
                (plan_input, plan), (capabilities_input, capabilities),
                (provider_input, provider), (resource_input, self.resource),
            ):
                path.write_bytes(canonical_bytes(value.model_dump(mode="json")) + b"\n")
            with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
                cmd_persist_artifact(SimpleNamespace(
                    artifact_type="low-level-plan", input=str(plan_input), plan=str(plan_input)
                ))
            fixed_plan = self.root / ".rb-safe-operation" / "artifacts" / self.plan.run_id / "low-level-plan.json"
            output = SimpleNamespace(buffer=io.BytesIO())
            with patch("sys.stdout", output), patch(
                "rb_safe_operation.cli.capture_file_metadata", self.metadata_loader
            ):
                cmd_assess_preflight(SimpleNamespace(
                    plan=str(fixed_plan), project_policy=None,
                    capabilities=str(capabilities_input), provider_grant=str(provider_input),
                    run_resource_grant=str(resource_input), approvals=None,
                    prior_assessment_bundle=None,
                ))
            preflight_payload = parse_json_strict(output.buffer.getvalue())
            self.assertNotIn(
                "preflight", preflight_payload,
                [item["explanation"] for item in preflight_payload.get("preflight", {}).get("findings", [])],
            )
            outer = self

            class CliPlanHost:
                def __init__(inner_self, *args, **kwargs):
                    inner_self.call_records = []

                def assess_plan(inner_self, request):
                    semantic = outer.semantic.model_copy(update={
                        "provider_grant_hash": request.context.provider_grant_hash,
                        "required_role_assurance_profiles": ["instruction_only_proposal_host"],
                    })
                    response = PlanAssessmentResponse(
                        schema_version="1.0", request_token=request.context.request_token,
                        plan_hash=request.preflight.plan_hash,
                        preflight_hash=ref(
                            "deterministic-preflight", "3.0",
                            request.preflight.model_dump(mode="json"),
                        ),
                        policy_hash=request.preflight.policy_hash,
                        snapshot_hash=request.preflight.snapshot_hash,
                        semantic_proposal=semantic,
                        policy_binding=request.context.policy_binding,
                    )
                    request_bytes = canonical_bytes(request.model_dump(mode="json"))
                    response_bytes = canonical_bytes(response.model_dump(mode="json"))
                    inner_self.call_records.append(RoleCallRecord(
                        schema_version="2.0", call_id="call-cli-plan-assessor",
                        role="plan_assessor", adapter="json_line",
                        assurance_profile="instruction_only_proposal_host",
                        provider_grant_hash=request.context.provider_grant_hash,
                        policy_binding=request.context.policy_binding,
                        request_hash=hashlib.sha256(request_bytes).hexdigest(),
                        response_hash=hashlib.sha256(response_bytes).hexdigest(),
                        outcome="success", usage_complete=True,
                        provider=provider.provider, endpoint=provider.endpoint,
                        model=provider.model, model_revision=provider.model_revision,
                        requests=1, tool_calls=0, input_tokens=0, output_tokens=0,
                        request_bytes=len(request_bytes), response_bytes=len(response_bytes),
                        elapsed_milliseconds=1, cost_decimal="0",
                        cost_provenance="provider_declared_zero",
                    ))
                    return response

            with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())), patch(
                "rb_safe_operation.cli.capture_file_metadata", self.metadata_loader
            ), patch("rb_safe_operation.cli.JsonLineProposalRoleHost", CliPlanHost):
                cmd_assess(SimpleNamespace(
                    plan=str(fixed_plan), project_policy=None,
                    capabilities=str(capabilities_input), provider_grant=str(provider_input),
                    run_resource_grant=str(resource_input), approvals=None,
                    prior_assessment_bundle=None,
                ))
            fixed_bundle = fixed_plan.with_name("assessment-bundle.json")
            bundle = AssessmentBundleV2.model_validate(parse_json_strict(fixed_bundle.read_bytes()))
            self.assertTrue(bundle.assessment.safe)
            semantic_calls = fixed_plan.parent / "semantic-calls"
            call_roots = list(semantic_calls.iterdir())
            self.assertEqual(len(call_roots), 1)
            self.assertTrue((call_roots[0] / "request.json").is_file())
            self.assertTrue((call_roots[0] / "response.json").is_file())
            self.assertTrue((call_roots[0] / "role-call-record.json").is_file())
            fixed_bundle.unlink()

            class NoPlanAssessorReplay:
                def __init__(inner_self, *args, **kwargs):
                    inner_self.call_records = []

                def assess_plan(inner_self, request):
                    raise AssertionError("completed plan-assessor call was repeated")

                def adopt_call_record(inner_self, record):
                    inner_self.call_records.append(record)

            with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())), patch(
                "rb_safe_operation.cli.capture_file_metadata", self.metadata_loader
            ), patch("rb_safe_operation.cli.JsonLineProposalRoleHost", NoPlanAssessorReplay):
                cmd_assess(SimpleNamespace(
                    plan=str(fixed_plan), project_policy=None,
                    capabilities=str(capabilities_input), provider_grant=str(provider_input),
                    run_resource_grant=str(resource_input), approvals=None,
                    prior_assessment_bundle=None,
                ))
            self.assertTrue(fixed_bundle.is_file())
            with self.assertRaises(FileExistsError):
                with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
                    cmd_persist_artifact(SimpleNamespace(
                        artifact_type="low-level-plan", input=str(plan_input), plan=str(plan_input)
                    ))


if __name__ == "__main__":
    unittest.main()
