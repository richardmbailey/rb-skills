from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from pydantic import ValidationError

from rb_safe_operation.compatibility import LegacyArtifactNotExecutable, inspect_legacy_artifact, require_executable_schema
from rb_safe_operation.models import EvidenceRef, Finding, HashRef
from rb_safe_operation.proposal_models import (
    AgentPatchProposal,
    ApplyIntent,
    BoundedPatchProposal,
    CoordinatorBundleV2,
    ExecutionReportV2,
    HostCapabilitiesV2,
    HumanInterventionV2,
    PatchAssessment,
    PatchProposalPreflight,
    PatchSemanticAssessmentProposal,
    ProposalContext,
    ProviderGrant,
    RepairAttemptV2,
    RunManifestV2,
    RunResourceGrant,
    SourceObservation,
    VerificationProposalV2,
    VerificationReportV2,
)
from rb_safe_operation.policy_models import PathPolicyDecision, PolicyBinding
from rb_safe_operation.schemas import MODEL_SCHEMAS, export_schemas, model_for


ZERO = "0" * 64
ONE = "1" * 64


def ref(artifact_type: str, version: str, value: str = ZERO) -> HashRef:
    return HashRef(artifact_type=artifact_type, schema_version=version, value=value)


def finding(blocking: bool = True) -> Finding:
    return Finding(
        finding_id="finding-1",
        invariant_id="O-001",
        operation_ids=["op-1"],
        effect_ids=["effect-1"],
        category="operation_contract",
        severity="high",
        evidence_ids=[],
        evidence_provenance=[],
        finding_provenance="coordinator_observed",
        explanation="proposal is not permitted",
        remediation_or_human_decision="create a new assessed proposal",
        blocking=blocking,
    )


def policy_binding() -> PolicyBinding:
    return PolicyBinding(
        schema_version="1.0",
        project_root="/project",
        policy_path="/project/.rb-safe-operation-policy.json",
        presence="absent",
        global_policy_hash=ref("active-policy", "1.0"),
        source_policy_sha256=ZERO,
        effective_policy_hash=ref("active-policy", "2.0"),
    )


def allowed_read(path: str) -> PathPolicyDecision:
    return PathPolicyDecision(
        schema_version="1.0", capability="read", requested_path=path,
        allowed=True, matched_rule_ids=[], component_identity_hash=ZERO,
        uncertainty=None,
    )


class ProposalContractTests(unittest.TestCase):
    def provider_grant(self) -> ProviderGrant:
        return ProviderGrant(
            schema_version="1.0",
            grant_id="provider-grant-1",
            issued_at="2026-07-28T10:00:00Z",
            expires_at="2026-07-28T11:00:00Z",
            roles=["plan_assessor", "proposer", "patch_assessor", "verifier"],
            adapter="pydantic_ai",
            provider="test-provider",
            endpoint="in-memory://function-model",
            model="function-model",
            model_revision="test-1",
            credential_audience="none:test-only",
            request_data_classes=["internal_source"],
            response_data_classes=["patch_proposal", "patch_assessment"],
            maximum_data_classification="internal",
            retention_disclosure="in-memory test model retains no request",
            training_use="disallowed",
            max_calls=4,
            max_request_bytes=100_000,
            max_input_tokens=10_000,
            max_output_tokens=10_000,
            max_seconds=60,
            max_cost_decimal="0",
            cost_accounting="declared_zero",
            temperature_decimal="0",
            seed=7,
            structured_output_mode="tool",
            redirect_endpoints=[],
            approval_hash=None,
        )

    def resource_grant(self) -> RunResourceGrant:
        return RunResourceGrant(
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
            max_elapsed_seconds=60,
            max_cost_decimal="0",
            replenishes_grant_id=None,
            authorization_hash=ref("human-authorization", "1.0"),
        )

    def context(self) -> ProposalContext:
        return ProposalContext(
            schema_version="2.0",
            context_id="context-1",
            request_token="request-1",
            operation_id="op-1",
            attempt_id="attempt-initial",
            role="proposer",
            adapter="pydantic_ai",
            assurance_profile="framework_tool_enforced_proposer",
            plan_hash=ref("low-level-plan", "3.0"),
            plan_assessment_hash=ref("assessment", "3.0"),
            operation_hash=ref("operation", "2.0"),
            active_policy_hash=ref("active-policy", "2.0"),
            policy_binding=policy_binding(),
            base_snapshot_hash=ref("repository-snapshot", "3.0"),
            provider_grant_hash=ref("provider-grant", "1.0"),
            run_resource_grant_hash=ref("run-resource-grant", "1.0"),
            repair_attempt_hash=None,
            input_artifact_hashes=[ref("instructions", "1.0")],
            instruction_hashes={"/project/AGENTS.md": ZERO},
            source_observations=[
                SourceObservation(
                    observation_id="source-1",
                    path="/project/input.txt",
                    byte_start=0,
                    byte_end=6,
                    content_hash=ZERO,
                    metadata_hash=ONE,
                    data_classification="internal",
                    policy_decision=allowed_read("/project/input.txt"),
                )
            ],
            prompt_packet_hash=ZERO,
            toolset_hash=ZERO,
            created_at="2026-07-28T10:00:00Z",
        )

    def agent_proposal(self) -> AgentPatchProposal:
        return AgentPatchProposal(
            schema_version="1.0",
            request_token="request-1",
            operation_id="op-1",
            attempt_id="attempt-initial",
            intent_summary="replace a with b",
            unified_diff="--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-a\n+b\n",
            claimed_created_paths=[],
            claimed_modified_paths=["/project/input.txt"],
            claimed_deleted_paths=[],
            claimed_effect_ids=["effect-1"],
            evidence=[
                EvidenceRef(
                    evidence_id="proposal-evidence-1",
                    provenance="agent_reported",
                    locator="agent-report:proposal-evidence-1",
                    summary="proposal constructed",
                )
            ],
            no_other_changes=True,
        )

    def bounded_proposal(self) -> BoundedPatchProposal:
        return BoundedPatchProposal(
            schema_version="2.0",
            proposal_id="proposal-1",
            context_hash=ref("proposal-context", "2.0"),
            agent_proposal_hash=ref("agent-patch-proposal", "1.0"),
            plan_hash=ref("low-level-plan", "3.0"),
            plan_assessment_hash=ref("assessment", "3.0"),
            operation_hash=ref("operation", "2.0"),
            active_policy_hash=ref("active-policy", "2.0"),
            policy_binding=policy_binding(),
            base_snapshot_hash=ref("repository-snapshot", "3.0"),
            repair_attempt_hash=None,
            patch_hash=ZERO,
            created_paths=[],
            modified_paths=["/project/input.txt"],
            deleted_paths=[],
            preimage_hashes={"/project/input.txt": ZERO},
            postimage_hashes={"/project/input.txt": ONE},
            metadata_hashes={"/project/input.txt": ZERO},
            expected_effect_ids=["effect-1"],
            proposer_role="proposer",
            assurance_profile="framework_tool_enforced_proposer",
            evidence=self.agent_proposal().evidence,
        )

    def test_provider_and_resource_grants_are_finite_and_strict(self):
        self.assertEqual(self.provider_grant().max_calls, 4)
        self.assertEqual(self.resource_grant().max_proposer_calls, 2)
        with self.assertRaises(ValidationError):
            self.provider_grant().model_copy(update={"expires_at": "2026-07-28T09:00:00Z"}).__class__.model_validate(
                self.provider_grant().model_dump() | {"expires_at": "2026-07-28T09:00:00Z"}
            )
        with self.assertRaises(ValidationError):
            ProviderGrant.model_validate(self.provider_grant().model_dump() | {"unexpected": True})

    def test_context_rejects_duplicate_source_observation_identity(self):
        context = self.context()
        with self.assertRaises(ValidationError):
            ProposalContext.model_validate(
                context.model_dump() | {"source_observations": [item.model_dump() for item in context.source_observations] * 2}
            )

    def test_agent_proposal_requires_closed_disjoint_claims_and_assertion(self):
        self.assertTrue(self.agent_proposal().no_other_changes)
        data = self.agent_proposal().model_dump()
        data["claimed_created_paths"] = ["/project/input.txt"]
        with self.assertRaises(ValidationError):
            AgentPatchProposal.model_validate(data)
        with self.assertRaises(ValidationError):
            AgentPatchProposal.model_validate(self.agent_proposal().model_dump() | {"no_other_changes": False})

    def test_bounded_proposal_requires_hashes_for_exact_derived_inventory(self):
        self.assertEqual(self.bounded_proposal().modified_paths, ["/project/input.txt"])
        data = self.bounded_proposal().model_dump()
        data["postimage_hashes"] = {}
        with self.assertRaises(ValidationError):
            BoundedPatchProposal.model_validate(data)

    def test_preflight_and_patch_assessment_verdicts_cannot_contradict_findings(self):
        preflight = PatchProposalPreflight(
            schema_version="2.0",
            preflight_id="preflight-1",
            proposal_hash=ref("bounded-patch-proposal", "2.0"),
            plan_hash=ref("low-level-plan", "3.0"),
            policy_hash=ref("active-policy", "2.0"),
            snapshot_hash=ref("repository-snapshot", "3.0"),
            policy_binding=policy_binding(),
            deterministic_pass=True,
            semantic_assessment_required=True,
            findings=[],
        )
        semantic = PatchSemanticAssessmentProposal(
            schema_version="2.0",
            request_token="assessment-request-1",
            proposal_hash=ref("bounded-patch-proposal", "2.0"),
            semantic_pass=True,
            findings=[],
            covered_paths=["/project/input.txt"],
            covered_effect_ids=["effect-1"],
            no_uncontrolled_detrimental_side_effects=True,
            policy_binding=policy_binding(),
        )
        assessment = PatchAssessment(
            schema_version="2.0",
            assessment_id="patch-assessment-1",
            proposal_hash=ref("bounded-patch-proposal", "2.0"),
            preflight_hash=ref("patch-proposal-preflight", "2.0"),
            semantic_proposal_hash=ref("patch-semantic-assessment-proposal", "2.0"),
            complete_context=True,
            deterministic_pass=True,
            semantic_pass=True,
            safe=True,
            status="approved",
            findings=[],
            policy_binding=policy_binding(),
        )
        self.assertTrue(preflight.deterministic_pass and semantic.semantic_pass and assessment.safe)
        with self.assertRaises(ValidationError):
            PatchProposalPreflight.model_validate(preflight.model_dump() | {"findings": [finding().model_dump()]})
        with self.assertRaises(ValidationError):
            PatchAssessment.model_validate(assessment.model_dump() | {"complete_context": False})

    def test_report_and_apply_intent_are_coordinator_owned_and_bound(self):
        report = ExecutionReportV2(
            schema_version="3.0",
            operation_id="op-1",
            execution_kind="bounded_proposal",
            proposal_hash=ref("bounded-patch-proposal", "2.0"),
            patch_assessment_hash=ref("patch-assessment", "2.0"),
            success=True,
            evidence=[],
            expected_effect_ids_observed=["effect-1"],
            unexpected_effects=[],
            committed_postimage_hashes={"/project/input.txt": ONE},
            provenance="coordinator_observed",
            next_strategy=None,
            policy_binding=policy_binding(),
        )
        intent = ApplyIntent(
            schema_version="2.0",
            intent_id="intent-1",
            operation_id="op-1",
            execution_kind="bounded_proposal",
            operation_hash=ref("operation", "2.0"),
            proposal_hash=ref("bounded-patch-proposal", "2.0"),
            patch_assessment_hash=ref("patch-assessment", "2.0"),
            approval_hashes=[],
            ordered_targets=["/project/input.txt"],
            preimage_hashes={"/project/input.txt": ZERO},
            postimage_hashes={"/project/input.txt": ONE},
            committed_targets=[],
            state="prepared",
            policy_binding=policy_binding(),
        )
        self.assertEqual(report.provenance, "coordinator_observed")
        self.assertEqual(intent.state, "prepared")
        with self.assertRaises(ValidationError):
            ExecutionReportV2.model_validate(report.model_dump() | {"provenance": "agent_reported"})

        exact_intent = ApplyIntent.model_validate(intent.model_dump() | {
            "execution_kind": "exact",
            "proposal_hash": None,
            "patch_assessment_hash": None,
            "approval_hashes": [ref("approval", "3.0").model_dump()],
        })
        self.assertEqual(exact_intent.approval_hashes[0].schema_version, "3.0")
        with self.assertRaises(ValidationError):
            ApplyIntent.model_validate(
                exact_intent.model_dump()
                | {"approval_hashes": [ref("approval", "1.0").model_dump()]}
            )
        bounded_with_approval = ApplyIntent.model_validate(
            intent.model_dump()
            | {"approval_hashes": [ref("approval", "3.0").model_dump()]}
        )
        self.assertEqual(bounded_with_approval.approval_hashes[0].schema_version, "3.0")

    def test_manifest_bundle_and_capabilities_use_final_lifecycle(self):
        manifest = RunManifestV2(
            schema_version="3.0",
            run_id="run-1",
            state="assessing_proposal",
            suspended_from=None,
            plan_hash=ref("low-level-plan", "3.0"),
            assessment_hash=ref("assessment", "3.0"),
            policy_hash=ref("active-policy", "2.0"),
            policy_binding=policy_binding(),
            snapshot_hash=ref("repository-snapshot", "3.0"),
            provider_grant_hash=ref("provider-grant", "1.0"),
            run_resource_grant_hash=ref("run-resource-grant", "1.0"),
            current_operation_id="op-1",
            current_proposal_hash=ref("bounded-patch-proposal", "2.0"),
            current_patch_assessment_hash=None,
            current_apply_intent_hash=None,
            event_head_hash=None,
        )
        bundle = CoordinatorBundleV2(
            schema_version="3.0",
            project_root="/project",
            run_id="run-1",
            next_operation_index=0,
            manifest=manifest,
            plan_hash=manifest.plan_hash,
            assessment_hash=manifest.assessment_hash,
            policy_hash=manifest.policy_hash,
            policy_binding=policy_binding(),
            base_snapshot_hash=manifest.snapshot_hash,
            host_capabilities_hash=ref("host-capabilities", "3.0"),
            provider_grant_hash=manifest.provider_grant_hash,
            run_resource_grant_hash=manifest.run_resource_grant_hash,
            proposal_hash=manifest.current_proposal_hash,
            proposal_preflight_hash=None,
            patch_assessment_hash=None,
            apply_intent=None,
            execution_reports=[],
            repair_attempts=[],
        )
        capabilities = HostCapabilitiesV2(
            schema_version="3.0",
            profile="semi_formal",
            role_read_only="instruction_only",
            role_tool_allocation="framework_enforced",
            product_state_observation="coordinator_observed",
            complete_child_trace=False,
            atomic_path_enforcement=False,
            atomic_lease_create=True,
            bounded_resource_enforcement="framework_enforced",
            fresh_context_enforcement="instruction_only",
            provider_identity_observation="coordinator_observed",
            policy_aware_role_allocation=True,
        )
        self.assertEqual(bundle.manifest.state, "assessing_proposal")
        self.assertEqual(capabilities.role_tool_allocation, "framework_enforced")

    def test_verification_repair_and_human_artifacts_bind_proposal_cycle(self):
        proposal = VerificationProposalV2(
            schema_version="3.0",
            plan_hash=ref("low-level-plan", "3.0"),
            assessment_hash=ref("assessment", "3.0"),
            snapshot_hash=ref("repository-snapshot", "3.0"),
            proposal_hashes=[ref("bounded-patch-proposal", "2.0")],
            patch_assessment_hashes=[ref("patch-assessment", "2.0")],
            execution_report_hashes=[ref("execution-report", "3.0")],
            verifier_context_id="verify-context-1",
            success_criteria_met=["static_file_state::content matches"],
            verifier_checks_passed=["static_file_state::product_diff"],
            observed_effect_ids=["effect-1"],
            evidence=[],
            criterion_evidence={},
            check_evidence={},
            effect_evidence={},
            findings=[],
            policy_binding=policy_binding(),
        )
        report = VerificationReportV2(
            schema_version="3.0",
            verification_id="verification-1",
            plan_hash=proposal.plan_hash,
            assessment_hash=proposal.assessment_hash,
            snapshot_hash=proposal.snapshot_hash,
            proposal_hashes=proposal.proposal_hashes,
            patch_assessment_hashes=proposal.patch_assessment_hashes,
            execution_report_hashes=proposal.execution_report_hashes,
            independent_context=False,
            independence_assurance="instruction_only",
            coordinator_evidence_ids=["coordinator-evidence-1"],
            verifier_evidence_ids=["verifier-evidence-1"],
            success_criteria_met=proposal.success_criteria_met,
            verifier_checks_passed=proposal.verifier_checks_passed,
            findings=[],
            verified=True,
            provenance="coordinator_observed",
            policy_binding=policy_binding(),
        )
        repair = RepairAttemptV2(
            schema_version="3.0",
            attempt_id="repair-1",
            finding_id="finding-1",
            hypothesis="the exact local text is wrong",
            observed_result="verification found a mismatch",
            reconsidered_assumption="the prior wording was sufficient",
            materially_different_next_strategy="propose a narrower replacement",
            strategy_code="narrow_targeted_correction",
            high_risk_replay=False,
            fresh_idempotency_proof=None,
            approval_id=None,
            prior_proposal_hash=proposal.proposal_hashes[0],
            resource_grant_hash=ref("run-resource-grant", "1.0"),
            outcome="proposing",
            policy_binding=policy_binding(),
        )
        intervention = HumanInterventionV2(
            schema_version="3.0",
            decision_type="inspect_indeterminate_state",
            plan_hash=proposal.plan_hash,
            assessment_hash=proposal.assessment_hash,
            policy_hash=ref("active-policy", "2.0"),
            snapshot_hash=proposal.snapshot_hash,
            proposal_hash=proposal.proposal_hashes[0],
            patch_assessment_hash=proposal.patch_assessment_hashes[0],
            apply_intent_hash=ref("apply-intent", "2.0"),
            operation_id="op-1",
            effect_id="effect-1",
            timestamp="2026-07-28T10:30:00Z",
            rationale="target state no longer matches the journal",
            resulting_version_or_outcome="new run required",
            approval_expiry=None,
            idempotency_key=None,
            principal=None,
            identity_verification="unavailable",
            policy_binding=policy_binding(),
        )
        self.assertTrue(report.verified)
        self.assertEqual(repair.outcome, "proposing")
        self.assertEqual(intervention.decision_type, "inspect_indeterminate_state")


class LegacyCompatibilityTests(unittest.TestCase):
    def test_legacy_bounded_plan_is_audit_readable_but_not_executable(self):
        legacy = {
            "schema_version": "1.0",
            "plan_id": "legacy-plan",
            "run_id": "legacy-run",
            "operations": [{"kind": "bounded_agent_task", "operation_id": "legacy-task"}],
        }
        record = inspect_legacy_artifact("low-level-plan", legacy)
        self.assertEqual(record.schema_version, "1.0")
        self.assertEqual(record.stable_identifiers["plan_id"], "legacy-plan")
        with self.assertRaises(LegacyArtifactNotExecutable):
            require_executable_schema("low-level-plan", legacy, expected_version="3.0")

    def test_legacy_paused_manifest_cannot_resume(self):
        legacy = {"schema_version": "1.0", "run_id": "legacy-run", "state": "paused_resource"}
        record = inspect_legacy_artifact("run-manifest", legacy)
        self.assertEqual(record.summary["state"], "paused_resource")
        with self.assertRaises(LegacyArtifactNotExecutable):
            require_executable_schema("run-manifest", legacy, expected_version="3.0")


class ArtifactSchemaVersionTests(unittest.TestCase):
    def test_registry_keeps_legacy_and_proposal_first_versions(self):
        self.assertIsNot(model_for("low-level-plan", "1.0"), model_for("low-level-plan", "3.0"))
        self.assertIn(("coordinator-bundle", "3.0"), MODEL_SCHEMAS)
        self.assertIn(("provider-grant", "1.0"), MODEL_SCHEMAS)
        self.assertIn(("acceptance-run-summary", "1.0"), MODEL_SCHEMAS)
        with self.assertRaisesRegex(ValueError, "unsupported_artifact_version"):
            model_for("low-level-plan", "2.0")

    def test_schema_export_uses_each_artifact_version(self):
        runtime_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            written = {path.name for path in export_schemas(Path(temporary), runtime_root, "source-hash")}
        self.assertIn("low-level-plan-1.0.schema.json", written)
        self.assertIn("low-level-plan-3.0.schema.json", written)
        self.assertIn("provider-grant-1.0.schema.json", written)
        self.assertIn("coordinator-bundle-3.0.schema.json", written)


if __name__ == "__main__":
    unittest.main()
