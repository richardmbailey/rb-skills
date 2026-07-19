from __future__ import annotations

import json
import hashlib
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pydantic import ValidationError

from rb_safe_operation.audit import AuditError, AuditLog, build_event, redact
from rb_safe_operation.canonical import CanonicalizationError, artifact_hash, canonical_bytes, canonical_decimal, parse_json_strict
from rb_safe_operation.cli import cmd_assess, cmd_assess_preflight, cmd_coordinate, cmd_coordinate_resume, cmd_host_capabilities, cmd_persist_artifact
from rb_safe_operation.fakes import FakeAgentHost, FakeFilesystem, FakeSubprocess, Ledger
from rb_safe_operation.models import Approval, AssessmentBundle, DeterministicPreflight, EventPayload, Finding, HostCapabilities, ProjectPolicy, RepairAttempt, RunManifest
from rb_safe_operation.paths import PathViolation, resolve_contained
from rb_safe_operation.planning import COMMAND_CLASSIFICATIONS, PlanningError, classify_command, discover_instruction_files, select_markdown_phase, validate_continuity
from rb_safe_operation.policy import default_global_policy, effect_allowed, merge_policy
from rb_safe_operation.schemas import check_drift, export_schemas
from rb_safe_operation.state import StateError, acquire_lease, capture_snapshot, escalate_resume_drift, heartbeat_lease, release_lease, snapshot_materially_equal, transition
from rb_safe_operation.workflow import ExecutionCoordinator, ResourcePause, WorkflowError, assess_plan as runtime_assess_plan, begin_verification_context, canonical_semantic_proposal, deterministic_preflight, execute_fake, hash_ref, verify_reports

from helpers import capabilities, current_snapshot, effect, safe_plan, semantic, verification_proposal


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


class CanonicalTests(unittest.TestCase):
    def test_duplicate_and_normalized_keys_fail(self):
        with self.assertRaises(CanonicalizationError):
            parse_json_strict('{"a":1,"a":2}')
        with self.assertRaises(CanonicalizationError):
            parse_json_strict('{"é":1,"é":2}')

    def test_float_bom_and_surrogate_fail(self):
        for value in (b'\xef\xbb\xbf{}', '{"n":1.2}', '"\ud800"'):
            with self.assertRaises(CanonicalizationError):
                parse_json_strict(value)

    def test_fixed_canonical_and_hash_vectors(self):
        payload = {"z": "e\u0301\r\n", "a": True}
        self.assertEqual(canonical_bytes(payload), '{"a":true,"z":"é\\n"}'.encode())
        self.assertEqual(len(artifact_hash("test", "1.0", payload)), 64)
        self.assertNotEqual(artifact_hash("test", "1.0", payload), artifact_hash("other", "1.0", payload))

    def test_decimal_contract(self):
        self.assertEqual(canonical_decimal("12.3"), "12.3")
        for value in ("-0", "+1", "01", "1.0", "1e2"):
            with self.assertRaises(CanonicalizationError):
                canonical_decimal(value)

    def test_documented_host_capabilities_command_emits_accepted_canonical_profile(self):
        output = SimpleNamespace(buffer=io.BytesIO())
        with patch("sys.stdout", output):
            cmd_host_capabilities(SimpleNamespace(output=None))
        emitted = output.buffer.getvalue()
        profile = HostCapabilities.model_validate(parse_json_strict(emitted))
        self.assertEqual(profile, capabilities())
        self.assertEqual(emitted, canonical_bytes(profile.model_dump(mode="json")) + b"\n")


class ModelPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "input.txt").write_text("hello", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_unknown_plan_field_fails(self):
        data = safe_plan(self.root).model_dump(mode="json")
        data["unexpected"] = True
        with self.assertRaises(ValidationError):
            safe_plan(self.root).__class__.model_validate(data)

    def test_policy_merge_narrows(self):
        baseline = default_global_policy(str(self.root))
        project = ProjectPolicy(
            schema_version="1.0", deny_operations=["x"], deny_adapters=["exec_argv"], deny_effect_classes=[], deny_command_forms=[],
            intersect_path_roots=[str(self.root / "src")], intersect_executable_hashes=[], intersect_network_grants=[],
            intersect_environment_names=[], lower_maximums={"max_seconds": 10}, require_approvals=["custom"],
            require_minimum_enforcement={"verifier_read_only": "host_enforced"},
            require_minimum_observation={"product_state": "host_observed"}, require_evidence_sources=["extra"], require_verification=["extra-check"],
        )
        merged = merge_policy(baseline, project)
        self.assertEqual(merged.active_policy.allowed_path_roots, [str(self.root / "src")])
        self.assertEqual(merged.active_policy.limits.max_seconds, 10)
        self.assertIn("exec_argv", merged.active_policy.denied_adapters)
        self.assertGreaterEqual(len(merged.proof), 10)

    def test_policy_widening_fails(self):
        baseline = default_global_policy(str(self.root))
        project = ProjectPolicy(
            schema_version="1.0", deny_operations=[], deny_adapters=[], deny_effect_classes=[], deny_command_forms=[],
            intersect_path_roots=None, intersect_executable_hashes=None, intersect_network_grants=None,
            intersect_environment_names=None, lower_maximums={"max_seconds": baseline.limits.max_seconds + 1}, require_approvals=[],
            require_minimum_enforcement={}, require_minimum_observation={}, require_evidence_sources=[], require_verification=[],
        )
        with self.assertRaisesRegex(ValueError, "widening"):
            merge_policy(baseline, project)

    def test_effect_rows(self):
        policy = default_global_policy(str(self.root))
        allowed = safe_plan(self.root).operations[0].effects[0]
        self.assertTrue(effect_allowed(allowed, policy, set())[0])
        blocked = allowed.model_copy(update={"residual_severity": "high"})
        self.assertFalse(effect_allowed(blocked, policy, set())[0])
        review = allowed.model_copy(update={"residual_severity": "medium"})
        self.assertFalse(effect_allowed(review, policy, set())[0])
        self.assertTrue(effect_allowed(review, policy, {review.effect_id})[0])

    def test_cumulative_effect_cannot_understate_members(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["operations"][0]["effects"][0]["residual_severity"] = "medium"
        cumulative = dict(data["operations"][0]["effects"][0])
        cumulative.update({
            "effect_id": "effect-cumulative", "kind": "cumulative", "residual_severity": "medium",
            "cumulative_interaction": "amplifying", "cumulative_member_effect_ids": ["effect-read"],
        })
        data["operations"][0]["effects"].append(cumulative)
        with self.assertRaises(ValidationError):
            plan.__class__.model_validate(data)
        data["operations"][0]["effects"][1]["residual_severity"] = "high"
        self.assertEqual(plan.__class__.model_validate(data).operations[0].effects[1].residual_severity, "high")

    def test_duplicate_plan_evidence_and_semantic_finding_ids_fail(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["evidence"].append(dict(data["evidence"][0]))
        with self.assertRaisesRegex(ValidationError, "evidence IDs must be unique"):
            plan.__class__.model_validate(data)
        finding = Finding(
            finding_id="duplicate-finding", invariant_id="E-004", operation_ids=[], effect_ids=[],
            category="finding_identity", severity="high", evidence_ids=[],
            evidence_provenance=[], finding_provenance="agent_reported", explanation="x",
            remediation_or_human_decision="revise", blocking=True,
        )
        proposal = semantic(False).model_dump(mode="json")
        proposal["findings"] = [finding.model_dump(mode="json"), finding.model_dump(mode="json")]
        with self.assertRaisesRegex(ValidationError, "semantic finding IDs must be unique"):
            semantic(False).__class__.model_validate(proposal)

    def test_finding_severity_category_and_invariant_are_closed(self):
        base = {
            "finding_id": "finding-closed", "invariant_id": "E-004", "operation_ids": [], "effect_ids": [],
            "category": "finding_identity", "severity": "critical", "evidence_ids": [],
            "evidence_provenance": [], "finding_provenance": "agent_reported",
            "explanation": "bounded", "remediation_or_human_decision": "revise", "blocking": True,
        }
        for change in (
            {"invariant_id": "Z-999"}, {"category": "CANARY-CATEGORY"}, {"blocking": False},
        ):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                Finding.model_validate({**base, **change})

    def test_semantic_references_coverage_and_provenance_fail_closed(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        finding = Finding(
            finding_id="semantic-invalid-references", invariant_id="E-004",
            operation_ids=["unknown-operation"], effect_ids=["unknown-effect"],
            category="finding_identity", severity="high", evidence_ids=["unknown-evidence"],
            evidence_provenance=["host_observed"], finding_provenance="agent_reported",
            explanation="CANARY-REFERENCE-PROSE", remediation_or_human_decision="CANARY-REMEDIATION", blocking=True,
        )
        proposal = semantic().model_copy(update={
            "findings": [finding], "covered_evidence_ids": ["evidence-source", "CANARY-COVERAGE"],
        })
        assessment = runtime_assess_plan(
            plan, policy, policy, current_snapshot(plan), capabilities(), proposal, [],
        )
        self.assertFalse(assessment.safe)
        self.assertIn("semantic-reference-integrity", {item.finding_id for item in assessment.findings})
        self.assertNotIn("CANARY", canonical_bytes(assessment.model_dump(mode="json")).decode("utf-8"))

    def test_semantic_finding_cannot_shadow_deterministic_finding(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        forged = capabilities().model_copy(update={"complete_child_trace": True})
        colliding = Finding(
            finding_id="identity-host-capabilities", invariant_id="E-004", operation_ids=[], effect_ids=[],
            category="plan_fidelity", severity="high", evidence_ids=["evidence-source"],
            evidence_provenance=["coordinator_observed"], finding_provenance="agent_reported", explanation="attempted shadow",
            remediation_or_human_decision="revise", blocking=True,
        )
        proposal = semantic(False).model_copy(update={"findings": [colliding]})
        assessment = runtime_assess_plan(
            plan, policy, policy, current_snapshot(plan), forged, proposal, [],
        )
        self.assertFalse(assessment.safe)
        self.assertEqual(assessment.findings[0].finding_id, "identity-host-capabilities")
        self.assertRegex(assessment.findings[1].finding_id, r"^finding-[0-9a-f]{32}$")
        self.assertNotEqual(assessment.findings[0].finding_id, assessment.findings[1].finding_id)

    def test_forged_host_enforcement_capabilities_cannot_authorize(self):
        plan = safe_plan(self.root)
        forged = capabilities().model_copy(update={
            "profile": "strict_isolation", "role_read_only": "host_enforced",
            "product_state_observation": "host_observed", "complete_child_trace": True,
            "atomic_path_enforcement": True, "bounded_resource_enforcement": "host_enforced",
            "fresh_context_enforcement": "host_enforced",
        })
        result = assess_plan(plan, default_global_policy(str(self.root)), forged, semantic(), [])
        self.assertFalse(result.safe)
        self.assertEqual(result.profile, "semi_formal")
        self.assertIn("unsupported_host_capability", {item.category for item in result.findings})

    def test_cumulative_effect_graph_rejects_self_duplicate_and_cycle(self):
        plan = safe_plan(self.root)
        base = plan.model_dump(mode="json")
        member = dict(base["operations"][0]["effects"][0])

        self_member = dict(member)
        self_member.update({
            "effect_id": "effect-self", "kind": "cumulative", "residual_severity": "medium",
            "cumulative_interaction": "additive", "cumulative_member_effect_ids": ["effect-self"],
        })
        self_data = plan.model_dump(mode="json")
        self_data["operations"][0]["effects"].append(self_member)
        with self.assertRaisesRegex(ValidationError, "cannot include itself"):
            plan.__class__.model_validate(self_data)

        duplicate = dict(self_member)
        duplicate.update({"effect_id": "effect-duplicate", "cumulative_member_effect_ids": ["effect-read", "effect-read"]})
        duplicate_data = plan.model_dump(mode="json")
        duplicate_data["operations"][0]["effects"].append(duplicate)
        with self.assertRaisesRegex(ValidationError, "duplicate members"):
            plan.__class__.model_validate(duplicate_data)

        first = dict(self_member)
        first.update({"effect_id": "effect-cycle-a", "cumulative_member_effect_ids": ["effect-cycle-b"]})
        second = dict(self_member)
        second.update({"effect_id": "effect-cycle-b", "cumulative_member_effect_ids": ["effect-cycle-a"]})
        cycle_data = plan.model_dump(mode="json")
        cycle_data["operations"][0]["effects"].extend([first, second])
        with self.assertRaisesRegex(ValidationError, "contains a cycle"):
            plan.__class__.model_validate(cycle_data)

    def test_assessment_safe_and_unsafe(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        safe = assess_plan(plan, policy, capabilities(), semantic(), [])
        self.assertTrue(safe.safe)
        data = plan.model_dump(mode="json")
        data["operations"][0]["effects"][0]["residual_severity"] = "high"
        unsafe_plan = plan.__class__.model_validate(data)
        unsafe = assess_plan(unsafe_plan, policy, capabilities(), semantic(), [])
        self.assertFalse(unsafe.safe)
        self.assertEqual(unsafe.status, "rejected")

    def test_exact_current_approval_allows_review_effect(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["operations"][0]["effects"][0]["residual_severity"] = "medium"
        data["operations"][0]["effects"][0]["approval_class"] = "privacy_sensitive"
        plan = plan.__class__.model_validate(data)
        operation = plan.operations[0]
        approval = Approval(
            approval_id="approval-1", plan_hash=hash_ref("low-level-plan", plan.model_dump(mode="json")),
            operation_hash=hash_ref("operation", operation.model_dump(mode="json")), effect_id="effect-read",
            policy_hash=plan.merged_policy_hash, snapshot_hash=hash_ref("repository-snapshot", plan.snapshot.model_dump(mode="json")),
            effect_class="repository_read", approval_class="privacy_sensitive", target=str(self.root / "input.txt"),
            expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"), one_use=True, consumed=False,
            idempotency_key="key-1", principal=None, identity_verification="unavailable",
        )
        assessment = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [approval])
        self.assertTrue(assessment.safe)
        stale = approval.model_copy(update={"expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")})
        self.assertFalse(assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [stale]).safe)

        duplicate_id = approval.model_copy(update={"target": str(self.root / "other.txt")})
        duplicate_result = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [approval, duplicate_id])
        self.assertFalse(duplicate_result.safe)
        self.assertIn("approval-identity-duplicate", {item.finding_id for item in duplicate_result.findings})
        with self.assertRaises(ValidationError):
            Approval.model_validate({**approval.model_dump(mode="json"), "identity_verification": "host_verified"})

    def test_mandatory_approval_classes_are_derived_not_planner_selected(self):
        policy = default_global_policy(str(self.root))
        for change, required_class in (
            ({"effect_class": "repository_delete"}, "destructive"),
            ({"data_classification": "personal", "approval_class": "rubber_stamp"}, "privacy_sensitive"),
            ({"cost_impact": "medium", "approval_class": "rubber_stamp"}, "material_cost"),
            ({"security_sensitive": True, "approval_class": "rubber_stamp"}, "security_sensitive"),
            ({"reversibility": "none", "approval_class": "rubber_stamp"}, "irreversible"),
        ):
            plan = safe_plan(self.root)
            data = plan.model_dump(mode="json")
            data["operations"][0]["effects"][0].update(change)
            plan = plan.__class__.model_validate(data)
            approvals = []
            if change.get("approval_class") == "rubber_stamp":
                operation = plan.operations[0]
                approvals = [Approval(
                    approval_id=f"rubber-{required_class}",
                    plan_hash=hash_ref("low-level-plan", plan.model_dump(mode="json")),
                    operation_hash=hash_ref("operation", operation.model_dump(mode="json")),
                    policy_hash=plan.merged_policy_hash,
                    snapshot_hash=hash_ref("repository-snapshot", plan.snapshot.model_dump(mode="json")),
                    effect_id=operation.effects[0].effect_id, effect_class=operation.effects[0].effect_class,
                    approval_class="rubber_stamp", target=str(self.root / "input.txt"),
                    expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    one_use=True, consumed=False, idempotency_key="bounded", principal=None,
                    identity_verification="unavailable",
                )]
            result = assess_plan(plan, policy, capabilities(), semantic(), approvals)
            self.assertFalse(result.safe)
            self.assertTrue(any(
                item.category == "approval_scope" and required_class in item.explanation
                for item in result.findings
            ), required_class)

    def test_effect_evidence_provenance_and_detectability_are_consistent(self):
        plan = safe_plan(self.root)
        for update in (
            {"observation_sources": []},
            {"observation_sources": ["host_observed"]},
        ):
            data = plan.model_dump(mode="json")
            data["operations"][0]["effects"][0].update(update)
            with self.subTest(update=update), self.assertRaises(ValidationError):
                plan.__class__.model_validate(data)

        data = plan.model_dump(mode="json")
        data["evidence"][0]["provenance"] = "agent_reported"
        data["evidence"][0]["locator"] = "agent-report:evidence-source"
        data["operations"][0]["effects"][0]["observation_sources"] = ["agent_reported"]
        with self.assertRaisesRegex(ValidationError, "overstates detectability"):
            plan.__class__.model_validate(data)

    def test_plan_evidence_cannot_forge_host_or_unbound_coordinator_provenance(self):
        plan = safe_plan(self.root)
        for provenance, locator, message in (
            ("host_observed", str(self.root / "input.txt"), "cannot claim host_observed"),
            ("coordinator_observed", str(self.root / "not-in-snapshot.txt"), "snapshot-bound locator"),
            ("agent_reported", str(self.root / "input.txt"), "structural agent-report locator"),
        ):
            data = plan.model_dump(mode="json")
            data["evidence"][0].update({"provenance": provenance, "locator": locator})
            data["operations"][0]["effects"][0]["observation_sources"] = [provenance]
            if provenance == "agent_reported":
                data["operations"][0]["effects"][0]["detectability"] = "weak"
            with self.subTest(provenance=provenance), self.assertRaisesRegex(ValidationError, message):
                plan.__class__.model_validate(data)

    def test_strict_profile_fails_capability_gate(self):
        assessment = assess_plan(safe_plan(self.root), default_global_policy(str(self.root)), capabilities("strict_isolation"), semantic(), [])
        self.assertFalse(assessment.safe)
        self.assertIn("unsupported_host_capability", {item.category for item in assessment.findings})

    def test_concrete_targets_effects_and_merged_requirements_fail_closed(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        data = plan.model_dump(mode="json")
        data["operations"][0]["effects"][0]["targets"] = [str(self.root / "other.txt")]
        mismatched = plan.__class__.model_validate(data)
        result = assess_plan(mismatched, policy, capabilities(), semantic(), [])
        self.assertFalse(result.safe)
        self.assertIn("effect_inventory", {item.category for item in result.findings})

        project = ProjectPolicy(
            schema_version="1.0", deny_operations=[], deny_adapters=[], deny_effect_classes=[], deny_command_forms=[],
            intersect_path_roots=None, intersect_executable_hashes=None, intersect_network_grants=None,
            intersect_environment_names=None, lower_maximums={}, require_approvals=[],
            require_minimum_enforcement={}, require_minimum_observation={},
            require_evidence_sources=["unsupported-source"], require_verification=["unsupported-check"],
        )
        narrowed = merge_policy(policy, project).active_policy
        data = plan.model_dump(mode="json")
        data["merged_policy_hash"] = hash_ref("active-policy", narrowed.model_dump(mode="json")).model_dump(mode="json")
        narrowed_plan = plan.__class__.model_validate(data)
        result = assess_plan(narrowed_plan, narrowed, capabilities(), semantic(), [])
        self.assertFalse(result.safe)
        self.assertTrue({"missing_evidence", "incomplete_verification"}.issubset({item.category for item in result.findings}))

    def test_bounded_executables_without_hash_binding_are_rejected(self):
        plan = safe_plan(self.root, include_bounded=True)
        data = plan.model_dump(mode="json")
        data["operations"][1]["allowed_executables"] = {"/usr/bin/git": [["/usr/bin/git", "status"]]}
        with self.assertRaisesRegex(ValidationError, "identical keys"):
            plan.__class__.model_validate(data)

    def test_operation_policy_and_bounded_evidence_references_are_closed(self):
        plan = safe_plan(self.root, include_bounded=True)
        for operation_index, field, value, message in (
            (0, "policy_references", ["UNKNOWN-999"], "unknown policy references"),
            (1, "evidence_ids", ["unknown-evidence"], "unknown plan evidence IDs"),
        ):
            data = plan.model_dump(mode="json")
            data["operations"][operation_index][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(ValidationError, message):
                plan.__class__.model_validate(data)

    def test_duplicate_collections_and_patch_action_collisions_reject_at_model_boundary(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["operations"][0]["path_contract"]["read_roots"].append(
            data["operations"][0]["path_contract"]["read_roots"][0]
        )
        with self.assertRaisesRegex(ValidationError, "values must be unique"):
            plan.__class__.model_validate(data)

        patch = "--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-hello\n+changed\n"
        data = plan.model_dump(mode="json")
        operation = data["operations"][0]
        operation.update({
            "adapter": "apply_patch", "patch": patch, "patch_hash": hashlib.sha256(patch.encode()).hexdigest(),
            "preimage_hashes": {str(self.root / "input.txt"): hashlib.sha256((self.root / "input.txt").read_bytes()).hexdigest()},
            "expected_created_paths": [str(self.root / "input.txt")],
            "expected_modified_paths": [str(self.root / "input.txt")], "expected_deleted_paths": [],
        })
        for key in ("path", "byte_start", "byte_end", "expected_hash"):
            operation.pop(key)
        with self.assertRaisesRegex(ValidationError, "must be disjoint"):
            plan.__class__.model_validate(data)

    def test_omitted_applicable_instruction_is_rejected(self):
        (self.root / "AGENTS.md").write_text("Do not read input.txt", encoding="utf-8")
        plan = safe_plan(self.root)
        self.assertEqual(plan.snapshot.instruction_hashes, {})
        result = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [])
        self.assertFalse(result.safe)
        self.assertIn("instruction_scope", {item.category for item in result.findings})


class PathStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "inside.txt").write_text("ok", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_containment_and_protection(self):
        self.assertEqual(resolve_contained(str(self.root / "inside.txt"), [str(self.root)], []).resolved, str(self.root / "inside.txt"))
        with self.assertRaises(PathViolation):
            resolve_contained(str(self.root / ".." / "escape"), [str(self.root)], [])
        with self.assertRaises(PathViolation):
            resolve_contained(str(self.root / "inside.txt"), [str(self.root)], [str(self.root / "inside.txt")], mutation=True)

    def test_symlink_escape_fails(self):
        outside = Path(self.temporary.name).parent / "outside-rb-safe-test"
        outside.mkdir(exist_ok=True)
        link = self.root / "link"
        link.symlink_to(outside)
        try:
            with self.assertRaises(PathViolation):
                resolve_contained(str(link / "x"), [str(self.root)], [])
        finally:
            link.unlink()
            outside.rmdir()

    def test_snapshot_and_lease(self):
        snapshot = capture_snapshot(str(self.root), ["inside.txt"], [], [])
        lease = acquire_lease(str(self.root), "run", snapshot.device_identity, None)
        with self.assertRaises(StateError):
            acquire_lease(str(self.root), "other", snapshot.device_identity, None)
        heartbeat_lease(lease)
        release_lease(lease)
        self.assertFalse(lease.path.exists())

    def test_non_git_snapshot_detects_unselected_file(self):
        before = capture_snapshot(str(self.root), ["inside.txt"], [], [])
        (self.root / "UNDECLARED.txt").write_text("unexpected", encoding="utf-8")
        after = capture_snapshot(str(self.root), ["inside.txt"], [], [])
        equal, differences = snapshot_materially_equal(before, after)
        self.assertFalse(equal)
        self.assertIn("full_file_inventory", differences)

    def test_snapshot_path_semantics_metadata_is_material(self):
        snapshot = capture_snapshot(str(self.root), ["inside.txt"], [], [])
        for field, value in (
            ("platform", snapshot.platform + "-changed"),
            ("case_sensitive", not snapshot.case_sensitive),
            ("unicode_normalization", "NFD"),
        ):
            changed = snapshot.model_copy(update={field: value})
            equal, differences = snapshot_materially_equal(snapshot, changed)
            self.assertFalse(equal)
            self.assertIn(field, differences)

    def test_git_observation_failure_is_explicit(self):
        (self.root / ".git").mkdir()
        with self.assertRaisesRegex(StateError, "Git observation failed"):
            capture_snapshot(str(self.root), ["inside.txt"], [], [])

    def test_git_snapshot_disables_repository_fsmonitor_execution(self):
        git = Path("/usr/bin/git")
        if not git.is_file():
            self.skipTest("fixed Git executable unavailable")
        repository = self.root / "git-project"
        repository.mkdir()
        subprocess.run([str(git), "init", str(repository)], check=True, capture_output=True)
        marker = self.root / "fsmonitor-ran"
        hook = repository / "fsmonitor-hook"
        hook.write_text(f"#!/bin/sh\ntouch '{marker}'\nprintf '0\\n'\n", encoding="utf-8")
        hook.chmod(0o700)
        subprocess.run([str(git), "-C", str(repository), "config", "core.fsmonitor", str(hook)], check=True)
        (repository / "tracked.txt").write_text("value", encoding="utf-8")
        subprocess.run([str(git), "-C", str(repository), "add", "tracked.txt"], check=True)
        subprocess.run(
            [str(git), "-C", str(repository), "-c", "user.name=Snapshot Test", "-c", "user.email=snapshot@example.invalid", "commit", "-m", "initial"],
            check=True, capture_output=True,
        )
        marker.unlink(missing_ok=True)
        capture_snapshot(str(repository), ["tracked.txt"], [], [])
        self.assertFalse(marker.exists())

    def test_git_porcelain_preserves_unstaged_status_and_whitespace_filename(self):
        git = Path("/usr/bin/git")
        if not git.is_file():
            self.skipTest("fixed Git executable unavailable")
        repository = self.root / "git-status-project"
        repository.mkdir()
        subprocess.run([str(git), "init", str(repository)], check=True, capture_output=True)
        tracked = repository / " leading space.txt"
        tracked.write_text("before", encoding="utf-8")
        subprocess.run([str(git), "-C", str(repository), "add", " leading space.txt"], check=True)
        subprocess.run(
            [str(git), "-C", str(repository), "-c", "user.name=Snapshot Test", "-c", "user.email=snapshot@example.invalid", "commit", "-m", "initial"],
            check=True, capture_output=True,
        )
        tracked.write_text("after", encoding="utf-8")
        snapshot = capture_snapshot(str(repository), [str(tracked)], [], [])
        self.assertEqual(set(snapshot.unstaged_paths), {" leading space.txt"})
        self.assertEqual(snapshot.staged_paths, {})

    def test_product_symlink_to_control_root_is_inventoried_as_drift(self):
        control = self.root / ".rb-safe-operation"
        control.mkdir()
        before = capture_snapshot(str(self.root), ["inside.txt"], [], [], [str(control)])
        (self.root / "product-control-link").symlink_to(control, target_is_directory=True)
        after = capture_snapshot(str(self.root), ["inside.txt"], [], [], [str(control)])
        equal, differences = snapshot_materially_equal(before, after)
        self.assertFalse(equal)
        self.assertIn("full_file_inventory", differences)
        self.assertTrue(after.full_file_inventory["product-control-link"].startswith("symlink:"))

    def test_lifecycle(self):
        manifest = RunManifest(schema_version="1.0", run_id="r", state="drafting", suspended_from=None, plan_hash=None, assessment_hash=None, policy_hash=None, snapshot_hash=None, event_head_hash=None)
        manifest = transition(manifest, "validating", ["e"])
        manifest = transition(manifest, "approved", ["e"])
        manifest = transition(manifest, "executing", ["e"])
        paused = transition(manifest, "paused_resource", ["e"])
        self.assertEqual(paused.suspended_from, "executing")
        resumed = transition(paused, "executing", ["e"], resumed_state="executing")
        self.assertIsNone(resumed.suspended_from)
        with self.assertRaises(StateError):
            transition(resumed, "verified", ["e"])

    def test_phase_selection_instructions_and_continuity(self):
        plan = self.root / "PLAN.md"
        plan.write_text("# Plan\n\n## Summary\nOverview.\n\n## Phase 1: First\nDo one.\n\n## Phase 2: Second\nDo two.\n\n## Risks\nNone.\n", encoding="utf-8")
        (self.root / "AGENTS.md").write_text("root", encoding="utf-8")
        nested = self.root / "src"
        nested.mkdir()
        (nested / "AGENTS.md").write_text("nested", encoding="utf-8")
        selection = select_markdown_phase(str(plan), "1")
        self.assertEqual(selection.source.phase_id, "phase-1")
        self.assertEqual(selection.later_phase_ids, ["phase-2"])
        with self.assertRaises(PlanningError):
            select_markdown_phase(str(plan), "risks")
        self.assertEqual(len(discover_instruction_files(str(self.root), [str(nested / "file.py")])), 2)
        validate_continuity("phase-1", selection.later_phase_ids, ["phase-1", "phase-2"])
        with self.assertRaises(PlanningError):
            validate_continuity("phase-1", [], ["phase-1", "phase-2"])

    def test_phase_selection_ignores_fenced_phase_headings(self):
        plan = self.root / "FENCED.md"
        plan.write_text(
            "## Phase 1: First\nSafety-critical A.\n\n```markdown\n## Phase 99: Example\n```\n\nSafety-critical B.\n\n## Phase 2: Second\nLater.\n",
            encoding="utf-8",
        )
        selection = select_markdown_phase(str(plan), "1")
        self.assertIn("Safety-critical B.", selection.source.selected_text)
        self.assertEqual(selection.later_phase_ids, ["phase-2"])

    def test_transitive_command_classification(self):
        self.assertIn("shell", classify_command("/bin/bash", ["/bin/bash", "-c", "echo x"], True))
        self.assertIn("inline_interpreter", classify_command("/usr/bin/python3", ["/usr/bin/python3", "-c", "print(1)"], True))
        self.assertIn("task_runner_or_package_script", classify_command("/usr/bin/npm", ["npm", "test"], True))
        self.assertIn("dynamic_module", classify_command("/usr/bin/python3", ["/usr/bin/python3", "-m", "arbitrary_module"], True))
        self.assertEqual(set(default_global_policy(str(self.root)).denied_command_forms), set(COMMAND_CLASSIFICATIONS))


class AuditFakeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "input.txt").write_text("hello", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_audit_chain_redacts_and_detects_corruption(self):
        log = AuditLog(str(self.root / "audit"), "run")
        payload = EventPayload(event_type="start", lifecycle_from="drafting", lifecycle_to="validating", operation_id=None, summary="start", evidence_ids=["e"])
        first = log.append(payload, "coordinator_observed", {"api_token": "canary", "safe": "yes"})
        self.assertNotIn("canary", (self.root / "audit").read_text() if (self.root / "audit").is_file() else json.dumps(first.model_dump(mode="json")))
        second = log.append(payload, "agent_reported", {"result": "ok"})
        self.assertEqual(second.previous_event_record_hash, first.event_record_hash)
        path = sorted((self.root / "audit").glob("*.json"))[1]
        data = json.loads(path.read_text())
        data["observation"]["data"]["result"] = "changed"
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(AuditError):
            log.validate_chain()

    def test_unsafe_never_calls_product_fake(self):
        ledger = Ledger()
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["operations"][0]["effects"][0]["residual_severity"] = "critical"
        plan = plan.__class__.model_validate(data)
        assessment = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [])
        with self.assertRaises(WorkflowError):
            execute_fake(plan, assessment, FakeFilesystem(ledger, {str(self.root / "input.txt"): b"hello"}), FakeSubprocess(ledger, set()))
        ledger.assert_no("filesystem")
        ledger.assert_no("subprocess")

    def test_safe_exact_and_bounded_reaches_verification(self):
        ledger = Ledger()
        plan = safe_plan(self.root, include_bounded=True)
        assessment = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [])
        agent = FakeAgentHost(ledger, [{
            "schema_version": "1.0", "operation_id": "task-1", "success": True, "evidence": [{"evidence_id":"completion-task-1","provenance":"agent_reported","locator":"agent-report:completion-task-1","summary":"complete"}],
            "expected_effect_ids_observed": ["effect-task"], "unexpected_effects": [], "next_strategy": None,
        }])
        reports = execute_fake(plan, assessment, FakeFilesystem(ledger, {str(self.root / "input.txt"): b"hello"}), FakeSubprocess(ledger, set()), agent)
        context = begin_verification_context(plan, assessment, "fresh-verifier-1", current_snapshot(plan))
        verification = verify_reports(plan, assessment, reports, verification_proposal(plan, assessment, context), context)
        self.assertTrue(verification.verified)
        self.assertEqual([item["role"] for item in ledger.entries if item["capability"] == "agent"], ["executor"])

    def test_schema_export_and_drift(self):
        expected = self.root / "schemas"
        runtime = Path(__file__).resolve().parents[1]
        export_schemas(expected, runtime)
        generated = self.root / "generated"
        export_schemas(generated, runtime)
        self.assertEqual(check_drift(expected, generated), [])
        file = next(generated.glob("*.json"))
        file.write_text("{}", encoding="utf-8")
        self.assertEqual(len(check_drift(expected, generated)), 1)

    def test_real_apply_patch_adapter(self):
        target = self.root / "input.txt"
        target.write_text("hello\n", encoding="utf-8")
        original = target.read_bytes()
        patch = "diff --git a/input.txt b/input.txt\n--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-hello\n+changed\n"
        base = safe_plan(self.root)
        data = base.model_dump(mode="json")
        common = data["operations"][0]
        common.update({
            "kind": "exact_action", "adapter": "apply_patch", "patch": patch,
            "patch_hash": hashlib.sha256(patch.encode()).hexdigest(),
            "preimage_hashes": {str(target): hashlib.sha256(original).hexdigest()},
            "expected_created_paths": [], "expected_modified_paths": [str(target)], "expected_deleted_paths": [],
        })
        for key in ("path", "byte_start", "byte_end", "expected_hash"):
            common.pop(key)
        common["path_contract"]["modify_roots"] = [str(self.root)]
        common["effects"][0]["effect_class"] = "repository_modify"
        plan = base.__class__.model_validate(data)
        assessment = assess_plan(plan, default_global_policy(str(self.root)), capabilities(), semantic(), [])
        self.assertTrue(assessment.safe)
        policy = default_global_policy(str(self.root))
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        reports = coordinator.execute()
        coordinator.abandon()
        self.assertTrue(reports[0].success)
        self.assertEqual(target.read_text(encoding="utf-8"), "changed\n")

    def test_first_release_rejects_locally_widened_exec_and_check_adapters(self):
        executable = Path(shutil.which("true") or "/usr/bin/true").resolve(strict=True)
        executable_hash = hashlib.sha256(executable.read_bytes()).hexdigest()
        for adapter in ("exec_argv", "check"):
            base = safe_plan(self.root)
            data = base.model_dump(mode="json")
            data["run_id"] = f"run-{adapter}"
            data["plan_id"] = f"plan-{adapter}"
            operation = data["operations"][0]
            operation.update({
                "kind": "exact_action", "adapter": adapter, "executable_path": str(executable),
                "executable_hash": executable_hash, "argv": [str(executable)], "input_hashes": {},
                "child_processes_declared": True,
            })
            if adapter == "check":
                operation.update({"expected_exit_codes": [0], "declared_generated_paths": []})
            for key in ("path", "byte_start", "byte_end", "expected_hash"):
                operation.pop(key)
            operation["effects"][0]["effect_class"] = "local_process"
            operation["effects"][0]["targets"] = [str(executable)]
            plan = base.__class__.model_validate(data)
            policy = default_global_policy(str(self.root)).model_copy(update={"allowed_executable_hashes": [executable_hash]})
            plan_data = plan.model_dump(mode="json")
            plan_data["merged_policy_hash"] = hash_ref("active-policy", policy.model_dump(mode="json")).model_dump(mode="json")
            plan = plan.__class__.model_validate(plan_data)
            assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
            self.assertFalse(assessment.safe)
            self.assertIn("policy_widening", {item.category for item in assessment.findings})
            with self.assertRaises(WorkflowError):
                ExecutionCoordinator(plan, assessment, default_global_policy(str(self.root)), policy, capabilities(), semantic())

    def test_hashed_python_check_is_rejected_without_capability_sandbox(self):
        executable = Path(os.path.realpath(os.sys.executable))
        script = self.root / "check_script.py"
        script.write_text("from pathlib import Path\nassert Path(__file__).with_name('input.txt').read_text() == 'hello'\n", encoding="utf-8")
        base = safe_plan(self.root)
        data = base.model_dump(mode="json")
        operation = data["operations"][0]
        operation.update({
            "kind": "exact_action", "adapter": "check", "executable_path": str(executable),
            "executable_hash": hashlib.sha256(executable.read_bytes()).hexdigest(),
            "argv": [str(executable), "-I", "-B", str(script)],
            "input_hashes": {
                str(script): hashlib.sha256(script.read_bytes()).hexdigest(),
                str(self.root / "input.txt"): hashlib.sha256((self.root / "input.txt").read_bytes()).hexdigest(),
            },
            "expected_exit_codes": [0], "declared_generated_paths": [], "child_processes_declared": False,
        })
        for key in ("path", "byte_start", "byte_end", "expected_hash"):
            operation.pop(key)
        operation["effects"] = [
            effect("effect-check-read", "repository_read", targets=[str(script), str(self.root / "input.txt")]),
            effect("effect-check-process", "local_process", targets=[str(executable)]),
        ]
        policy = default_global_policy(str(self.root))
        data["global_policy_hash"] = hash_ref("active-policy", policy.model_dump(mode="json")).model_dump(mode="json")
        data["merged_policy_hash"] = data["global_policy_hash"]
        plan = base.__class__.model_validate(data)
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        self.assertFalse(assessment.safe)
        self.assertIn("transitive_execution", {item.category for item in assessment.findings})

    def test_high_risk_repair_gate(self):
        base = {
            "schema_version": "1.0", "attempt_id": "a", "finding_id": "f", "hypothesis": "h",
            "observed_result": "r", "reconsidered_assumption": "a", "materially_different_next_strategy": "s",
            "high_risk_replay": True, "fresh_idempotency_proof": None, "approval_id": None,
        }
        with self.assertRaises(ValidationError):
            RepairAttempt.model_validate(base)
        base.update({"fresh_idempotency_proof": "proof", "approval_id": "approval"})
        self.assertTrue(RepairAttempt.model_validate(base).high_risk_replay)


class SecurityRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name).resolve()
        (self.root / "input.txt").write_text("hello", encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def _review_plan_and_approval(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        effect_data = data["operations"][0]["effects"][0]
        effect_data["residual_severity"] = "medium"
        effect_data["approval_class"] = "privacy_sensitive"
        plan = plan.__class__.model_validate(data)
        operation = plan.operations[0]
        approval = Approval(
            approval_id="approval-review",
            plan_hash=hash_ref("low-level-plan", plan.model_dump(mode="json")),
            operation_hash=hash_ref("operation", operation.model_dump(mode="json")),
            policy_hash=plan.merged_policy_hash,
            snapshot_hash=hash_ref("repository-snapshot", plan.snapshot.model_dump(mode="json")),
            effect_id=operation.effects[0].effect_id,
            effect_class=operation.effects[0].effect_class,
            approval_class="privacy_sensitive",
            target=str(self.root / "input.txt"),
            expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            one_use=True,
            consumed=False,
            idempotency_key=None,
            principal=None,
            identity_verification="unavailable",
        )
        return plan, approval

    def test_run_and_approval_control_components_reject_symlink_redirection(self):
        policy = default_global_policy(str(self.root))
        plan = safe_plan(self.root)
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        control = self.root / ".rb-safe-operation"
        control.mkdir()
        outside_runs = control / "redirected-runs"
        outside_runs.mkdir()
        (control / "runs").symlink_to(outside_runs, target_is_directory=True)
        with self.assertRaisesRegex(WorkflowError, "symbolic link"):
            ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        self.assertEqual(list(outside_runs.iterdir()), [])
        self.assertFalse((control / "execution.lease").exists())

        (control / "runs").unlink()
        plan, approval = self._review_plan_and_approval()
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [approval])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        outside_approvals = control / "redirected-approvals"
        outside_approvals.mkdir()
        (control / "approvals").symlink_to(outside_approvals, target_is_directory=True)
        with self.assertRaisesRegex(WorkflowError, "symbolic link"):
            coordinator.execute()
        self.assertEqual(list(outside_approvals.iterdir()), [])
        self.assertFalse((control / "execution.lease").exists())

    def test_policy_source_and_snapshot_identity_drift_reject(self):
        policy = default_global_policy(str(self.root))
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["merged_policy_hash"]["value"] = "f" * 64
        mismatched_policy = plan.__class__.model_validate(data)
        self.assertFalse(assess_plan(mismatched_policy, policy, capabilities(), semantic(), []).safe)

        plan = safe_plan(self.root)
        Path(plan.source_phase.plan_path).write_text("# Plan\n\n## Phase 1: Changed\nChanged.\n", encoding="utf-8")
        source_drift = assess_plan(plan, policy, capabilities(), semantic(), [])
        self.assertFalse(source_drift.safe)
        self.assertIn("artifact_identity", {item.category for item in source_drift.findings})

        plan = safe_plan(self.root)
        changed = plan.snapshot.model_copy(update={"untracked_paths": {"new.txt": "a" * 64}})
        equal, differences = snapshot_materially_equal(plan.snapshot, changed)
        self.assertFalse(equal)
        self.assertIn("untracked_paths", differences)

    def test_approval_target_class_and_required_class_are_exact(self):
        plan, approval = self._review_plan_and_approval()
        policy = default_global_policy(str(self.root))
        wrong_target = approval.model_copy(update={"target": str(self.root / "other.txt")})
        self.assertFalse(assess_plan(plan, policy, capabilities(), semantic(), [wrong_target]).safe)
        wrong_class = approval.model_copy(update={"approval_class": "security_sensitive"})
        self.assertFalse(assess_plan(plan, policy, capabilities(), semantic(), [wrong_class]).safe)
        self.assertTrue(assess_plan(plan, policy, capabilities(), semantic(), [approval]).safe)
        duplicate = approval.model_copy(update={"approval_id": "approval-duplicate"})
        self.assertFalse(assess_plan(plan, policy, capabilities(), semantic(), [approval, duplicate]).safe)

        extra = approval.model_copy(update={"approval_id": "approval-extra", "target": str(self.root / "other.txt")})
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [approval, extra])
        self.assertTrue(assessment.safe)
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.execute()
        approval_root = Path(plan.snapshot.control_plane_roots[0]) / "approvals" / plan.run_id
        self.assertTrue((approval_root / "approval-review.consumed").is_file())
        self.assertFalse((approval_root / "approval-extra.consumed").exists())
        coordinator.abandon()

        low_data = safe_plan(self.root).model_dump(mode="json")
        low_data["operations"][0]["effects"][0]["approval_class"] = "privacy_sensitive"
        low_plan = plan.__class__.model_validate(low_data)
        self.assertFalse(assess_plan(low_plan, policy, capabilities(), semantic(), []).safe)

    def test_caller_cannot_replace_immutable_global_policy(self):
        plan = safe_plan(self.root)
        baseline = default_global_policy(str(self.root))
        widened = baseline.model_copy(update={"allowed_executable_hashes": ["f" * 64]})
        data = plan.model_dump(mode="json")
        widened_hash = hash_ref("active-policy", widened.model_dump(mode="json")).model_dump(mode="json")
        data["global_policy_hash"] = widened_hash
        data["merged_policy_hash"] = widened_hash
        forged_plan = plan.__class__.model_validate(data)
        result = runtime_assess_plan(
            forged_plan, widened, widened, current_snapshot(forged_plan), capabilities(), semantic(), []
        )
        self.assertFalse(result.safe)
        self.assertIn("identity-global-policy-source", {item.finding_id for item in result.findings})

    def test_mismatched_assessment_cannot_mutate(self):
        approved_plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(approved_plan, policy, capabilities(), semantic(), [])
        target = self.root / "input.txt"
        patch = "diff --git a/input.txt b/input.txt\n--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-hello\n+changed\n"
        data = approved_plan.model_dump(mode="json")
        operation = data["operations"][0]
        operation.update({
            "kind": "exact_action", "adapter": "apply_patch", "patch": patch,
            "patch_hash": hashlib.sha256(patch.encode()).hexdigest(),
            "preimage_hashes": {str(target): hashlib.sha256(target.read_bytes()).hexdigest()},
            "expected_created_paths": [], "expected_modified_paths": [str(target)], "expected_deleted_paths": [],
        })
        for key in ("path", "byte_start", "byte_end", "expected_hash"):
            operation.pop(key)
        operation["path_contract"]["modify_roots"] = [str(self.root)]
        operation["effects"][0]["effect_class"] = "repository_modify"
        changed_plan = approved_plan.__class__.model_validate(data)
        with self.assertRaisesRegex(WorkflowError, "plan identity"):
            ExecutionCoordinator(changed_plan, assessment, policy, policy, capabilities(), semantic())
        self.assertEqual(target.read_text(encoding="utf-8"), "hello")

    def test_model_copy_cannot_forge_rejected_assessment(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        rejected = assess_plan(plan, policy, capabilities(), semantic(False), [])
        forged = rejected.model_copy(update={"safe": True})
        with self.assertRaises((WorkflowError, ValidationError)):
            ExecutionCoordinator(plan, forged, policy, policy, capabilities(), semantic())
        self.assertFalse((self.root / ".rb-safe-operation" / "execution.lease").exists())

    def test_verification_requires_safe_bound_complete_proposal(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        report = execute_fake(
            plan, assessment,
            FakeFilesystem(Ledger(), {str(self.root / "input.txt"): b"hello"}),
            FakeSubprocess(Ledger(), set()),
        )[0]
        context = begin_verification_context(plan, assessment, "fresh-security-verifier", current_snapshot(plan))
        proposal = verification_proposal(plan, assessment, context).model_copy(update={"success_criteria_met": []})
        self.assertFalse(verify_reports(plan, assessment, [report], proposal, context).verified)

        unsafe_data = plan.model_dump(mode="json")
        unsafe_data["operations"][0]["effects"][0]["residual_severity"] = "critical"
        unsafe_plan = plan.__class__.model_validate(unsafe_data)
        rejected = assess_plan(unsafe_plan, policy, capabilities(), semantic(), [])
        with self.assertRaises(WorkflowError):
            begin_verification_context(unsafe_plan, rejected, "forged", current_snapshot(unsafe_plan))

    def test_verifier_cannot_promote_agent_evidence_provenance(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        report = execute_fake(
            plan, assessment,
            FakeFilesystem(Ledger(), {str(self.root / "input.txt"): b"hello"}),
            FakeSubprocess(Ledger(), set()),
        )[0]
        context = begin_verification_context(plan, assessment, "provenance-verifier", current_snapshot(plan))
        proposal = verification_proposal(plan, assessment, context)
        promoted = proposal.model_copy(update={
            "evidence": [proposal.evidence[0].model_copy(update={
                "provenance": "coordinator_observed",
                "locator": str(self.root / "nonexistent"),
            })]
        })
        verification = verify_reports(plan, assessment, [report], promoted, context)
        self.assertFalse(verification.verified)
        self.assertFalse(verification.independent_context)
        self.assertEqual(verification.independence_assurance, "instruction_only")

    def test_verifier_control_plane_write_stops_and_releases(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.execute()
        context = coordinator.open_verification("control-plane-verifier")
        rogue = self.root / ".rb-safe-operation" / "verifier-wrote.txt"
        rogue.write_text("unexpected", encoding="utf-8")
        with self.assertRaisesRegex(WorkflowError, "protected control-plane"):
            coordinator.verify(verification_proposal(plan, assessment, context), context)
        self.assertEqual(coordinator.manifest.state, "human_required")
        self.assertFalse((self.root / ".rb-safe-operation" / "execution.lease").exists())

    def test_malformed_direct_verifier_proposal_releases_lease(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.execute()
        context = coordinator.open_verification("malformed-verifier")
        with self.assertRaisesRegex(WorkflowError, "failed typed validation"):
            coordinator.verify({"schema_version": "1.0"}, context)
        self.assertEqual(coordinator.manifest.state, "human_required")
        self.assertFalse((self.root / ".rb-safe-operation" / "execution.lease").exists())

    def test_audit_duplicate_keys_and_nested_suspension_fail(self):
        log = AuditLog(str(self.root / "audit-strict"), "run")
        payload = EventPayload(event_type="start", lifecycle_from="drafting", lifecycle_to="validating", operation_id=None, summary="start", evidence_ids=["e"])
        log.append(payload, "coordinator_observed", {"status": "start"})
        path = next((self.root / "audit-strict").glob("*.json"))
        raw = path.read_bytes().replace(b'"algorithm":"sha256"', b'"algorithm":"sha256","algorithm":"sha256"')
        path.write_bytes(raw)
        with self.assertRaises(AuditError):
            log.validate_chain()

        manifest = RunManifest(schema_version="1.0", run_id="r", state="paused_resource", suspended_from="executing", plan_hash=None, assessment_hash=None, policy_hash=None, snapshot_hash=None, event_head_hash=None)
        with self.assertRaises(StateError):
            transition(manifest, "human_required", ["drift"])
        escalated = escalate_resume_drift(manifest, ["drift"])
        self.assertEqual((escalated.state, escalated.suspended_from), ("human_required", "executing"))

    def test_coordinator_holds_lease_audits_consumes_and_verifies(self):
        plan, approval = self._review_plan_and_approval()
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [approval])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        self.assertTrue(coordinator.lease.path.exists())
        reports = coordinator.execute()
        consumed = Path(plan.snapshot.control_plane_roots[0]) / "approvals" / plan.run_id / f"{approval.approval_id}.consumed"
        self.assertTrue(consumed.is_file())
        context = coordinator.open_verification("fresh-coordinator-verifier")
        verified = coordinator.verify(verification_proposal(plan, assessment, context), context)
        self.assertTrue(verified.verified)
        self.assertIsNone(coordinator.lease)
        self.assertEqual(coordinator.manifest.state, "verified")
        run_root = Path(plan.snapshot.control_plane_roots[0]) / "runs" / plan.run_id
        self.assertEqual(len(list(run_root.glob("[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]-*.json"))), 4)
        self.assertTrue((run_root / "coordinator-bundle.json").is_file())

    def test_approval_receipts_are_scoped_per_run(self):
        first_plan, first_approval = self._review_plan_and_approval()
        policy = default_global_policy(str(self.root))
        first_assessment = assess_plan(first_plan, policy, capabilities(), semantic(), [first_approval])
        first = ExecutionCoordinator(first_plan, first_assessment, policy, policy, capabilities(), semantic())
        first.execute()
        first.abandon()

        data = first_plan.model_dump(mode="json")
        data["run_id"] = "run-2"
        data["plan_id"] = "plan-2"
        data["current_artifact_locations"] = [
            str(self.root / ".rb-safe-operation" / "artifacts" / "run-2" / "low-level-plan.json")
        ]
        second_plan = first_plan.__class__.model_validate(data)
        second_approval = first_approval.model_copy(update={
            "approval_id": "approval-review-2",
            "plan_hash": hash_ref("low-level-plan", second_plan.model_dump(mode="json")),
        })
        second_assessment = assess_plan(second_plan, policy, capabilities(), semantic(), [second_approval])
        self.assertTrue(second_assessment.safe)
        second = ExecutionCoordinator(second_plan, second_assessment, policy, policy, capabilities(), semantic())
        second.execute()
        self.assertTrue((self.root / ".rb-safe-operation" / "approvals" / "run-1" / "approval-review.consumed").is_file())
        self.assertTrue((self.root / ".rb-safe-operation" / "approvals" / "run-2" / "approval-review-2.consumed").is_file())
        second.abandon()

    def test_coordinator_bounds_fresh_agent_task_packet(self):
        plan = safe_plan(self.root, include_bounded=True)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        ledger = Ledger()
        host = FakeAgentHost(ledger, [{
            "schema_version": "1.0", "operation_id": "task-1", "success": True, "evidence": [{"evidence_id":"completion-task-1","provenance":"agent_reported","locator":"agent-report:completion-task-1","summary":"complete"}],
            "expected_effect_ids_observed": ["effect-task"], "unexpected_effects": [], "next_strategy": None,
        }])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic(), agent_host=host)
        reports = coordinator.execute()
        self.assertEqual([report.operation_id for report in reports], ["read-1", "task-1"])
        packets = [entry for entry in ledger.entries if entry["capability"] == "agent"]
        self.assertEqual([entry["role"] for entry in packets], ["executor"])
        self.assertEqual(set(packets[0]["packet_keys"]), {"operation", "evidence"})
        coordinator.abandon()

    def test_bounded_commands_subprocesses_and_delegation_fail_assessment(self):
        plan = safe_plan(self.root, include_bounded=True)
        policy = default_global_policy(str(self.root))
        for field, value, expected_category in (
            ("allowed_tools", ["exec_argv"], "unsupported_tool"),
            ("subprocesses", ["run anything"], "transitive_execution"),
            ("delegation", ["arbitrary subagent"], "delegation"),
        ):
            data = plan.model_dump(mode="json")
            data["operations"][1][field] = value
            changed = plan.__class__.model_validate(data)
            result = assess_plan(changed, policy, capabilities(), semantic(), [])
            self.assertFalse(result.safe)
            self.assertIn(expected_category, {item.category for item in result.findings})

    def test_bounded_failure_or_unexpected_effect_never_advances_cursor(self):
        for success, unexpected in ((False, []), (True, ["surprise"])):
            with self.subTest(success=success, unexpected=unexpected):
                root = self.root / ("failure" if not success else "unexpected")
                root.mkdir()
                (root / "input.txt").write_text("hello", encoding="utf-8")
                plan = safe_plan(root, include_bounded=True)
                policy = default_global_policy(str(root))
                assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
                host = FakeAgentHost(Ledger(), [{
                    "schema_version": "1.0", "operation_id": "task-1", "success": success,
                    "evidence": [{"evidence_id":"completion-task-1","provenance":"agent_reported","locator":"agent-report:completion-task-1","summary":"complete"}],
                    "expected_effect_ids_observed": ["effect-task"], "unexpected_effects": unexpected,
                    "next_strategy": "retry",
                }])
                coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic(), agent_host=host)
                with self.assertRaisesRegex(WorkflowError, "failure or unexpected effects"):
                    coordinator.execute()
                self.assertEqual(coordinator.next_operation_index, 1)
                self.assertEqual([item.operation_id for item in coordinator.reports], ["read-1"])

    def test_zero_bounded_call_budget_is_rejected_before_agent_invocation(self):
        plan = safe_plan(self.root, include_bounded=True)
        data = plan.model_dump(mode="json")
        data["operations"][1]["resource_limits"]["max_calls"] = 0
        plan = plan.__class__.model_validate(data)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        self.assertFalse(assessment.safe)
        self.assertIn("policy_limit", {item.category for item in assessment.findings})

    def test_control_metadata_and_lease_are_checked_around_agent_dispatch(self):
        plan = safe_plan(self.root, include_bounded=True)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])

        class LeaseTamperingHost:
            def invoke(inner_self, role, packet):
                lease = self.root / ".rb-safe-operation" / "execution.lease"
                lease.chmod(0o644)
                return {
                    "schema_version":"1.0", "operation_id":"task-1", "success":True,
                    "evidence":[{"evidence_id":"completion-task-1","provenance":"agent_reported","locator":"agent-report:completion-task-1","summary":"complete"}],
                    "expected_effect_ids_observed":["effect-task"], "unexpected_effects":[], "next_strategy":None,
                }

        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic(), agent_host=LeaseTamperingHost())
        with self.assertRaisesRegex(WorkflowError, "protected control-plane state"):
            coordinator.execute()

    def test_agent_free_text_is_omitted_before_bundle_persistence(self):
        plan = safe_plan(self.root, include_bounded=True)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        canary = "CANARY-EXECUTOR-SECRET"
        host = FakeAgentHost(Ledger(), [{
            "schema_version":"1.0", "operation_id":"task-1", "success":True,
            "evidence":[{"evidence_id":"completion-task-1","provenance":"agent_reported","locator":"agent-report:completion-task-1","summary":canary}],
            "expected_effect_ids_observed":["effect-task"], "unexpected_effects":[], "next_strategy":canary,
        }])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic(), agent_host=host)
        coordinator.execute()
        self.assertNotIn(canary, coordinator.bundle_path.read_text(encoding="utf-8"))
        coordinator.abandon()

    def test_durable_handoff_artifacts_are_fixed_create_only_and_snapshot_excluded(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        raw_semantic = semantic().model_copy(update={"enforcement_disclosures": ["CANARY-ASSESSOR-PROSE"]})
        artifact_temp = tempfile.TemporaryDirectory()
        self.addCleanup(artifact_temp.cleanup)
        temporary = Path(artifact_temp.name)
        plan_input = temporary / "plan.json"
        capabilities_input = temporary / "capabilities.json"
        semantic_input = temporary / "semantic.json"
        preflight_input = temporary / "preflight.json"
        plan_input.write_bytes(canonical_bytes(plan.model_dump(mode="json")) + b"\n")
        capabilities_input.write_bytes(canonical_bytes(capabilities().model_dump(mode="json")) + b"\n")
        semantic_input.write_bytes(canonical_bytes(raw_semantic.model_dump(mode="json")) + b"\n")

        before = current_snapshot(plan)
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_persist_artifact(SimpleNamespace(artifact_type="low-level-plan", input=str(plan_input), plan=str(plan_input)))
        fixed_plan = self.root / ".rb-safe-operation" / "artifacts" / plan.run_id / "low-level-plan.json"
        preflight = deterministic_preflight(plan, policy, policy, current_snapshot(plan), capabilities(), [])
        preflight_input.write_bytes(canonical_bytes(preflight.model_dump(mode="json")) + b"\n")
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_assess(SimpleNamespace(
                plan=str(fixed_plan), project_policy=None, capabilities=str(capabilities_input),
                preflight=str(preflight_input), semantic_proposal=str(semantic_input), approvals=None,
                prior_assessment_bundle=None, output=None,
            ))
        after = current_snapshot(plan)
        self.assertTrue(snapshot_materially_equal(before, after)[0])
        artifact_root = self.root / ".rb-safe-operation" / "artifacts" / plan.run_id
        self.assertNotIn("CANARY-ASSESSOR-PROSE", (artifact_root / "assessment-bundle.json").read_text(encoding="utf-8"))
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            with self.assertRaises(FileExistsError):
                cmd_persist_artifact(SimpleNamespace(artifact_type="low-level-plan", input=str(plan_input), plan=str(plan_input)))

    def test_failed_deterministic_preflight_persists_false_without_semantic_input(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["operations"][0]["effects"][0]["residual_severity"] = "high"
        plan = plan.__class__.model_validate(data)
        artifact_temp = tempfile.TemporaryDirectory()
        self.addCleanup(artifact_temp.cleanup)
        inputs = Path(artifact_temp.name)
        plan_input = inputs / "plan.json"
        capabilities_input = inputs / "capabilities.json"
        plan_input.write_bytes(canonical_bytes(plan.model_dump(mode="json")) + b"\n")
        capabilities_input.write_bytes(canonical_bytes(capabilities().model_dump(mode="json")) + b"\n")
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_persist_artifact(SimpleNamespace(artifact_type="low-level-plan", input=str(plan_input), plan=str(plan_input)))
            cmd_assess_preflight(SimpleNamespace(
                plan=str(self.root / ".rb-safe-operation" / "artifacts" / plan.run_id / "low-level-plan.json"),
                project_policy=None, capabilities=str(capabilities_input), approvals=None,
                prior_assessment_bundle=None,
            ))
        bundle_path = self.root / ".rb-safe-operation" / "artifacts" / plan.run_id / "assessment-bundle.json"
        bundle = AssessmentBundle.model_validate(parse_json_strict(bundle_path.read_bytes()))
        self.assertFalse(bundle.assessment.safe)
        self.assertFalse(bundle.assessment.deterministic_pass)

    def test_multiple_out_of_policy_roots_produce_one_false_preflight_finding(self):
        plan = safe_plan(self.root)
        data = plan.model_dump(mode="json")
        data["operations"][0]["path_contract"]["read_roots"] = ["/private/tmp/outside-one", "/private/tmp/outside-two"]
        plan = plan.__class__.model_validate(data)
        policy = default_global_policy(str(self.root))
        preflight = deterministic_preflight(plan, policy, policy, current_snapshot(plan), capabilities(), [])
        self.assertFalse(preflight.deterministic_pass)
        self.assertEqual(
            [item.finding_id for item in preflight.findings if item.finding_id == "path-read-1-read_roots"],
            ["path-read-1-read_roots"],
        )

    def test_malformed_semantic_output_persists_sanitized_immutable_false(self):
        plan = safe_plan(self.root)
        artifact_temp = tempfile.TemporaryDirectory()
        self.addCleanup(artifact_temp.cleanup)
        inputs = Path(artifact_temp.name)
        plan_input = inputs / "plan.json"
        capabilities_input = inputs / "capabilities.json"
        semantic_input = inputs / "semantic.json"
        preflight_input = inputs / "preflight.json"
        plan_input.write_bytes(canonical_bytes(plan.model_dump(mode="json")) + b"\n")
        capabilities_input.write_bytes(canonical_bytes(capabilities().model_dump(mode="json")) + b"\n")
        semantic_input.write_text(
            '{"schema_version":"1.0","semantic_pass":true,"findings":[{"finding_id":"CANARY-FINDING",'
            '"invariant_id":"CANARY-INVARIANT","operation_ids":["CANARY-OP"],"effect_ids":["CANARY-EFFECT"],'
            '"category":"CANARY-CATEGORY","severity":"critical","evidence_ids":["CANARY-EVIDENCE"],'
            '"evidence_provenance":["host_observed"],"finding_provenance":"coordinator_observed",'
            '"explanation":"CANARY-EXPLANATION","remediation_or_human_decision":"CANARY-REMEDIATION",'
            '"blocking":false}],"covered_evidence_ids":["CANARY-COVERAGE"],'
            '"enforcement_disclosures":["CANARY-DISCLOSURE"]}\n',
            encoding="utf-8",
        )
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_persist_artifact(SimpleNamespace(artifact_type="low-level-plan", input=str(plan_input), plan=str(plan_input)))
        fixed_plan = self.root / ".rb-safe-operation" / "artifacts" / plan.run_id / "low-level-plan.json"
        output = SimpleNamespace(buffer=io.BytesIO())
        with patch("sys.stdout", output):
            cmd_assess_preflight(SimpleNamespace(
                plan=str(fixed_plan), project_policy=None, capabilities=str(capabilities_input),
                approvals=None, prior_assessment_bundle=None,
            ))
        preflight_input.write_bytes(output.buffer.getvalue())
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_assess(SimpleNamespace(
                plan=str(fixed_plan), project_policy=None, capabilities=str(capabilities_input),
                preflight=str(preflight_input), semantic_proposal=str(semantic_input), approvals=None,
                prior_assessment_bundle=None,
            ))
        bundle_path = fixed_plan.with_name("assessment-bundle.json")
        bundle = AssessmentBundle.model_validate(parse_json_strict(bundle_path.read_bytes()))
        self.assertFalse(bundle.assessment.safe)
        self.assertIn("finding_identity", {item.category for item in bundle.assessment.findings})
        self.assertNotIn("CANARY", bundle_path.read_text(encoding="utf-8"))

    def test_passing_preflight_is_directly_consumable_and_reassessment_binds_prior_rejection(self):
        first_plan = safe_plan(self.root)
        artifact_temp = tempfile.TemporaryDirectory()
        self.addCleanup(artifact_temp.cleanup)
        inputs = Path(artifact_temp.name)
        capabilities_path = inputs / "capabilities.json"
        rejected_semantic_path = inputs / "semantic-rejected.json"
        approved_semantic_path = inputs / "semantic-approved.json"
        capabilities_path.write_bytes(canonical_bytes(capabilities().model_dump(mode="json")) + b"\n")
        rejected_semantic_path.write_bytes(canonical_bytes(semantic(False).model_dump(mode="json")) + b"\n")
        approved_semantic_path.write_bytes(canonical_bytes(semantic().model_dump(mode="json")) + b"\n")

        def persist_and_preflight(plan, label):
            plan_input = inputs / f"{label}-plan.json"
            preflight_input = inputs / f"{label}-preflight.json"
            plan_input.write_bytes(canonical_bytes(plan.model_dump(mode="json")) + b"\n")
            with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
                cmd_persist_artifact(SimpleNamespace(
                    artifact_type="low-level-plan", input=str(plan_input), plan=str(plan_input),
                ))
            fixed_plan = self.root / ".rb-safe-operation" / "artifacts" / plan.run_id / "low-level-plan.json"
            output = SimpleNamespace(buffer=io.BytesIO())
            with patch("sys.stdout", output):
                cmd_assess_preflight(SimpleNamespace(
                    plan=str(fixed_plan), project_policy=None, capabilities=str(capabilities_path),
                    approvals=None, prior_assessment_bundle=None,
                ))
            preflight_bytes = output.buffer.getvalue()
            preflight = DeterministicPreflight.model_validate(parse_json_strict(preflight_bytes))
            self.assertTrue(preflight.deterministic_pass)
            self.assertEqual(preflight_bytes, canonical_bytes(preflight.model_dump(mode="json")) + b"\n")
            preflight_input.write_bytes(preflight_bytes)
            return fixed_plan, preflight_input

        first_fixed_plan, first_preflight = persist_and_preflight(first_plan, "first")
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_assess(SimpleNamespace(
                plan=str(first_fixed_plan), project_policy=None, capabilities=str(capabilities_path),
                preflight=str(first_preflight), semantic_proposal=str(rejected_semantic_path), approvals=None,
                prior_assessment_bundle=None,
            ))
        first_bundle_path = first_fixed_plan.with_name("assessment-bundle.json")
        first_bundle = AssessmentBundle.model_validate(parse_json_strict(first_bundle_path.read_bytes()))
        self.assertFalse(first_bundle.assessment.safe)

        second_data = first_plan.model_dump(mode="json")
        second_data.update({"plan_id": "plan-2", "run_id": "run-2"})
        second_data["current_artifact_locations"] = [
            str(self.root / ".rb-safe-operation" / "artifacts" / "run-2" / "low-level-plan.json")
        ]
        second_plan = first_plan.__class__.model_validate(second_data)
        second_fixed_plan, second_preflight = persist_and_preflight(second_plan, "second")
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_assess(SimpleNamespace(
                plan=str(second_fixed_plan), project_policy=None, capabilities=str(capabilities_path),
                preflight=str(second_preflight), semantic_proposal=str(approved_semantic_path), approvals=None,
                prior_assessment_bundle=str(first_bundle_path),
            ))
        second_bundle = AssessmentBundle.model_validate(
            parse_json_strict(second_fixed_plan.with_name("assessment-bundle.json").read_bytes())
        )
        self.assertTrue(second_bundle.assessment.safe)
        self.assertEqual(
            second_bundle.assessment.prior_assessment_hash,
            hash_ref("assessment", first_bundle.assessment.model_dump(mode="json")),
        )

    def test_durable_artifact_persistence_rejects_symlink_control_root(self):
        plan = safe_plan(self.root)
        artifact_temp = tempfile.TemporaryDirectory()
        self.addCleanup(artifact_temp.cleanup)
        temporary = Path(artifact_temp.name)
        plan_input = temporary / "plan.json"
        plan_input.write_bytes(canonical_bytes(plan.model_dump(mode="json")) + b"\n")
        (self.root / ".rb-safe-operation").symlink_to(temporary, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            cmd_persist_artifact(SimpleNamespace(artifact_type="low-level-plan", input=str(plan_input), plan=str(plan_input)))

    def test_semantic_assessment_proposal_must_reproduce_assessment(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        with self.assertRaisesRegex(WorkflowError, "does not reproduce"):
            ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic(False))

    def test_coordinate_rejects_transient_handoff_paths(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        proposal = canonical_semantic_proposal(semantic())
        assessment = assess_plan(plan, policy, capabilities(), proposal, [])
        bundle = AssessmentBundle(schema_version="1.0", assessment=assessment, semantic_proposal=proposal)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        plan_path = root / "plan.json"
        bundle_path = root / "assessment-bundle.json"
        capabilities_path = root / "capabilities.json"
        plan_path.write_bytes(canonical_bytes(plan.model_dump(mode="json")) + b"\n")
        bundle_path.write_bytes(canonical_bytes(bundle.model_dump(mode="json")) + b"\n")
        capabilities_path.write_bytes(canonical_bytes(capabilities().model_dump(mode="json")) + b"\n")
        with self.assertRaisesRegex(ValueError, "fixed create-only path"):
            cmd_coordinate(SimpleNamespace(
                plan=str(plan_path), assessment_bundle=str(bundle_path), project_policy=None,
                capabilities=str(capabilities_path), verifier_context_id="never", output=None,
            ))

    def test_verified_coordinate_driver_pauses_and_releases_on_verifier_eof(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        proposal = semantic()
        artifact_temp = tempfile.TemporaryDirectory()
        self.addCleanup(artifact_temp.cleanup)
        artifact_root = Path(artifact_temp.name)
        paths: dict[str, str] = {}
        preflight = deterministic_preflight(plan, policy, policy, current_snapshot(plan), capabilities(), [])
        for name, value in (("plan", plan), ("capabilities", capabilities()), ("semantic", proposal), ("preflight", preflight)):
            path = artifact_root / f"{name}.json"
            path.write_bytes(canonical_bytes(value.model_dump(mode="json")) + b"\n")
            paths[name] = str(path)
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            cmd_persist_artifact(SimpleNamespace(artifact_type="low-level-plan", input=paths["plan"], plan=paths["plan"]))
            cmd_assess(SimpleNamespace(
                plan=str(self.root / ".rb-safe-operation" / "artifacts" / plan.run_id / "low-level-plan.json"),
                project_policy=None, capabilities=paths["capabilities"], preflight=paths["preflight"],
                semantic_proposal=paths["semantic"], approvals=None, prior_assessment_bundle=None, output=None,
            ))

        class Stream:
            def __init__(inner_self, initial=b""):
                inner_self.buffer = io.BytesIO(initial)

        args = SimpleNamespace(
            plan=str(self.root / ".rb-safe-operation" / "artifacts" / plan.run_id / "low-level-plan.json"),
            assessment_bundle=str(self.root / ".rb-safe-operation" / "artifacts" / plan.run_id / "assessment-bundle.json"),
            project_policy=None,
            capabilities=paths["capabilities"],
            verifier_context_id="driver-verifier", output=None,
        )
        with patch("sys.stdin", Stream()), patch("sys.stdout", Stream()):
            with self.assertRaisesRegex(RuntimeError, "verifier response stream ended"):
                cmd_coordinate(args)
        self.assertFalse((self.root / ".rb-safe-operation" / "execution.lease").exists())
        bundle = parse_json_strict((self.root / ".rb-safe-operation" / "runs" / plan.run_id / "coordinator-bundle.json").read_bytes())
        self.assertEqual(bundle["manifest"]["state"], "paused_resource")

    def test_coordinate_resume_rejects_repair_and_returns_to_durable_pause(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.execute()
        context = coordinator.open_verification("resume-repair-verifier")
        finding = Finding(
            finding_id="resume-repair-finding", invariant_id="E-003", operation_ids=["read-1"],
            effect_ids=[], category="repairable_local", severity="medium",
            evidence_ids=["verification-observation"], evidence_provenance=["agent_reported"], finding_provenance="agent_reported",
            explanation="repair needed", remediation_or_human_decision="change strategy", blocking=True,
        )
        failed = verification_proposal(plan, assessment, context).model_copy(update={"findings": [finding]})
        self.assertFalse(coordinator.verify(failed, context).verified)
        coordinator.pause_resource("driver-repair-pause")

        artifact_temp = tempfile.TemporaryDirectory()
        self.addCleanup(artifact_temp.cleanup)
        artifact_root = Path(artifact_temp.name)
        capabilities_path = artifact_root / "capabilities.json"
        capabilities_path.write_bytes(canonical_bytes(capabilities().model_dump(mode="json")) + b"\n")
        repair_path = artifact_root / "repair.json"
        repair_path.write_bytes(canonical_bytes(RepairAttempt(
            schema_version="1.0", attempt_id="invalid-resume-attempt", finding_id="unknown-finding",
            hypothesis="changed", observed_result="failed", reconsidered_assumption="old",
            materially_different_next_strategy="new", high_risk_replay=False,
            fresh_idempotency_proof=None, approval_id=None,
        ).model_dump(mode="json")) + b"\n")
        args = SimpleNamespace(
            project_root=str(self.root), run_id=plan.run_id, capabilities=str(capabilities_path),
            resume_evidence_id="driver-human-resume", repair_attempt=str(repair_path),
            verifier_context_id="unused-after-rejection", output=None,
        )
        with patch("sys.stdout", SimpleNamespace(buffer=io.BytesIO())):
            with self.assertRaisesRegex(WorkflowError, "current verifier finding"):
                cmd_coordinate_resume(args)
        self.assertFalse((self.root / ".rb-safe-operation" / "execution.lease").exists())
        bundle = parse_json_strict((self.root / ".rb-safe-operation" / "runs" / plan.run_id / "coordinator-bundle.json").read_bytes())
        self.assertEqual(bundle["manifest"]["state"], "paused_resource")

    def test_executor_cannot_modify_protected_control_state(self):
        plan = safe_plan(self.root, include_bounded=True)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])

        class TamperingHost:
            def invoke(inner_self, role, packet):
                bundle = self.root / ".rb-safe-operation" / "runs" / plan.run_id / "coordinator-bundle.json"
                bundle.write_text("{}\n", encoding="utf-8")
                operation = packet["operation"]
                return {
                    "schema_version": "1.0", "operation_id": operation["operation_id"], "success": True,
                    "evidence": [{"evidence_id":"completion-task-1","provenance":"agent_reported","locator":"agent-report:completion-task-1","summary":"complete"}], "expected_effect_ids_observed": [item["effect_id"] for item in operation["effects"]],
                    "unexpected_effects": [], "next_strategy": None,
                }

        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic(), agent_host=TamperingHost())
        with self.assertRaises(WorkflowError):
            coordinator.execute()
        self.assertFalse((self.root / ".rb-safe-operation" / "execution.lease").exists())

    def test_coordinator_failure_records_human_stop_and_releases_lease(self):
        plan = safe_plan(self.root, include_bounded=True)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        host = FakeAgentHost(Ledger(), [{
            "schema_version": "1.0", "operation_id": "task-1", "success": True, "evidence": [{"evidence_id":"completion-task-1","provenance":"agent_reported","locator":"agent-report:completion-task-1","summary":"complete"}],
            "expected_effect_ids_observed": ["undeclared-effect"], "unexpected_effects": [], "next_strategy": None,
        }])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic(), agent_host=host)
        with self.assertRaisesRegex(WorkflowError, "effect inventory"):
            coordinator.execute()
        self.assertEqual(coordinator.manifest.state, "human_required")
        self.assertIsNone(coordinator.lease)

    def test_five_reversible_repair_cycles_can_reverify(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        for index in range(5):
            coordinator.execute()
            context = coordinator.open_verification(f"repair-verifier-{index}")
            finding = Finding(
                finding_id=f"repairable-{index}", invariant_id="L-003", operation_ids=["read-1"],
                effect_ids=[], category="repairable_local", severity="medium", evidence_ids=["verification-observation"],
                evidence_provenance=["agent_reported"], finding_provenance="agent_reported", explanation="reversible in-envelope issue remains",
                remediation_or_human_decision="use a materially different local strategy", blocking=True,
            )
            proposal = verification_proposal(plan, assessment, context).model_copy(update={"findings": [finding]})
            failed_report = coordinator.verify(proposal, context)
            self.assertFalse(failed_report.verified)
            coordinator.resume_repair(RepairAttempt(
                schema_version="1.0", attempt_id=f"attempt-{index}", finding_id=failed_report.findings[0].finding_id,
                hypothesis=f"hypothesis-{index}", observed_result="verifier finding retained",
                reconsidered_assumption=f"assumption-{index}", materially_different_next_strategy=f"strategy-{index}",
                high_risk_replay=False, fresh_idempotency_proof=None, approval_id=None,
            ))
        coordinator.execute()
        context = coordinator.open_verification("repair-verifier-final")
        self.assertTrue(coordinator.verify(verification_proposal(plan, assessment, context), context).verified)
        self.assertEqual(coordinator.manifest.state, "verified")

    def test_resource_pause_releases_and_resume_revalidates_lease(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.pause_resource("host-budget")
        self.assertEqual((coordinator.manifest.state, coordinator.manifest.suspended_from), ("paused_resource", "executing"))
        self.assertIsNone(coordinator.lease)
        coordinator.resume_after_pause("human-resume")
        self.assertEqual(coordinator.manifest.state, "executing")
        self.assertIsNotNone(coordinator.lease)
        coordinator.execute()
        coordinator.abandon()

    def test_paused_coordinator_reloads_reports_and_terminal_run_does_not_restart(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.execute()
        coordinator.pause_resource("verification-budget")

        with self.assertRaisesRegex(WorkflowError, "run identity already exists"):
            ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        resumed = ExecutionCoordinator.reload(str(self.root), plan.run_id, capabilities())
        self.assertEqual(resumed.manifest.suspended_from, "verifying")
        self.assertEqual(resumed.next_operation_index, len(plan.operations))
        self.assertEqual([item.operation_id for item in resumed.reports], [item.operation_id for item in plan.operations])
        resumed.resume_after_pause("human-resume")
        context = resumed.open_verification("restart-verifier")
        self.assertTrue(resumed.verify(verification_proposal(plan, assessment, context), context).verified)
        with self.assertRaisesRegex(WorkflowError, "terminal coordinator run"):
            ExecutionCoordinator.reload(str(self.root), plan.run_id, capabilities())

    def test_paused_coordinator_reloads_before_first_operation(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.pause_resource("execution-budget")

        resumed = ExecutionCoordinator.reload(str(self.root), plan.run_id, capabilities())
        self.assertEqual(resumed.next_operation_index, 0)
        resumed.resume_after_pause("human-resume")
        self.assertEqual([item.operation_id for item in resumed.execute()], [item.operation_id for item in plan.operations])
        resumed.abandon()

    def test_paused_coordinator_rejects_bundle_audit_head_tampering(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.pause_resource("execution-budget")
        bundle = Path(plan.snapshot.control_plane_roots[0]) / "runs" / plan.run_id / "coordinator-bundle.json"
        payload = parse_json_strict(bundle.read_bytes())
        payload["manifest"]["event_head_hash"] = "0" * 64
        bundle.write_bytes(canonical_bytes(payload) + b"\n")
        with self.assertRaisesRegex(WorkflowError, "bind the audit head"):
            ExecutionCoordinator.reload(str(self.root), plan.run_id, capabilities())

    def test_paused_coordinator_rejects_synthetic_completed_report_prefix(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.pause_resource("execution-budget")
        bundle = Path(plan.snapshot.control_plane_roots[0]) / "runs" / plan.run_id / "coordinator-bundle.json"
        payload = parse_json_strict(bundle.read_bytes())
        payload["next_operation_index"] = 1
        payload["reports"] = [{
            "schema_version": "1.0", "operation_id": "read-1", "success": True, "evidence": [],
            "expected_effect_ids_observed": ["effect-read"], "unexpected_effects": [], "next_strategy": None,
        }]
        bundle.write_bytes(canonical_bytes(payload) + b"\n")
        with self.assertRaisesRegex(WorkflowError, "not committed to the audit chain"):
            ExecutionCoordinator.reload(str(self.root), plan.run_id, capabilities())

    def test_paused_repair_reloads_audited_changed_strategy(self):
        plan = safe_plan(self.root)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic())
        coordinator.execute()
        context = coordinator.open_verification("repair-restart-verifier")
        finding = Finding(
            finding_id="repair-restart-finding", invariant_id="L-003", operation_ids=["read-1"],
            effect_ids=[], category="repairable_local", severity="medium", evidence_ids=["verification-observation"],
            evidence_provenance=["agent_reported"], finding_provenance="agent_reported", explanation="reversible issue remains",
            remediation_or_human_decision="use a changed bounded strategy", blocking=True,
        )
        proposal = verification_proposal(plan, assessment, context).model_copy(update={"findings": [finding]})
        failed_report = coordinator.verify(proposal, context)
        self.assertFalse(failed_report.verified)
        attempt = RepairAttempt(
            schema_version="1.0", attempt_id="repair-restart-attempt", finding_id=failed_report.findings[0].finding_id,
            hypothesis="changed hypothesis", observed_result="finding retained",
            reconsidered_assumption="prior assumption", materially_different_next_strategy="changed strategy",
            high_risk_replay=False, fresh_idempotency_proof=None, approval_id=None,
        )
        coordinator.resume_repair(attempt)
        coordinator.pause_resource("repair-budget")

        resumed = ExecutionCoordinator.reload(str(self.root), plan.run_id, capabilities())
        self.assertEqual([item.attempt_id for item in resumed.repair_attempts], [attempt.attempt_id])
        self.assertEqual(resumed.pending_repair_attempt.attempt_id, attempt.attempt_id)
        resumed.resume_after_pause("human-resume")
        resumed.execute()
        resumed.abandon()

    def test_mutating_bounded_repair_restarts_at_finding_and_reverifies(self):
        plan = safe_plan(self.root, include_bounded=True)
        data = plan.model_dump(mode="json")
        task = data["operations"][1]
        task["allowed_tools"] = ["apply_patch"]
        task["path_contract"]["read_roots"] = []
        task["path_contract"]["modify_roots"] = [str(self.root)]
        task["effects"][0]["effect_class"] = "repository_modify"
        task["effects"][0]["targets"] = [str(self.root)]
        plan = plan.__class__.model_validate(data)
        policy = default_global_policy(str(self.root))
        assessment = assess_plan(plan, policy, capabilities(), semantic(), [])
        self.assertTrue(assessment.safe)

        class RepairingHost:
            def __init__(inner_self):
                inner_self.calls = 0

            def invoke(inner_self, role, packet):
                inner_self.calls += 1
                if inner_self.calls == 2:
                    self.assertEqual(packet["repair_context"]["strategy_code"], "diagnose_with_fresh_evidence")
                    self.assertEqual(packet["repair_context"]["finding"]["invariant_id"], "E-003")
                (self.root / "input.txt").write_text("bad" if inner_self.calls == 1 else "good", encoding="utf-8")
                operation = packet["operation"]
                return {
                    "schema_version": "1.0", "operation_id": operation["operation_id"], "success": True,
                    "evidence": [{"evidence_id":"completion-task-1","provenance":"agent_reported","locator":"agent-report:completion-task-1","summary":"complete"}], "expected_effect_ids_observed": ["effect-task"],
                    "unexpected_effects": [], "next_strategy": None,
                }

        host = RepairingHost()
        coordinator = ExecutionCoordinator(plan, assessment, policy, policy, capabilities(), semantic(), agent_host=host)
        coordinator.execute()
        context = coordinator.open_verification("mutating-repair-first")
        finding = Finding(
            finding_id="mutating-repair-finding", invariant_id="E-003", operation_ids=["task-1"],
            effect_ids=["effect-task"], category="repairable_local", severity="medium",
            evidence_ids=["verification-observation"], evidence_provenance=["agent_reported"], finding_provenance="agent_reported",
            explanation="bounded product state is still incorrect", remediation_or_human_decision="use the changed bounded strategy", blocking=True,
        )
        failed = verification_proposal(plan, assessment, context).model_copy(update={"findings": [finding]})
        failed_report = coordinator.verify(failed, context)
        self.assertFalse(failed_report.verified)
        coordinator.pause_resource("repair-restart-budget")

        resumed = ExecutionCoordinator.reload(str(self.root), plan.run_id, capabilities(), agent_host=host)
        resumed.resume_after_pause("human-resume")
        resumed.resume_repair(RepairAttempt(
            schema_version="1.0", attempt_id="mutating-repair-attempt", finding_id=failed_report.findings[0].finding_id,
            hypothesis="the prior rewrite was incomplete", observed_result="verifier observed bad state",
            reconsidered_assumption="one rewrite was sufficient", materially_different_next_strategy="rewrite the bounded target with corrected content",
            high_risk_replay=False, fresh_idempotency_proof=None, approval_id=None,
        ))
        resumed.execute()
        self.assertEqual([item.operation_id for item in resumed.reports], ["read-1", "task-1"])
        self.assertEqual((self.root / "input.txt").read_text(encoding="utf-8"), "good")
        context = resumed.open_verification("mutating-repair-final")
        self.assertTrue(resumed.verify(verification_proposal(plan, assessment, context), context).verified)

    def test_apply_patch_rejects_unmodelled_mode_metadata(self):
        from rb_safe_operation.workflow import _patch_paths

        patch = "diff --git a/link b/link\nnew file mode 120000\n--- /dev/null\n+++ b/link\n@@ -0,0 +1 @@\n+target\n"
        with self.assertRaisesRegex(WorkflowError, "unmodelled"):
            _patch_paths(patch)

    def test_apply_patch_rejects_duplicate_and_cross_action_targets(self):
        from rb_safe_operation.workflow import _patch_paths

        duplicate = (
            "--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-old\n+first\n"
            "--- a/input.txt\n+++ b/input.txt\n@@ -1 +1 @@\n-old\n+second\n"
        )
        with self.assertRaisesRegex(WorkflowError, "appears more than once"):
            _patch_paths(duplicate)

        cross_action = (
            "--- /dev/null\n+++ b/new.txt\n@@ -0,0 +1 @@\n+created\n"
            "--- a/new.txt\n+++ b/new.txt\n@@ -1 +1 @@\n-created\n+modified\n"
        )
        with self.assertRaisesRegex(WorkflowError, "across actions"):
            _patch_paths(cross_action)


if __name__ == "__main__":
    unittest.main()
