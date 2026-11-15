"""Typed public contracts. Exported JSON schemas are derived from these models."""
from __future__ import annotations
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field

class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

class Artifact(Contract):
    id: Annotated[str, Field(min_length=1)]
    path: Annotated[str, Field(min_length=1)]
    sha256: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    media_type: Annotated[str, Field(min_length=1)]
    bytes: Annotated[int, Field(ge=0)]
    sensitivity: Literal['ordinary', 'restricted']
    redacted: bool
    access: Literal['local', 'restricted_reference', 'expired']

class Target(Contract):
    environment: Literal['local', 'sandbox', 'staging', 'production']
    identity: Annotated[str, Field(min_length=1)]
    config_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]

class Tool(Contract):
    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]
    parser_version: Annotated[str, Field(min_length=1)]

class Command(Contract):
    argv: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
    cwd: Annotated[str, Field(min_length=1)]
    environment_names: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]

class LimitsMaxSpend0(Contract):
    amount: Annotated[float, Field(ge=0)]
    currency: Annotated[str, Field(min_length=1)]

class Limits(Contract):
    timeout_seconds: Annotated[int, Field(ge=1)]
    termination_grace_seconds: Annotated[int, Field(ge=0)]
    max_output_bytes: Annotated[int, Field(ge=1)]
    max_concurrency: Annotated[int, Field(ge=1)]
    max_model_calls: Annotated[int, Field(ge=0)]
    max_tool_calls: Annotated[int, Field(ge=0)]
    max_spend: LimitsMaxSpend0 | None

class CriterionExpected3(Contract):
    lower: float
    upper: float

class Criterion(Contract):
    id: Annotated[str, Field(min_length=1)]
    requirement_id: Annotated[str, Field(min_length=1)]
    type: Literal['assertion', 'metric', 'attestation']
    predicate: Literal['equals', 'at_most', 'at_least', 'between', 'is_true', 'attested']
    expected: float | bool | Annotated[str, Field(min_length=1)] | CriterionExpected3
    unit: Annotated[str, Field(min_length=1)] | None
    justification: Annotated[str, Field(min_length=1)]

class ModulePlanAdapter(Contract):
    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]

class ModulePlan(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'kind': {'const': 'executable'}}}, 'then': {'properties': {'command': {'$ref': 'https://rb-skills.invalid/rb-build-test-suite/1.0.0/contracts.schema.json#/$defs/Command'}, 'evidence_import': {'type': 'null'}, 'execution_contract': {'$ref': 'https://rb-skills.invalid/rb-build-test-suite/1.0.0/contracts.schema.json#/$defs/ExecutionContract'}}}, 'else': {'properties': {'command': {'type': 'null'}, 'evidence_import': {'$ref': 'https://rb-skills.invalid/rb-build-test-suite/1.0.0/contracts.schema.json#/$defs/EvidenceImport'}, 'execution_contract': {'type': 'null'}, 'static_contract': {'type': 'null'}}}}, {'if': {'properties': {'kind': {'const': 'human_review'}}}, 'then': {'properties': {'evidence_import': {'properties': {'reviewer_identity': {'type': 'string', 'minLength': 1}}}}}}, {'if': {'properties': {'kind': {'const': 'agent_review'}}}, 'then': {'properties': {'evidence_import': {'properties': {'host_invocation_ref': {'type': 'string', 'minLength': 1}}}}}}, {'if': {'properties': {'kind': {'const': 'observation'}}}, 'then': {'properties': {'evidence_import': {'properties': {'observation': {'type': 'object'}}}}}}]})
    schema_version: Literal['1.0.0']
    plan_id: Annotated[str, Field(min_length=1)]
    run_id: Annotated[str, Field(min_length=1)]
    module_id: Annotated[str, Field(min_length=1)]
    capability_id: Literal['unit', 'functional', 'component', 'fuzz', 'property_based', 'formal_verification', 'static_analysis', 'mutation', 'coverage', 'benchmark', 'contract', 'lint', 'acceptance', 'regression', 'smoke', 'usability', 'ui_ux', 'penetration', 'threat_modelling', 'performance', 'integration', 'tap_compare', 'load', 'shadowing', 'configuration', 'soak', 'canary', 'release_monitoring', 'traffic_shaping', 'feature_flags', 'exception_tracking', 'teeing', 'profiling', 'logs_events', 'chaos', 'operational_monitoring', 'ab_experiment', 'tracing', 'dynamic_exploration', 'real_user_monitoring', 'auditing', 'on_call_experience', 'independent_verification']
    kind: Literal['executable', 'observation', 'procedure', 'human_review', 'agent_review']
    adapter: ModulePlanAdapter
    candidate_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    policy_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    requirement_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
    subtypes: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    required: bool
    profile: Literal['quick', 'standard', 'deep']
    inputs: Annotated[list[Artifact], Field(min_length=0)]
    depends_on: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    command: Command | None
    target: Target
    effects: Annotated[list[Literal['local_read', 'disposable_write', 'network_read', 'network_write', 'process_attach', 'live_traffic', 'disruption', 'notification', 'deployment']], Field(min_length=0)]
    authority_refs: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    limits: Limits
    criteria: Annotated[list[Criterion], Field(min_length=1)]
    evidence_import: EvidenceImport | None
    execution_contract: ExecutionContract | None
    static_contract: StaticContract | None

class Candidate(Contract):
    snapshot_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    git_commit: Annotated[str, Field(min_length=1)] | None
    dirty: bool | None
    scope: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
    excluded_inputs: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]

class Provenance(Contract):
    specification_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    policy_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    tests_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    config_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    catalogue_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    runner_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    environment_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]

class EnvironmentRuntimeVersionsItem(Contract):
    name: Annotated[str, Field(min_length=1)]
    version: Annotated[str, Field(min_length=1)]

class Environment(Contract):
    os: Annotated[str, Field(min_length=1)]
    architecture: Annotated[str, Field(min_length=1)]
    runtime_versions: Annotated[list[EnvironmentRuntimeVersionsItem], Field(min_length=1)]
    lock_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    isolation_requested: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    isolation_enforced: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    hardware: Annotated[str, Field(min_length=1)] | None
    limitations: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]

class Receipt(Contract):
    id: Annotated[str, Field(min_length=1)]
    producer: Annotated[str, Field(min_length=1)]
    authentication: Literal['local', 'host_receipt', 'external_authenticated']
    started_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]
    finished_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]
    duration_seconds: Annotated[float, Field(ge=0)]
    exit_code: int | None
    tool: Tool
    command: Command | None
    termination: Literal['normal', 'timeout', 'cancelled', 'error']
    artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    authority_refs: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    execution_evidence: ExecutionEvidence | None
    static_evidence: StaticEvidence | None

class Counts(Contract):
    collected: Annotated[int, Field(ge=0)]
    passed: Annotated[int, Field(ge=0)]
    failed: Annotated[int, Field(ge=0)]
    skipped: Annotated[int, Field(ge=0)]
    xfailed: Annotated[int, Field(ge=0)]
    xpassed: Annotated[int, Field(ge=0)]
    errors: Annotated[int, Field(ge=0)]

class CriterionResult(Contract):
    criterion_id: Annotated[str, Field(min_length=1)]
    outcome: Literal['satisfied', 'violated', 'unknown']
    observed: float | bool | Annotated[str, Field(min_length=1)] | None
    unit: Annotated[str, Field(min_length=1)] | None
    artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    rationale: Annotated[str, Field(min_length=1)]

class ModuleResultReusedFrom0(Contract):
    run_id: Annotated[str, Field(min_length=1)]
    module_id: Annotated[str, Field(min_length=1)]
    evidence_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    identity_match: Annotated[str, Field(min_length=1)]

class ModuleResult(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'assessment': {'const': 'PASSED'}}}, 'then': {'properties': {'execution': {'const': 'completed'}, 'receipt': {'$ref': 'https://rb-skills.invalid/rb-build-test-suite/1.0.0/contracts.schema.json#/$defs/Receipt'}, 'criteria': {'minItems': 1, 'items': {'properties': {'outcome': {'const': 'satisfied'}}}}}}}, {'if': {'properties': {'execution': {'const': 'not_run'}}}, 'then': {'properties': {'assessment': {'const': 'NOT_RUN'}, 'receipt': {'type': 'null'}}}}, {'if': {'properties': {'execution': {'const': 'blocked'}}}, 'then': {'properties': {'assessment': {'const': 'BLOCKED'}}}}, {'if': {'properties': {'execution': {'const': 'error'}}}, 'then': {'properties': {'assessment': {'const': 'REQUIRES_REVIEW'}}}}]})
    module_id: Annotated[str, Field(min_length=1)]
    plan_id: Annotated[str, Field(min_length=1)]
    attempt: Annotated[int, Field(ge=1)]
    execution: Literal['completed', 'not_run', 'blocked', 'timed_out', 'cancelled', 'error']
    assessment: Literal['PASSED', 'FAILED', 'NOT_RUN', 'BLOCKED', 'REQUIRES_REVIEW']
    reason: Annotated[str, Field(min_length=1)]
    receipt: Receipt | None
    criteria: Annotated[list[CriterionResult], Field(min_length=0)]
    counts: Counts | None
    artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    reused_from: ModuleResultReusedFrom0 | None

class Capability(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'disposition': {'const': 'not_applicable'}}}, 'then': {'properties': {'required': {'const': False}, 'assessment': {'const': 'NOT_APPLICABLE'}, 'module_ids': {'maxItems': 0}}}}]})
    id: Literal['unit', 'functional', 'component', 'fuzz', 'property_based', 'formal_verification', 'static_analysis', 'mutation', 'coverage', 'benchmark', 'contract', 'lint', 'acceptance', 'regression', 'smoke', 'usability', 'ui_ux', 'penetration', 'threat_modelling', 'performance', 'integration', 'tap_compare', 'load', 'shadowing', 'configuration', 'soak', 'canary', 'release_monitoring', 'traffic_shaping', 'feature_flags', 'exception_tracking', 'teeing', 'profiling', 'logs_events', 'chaos', 'operational_monitoring', 'ab_experiment', 'tracing', 'dynamic_exploration', 'real_user_monitoring', 'auditing', 'on_call_experience', 'independent_verification']
    disposition: Literal['selected', 'deferred', 'not_applicable', 'unresolved']
    reason: Annotated[str, Field(min_length=1)]
    required: bool
    module_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    assessment: Literal['PASSED', 'FAILED', 'NOT_RUN', 'NOT_APPLICABLE', 'BLOCKED', 'REQUIRES_REVIEW']

class Finding(Contract):
    id: Annotated[str, Field(min_length=1)]
    severity: Literal['critical', 'high', 'medium', 'low', 'informational']
    claim: Annotated[str, Field(min_length=1)]
    requirement_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    module_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    remediation: Annotated[str, Field(min_length=1)]
    blocking: bool
    resolution: Literal['open', 'resolved']
    resolution_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]

class Independence(Contract):
    status: Literal['completed', 'blocked', 'not_run', 'partial']
    session_ref: Annotated[str, Field(min_length=1)] | None
    packet_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')] | None
    context_separation: Annotated[str, Field(min_length=1)]
    write_isolation: Annotated[str, Field(min_length=1)]
    enforcement: Literal['prompt_only', 'host_enforced', 'externally_enforced', 'unavailable']
    oracle_refs: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    receipt_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    limitations: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    recommendation: Literal['accept', 'reject', 'escalate', 'unavailable']

class Gate(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'outcome': {'const': 'ACCEPTED'}}}, 'then': {'properties': {'required_failures': {'maxItems': 0}, 'required_gaps': {'maxItems': 0}, 'blocking_finding_ids': {'maxItems': 0}}}}]})
    outcome: Literal['ACCEPTED', 'REJECTED', 'INSUFFICIENT_EVIDENCE', 'NOT_EVALUATED']
    policy_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    required_failures: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    required_gaps: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    blocking_finding_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    rationale: Annotated[str, Field(min_length=1)]

class EvaluationDerivation(Contract):
    schema_version: Literal['1.0.0']
    evaluator_version: Literal['0.1.0']
    source_evidence_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    assessed_evidence_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    policy_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    evaluated_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]

class EvidenceRun(Contract):
    evaluation: EvaluationDerivation | None = None
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'gate': {'properties': {'outcome': {'const': 'ACCEPTED'}}}}}, 'then': {'properties': {'state': {'const': 'finalised'}, 'finished_at': {'type': 'string', 'format': 'date-time', 'pattern': 'Z$'}}}}, {'if': {'properties': {'adoption': {'properties': {'completion': {'const': 'verified'}}}}}, 'then': {'properties': {'gate': {'properties': {'outcome': {'const': 'ACCEPTED'}}}}}}, {'if': {'properties': {'gate': {'properties': {'outcome': {'const': 'ACCEPTED'}}}}}, 'then': {'properties': {'change_impact': {'properties': {'status': {'const': 'reviewed'}, 'unresolved_behavior_ids': {'maxItems': 0}}}}}}]})
    schema_version: Literal['1.0.0']
    run_id: Annotated[str, Field(min_length=1)]
    started_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]
    finished_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})] | None
    state: Literal['in_progress', 'finalised', 'cancelled', 'interrupted']
    focus: Literal['development', 'operations', 'full']
    profile: Literal['quick', 'standard', 'deep']
    candidate: Candidate
    provenance: Provenance
    environment: Environment
    capabilities: Annotated[list[Capability], Field(min_length=43, max_length=43)]
    plans: Annotated[list[Artifact], Field(min_length=0)]
    results: Annotated[list[ModuleResult], Field(min_length=0)]
    artifacts: Annotated[list[Artifact], Field(min_length=0)]
    findings: Annotated[list[Finding], Field(min_length=0)]
    independence: Independence
    gate: Gate
    limitations: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    adoption: Adoption
    change_impact: ChangeImpact

class SummaryCapabilityCounts(Contract):
    PASSED: Annotated[int, Field(ge=0)]
    FAILED: Annotated[int, Field(ge=0)]
    NOT_RUN: Annotated[int, Field(ge=0)]
    NOT_APPLICABLE: Annotated[int, Field(ge=0)]
    BLOCKED: Annotated[int, Field(ge=0)]
    REQUIRES_REVIEW: Annotated[int, Field(ge=0)]

class Summary(Contract):
    capability_counts: SummaryCapabilityCounts
    logical_checks: Annotated[int, Field(ge=0)]
    attempts: Annotated[int, Field(ge=0)]
    test_counts: Counts | None
    required_failed: Annotated[int, Field(ge=0)]
    optional_failed: Annotated[int, Field(ge=0)]

class ReportModule(Contract):
    module_id: Annotated[str, Field(min_length=1)]
    attempt: Annotated[int, Field(ge=1)]
    capability_id: Literal['unit', 'functional', 'component', 'fuzz', 'property_based', 'formal_verification', 'static_analysis', 'mutation', 'coverage', 'benchmark', 'contract', 'lint', 'acceptance', 'regression', 'smoke', 'usability', 'ui_ux', 'penetration', 'threat_modelling', 'performance', 'integration', 'tap_compare', 'load', 'shadowing', 'configuration', 'soak', 'canary', 'release_monitoring', 'traffic_shaping', 'feature_flags', 'exception_tracking', 'teeing', 'profiling', 'logs_events', 'chaos', 'operational_monitoring', 'ab_experiment', 'tracing', 'dynamic_exploration', 'real_user_monitoring', 'auditing', 'on_call_experience', 'independent_verification']
    required: bool
    tool: Tool | None
    execution: Literal['completed', 'not_run', 'blocked', 'timed_out', 'cancelled', 'error']
    assessment: Literal['PASSED', 'FAILED', 'NOT_RUN', 'BLOCKED', 'REQUIRES_REVIEW']
    duration_seconds: Annotated[float, Field(ge=0)] | None
    reason: Annotated[str, Field(min_length=1)]
    criteria: Annotated[list[CriterionResult], Field(min_length=0)]
    artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    criterion_definitions: Annotated[list[Criterion], Field(min_length=1)]
    execution_contract: ExecutionContract | None
    static_contract: StaticContract | None
    execution_evidence: ExecutionEvidence | None
    static_evidence: StaticEvidence | None

class ScientificCheck(Contract):
    claim: Annotated[str, Field(min_length=1)]
    requirement_id: Annotated[str, Field(min_length=1)]
    module_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
    subtype: Annotated[str, Field(min_length=1)]
    units: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    oracle_refs: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    tolerance_justification: Annotated[str, Field(min_length=1)]
    outcome: Literal['PASSED', 'FAILED', 'NOT_RUN', 'BLOCKED', 'REQUIRES_REVIEW']
    artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    limitations: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]

class ChartSeriesItemPointsItem(Contract):
    x: float
    y: float | None

class ChartSeriesItem(Contract):
    name: Annotated[str, Field(min_length=1)]
    meaning: Annotated[str, Field(min_length=1)]
    points: Annotated[list[ChartSeriesItemPointsItem], Field(min_length=1)]

class Chart(Contract):
    id: Annotated[str, Field(min_length=1)]
    title: Annotated[str, Field(min_length=1)]
    x_label: Annotated[str, Field(min_length=1)]
    x_unit: Annotated[str, Field(min_length=1)]
    y_label: Annotated[str, Field(min_length=1)]
    y_unit: Annotated[str, Field(min_length=1)]
    source_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
    series: Annotated[list[ChartSeriesItem], Field(min_length=1)]
    limitations: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]

class Section(Contract):
    id: Literal['overview', 'capabilities', 'checks', 'findings', 'scientific', 'independence', 'performance', 'provenance', 'limitations']
    title: Annotated[str, Field(min_length=1)]
    availability: Literal['present', 'not_applicable', 'unavailable']
    explanation: Annotated[str, Field(min_length=1)]

class ReportModel(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'adoption': {'properties': {'completion': {'const': 'verified'}}}}}, 'then': {'properties': {'gate': {'properties': {'outcome': {'const': 'ACCEPTED'}}}}}}, {'if': {'properties': {'gate': {'properties': {'outcome': {'const': 'ACCEPTED'}}}}}, 'then': {'properties': {'change_impact': {'properties': {'status': {'const': 'reviewed'}, 'unresolved_behavior_ids': {'maxItems': 0}}}}}}]})
    schema_version: Literal['1.0.0']
    run_id: Annotated[str, Field(min_length=1)]
    evidence_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    rendered_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]
    candidate: Candidate
    focus: Literal['development', 'operations', 'full']
    profile: Literal['quick', 'standard', 'deep']
    run_started_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]
    run_finished_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})] | None
    gate: Gate
    summary: Summary
    sections: Annotated[list[Section], Field(min_length=9, max_length=9)]
    capabilities: Annotated[list[Capability], Field(min_length=43, max_length=43)]
    modules: Annotated[list[ReportModule], Field(min_length=0)]
    findings: Annotated[list[Finding], Field(min_length=0)]
    scientific_checks: Annotated[list[ScientificCheck], Field(min_length=0)]
    independence: Independence
    charts: Annotated[list[Chart], Field(min_length=0)]
    provenance: Provenance
    environment: Environment
    artifact_links: Annotated[list[Artifact], Field(min_length=0)]
    limitations: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0)]
    adoption: Adoption
    change_impact: ChangeImpact

class EvidenceImportObservation0(Contract):
    window_start: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]
    window_end: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]
    minimum_samples: Annotated[int, Field(ge=1)]
    maximum_age_seconds: Annotated[int, Field(ge=0)]
    evaluated_at: Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]

class EvidenceImport(Contract):
    source_identity: Annotated[str, Field(min_length=1)]
    source_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
    receipt_artifact_id: Annotated[str, Field(min_length=1)]
    expected_candidate_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    expected_policy_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    target: Target
    reviewer_identity: Annotated[str, Field(min_length=1)] | None
    host_invocation_ref: Annotated[str, Field(min_length=1)] | None
    observation: EvidenceImportObservation0 | None

class Adoption(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'enforcement': {'const': 'protected_ci_verified'}}}, 'then': {'properties': {'protection_receipt_ids': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1, 'uniqueItems': True}}}}, {'if': {'properties': {'completion': {'const': 'verified'}}}, 'then': {'properties': {'required_gap_ids': {'maxItems': 0}}}}]})
    schema_version: Literal['1.0.0']
    candidate_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    policy_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    run_id: Annotated[str, Field(min_length=1)]
    instruction_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1, json_schema_extra={'uniqueItems': True})]
    runner_argv: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1)]
    supported_workflows: Annotated[list[Literal['ordinary_implementation', 'scientific_implementation', 'plan_execution', 'direct_completion']], Field(min_length=1, json_schema_extra={'uniqueItems': True})]
    enforcement: Literal['cooperative', 'protected_ci_requested', 'protected_ci_verified']
    protection_receipt_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    completion: Literal['verified', 'incomplete']
    required_gap_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]

class ChangedPath(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'change': {'const': 'renamed'}}}, 'then': {'properties': {'previous_path': {'type': 'string', 'minLength': 1}}}, 'else': {'properties': {'previous_path': {'type': 'null'}}}}]})
    path: Annotated[str, Field(min_length=1)]
    kind: Literal['source', 'configuration', 'data', 'test', 'documentation', 'interface']
    change: Literal['added', 'modified', 'deleted', 'renamed']
    previous_path: Annotated[str, Field(min_length=1)] | None

class ChangedBehaviour(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'disposition': {'const': 'covered'}}}, 'then': {'properties': {'requirement_ids': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1, 'uniqueItems': True}, 'module_ids': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1, 'uniqueItems': True}, 'review_artifact_id': {'type': 'string', 'minLength': 1}}}}, {'if': {'properties': {'disposition': {'const': 'excluded'}}}, 'then': {'properties': {'review_artifact_id': {'type': 'string', 'minLength': 1}}}}]})
    id: Annotated[str, Field(min_length=1)]
    description: Annotated[str, Field(min_length=1)]
    changed_paths: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1, json_schema_extra={'uniqueItems': True})]
    interface_refs: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    requirement_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    module_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    disposition: Literal['covered', 'excluded', 'unresolved']
    justification: Annotated[str, Field(min_length=1)]
    scientific_effects: Annotated[list[Literal['implementation', 'assumptions', 'tolerances', 'empirical_validity']], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    review_artifact_id: Annotated[str, Field(min_length=1)] | None

class ChangeImpact(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'status': {'const': 'reviewed'}}}, 'then': {'properties': {'review_artifact_id': {'type': 'string', 'minLength': 1}}}}]})
    schema_version: Literal['1.0.0']
    baseline_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')] | None
    candidate_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    inventory_artifact_id: Annotated[str, Field(min_length=1)]
    requirement_inventory_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    status: Literal['pending', 'reviewed']
    review_artifact_id: Annotated[str, Field(min_length=1)] | None
    changes: Annotated[list[ChangedPath], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    behaviours: Annotated[list[ChangedBehaviour], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    unresolved_behavior_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]

class ExecutionContract(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'mode': {'const': 'distribution'}}}, 'then': {'properties': {'distribution_digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'manifest_artifact_ids': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1, 'uniqueItems': True}}}, 'else': {'properties': {'distribution_digest': {'type': 'null'}}}}]})
    mode: Literal['checkout', 'editable', 'distribution', 'script', 'not_applicable']
    source_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    distribution_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')] | None
    manifest_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    expected_test_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]

class ImportOrigin(Contract):
    name: Annotated[str, Field(min_length=1)]
    path: Annotated[str, Field(min_length=1)]
    sha256: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]

class ExecutionEvidence(Contract):
    model_config = ConfigDict(json_schema_extra={'allOf': [{'if': {'properties': {'mode': {'const': 'distribution'}}}, 'then': {'properties': {'distribution_digest': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}, 'manifest_artifact_ids': {'type': 'array', 'items': {'type': 'string', 'minLength': 1}, 'minItems': 1, 'uniqueItems': True}}}, 'else': {'properties': {'distribution_digest': {'type': 'null'}}}}]})
    mode: Literal['checkout', 'editable', 'distribution', 'script', 'not_applicable']
    source_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    distribution_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')] | None
    manifest_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    first_party_origins: Annotated[list[ImportOrigin], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    collected_test_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    executed_test_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]

class StaticContract(Contract):
    tool: Annotated[str, Field(min_length=1)]
    claim: Annotated[str, Field(min_length=1)]
    intended_paths: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1, json_schema_extra={'uniqueItems': True})]
    policy_artifact_id: Annotated[str, Field(min_length=1)]
    config_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    assessment_only: Literal[True]

class ScopeLimitation(Contract):
    path: Annotated[str, Field(min_length=1)]
    region: Annotated[str, Field(min_length=1)] | None
    reason: Annotated[str, Field(min_length=1)]
    policy_ref: Annotated[str, Field(min_length=1)]

class StaticEvidence(Contract):
    effective_config_artifact_ids: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=1, json_schema_extra={'uniqueItems': True})]
    checked_paths: Annotated[list[Annotated[str, Field(min_length=1)]], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    excluded: Annotated[list[ScopeLimitation], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    unchecked: Annotated[list[ScopeLimitation], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    suppressions: Annotated[list[ScopeLimitation], Field(min_length=0, json_schema_extra={'uniqueItems': True})]
    before_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    after_digest: Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
    assessment_only: bool


for _model in list(globals().values()):
    if isinstance(_model, type) and issubclass(_model, Contract):
        _model.model_rebuild()

CapabilityId = ModulePlan.model_fields['capability_id'].annotation
CAPABILITY_IDS = tuple(__import__('typing').get_args(CapabilityId))
Text = Annotated[str, Field(min_length=1)]
Digest = Annotated[str, Field(pattern='^[0-9a-f]{64}$')]
Timestamp = Annotated[str, Field(pattern='Z$', json_schema_extra={'format': 'date-time'})]

class CatalogueEntry(Contract):
    number: Annotated[int, Field(ge=1, le=43)]
    id: CapabilityId
    name: Text
    original_phase: Literal['pre_production', 'deployment', 'release', 'post_release', 'cross_cutting'] | None
    original_phase_note: Text
    qualification: Literal['unsupported', 'qualified']
    focuses: Annotated[list[Literal['development', 'operations', 'full']], Field(min_length=1)]
    kinds: Annotated[list[Literal['executable', 'observation', 'procedure', 'human_review', 'agent_review']], Field(min_length=1)]
    purpose: Text
    applicability: Text
    construction: Annotated[list[Text], Field(min_length=1)]
    tools: list[Text]
    evidence: Text
    acceptance: Text
    cost: Text
    profile_hint: Literal['quick', 'standard', 'deep']
    effects: list[Text]
    authority: Text
    subtypes: list[Text]

class Catalogue(Contract):
    schema_version: Literal['1.0.0']
    entries: Annotated[list[CatalogueEntry], Field(min_length=43, max_length=43)]

class ManagedFile(Contract):
    path: Text
    sha256: Digest
    owner: Literal['generated', 'user']
    version: Text
    backup_path: Text | None
    previous_sha256: Digest | None

class LifecycleEvent(Contract):
    schema_version: Literal['1.0.0']
    run_id: Text
    sequence: Annotated[int, Field(ge=1)]
    timestamp: Timestamp
    actor: Text
    module_id: Text | None
    previous_state: Text
    state: Text
    receipt_ids: list[Text]
    artifact_ids: list[Text]

class VerifierPacket(Contract):
    schema_version: Literal['1.0.0']
    run_id: Text
    candidate_digest: Digest
    requirement_digest: Digest
    policy_digest: Digest
    requirement_artifact_ids: Annotated[list[Text], Field(min_length=1)]
    oracle_artifact_ids: list[Text]
    allowed_read_paths: list[Text]
    allowed_write_paths: list[Text]
    prohibited_paths: list[Text]
    limits: Limits
    known_limitations: list[Text]

class Profile(Contract):
    name: Literal['quick', 'standard', 'deep']
    capability_ids: list[CapabilityId]
    limits: Limits

class RequirementSource(Contract):
    path: Text
    sha256: Digest
    criterion_ids: Annotated[list[Text], Field(min_length=1)]
    authorised_owner: Text

class ReportingConfig(Contract):
    retention_days: Annotated[int, Field(ge=0)]
    redact: bool
    include_raw_artifacts: bool
    output_path: Text

class ExecutionRequest(Contract):
    mode: Literal['checkout', 'editable', 'distribution', 'script', 'not_applicable']
    distribution_path: Text | None
    first_party_paths: dict[Text, Text]
    expected_test_ids: list[Text]

class StaticRequest(Contract):
    tool: Text
    claim: Text
    intended_paths: Annotated[list[Text], Field(min_length=1)]
    policy_path: Text
    config_paths: list[Text]

class ModuleRequest(Contract):
    module_id: Text
    capability_id: CapabilityId
    kind: Literal['executable', 'observation', 'procedure', 'human_review', 'agent_review']
    adapter: ModulePlanAdapter
    requirement_ids: Annotated[list[Text], Field(min_length=1)]
    subtypes: list[Text]
    required: bool
    profile: Literal['quick', 'standard', 'deep']
    input_paths: list[Text]
    depends_on: list[Text]
    command: Command | None
    target: Target
    effects: ModulePlan.model_fields['effects'].annotation
    authority_refs: list[Text]
    limits: Limits
    criteria: Annotated[list[Criterion], Field(min_length=1)]
    execution_request: ExecutionRequest | None
    static_request: StaticRequest | None
    evidence_import_path: Text | None

class AdoptionRequest(Contract):
    runner_argv: Annotated[list[Text], Field(min_length=1)]
    instruction_paths: Annotated[list[Text], Field(min_length=1)]
    supported_workflows: Adoption.model_fields['supported_workflows'].annotation
    enforcement: Literal['cooperative', 'protected_ci_requested']

class ProjectConfig(Contract):
    schema_version: Literal['1.0.0']
    project_root: Text
    focus: Literal['development', 'operations', 'full']
    default_profile: Literal['quick', 'standard', 'deep']
    environment_command: Annotated[list[Text], Field(min_length=1)]
    lock_digest: Digest
    supported_os: Annotated[list[Text], Field(min_length=1)]
    runner_version: Text
    profiles: Annotated[list[Profile], Field(min_length=1)]
    requirements: Annotated[list[RequirementSource], Field(min_length=1)]
    modules: list[ModuleRequest]
    capabilities: Annotated[list[Capability], Field(min_length=43, max_length=43)]
    references: list[Artifact]
    operations: list[Text]
    adoption: AdoptionRequest
    change_impact_path: Text
    reporting: ReportingConfig

RECORD_MODELS = {
    'module-plan': ModulePlan, 'evidence': EvidenceRun, 'report': ReportModel,
    'config': ProjectConfig, 'catalogue': Catalogue, 'managed-file': ManagedFile,
    'event': LifecycleEvent, 'verifier-packet': VerifierPacket,
    'criterion': Criterion, 'module-request': ModuleRequest,
}

def schemas():
    """Generate a closed, package-local Draft 2020-12 schema bundle."""
    definitions = {}
    roots = {}
    for name, model in RECORD_MODELS.items():
        schema = model.model_json_schema(ref_template='#/$defs/{model}')
        definitions.update(schema.pop('$defs', {}))
        definitions[model.__name__] = schema
        roots[name + '.schema.json'] = {
            '$schema': 'https://json-schema.org/draft/2020-12/schema',
            '$id': 'https://rb-skills.invalid/rb-build-test-suite/1.0.0/' + name + '.schema.json',
            '$ref': 'https://rb-skills.invalid/rb-build-test-suite/1.0.0/contracts.schema.json#/$defs/' + model.__name__,
        }
    roots['contracts.schema.json'] = {
        '$schema': 'https://json-schema.org/draft/2020-12/schema',
        '$id': 'https://rb-skills.invalid/rb-build-test-suite/1.0.0/contracts.schema.json',
        '$defs': definitions,
    }
    return roots

class ExecutionManifest(Contract):
    """Frozen first-party content identity, supplied as a hashed JSON artifact."""
    schema_version: Literal['1.0.0']
    source_digest: Digest
    distribution_digest: Digest | None
    config_digest: Digest
    environment_digest: Digest
    build_tool: Text | None
    origins: Annotated[list[ImportOrigin], Field(min_length=1)]

class StaticPolicy(Contract):
    schema_version: Literal['1.0.0']
    policy_digest: Digest
    allowed_limitations: list[ScopeLimitation]

RECORD_MODELS.update({'execution-manifest': ExecutionManifest, 'static-policy': StaticPolicy})

class InventoryPath(Contract):
    path: Text
    kind: Literal['source', 'configuration', 'data', 'test', 'documentation', 'interface']
    change: Literal['added', 'modified', 'deleted', 'renamed']
    previous_path: Text | None
    before_digest: Digest | None
    after_digest: Digest | None

class ChangeInventory(Contract):
    schema_version: Literal['1.0.0']
    baseline_digest: Digest | None
    candidate_digest: Digest
    changes: list[InventoryPath]

RECORD_MODELS['change-inventory'] = ChangeInventory
