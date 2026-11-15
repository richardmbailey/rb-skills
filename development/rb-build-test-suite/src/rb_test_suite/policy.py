"""Evaluate observations against frozen criteria; never accept asserted verdicts."""
from __future__ import annotations
import copy
import math
from .validation import ContractError, validate_record


def evaluate_criterion(definition, observed):
    """Compare a scalar or CriterionResult; missing/mistyped evidence is unknown.

    Attestations require authenticated host integration, deliberately unavailable
    in this pure evaluator. An editable string cannot authenticate a reviewer.
    """
    definition = validate_record('criterion', definition)
    if isinstance(observed, dict):
        if observed.get('unit') != definition['unit']:
            return 'unknown'
        value = observed.get('observed')
    else:
        value = observed
        if definition['unit'] is not None:
            return 'unknown'  # A scalar alone provides no unit provenance.
    if value is None:
        return 'unknown'
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError('non-finite observation')
    predicate, expected = definition['predicate'], definition['expected']
    numeric = type(value) in (int, float)
    if predicate == 'attested':
        return 'unknown'
    if predicate == 'is_true':
        if type(value) is not bool:
            return 'unknown'
        success = value
    elif predicate == 'equals':
        if type(value) is not type(expected):
            # JSON numbers share a type, but booleans do not.
            if not (numeric and type(expected) in (int, float)):
                return 'unknown'
        success = value == expected
    elif not numeric:
        return 'unknown'
    elif predicate == 'at_most':
        success = value <= expected
    elif predicate == 'at_least':
        success = value >= expected
    elif predicate == 'between':
        success = expected['lower'] <= value <= expected['upper']
    else:
        raise ContractError('unsupported predicate')
    return 'satisfied' if success else 'violated'


def _aggregate(states):
    if 'FAILED' in states:
        return 'FAILED'
    if states and all(s == 'PASSED' for s in states):
        return 'PASSED'
    unresolved = [s for s in states if s != 'PASSED']
    if unresolved and all(s == 'BLOCKED' for s in unresolved):
        return 'BLOCKED'
    if unresolved and all(s == 'NOT_RUN' for s in unresolved):
        return 'NOT_RUN'
    return 'REQUIRES_REVIEW'


def _artifact_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith('artifact_ids'):
                yield from item
            elif key.endswith('artifact_id') and item is not None:
                yield item
            else:
                yield from _artifact_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _artifact_refs(item)


def _execution_gaps(plan, result, artifact_data, provenance):
    gaps = []
    receipt = result['receipt']
    if receipt is None:
        return ['receipt']
    if receipt['termination'] != 'normal' or (plan['kind'] == 'executable' and receipt['exit_code'] != 0):
        gaps.append('incomplete_execution')
    if receipt['command'] != plan['command']:
        gaps.append('command_identity')
    contract = plan['execution_contract']
    actual = receipt['execution_evidence']
    if contract:
        if actual is None:
            gaps.append('execution_capture')
        else:
            for field in ('mode', 'source_digest', 'distribution_digest'):
                if actual[field] != contract[field]:
                    gaps.append('execution_' + field)
            expected = set(contract['expected_test_ids'])
            if expected != set(actual['collected_test_ids']) or expected != set(actual['executed_test_ids']):
                gaps.append('test_identity')
            if contract['mode'] != 'not_applicable':
                if not expected:
                    gaps.append('empty_test_selection')
                if not actual['first_party_origins'] or not actual['manifest_artifact_ids']:
                    gaps.append('import_origins')
                manifests = []
                for ref in contract['manifest_artifact_ids']:
                    if ref in artifact_data:
                        manifests.append(validate_record('execution-manifest', artifact_data[ref]))
                if not manifests or set(contract['manifest_artifact_ids']) != set(actual['manifest_artifact_ids']):
                    gaps.append('import_manifest_missing')
                else:
                    expected_origins = [o for manifest in manifests for o in manifest['origins']]
                    identity = lambda o: (o['name'], o['path'], o['sha256'])
                    if sorted(map(identity, expected_origins)) != sorted(map(identity, actual['first_party_origins'])):
                        gaps.append('import_origin_mismatch')
                    for manifest in manifests:
                        if (manifest['source_digest'] != contract['source_digest'] or
                            manifest['distribution_digest'] != contract['distribution_digest'] or
                            manifest['config_digest'] != provenance['config_digest'] or
                            manifest['environment_digest'] != provenance['environment_digest'] or
                            (contract['mode'] == 'distribution' and manifest['build_tool'] is None)):
                            gaps.append('import_manifest_identity')
            counts = result['counts']
            if expected:
                if counts is None or counts['collected'] != len(expected):
                    gaps.append('test_counts')
                elif any(counts[k] for k in ('skipped', 'xfailed', 'xpassed', 'errors')):
                    gaps.append('unaccepted_test_outcomes')
                elif sum(counts[k] for k in ('passed', 'failed', 'skipped', 'xfailed', 'xpassed')) != counts['collected']:
                    gaps.append('test_count_reconciliation')
    elif actual is not None:
        gaps.append('unexpected_execution_capture')
    static = plan['static_contract']
    measured = receipt['static_evidence']
    if static:
        if measured is None:
            gaps.append('static_capture')
        else:
            if not measured['assessment_only'] or measured['before_digest'] != measured['after_digest'] or measured['before_digest'] != plan['candidate_digest']:
                gaps.append('static_source_mutation')
            accounted = set(measured['checked_paths']) | {r['path'] for r in measured['excluded'] + measured['unchecked']}
            if not set(static['intended_paths']) <= accounted:
                gaps.append('static_scope')
            policy_record = artifact_data.get(static['policy_artifact_id'])
            limitations = measured['excluded'] + measured['unchecked'] + measured['suppressions']
            if policy_record is None:
                gaps.append('static_policy_unavailable')
            else:
                policy_record = validate_record('static-policy', policy_record)
                if policy_record['policy_digest'] != plan['policy_digest'] or any(r not in policy_record['allowed_limitations'] for r in limitations):
                    gaps.append('static_limitation_not_accepted')
            if any(r['policy_ref'] != static['policy_artifact_id'] for r in measured['excluded'] + measured['unchecked'] + measured['suppressions']):
                gaps.append('static_limitation_policy')
    elif measured is not None:
        gaps.append('unexpected_static_capture')
    if plan['evidence_import']:
        # Imported producer strings, host refs and timestamps need an authenticated
        # import verifier. Until P5/P7 supplies one they are explicitly insufficient.
        gaps.append('import_authentication_unverified')
    return gaps


def evaluate_run(evidence, plans, unavailable_artifacts=None, artifact_data=None):
    """Internal evaluator; validate_run owns structural and reference validation."""
    out = copy.deepcopy(evidence)
    artifact_data = artifact_data or {}
    by_id = {p['module_id']: p for p in plans}
    known_artifacts = {a['id'] for a in evidence['artifacts'] + evidence['plans']}
    unavailable = set(unavailable_artifacts or ())
    module_states = {}
    required_gaps = set()
    required_failures = set()
    capabilities = {c['id']: c for c in out['capabilities']}
    for result in out['results']:
        plan = by_id[result['module_id']]
        required = plan['required'] or capabilities[plan['capability_id']]['required']
        observations = {c['criterion_id']: c for c in result['criteria']}
        outcomes = []
        gaps = _execution_gaps(plan, result, artifact_data, out['provenance'])
        if any(item['id'] not in known_artifacts - unavailable for item in plan['inputs']):
            gaps.append('input_artifacts_unavailable')
        if plan['plan_id'] in unavailable:
            gaps.append('frozen_plan_unavailable')
        if any(ref not in known_artifacts - unavailable for ref in _artifact_refs(plan)):
            gaps.append('plan_artifacts_unavailable')
        if not set(out['environment']['isolation_requested']) <= set(out['environment']['isolation_enforced']):
            gaps.append('isolation_unavailable')
        for definition in plan['criteria']:
            observed = observations.get(definition['id'])
            outcome = evaluate_criterion(definition, observed)
            if observed is not None:
                refs = observed['artifact_ids']
                if not refs or not set(refs) <= known_artifacts - unavailable:
                    outcome = 'unknown'
                observed['outcome'] = outcome
            outcomes.append(outcome)
        if any(ref not in known_artifacts - unavailable for ref in _artifact_refs(result)):
            gaps.append('result_artifacts_unavailable')
        if result['reused_from'] is not None:
            gaps.append('reuse_identity_unverified')
        counts_failed = bool(result['counts'] and result['counts']['failed'])
        if counts_failed:
            gaps.append('tool_reported_failed_tests')
        # A known violation is retained through timeout or unrelated gaps.
        if 'violated' in outcomes or counts_failed:
            state = 'FAILED'
        elif result['execution'] == 'not_run':
            state = 'NOT_RUN'
        elif result['execution'] == 'blocked':
            state = 'BLOCKED'
        elif result['execution'] != 'completed' or gaps or any(v != 'satisfied' for v in outcomes):
            state = 'REQUIRES_REVIEW'
        else:
            state = 'PASSED'
        result['assessment'] = state
        result['reason'] = 'Evaluated frozen criteria.' + (' Evidence gaps: ' + ', '.join(gaps) + '.' if gaps else '')
        module_states.setdefault(result['module_id'], []).append(state)
        if required and state == 'FAILED':
            required_failures.add(result['module_id'])
        elif required and state != 'PASSED':
            required_gaps.add(result['module_id'])
    states = {mid: _aggregate(values) for mid, values in module_states.items()}
    # Propagate unresolved dependencies to a fixed point, independent of plan order.
    for _ in plans:
        for plan in plans:
            mid = plan['module_id']
            if any(states.get(dep) != 'PASSED' for dep in plan['depends_on']) and states.get(mid) != 'FAILED':
                states[mid] = 'BLOCKED'
    for plan in plans:
        mid = plan['module_id']
        if mid not in states:
            states[mid] = 'NOT_RUN'
        if any(states.get(dep) != 'PASSED' for dep in plan['depends_on']) and states[mid] != 'FAILED':
            states[mid] = 'BLOCKED'
        if plan['required'] and states[mid] != 'PASSED':
            (required_failures if states[mid] == 'FAILED' else required_gaps).add(mid)
    for capability in out['capabilities']:
        disposition = capability['disposition']
        if disposition == 'not_applicable':
            state = 'NOT_APPLICABLE'
        elif disposition == 'deferred':
            state = 'NOT_RUN'
        elif disposition == 'unresolved':
            state = 'REQUIRES_REVIEW'
        else:
            state = _aggregate([states[mid] for mid in capability['module_ids']])
        capability['assessment'] = state
        if capability['required'] and state != 'PASSED':
            (required_failures if state == 'FAILED' else required_gaps).add(capability['id'])
    impact = out['change_impact']
    adoption = out['adoption']
    candidate = out['candidate']['snapshot_digest']
    policy = out['provenance']['policy_digest']
    if impact['candidate_digest'] != candidate or impact['requirement_inventory_digest'] != out['provenance']['specification_digest']:
        required_gaps.add('change_impact_identity')
    inventory = artifact_data.get(impact['inventory_artifact_id'])
    if inventory is None:
        required_gaps.add('change_inventory_unavailable')
    else:
        inventory = validate_record('change-inventory', inventory)
        projected = [{k: v for k, v in item.items() if k not in ('before_digest', 'after_digest')} for item in inventory['changes']]
        if (inventory['baseline_digest'] != impact['baseline_digest'] or inventory['candidate_digest'] != candidate or
            sorted(projected, key=lambda c: c['path']) != sorted(impact['changes'], key=lambda c: c['path'])):
            required_gaps.add('change_inventory_mismatch')
    if impact['status'] != 'reviewed':
        required_gaps.add('change_impact_review')
    changed = {c['path'] for c in impact['changes']}
    mapped = {p for b in impact['behaviours'] for p in b['changed_paths']}
    if mapped != changed:
        required_gaps.add('change_impact_paths')
    unresolved = {b['id'] for b in impact['behaviours'] if b['disposition'] == 'unresolved'}
    if unresolved or set(impact['unresolved_behavior_ids']) != unresolved:
        required_gaps.add('change_impact_unresolved')
    for behaviour in impact['behaviours']:
        if behaviour['disposition'] == 'covered':
            linked = [by_id[mid] for mid in behaviour['module_ids']]
            required_links = [p for p in linked if p['required'] or capabilities[p['capability_id']]['required']]
            requirements = {r for p in required_links for r in p['requirement_ids']}
            if not required_links or not set(behaviour['requirement_ids']) <= requirements:
                required_gaps.add('behaviour:' + behaviour['id'])
        if behaviour['disposition'] != 'unresolved' and not behaviour['review_artifact_id']:
            required_gaps.add('behaviour_review:' + behaviour['id'])
    if adoption['candidate_digest'] != candidate or adoption['policy_digest'] != policy or adoption['run_id'] != out['run_id']:
        required_gaps.add('adoption_identity')
    if adoption['enforcement'] in ('protected_ci_verified', 'protected_ci_requested'):
        required_gaps.add('protection_authentication_unverified')
        adoption['enforcement'] = 'protected_ci_requested'
    for area, value in [('adoption', adoption), ('change_impact', impact)]:
        if any(ref not in known_artifacts - unavailable for ref in _artifact_refs(value)):
            required_gaps.add(area + '_artifacts')
    if out['state'] != 'finalised':
        required_gaps.add('run_not_finalised')
    blocking = [f['id'] for f in out['findings'] if f['blocking'] and
                (f['resolution'] == 'open' or not f['resolution_artifact_ids'] or
                 not set(f['resolution_artifact_ids']) <= known_artifacts - unavailable)]
    outcome = 'REJECTED' if required_failures or blocking else 'INSUFFICIENT_EVIDENCE' if required_gaps else 'ACCEPTED'
    out['gate'] = {'outcome': outcome, 'policy_digest': policy,
                   'required_failures': sorted(required_failures), 'required_gaps': sorted(required_gaps),
                   'blocking_finding_ids': blocking, 'rationale': 'Recomputed from frozen criteria and available evidence.'}
    adoption['completion'] = 'verified' if outcome == 'ACCEPTED' else 'incomplete'
    adoption['required_gap_ids'] = sorted(required_gaps | required_failures | set(blocking))
    return out


def evaluate_gate(evidence, plans):
    """Validate and evaluate metadata only; artifact availability stays unverified."""
    from .validation import validate_run
    return validate_run(evidence, plans)['gate']


def exit_code(gate, cancelled=False, runner_error=False):
    if cancelled:
        return 130
    if runner_error:
        return 3
    if gate['outcome'] == 'REJECTED' or gate.get('required_failures') or gate.get('blocking_finding_ids'):
        return 1
    if gate['outcome'] != 'ACCEPTED' or gate.get('required_gaps'):
        return 2
    return 0
