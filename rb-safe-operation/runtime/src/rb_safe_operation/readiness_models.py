from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import PurePosixPath
from typing import Literal

from pydantic import Field, model_validator

from .models import HashRef, SafeIdentifier, StrictModel, UtcTimestamp
from .proposal_models import (
    DataClassification,
    HostCapabilitiesV2,
    ProposalAdapter,
    ProposalRole,
    ProviderGrant,
    RunResourceGrant,
)


ReadinessProfile = Literal[
    "exact_static", "framework_proposal", "codex_cli", "instruction_only_compatibility"
]
ReadinessStatus = Literal[
    "ready_exact_static",
    "ready_framework_proposal",
    "ready_codex_cli",
    "ready_instruction_only_compatibility",
    "not_ready",
]
CredentialStatus = Literal["available", "unavailable", "unknown", "not_required"]


def _absolute_project_root(value: str) -> None:
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or "\0" in value:
        raise ValueError("project_root must be an absolute literal path")


def _finite_decimal(value: str, field: str) -> str:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field} must be a canonical finite decimal") from exc
    if not parsed.is_finite() or parsed < 0:
        raise ValueError(f"{field} must be a non-negative finite decimal")
    canonical = format(parsed, "f")
    if "." in canonical:
        canonical = canonical.rstrip("0").rstrip(".")
    canonical = canonical or "0"
    if value != canonical:
        raise ValueError(f"{field} must use canonical decimal form {canonical}")
    return value


class ReadinessDiagnostic(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    code: SafeIdentifier
    blocking: bool
    summary: str = Field(min_length=1, max_length=1000)
    remediation: str = Field(min_length=1, max_length=2000)
    provenance: Literal["coordinator_observed", "operator_supplied"]


class DoctorRequest(StrictModel):
    schema_version: Literal["1.0"]
    request_id: SafeIdentifier
    observed_at: UtcTimestamp
    project_root: str
    requested_profile: ReadinessProfile
    adapter: ProposalAdapter
    requested_verification_modes: list[str]
    credential_handle: str | None = Field(default=None, max_length=300)
    credential_status: CredentialStatus
    provider_grant_path: str | None = None
    run_resource_grant_path: str | None = None
    schema_mirror_roots: list[str]

    @model_validator(mode="after")
    def closed_request(self) -> "DoctorRequest":
        _absolute_project_root(self.project_root)
        if not self.requested_verification_modes:
            raise ValueError("doctor requires at least one requested verification mode")
        if len(self.requested_verification_modes) != len(set(self.requested_verification_modes)):
            raise ValueError("requested verification modes must be unique")
        if len(self.schema_mirror_roots) != 4:
            raise ValueError("doctor requires exactly four installed schema mirror roots")
        for value in self.schema_mirror_roots:
            _absolute_project_root(value)
        if len(self.schema_mirror_roots) != len(set(self.schema_mirror_roots)):
            raise ValueError("schema mirror roots must be unique")
        for value in (self.provider_grant_path, self.run_resource_grant_path):
            if value is not None:
                _absolute_project_root(value)
        if self.credential_status == "not_required" and self.credential_handle is not None:
            raise ValueError("not-required credential status cannot name a handle")
        if self.credential_status != "not_required" and not self.credential_handle:
            raise ValueError("credential status requires an explicit external handle")
        return self


class ReadinessResult(StrictModel):
    schema_version: Literal["1.0"]
    request_id: SafeIdentifier
    request_hash: HashRef
    observed_at: UtcTimestamp
    project_root: str
    requested_profile: ReadinessProfile
    adapter: ProposalAdapter
    requested_verification_modes: list[str]
    status: ReadinessStatus
    effective_assurance_profile: str
    omitted_capabilities: list[str]
    diagnostics: list[ReadinessDiagnostic]
    exact_next_action: str

    @model_validator(mode="after")
    def verdict_consistency(self) -> "ReadinessResult":
        if self.request_hash.artifact_type != "doctor-request" or self.request_hash.schema_version != "1.0":
            raise ValueError("request_hash must reference doctor-request schema 1.0")
        blocking = any(item.blocking for item in self.diagnostics)
        expected = {
            "exact_static": "ready_exact_static",
            "framework_proposal": "ready_framework_proposal",
            "codex_cli": "ready_codex_cli",
            "instruction_only_compatibility": "ready_instruction_only_compatibility",
        }[self.requested_profile]
        if (self.status == "not_ready") != blocking:
            raise ValueError("not_ready must exactly match blocking diagnostics")
        if not blocking and self.status != expected:
            raise ValueError("ready status does not match requested profile")
        if len(self.omitted_capabilities) != len(set(self.omitted_capabilities)):
            raise ValueError("omitted capabilities must be unique")
        codes = [item.code for item in self.diagnostics]
        if len(codes) != len(set(codes)):
            raise ValueError("readiness diagnostic codes must be unique")
        return self


class RunPreparationRequest(StrictModel):
    schema_version: Literal["1.0"]
    preparation_id: SafeIdentifier
    run_id: SafeIdentifier
    project_root: str
    adapter: ProposalAdapter
    provider: str = Field(min_length=1, max_length=200)
    endpoint: str = Field(min_length=1, max_length=1000)
    model: str = Field(min_length=1, max_length=300)
    model_revision: str | None = Field(default=None, max_length=300)
    host_revision: str | None = Field(default=None, max_length=300)
    credential_handle: str = Field(min_length=1, max_length=300)
    credential_status: CredentialStatus
    credential_audience: str = Field(min_length=1, max_length=300)
    roles: list[ProposalRole]
    request_data_classes: list[str]
    response_data_classes: list[str]
    maximum_data_classification: DataClassification
    retention_disclosure: str = Field(min_length=1, max_length=2000)
    training_use: Literal["allowed", "disallowed", "unknown"]
    issued_at: UtcTimestamp
    expires_at: UtcTimestamp
    max_provider_calls: int = Field(gt=0)
    max_proposer_calls: int = Field(gt=0)
    max_assessor_calls: int = Field(gt=0)
    max_model_requests: int = Field(gt=0)
    max_read_tool_calls: int = Field(ge=0)
    max_read_tool_bytes: int = Field(ge=0)
    max_patch_bytes: int = Field(gt=0)
    max_request_bytes: int = Field(gt=0)
    max_response_bytes: int = Field(gt=0)
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    max_elapsed_seconds: int = Field(gt=0)
    max_cost_decimal: str
    automatic_retry_attempt_limit: int | Literal["unbounded"] = 0
    automatic_retry_classes: list[Literal["proposal_format_error"]] = Field(default_factory=list)
    cost_accounting: Literal["observed", "declared_zero", "unavailable"]
    temperature_decimal: str
    seed: int | None
    structured_output_mode: Literal["tool", "native", "prompted"]
    redirect_endpoints: list[str]
    authorization_hash: HashRef

    @model_validator(mode="after")
    def finite_explicit_request(self) -> "RunPreparationRequest":
        _absolute_project_root(self.project_root)
        if datetime.strptime(self.expires_at, "%Y-%m-%dT%H:%M:%SZ") <= datetime.strptime(
            self.issued_at, "%Y-%m-%dT%H:%M:%SZ"
        ):
            raise ValueError("preparation authority must expire after issue")
        if self.credential_status != "available":
            raise ValueError("run preparation requires explicit available credential status")
        if self.max_provider_calls != self.max_model_requests:
            raise ValueError("provider and aggregate model request ceilings must match")
        if self.max_proposer_calls + self.max_assessor_calls > self.max_model_requests:
            raise ValueError("role call ceilings exceed aggregate model request ceiling")
        if isinstance(self.automatic_retry_attempt_limit, int) and self.automatic_retry_attempt_limit < 0:
            raise ValueError("automatic retry attempt limit must be non-negative or unbounded")
        if len(self.automatic_retry_classes) != len(set(self.automatic_retry_classes)):
            raise ValueError("automatic retry classes must be unique")
        retries_enabled = self.automatic_retry_attempt_limit == "unbounded" or self.automatic_retry_attempt_limit > 0
        if retries_enabled != bool(self.automatic_retry_classes):
            raise ValueError(
                "automatic retry classes must be present exactly when automatic retries are enabled"
            )
        required_roles = {"plan_assessor", "proposer", "patch_assessor", "verifier"}
        if set(self.roles) != required_roles or len(self.roles) != len(required_roles):
            raise ValueError("run preparation requires exactly the four owned semantic roles")
        for field in ("request_data_classes", "response_data_classes", "redirect_endpoints"):
            values = getattr(self, field)
            if len(values) != len(set(values)):
                raise ValueError(f"{field} must be unique")
        if not self.request_data_classes or not self.response_data_classes:
            raise ValueError("request and response data classes cannot be empty")
        _finite_decimal(self.max_cost_decimal, "max_cost_decimal")
        _finite_decimal(self.temperature_decimal, "temperature_decimal")
        if self.cost_accounting == "declared_zero" and self.max_cost_decimal != "0":
            raise ValueError("declared-zero cost requires a zero ceiling")
        if self.cost_accounting == "unavailable":
            raise ValueError("unavailable cost accounting cannot authorise a run")
        if self.authorization_hash.artifact_type != "human-authorization" or self.authorization_hash.schema_version != "1.0":
            raise ValueError("authorization_hash must reference human-authorization schema 1.0")
        if self.adapter == "pydantic_ai" and not self.endpoint.startswith("https://"):
            raise ValueError("PydanticAI provider endpoint must use HTTPS")
        if self.adapter == "json_line" and not self.endpoint.startswith("host-mediated://"):
            raise ValueError("JSON-line endpoint must use host-mediated scheme")
        return self


class RunPreparationPreview(StrictModel):
    schema_version: Literal["1.0"]
    preparation_id: SafeIdentifier
    run_id: SafeIdentifier
    project_root: str
    project_root_device: int = Field(ge=0)
    project_root_inode: int = Field(gt=0)
    request_hash: HashRef
    credential_handle: str
    credential_status: Literal["available"]
    host_capabilities: HostCapabilitiesV2
    provider_grant: ProviderGrant
    run_resource_grant: RunResourceGrant
    assurance_statements: list[str]
    confirmation_binding_hash: HashRef
    exact_confirmation_statement: str


class RunPreparationConfirmation(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    confirmation_id: SafeIdentifier
    preview_hash: HashRef
    statement_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmed_at: UtcTimestamp
    confirmation_assurance: Literal["instruction_only"] = "instruction_only"

    @classmethod
    def from_statement(
        cls,
        *,
        confirmation_id: str,
        preview_hash: str,
        statement: str,
        confirmed_at: str,
    ) -> "RunPreparationConfirmation":
        return cls(
            confirmation_id=confirmation_id,
            preview_hash=HashRef(
                artifact_type="run-preparation-preview-body",
                schema_version="1.0",
                value=preview_hash,
            ),
            statement_hash=hashlib.sha256(statement.encode("utf-8")).hexdigest(),
            confirmed_at=confirmed_at,
        )


class RunPreparationPersistenceResult(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    preparation_id: SafeIdentifier
    artifact_paths: dict[str, str]
