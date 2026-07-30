from __future__ import annotations

from decimal import Decimal
import hashlib
import os
from pathlib import Path
import stat
from typing import Literal

from pydantic import Field, model_validator

from .canonical import canonical_bytes, canonical_decimal, parse_json_strict
from .models import HashRef, StrictModel
from .proposal_models import CoordinatorBundleV2, ProposalLifecycleState, ProposalRole


class AcceptanceRunSummary(StrictModel):
    """Redacted, content-free operational measurements for one constrained run."""

    schema_version: Literal["1.0"] = "1.0"
    project_root_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    run_id: str
    lifecycle_state: ProposalLifecycleState
    provider: str
    endpoint: str
    model: str
    model_revision: str | None
    host_revision: str | None
    provider_grant_hash: HashRef
    run_resource_grant_hash: HashRef
    coordinator_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    roles: list[ProposalRole]
    assurance_profiles: list[str]
    role_calls: int = Field(ge=0)
    model_requests: int = Field(ge=0)
    tool_calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    request_bytes: int = Field(ge=0)
    response_bytes: int = Field(ge=0)
    provider_elapsed_milliseconds: int = Field(ge=0)
    cost_decimal: str
    usage_complete: bool
    operation_count: int = Field(ge=0)
    execution_report_count: int = Field(ge=0)
    event_head_hash: str | None
    static_verification_only: Literal[True] = True
    assurance_limits: list[str]

    @model_validator(mode="after")
    def closed_summary(self) -> "AcceptanceRunSummary":
        canonical_decimal(self.cost_decimal)
        if len(self.assurance_profiles) != len(set(self.assurance_profiles)):
            raise ValueError("acceptance assurance profiles must be unique")
        if self.role_calls != len(self.roles):
            raise ValueError("acceptance role-call count differs from the role sequence")
        return self


def _read_bundle(path: Path) -> tuple[CoordinatorBundleV2, bytes]:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("acceptance coordinator bundle is not a regular file")
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            raw = handle.read()
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    bundle = CoordinatorBundleV2.model_validate(parse_json_strict(raw))
    if raw != canonical_bytes(bundle.model_dump(mode="json")) + b"\n":
        raise ValueError("acceptance coordinator bundle is not canonical")
    return bundle, raw


def summarize_acceptance_run(project_root: str, run_id: str) -> AcceptanceRunSummary:
    root = Path(project_root)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise ValueError("acceptance project root is invalid")
    control = root / ".rb-safe-operation"
    run_root = control / "runs" / run_id
    bundle_path = run_root / "coordinator-bundle.json"
    if any(path.is_symlink() for path in (control, run_root, bundle_path)):
        raise ValueError("acceptance run path contains a symbolic link")
    bundle, raw = _read_bundle(bundle_path)
    if bundle.project_root != str(root) or bundle.run_id != run_id:
        raise ValueError("acceptance bundle project or run identity differs")
    records = bundle.role_call_records
    known_cost = sum(
        (Decimal(item.cost_decimal) for item in records if item.cost_decimal is not None),
        Decimal("0"),
    )
    return AcceptanceRunSummary(
        project_root_sha256=hashlib.sha256(str(root).encode("utf-8")).hexdigest(),
        run_id=run_id, lifecycle_state=bundle.manifest.state,
        provider=bundle.provider_grant.provider, endpoint=bundle.provider_grant.endpoint,
        model=bundle.provider_grant.model, model_revision=bundle.provider_grant.model_revision,
        host_revision=bundle.provider_grant.host_revision,
        provider_grant_hash=bundle.provider_grant_hash,
        run_resource_grant_hash=bundle.run_resource_grant_hash,
        coordinator_bundle_sha256=hashlib.sha256(raw).hexdigest(),
        roles=[item.role for item in records],
        assurance_profiles=sorted({item.assurance_profile for item in records}),
        role_calls=len(records), model_requests=sum(item.requests for item in records),
        tool_calls=sum(item.tool_calls for item in records),
        input_tokens=sum(item.input_tokens for item in records),
        output_tokens=sum(item.output_tokens for item in records),
        request_bytes=sum(item.request_bytes for item in records),
        response_bytes=sum(item.response_bytes for item in records),
        provider_elapsed_milliseconds=sum(item.elapsed_milliseconds for item in records),
        cost_decimal=canonical_decimal(format(known_cost, "f")),
        usage_complete=all(item.usage_complete for item in records),
        operation_count=len(bundle.plan.operations),
        execution_report_count=len(bundle.execution_reports),
        event_head_hash=bundle.manifest.event_head_hash,
        assurance_limits=(
            [
                "Codex CLI capabilities are process-disabled but this is not proof of an operating-system sandbox",
                "the summary covers static verification rather than executable correctness",
                "ChatGPT service retention and complete child traces are not coordinator-controlled",
            ]
            if bundle.provider_grant.provider == "codex-cli"
            else [
                "framework tool allocation is not an operating-system sandbox",
                "the summary covers static verification rather than executable correctness",
                "provider-side retention and complete child traces are not coordinator-controlled",
            ]
        ),
    )
