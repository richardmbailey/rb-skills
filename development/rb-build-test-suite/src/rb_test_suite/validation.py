"""Bounded parsing, local schema validation, and deterministic record checks."""
from __future__ import annotations
import copy
import hashlib
import json
import math
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path, PurePosixPath

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from .models import RECORD_MODELS, CAPABILITY_IDS, schemas

class ContractError(ValueError):
    """Invalid input or inconsistent references (CLI exit 3)."""


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ContractError(f'duplicate key: {key}')
        out[key] = value
    return out


def _bounded(payload, max_bytes):
    if not isinstance(payload, (str, bytes)):
        raise ContractError('payload must be text or bytes')
    raw = payload.encode('utf-8') if isinstance(payload, str) else payload
    if len(raw) > max_bytes:
        raise ContractError('input exceeds byte limit')
    try:
        return raw.decode('utf-8')
    except UnicodeError as exc:
        raise ContractError('input must be UTF-8') from exc


def _finite(value, depth=0):
    if depth > 64:
        raise ContractError('input exceeds nesting limit')
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError('non-finite number')
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ContractError('object keys must be strings')
            _finite(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _finite(item, depth + 1)
    elif value is not None and type(value) not in (str, int, float, bool):
        raise ContractError('value is not a JSON scalar')


def parse_json(payload, max_bytes=1048576):
    try:
        data = json.loads(_bounded(payload, max_bytes), object_pairs_hook=_pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ContractError('non-finite number')))
        _finite(data)
        if not isinstance(data, dict):
            raise ContractError('record root must be an object')
        return data
    except (ValueError, RecursionError) as exc:
        raise ContractError(str(exc)) from exc


class _Loader(yaml.SafeLoader):
    def compose_node(self, parent, index):
        if self.check_event(yaml.AliasEvent):
            raise ContractError('YAML aliases are not accepted')
        return super().compose_node(parent, index)

    def construct_mapping(self, node, deep=False):
        if not isinstance(node, yaml.MappingNode):
            raise ContractError('expected YAML mapping')
        return _pairs((self.construct_object(k, deep=deep), self.construct_object(v, deep=deep))
                      for k, v in node.value)

# Keep timestamps as strings so both parser routes use the same format checker.
_Loader.yaml_implicit_resolvers = {
    k: [(tag, regex) for tag, regex in vals if tag != 'tag:yaml.org,2002:timestamp']
    for k, vals in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def parse_yaml(payload, max_bytes=1048576):
    try:
        data = yaml.load(_bounded(payload, max_bytes), Loader=_Loader)
        _finite(data)
        if not isinstance(data, dict):
            raise ContractError('record root must be an object')
        return data
    except (yaml.YAMLError, ValueError, TypeError, RecursionError) as exc:
        raise ContractError(str(exc)) from exc


@lru_cache(maxsize=1)
def _validators():
    bundle = schemas()
    registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in bundle.values())
    return {kind: Draft202012Validator(bundle[kind + '.schema.json'], registry=registry,
                                       format_checker=FormatChecker()) for kind in RECORD_MODELS}


def _unique(values, label):
    if len(values) != len(set(values)):
        raise ContractError('duplicate ' + label)


def relative_path(value):
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or '\\' in value or '\x00' in value or ':' in value:
        raise ContractError('unsafe relative path: ' + value)
    return path


def contained_path(root, value):
    relative_path(value)
    root = Path(root).resolve()
    resolved = (root / value).resolve()
    if not resolved.is_relative_to(root):
        raise ContractError('path escapes assigned root: ' + value)
    if resolved.exists() and not (resolved.is_file() or resolved.is_dir()):
        raise ContractError('unexpected device: ' + value)
    return resolved


def _walk_checks(data):
    if isinstance(data, dict):
        for key, value in data.items():
            if key in ('path', 'previous_path', 'cwd', 'project_root', 'output_path', 'backup_path', 'policy_path', 'distribution_path', 'evidence_import_path', 'change_impact_path') and value is not None:
                relative_path(value)
            if key in ('scope', 'excluded_inputs', 'changed_paths', 'intended_paths', 'checked_paths',
                       'allowed_read_paths', 'allowed_write_paths', 'prohibited_paths', 'input_paths', 'config_paths', 'instruction_paths', 'operations'):
                for path in value:
                    relative_path(path)
            if key == 'first_party_paths':
                for path in value.values():
                    relative_path(path)
            _walk_checks(value)
        for start, end in [('started_at', 'finished_at'), ('window_start', 'window_end'), ('run_started_at', 'run_finished_at')]:
            if data.get(start) and data.get(end) and datetime.fromisoformat(data[start]) > datetime.fromisoformat(data[end]):
                raise ContractError('time order: ' + start + ' > ' + end)
    elif isinstance(data, list):
        for item in data:
            _walk_checks(item)


def _criterion_checks(c):
    p, expected, kind = c['predicate'], c['expected'], c['type']
    numeric = type(expected) in (int, float)
    if p in ('at_most', 'at_least', 'between') and kind != 'metric':
        raise ContractError('numeric predicate requires metric criterion')
    if p in ('at_most', 'at_least') and not numeric:
        raise ContractError('numeric predicate requires numeric bound')
    if p == 'between' and (not isinstance(expected, dict) or expected['lower'] > expected['upper']):
        raise ContractError('between requires ordered lower/upper bounds')
    if p == 'is_true' and (kind != 'assertion' or expected is not True):
        raise ContractError('is_true requires an assertion expecting true')
    if p == 'equals' and isinstance(expected, dict):
        raise ContractError('equals requires a scalar')
    if (p == 'attested') != (kind == 'attestation') or (p == 'attested' and not isinstance(expected, str)):
        raise ContractError('attestation requires named attested predicate')


def validate_record(kind, data):
    if kind not in RECORD_MODELS:
        raise ContractError('unknown record kind: ' + kind)
    _finite(data)
    try:
        # Validate original scalar types first: JSON booleans must not become 1.0.
        _validators()[kind].validate(data)
        RECORD_MODELS[kind].model_validate(data)
    except Exception as exc:
        raise ContractError(f'{kind}: {exc}') from exc
    out = copy.deepcopy(data)
    _walk_checks(out)
    if kind == 'criterion':
        _criterion_checks(out)
    if kind in ('module-plan', 'module-request'):
        _unique([c['id'] for c in out['criteria']], 'criterion ID')
        _unique(out['requirement_ids'], 'requirement ID')
        _unique(out['depends_on'], 'dependency')
        for c in out['criteria']:
            _criterion_checks(c)
            if c['requirement_id'] not in out['requirement_ids']:
                raise ContractError('criterion references undeclared requirement')
    if kind == 'module-request':
        executable = out['kind'] == 'executable'
        if executable != (out['command'] is not None) or executable != (out['execution_request'] is not None) or executable == (out['evidence_import_path'] is not None):
            raise ContractError('module request execution/import mismatch')
        if not executable and out['static_request'] is not None:
            raise ContractError('import request cannot declare static execution')
        request = out['execution_request']
        if request:
            _unique(request['expected_test_ids'], 'expected test ID')
            if (request['mode'] == 'distribution') != (request['distribution_path'] is not None):
                raise ContractError('distribution request requires only its distribution path')
            if out['required'] and request['mode'] != 'not_applicable' and not request['expected_test_ids']:
                raise ContractError('required test request has empty selection')
    if kind == 'module-plan':
        if out['required'] and out['execution_contract'] and out['execution_contract']['mode'] != 'not_applicable' and not out['execution_contract']['expected_test_ids']:
            raise ContractError('required test module has empty selection')
        if out['execution_contract'] and out['execution_contract']['source_digest'] != out['candidate_digest']:
            raise ContractError('execution contract candidate mismatch')
        imported = out['evidence_import']
        if imported and (imported['expected_candidate_digest'] != out['candidate_digest'] or
                         imported['expected_policy_digest'] != out['policy_digest'] or imported['target'] != out['target']):
            raise ContractError('import plan identity mismatch')
    if kind in ('evidence', 'report', 'config'):
        ids = [c['id'] for c in out['capabilities']]
        if set(ids) != set(CAPABILITY_IDS) or len(ids) != 43:
            raise ContractError('exactly one disposition per capability required')
    if kind == 'change-inventory':
        _unique([c['path'] for c in out['changes']], 'inventory path')
        for change in out['changes']:
            action = change['change']
            if ((action == 'added') != (change['before_digest'] is None) or
                (action == 'deleted') != (change['after_digest'] is None) or
                (action == 'renamed') != (change['previous_path'] is not None)):
                raise ContractError('inconsistent inventory before/after identities')
    if kind == 'catalogue':
        if [(e['number'], e['id']) for e in out['entries']] != list(enumerate(CAPABILITY_IDS, 1)):
            raise ContractError('catalogue must retain all 43 IDs in order')
    if kind == 'config':
        _unique([p['name'] for p in out['profiles']], 'profile')
        if out['default_profile'] not in {p['name'] for p in out['profiles']}:
            raise ContractError('default profile is undefined')
        modules = {p['module_id']: p for p in out['modules']}
        _unique([p['module_id'] for p in out['modules']], 'module request ID')
        criteria = {c for source in out['requirements'] for c in source['criterion_ids']}
        for plan in out['modules']:
            validate_record('module-request', plan)
            if not set(plan['depends_on']) <= modules.keys():
                raise ContractError('unknown module request dependency')
            if not {c['id'] for c in plan['criteria']} <= criteria:
                raise ContractError('authoring criterion lacks pinned requirement source')
        pending, complete = set(modules), set()
        while pending:
            ready = {mid for mid in pending if set(modules[mid]['depends_on']) <= complete}
            if not ready:
                raise ContractError('module request dependency cycle')
            complete.update(ready)
            pending.difference_update(ready)
        for capability in out['capabilities']:
            _unique(capability['module_ids'], 'capability module request')
            if not set(capability['module_ids']) <= modules.keys():
                raise ContractError('unknown capability module request')
            if any(modules[mid]['capability_id'] != capability['id'] for mid in capability['module_ids']):
                raise ContractError('module request primary capability mismatch')
        for mid, request in modules.items():
            capability = next(c for c in out['capabilities'] if c['id'] == request['capability_id'])
            if mid not in capability['module_ids']:
                raise ContractError('module request omitted from primary capability')
    return out


def validate_run(data, plans, artifact_root=None):
    from .policy import evaluate_run
    evidence = validate_record('evidence', data)
    if evidence['gate']['policy_digest'] != evidence['provenance']['policy_digest']:
        raise ContractError('gate/provenance policy mismatch')
    if evidence.get('evaluation') and evidence['evaluation']['policy_digest'] != evidence['provenance']['policy_digest']:
        raise ContractError('evaluation/provenance policy mismatch')
    plans = [validate_record('module-plan', plan) for plan in plans]
    _unique([p['module_id'] for p in plans], 'module ID')
    _unique([p['plan_id'] for p in plans], 'plan ID')
    by_id = {p['module_id']: p for p in plans}
    artifacts = evidence['artifacts'] + evidence['plans']
    _unique([a['id'] for a in artifacts], 'artifact ID')
    _unique([a['path'] for a in artifacts], 'artifact path')
    registry = {a['id']: a for a in artifacts}
    input_registry = {}
    for plan in plans:
        _unique([a['id'] for a in plan['inputs']], 'plan input ID')
        for item in plan['inputs']:
            prior = registry.get(item['id'], input_registry.get(item['id']))
            if prior is not None and item != prior:
                raise ContractError('conflicting input artifact identity: ' + item['id'])
            input_registry[item['id']] = item
    _unique([f['id'] for f in evidence['findings']], 'finding ID')
    _unique([(r['module_id'], r['attempt']) for r in evidence['results']], 'module attempt')
    _unique([r['receipt']['id'] for r in evidence['results'] if r['receipt']], 'receipt ID')
    plan_ids = {a['id'] for a in evidence['plans']}
    if plan_ids != {p['plan_id'] for p in plans}:
        raise ContractError('frozen plan reference set differs from supplied plans')
    for p in plans:
        if p['run_id'] != evidence['run_id'] or p['candidate_digest'] != evidence['candidate']['snapshot_digest'] or p['policy_digest'] != evidence['provenance']['policy_digest']:
            raise ContractError('plan/run identity mismatch')
        if not set(p['depends_on']) <= by_id.keys():
            raise ContractError('unknown dependency')
    visited, active = set(), set()
    def visit(module):
        if module in active:
            raise ContractError('dependency cycle')
        if module in visited:
            return
        active.add(module)
        for dep in by_id[module]['depends_on']:
            visit(dep)
        active.remove(module)
        visited.add(module)
    for module in by_id:
        visit(module)
    for c in evidence['capabilities']:
        _unique(c['module_ids'], 'capability module reference')
        if not set(c['module_ids']) <= by_id.keys():
            raise ContractError('unknown capability module')
        for mid in c['module_ids']:
            if by_id[mid]['capability_id'] != c['id']:
                raise ContractError('module assigned to wrong primary capability')
    for p in plans:
        cap = next(c for c in evidence['capabilities'] if c['id'] == p['capability_id'])
        if p['module_id'] not in cap['module_ids']:
            raise ContractError('plan omitted from primary capability')
    for r in evidence['results']:
        if r['module_id'] not in by_id or r['plan_id'] != by_id[r['module_id']]['plan_id']:
            raise ContractError('result plan reference mismatch')
        _unique([c['criterion_id'] for c in r['criteria']], 'criterion observation')
        if not {c['criterion_id'] for c in r['criteria']} <= {c['id'] for c in by_id[r['module_id']]['criteria']}:
            raise ContractError('unknown criterion observation')
    requirements = {q for p in plans for q in p['requirement_ids']}
    for finding in evidence['findings']:
        if not set(finding['module_ids']) <= by_id.keys() or not set(finding['requirement_ids']) <= requirements:
            raise ContractError('unknown finding reference')
    for result in evidence['results']:
        receipt = result['receipt']
        if receipt and (datetime.fromisoformat(receipt['started_at']) < datetime.fromisoformat(evidence['started_at']) or
                        (evidence['finished_at'] and datetime.fromisoformat(receipt['finished_at']) > datetime.fromisoformat(evidence['finished_at']))):
            raise ContractError('receipt is outside run time window')
    impact = evidence['change_impact']
    _unique([b['id'] for b in impact['behaviours']], 'behaviour ID')
    _unique([c['path'] for c in impact['changes']], 'changed path')
    for b in impact['behaviours']:
        if not set(b['module_ids']) <= by_id.keys() or not set(b['requirement_ids']) <= requirements:
            raise ContractError('unknown impact reference')
    if not any(p['required'] or next(c['required'] for c in evidence['capabilities'] if c['id'] == p['capability_id']) for p in plans):
        raise ContractError('acceptance policy has no required criteria')
    unavailable = set()
    artifact_data = {}
    if artifact_root is not None:
        for a in artifacts:
            path = contained_path(artifact_root, a['path'])
            if a['access'] != 'local' or not path.is_file():
                unavailable.add(a['id'])
                continue
            with path.open('rb') as stream:
                actual_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if path.stat().st_size != a['bytes'] or actual_digest != a['sha256']:
                raise ContractError('artifact bytes/digest mismatch: ' + a['id'])
            if a['media_type'] == 'application/json' and a['bytes'] <= 1048576:
                artifact_data[a['id']] = parse_json(path.read_bytes())
    else:
        # A metadata record does not prove that its raw artifact is available.
        unavailable.update(a['id'] for a in artifacts)
    for plan in plans:
        frozen = artifact_data.get(plan['plan_id'])
        if frozen is not None and frozen != plan:
            raise ContractError('supplied plan differs from frozen plan artifact')
        if frozen is None:
            unavailable.add(plan['plan_id'])
    result = evaluate_run(evidence, plans, unavailable_artifacts=unavailable, artifact_data=artifact_data)
    def digest(record):
        return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    assessed = {key: value for key, value in result.items() if key != 'evaluation'}
    assessed_digest = digest(assessed)
    if evidence.get('evaluation') is not None:
        existing = evidence['evaluation']
        original_assessed = {key: value for key, value in evidence.items() if key != 'evaluation'}
        if existing['assessed_evidence_digest'] != digest(original_assessed) or assessed_digest != existing['assessed_evidence_digest']:
            raise ContractError('stale or inconsistent evaluation derivation; explicit reevaluation required')
        result['evaluation'] = copy.deepcopy(existing)
    else:
        result['evaluation'] = {'schema_version': '1.0.0', 'evaluator_version': '0.1.0',
                                'source_evidence_digest': digest(data), 'assessed_evidence_digest': assessed_digest,
                                'policy_digest': evidence['provenance']['policy_digest'],
                                'evaluated_at': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}
    validate_record('evidence', result)
    return result


def parse_xml(payload, max_bytes=1048576):
    """Parse bounded tool XML without DTDs, entity expansion or external input."""
    from defusedxml.ElementTree import fromstring
    from defusedxml.common import DefusedXmlException
    from xml.etree.ElementTree import ParseError
    try:
        root = fromstring(_bounded(payload, max_bytes), forbid_dtd=True,
                          forbid_entities=True, forbid_external=True)
        pending = [(root, 0)]
        while pending:
            node, depth = pending.pop()
            if depth > 64:
                raise ContractError('XML exceeds nesting limit')
            pending.extend((child, depth + 1) for child in node)
        return root
    except (DefusedXmlException, ParseError, ValueError) as exc:
        raise ContractError(str(exc)) from exc
