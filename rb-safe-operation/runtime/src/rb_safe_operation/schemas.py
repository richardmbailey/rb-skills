from __future__ import annotations

import json
from pathlib import Path

from pydantic import TypeAdapter

from . import SCHEMA_VERSION, __version__
from .canonical import artifact_hash, canonical_bytes, source_tree_hash
from .models import ActivePolicy, Approval, Assessment, AssessmentBundle, AuditEvent, DeterministicPreflight, ExecutionReport, HostCapabilities, HumanIntervention, LowLevelPlan, ProjectPolicy, RepairAttempt, RepositorySnapshot, RunManifest, SemanticAssessmentProposal, VerificationProposal, VerificationReport


MODELS = {
    "active-policy": ActivePolicy,
    "approval": Approval,
    "assessment": Assessment,
    "assessment-bundle": AssessmentBundle,
    "deterministic-preflight": DeterministicPreflight,
    "audit-event": AuditEvent,
    "execution-report": ExecutionReport,
    "host-capabilities": HostCapabilities,
    "low-level-plan": LowLevelPlan,
    "human-intervention": HumanIntervention,
    "project-policy": ProjectPolicy,
    "repository-snapshot": RepositorySnapshot,
    "repair-attempt": RepairAttempt,
    "run-manifest": RunManifest,
    "semantic-assessment-proposal": SemanticAssessmentProposal,
    "verification-proposal": VerificationProposal,
    "verification-report": VerificationReport,
}


def export_schemas(destination: Path, runtime_root: Path, runtime_source_hash: str | None = None) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    source_hash = runtime_source_hash or source_tree_hash(runtime_root)
    written: list[Path] = []
    for name, model in MODELS.items():
        schema = model.model_json_schema()
        envelope = {
            "generator_version": __version__,
            "model_schema_version": SCHEMA_VERSION,
            "runtime_source_hash": source_hash,
            "schema_payload_hash": artifact_hash("json-schema", "1.0", schema),
            "schema": schema,
        }
        path = destination / f"{name}-1.0.schema.json"
        path.write_bytes(canonical_bytes(envelope) + b"\n")
        written.append(path)
    return written


def check_drift(expected: Path, generated: Path) -> list[str]:
    differences: list[str] = []
    expected_names = {path.name for path in expected.glob("*.json")}
    generated_names = {path.name for path in generated.glob("*.json")}
    for name in sorted(expected_names | generated_names):
        left, right = expected / name, generated / name
        if not left.exists() or not right.exists() or left.read_bytes() != right.read_bytes():
            differences.append(name)
    return differences
