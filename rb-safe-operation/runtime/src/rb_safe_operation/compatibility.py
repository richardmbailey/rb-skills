from __future__ import annotations

import copy
from typing import Any

from pydantic import Field

from .canonical import artifact_hash
from .models import StrictModel


LEGACY_AUDIT_TYPES = frozenset(
    {
        "low-level-plan",
        "assessment",
        "assessment-bundle",
        "execution-report",
        "run-manifest",
        "audit-event",
        "repair-attempt",
        "verification-proposal",
        "verification-report",
        "human-intervention",
        "repository-snapshot",
        "host-capabilities",
    }
)


class LegacyArtifactNotExecutable(RuntimeError):
    """Raised when historical state reaches an action-bearing boundary."""


class LegacyAuditRecord(StrictModel):
    artifact_type: str
    schema_version: str
    artifact_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    stable_identifiers: dict[str, str]
    summary: dict[str, str | bool | int | None]
    original_payload: dict[str, Any]
    executable: bool
    resumable: bool


def inspect_legacy_artifact(artifact_type: str, payload: dict[str, Any]) -> LegacyAuditRecord:
    if artifact_type not in LEGACY_AUDIT_TYPES:
        raise ValueError(f"unsupported legacy artifact type: {artifact_type}")
    observed_version = payload.get("schema_version") if isinstance(payload, dict) else None
    if observed_version not in {"1.0", "2.0"}:
        raise ValueError("legacy audit inspection requires a schema-1.0 or schema-2.0 object")
    identifiers: dict[str, str] = {}
    for field in (
        "plan_id", "run_id", "assessment_id", "operation_id", "attempt_id", "verification_id", "preflight_id"
    ):
        value = payload.get(field)
        if isinstance(value, str):
            identifiers[field] = value
    summary: dict[str, str | bool | int | None] = {}
    for field in ("state", "status", "safe", "verified", "success", "sequence"):
        value = payload.get(field)
        if value is None or isinstance(value, (str, bool, int)):
            summary[field] = value
    copied = copy.deepcopy(payload)
    return LegacyAuditRecord(
        artifact_type=artifact_type,
        schema_version=observed_version,
        artifact_hash=artifact_hash(artifact_type, observed_version, copied),
        stable_identifiers=identifiers,
        summary=summary,
        original_payload=copied,
        executable=False,
        resumable=False,
    )


def require_executable_schema(artifact_type: str, payload: dict[str, Any], *, expected_version: str) -> None:
    observed = payload.get("schema_version") if isinstance(payload, dict) else None
    if observed != expected_version:
        raise LegacyArtifactNotExecutable(
            f"legacy_artifact_not_executable: {artifact_type} schema {observed!r} requires {expected_version!r}; "
            "recompile and reassess as a new run"
        )
