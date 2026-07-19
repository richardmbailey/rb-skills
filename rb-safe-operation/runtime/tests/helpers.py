from __future__ import annotations

import hashlib
from pathlib import Path

from rb_safe_operation.models import Assessment, HostCapabilities, LowLevelPlan, SemanticAssessmentProposal, VerificationProposal
from rb_safe_operation.planning import select_markdown_phase
from rb_safe_operation.policy import default_global_policy
from rb_safe_operation.state import capture_snapshot
from rb_safe_operation.workflow import hash_ref


ZERO_HASH = "0" * 64


def effect(effect_id: str = "effect-read", effect_class: str = "repository_read", **overrides):
    value = {
        "effect_id": effect_id,
        "kind": "direct",
        "effect_class": effect_class,
        "affected_party": "repository owner",
        "data_classification": "internal",
        "security_sensitive": False,
        "unmitigated_severity": "low",
        "residual_severity": "low",
        "likelihood": "possible",
        "exposure": "repository",
        "reversibility": "full",
        "detectability": "full",
        "mitigation": "verified",
        "recovery": "tested",
        "cost_impact": "none",
        "availability_impact": "none",
        "approval_class": None,
        "targets": [],
        "observation_sources": ["coordinator_observed"],
        "cumulative_interaction": "none", "cumulative_member_effect_ids": [],
        "evidence_ids": ["evidence-source"],
    }
    value.update(overrides)
    return value


def common(root: Path, operation_id: str, effect_value: dict):
    return {
        "operation_id": operation_id,
        "dependencies": [],
        "preconditions": ["snapshot matches"],
        "success_criteria": ["operation completes"],
        "verifier_checks": ["state matches contract", "product_diff", "undeclared_effects"],
        "stop_conditions": ["identity mismatch"],
        "path_contract": {
            "read_roots": [str(root)], "create_roots": [], "modify_roots": [], "delete_roots": [],
            "protected_roots": [str(root / ".rb-safe-operation")], "working_directories": [str(root)],
        },
        "environment": [], "network_grants": [], "subprocesses": [], "delegation": [], "approval_classes": [],
        "effects": [effect_value], "effect_inventory_complete": True, "policy_references": ["O-001", "E-002"],
        "resource_limits": {"max_seconds": 30, "max_processes": 1, "max_bytes": 1000000, "max_calls": 2, "max_cost_decimal": "0", "attempt_limit": "unbounded"},
    }


def safe_plan(root: Path, include_bounded: bool = False) -> LowLevelPlan:
    source = root / "input.txt"
    content = source.read_bytes()
    authoritative = root / "PLAN.md"
    authoritative.write_text(
        "# Plan\n\n## Phase 1: Read input\nRead the bounded input.\n\n## Phase 2: Later\nPreserve later work.\n",
        encoding="utf-8",
    )
    selection = select_markdown_phase(str(authoritative), "phase-1")
    read = {
        **common(root, "read-1", effect(targets=[str(source)])),
        "kind": "exact_action", "adapter": "read_file", "path": str(source), "byte_start": 0,
        "byte_end": len(content), "expected_hash": hashlib.sha256(content).hexdigest(),
    }
    operations = [read]
    if include_bounded:
        bounded = {
            **common(root, "task-1", effect("effect-task", targets=[str(root)])),
            "kind": "bounded_agent_task", "dependencies": ["read-1"], "goal": "inspect the bounded input",
            "non_goals": ["do not mutate"], "evidence_ids": ["evidence-source"], "allowed_tools": ["read"],
            "allowed_executables": {}, "allowed_executable_hashes": {}, "allowed_executable_input_hashes": {},
            "forbidden_actions": ["writes", "network"],
            "permitted_adaptations": ["choose_file_within_root", "diagnose_failure"],
            "diagnostic_checkpoint_rules": ["record changed strategy"], "completion_evidence": ["completion-task-1"],
            "escalation_conditions": ["new scope"],
        }
        operations.append(bounded)
    policy = default_global_policy(str(root))
    snapshot = capture_snapshot(
        str(root), [str(source), str(authoritative)], [], [], [str(root / ".rb-safe-operation")]
    ).model_dump(mode="json")
    plan = {
        "schema_version": "1.0", "plan_id": "plan-1", "run_id": "run-1",
        "source_phase": selection.source.model_dump(mode="json"),
        "snapshot": snapshot,
        "global_policy_hash": hash_ref("active-policy", policy.model_dump(mode="json")).model_dump(mode="json"),
        "merged_policy_hash": hash_ref("active-policy", policy.model_dump(mode="json")).model_dump(mode="json"),
        "operations": operations,
        "evidence": [{"evidence_id": "evidence-source", "provenance": "coordinator_observed", "locator": str(source), "summary": "bounded input hash"}],
        "later_phase_ids": ["phase-2"],
        "current_artifact_locations": [str(root / ".rb-safe-operation" / "artifacts" / "run-1" / "low-level-plan.json")],
        "exact_next_action": "assess plan", "semantic_guidance": [],
    }
    return LowLevelPlan.model_validate(plan)


def current_snapshot(plan: LowLevelPlan):
    return capture_snapshot(
        plan.snapshot.project_root,
        list(plan.snapshot.selected_file_hashes),
        list(plan.snapshot.instruction_hashes),
        plan.snapshot.expected_product_changes,
        plan.snapshot.control_plane_roots,
    )


def capabilities(profile: str = "semi_formal") -> HostCapabilities:
    return HostCapabilities(
        profile=profile, role_read_only="instruction_only", product_state_observation="coordinator_observed",
        complete_child_trace=False, atomic_path_enforcement=False, atomic_lease_create=True,
        bounded_resource_enforcement="instruction_only", fresh_context_enforcement="instruction_only",
    )


def semantic(pass_value: bool = True) -> SemanticAssessmentProposal:
    return SemanticAssessmentProposal(
        schema_version="1.0", semantic_pass=pass_value, findings=[], covered_evidence_ids=["evidence-source"],
        enforcement_disclosures=["assessor and verifier restrictions are instruction_only; child trace is incomplete"],
    )


def verification_proposal(plan: LowLevelPlan, assessment: Assessment, context) -> VerificationProposal:
    evidence_id = "verification-observation"
    criteria = sorted({item for operation in plan.operations for item in operation.success_criteria})
    checks = sorted({item for operation in plan.operations for item in operation.verifier_checks})
    effects = sorted({effect.effect_id for operation in plan.operations for effect in operation.effects})
    return VerificationProposal(
        schema_version="1.0",
        plan_hash=hash_ref("low-level-plan", plan.model_dump(mode="json")),
        assessment_hash=hash_ref("assessment", assessment.model_dump(mode="json")),
        snapshot_hash=context.snapshot_hash,
        verifier_context_id=context.context_id,
        success_criteria_met=criteria,
        verifier_checks_passed=checks,
        observed_effect_ids=effects,
        evidence=[{
            "evidence_id": evidence_id,
            "provenance": "agent_reported",
            "locator": f"agent-report:{evidence_id}",
            "summary": "fresh verifier observed declared criteria, checks, and effects",
        }],
        criterion_evidence={item: [evidence_id] for item in criteria},
        check_evidence={item: [evidence_id] for item in checks},
        effect_evidence={item: [evidence_id] for item in effects},
        findings=[],
    )
