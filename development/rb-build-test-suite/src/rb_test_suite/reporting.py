"""Offline presentation of already evaluated evidence. This module never runs policy.

The evaluation digest protects against accidental mutation, not a hostile producer.
Call validate_run with the evidence bundle before projecting a new source record.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import quote

from .models import CAPABILITY_IDS
from .policy import evaluate_criterion
from .validation import ContractError, validate_record, relative_path

MAX_REPORT_BYTES = 8 * 1024 * 1024
STATES = ('PASSED', 'FAILED', 'NOT_RUN', 'NOT_APPLICABLE', 'BLOCKED', 'REQUIRES_REVIEW')
SECTIONS = ('overview', 'capabilities', 'checks', 'findings', 'scientific', 'independence',
            'performance', 'provenance', 'limitations')
ASSETS = Path(__file__).resolve().parents[2] / 'assets' / 'report'


def canonical_digest(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode()).hexdigest()


def _bounded(record):
    if len(json.dumps(record, allow_nan=False).encode()) > MAX_REPORT_BYTES:
        raise ContractError('report input exceeds 8 MiB bound')


def _unique(values, label):
    if len(values) != len(set(values)):
        raise ContractError('duplicate ' + label)


def _refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith('artifact_ids') or key == 'source_artifact_ids':
                yield from item
            elif key.endswith('artifact_id') and item is not None:
                yield item
            else:
                yield from _refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _refs(item)


def _summary(capabilities, modules, test_counts, logical_checks=None):
    failed = {m['module_id']: m['required'] for m in modules if m['assessment'] == 'FAILED'}
    return {'capability_counts': {s: sum(c['assessment'] == s for c in capabilities) for s in STATES},
            'logical_checks': len({m['module_id'] for m in modules}) if logical_checks is None else logical_checks,
            'attempts': len(modules), 'test_counts': test_counts,
            'required_failed': sum(failed.values()), 'optional_failed': sum(not r for r in failed.values())}


def _counts(results):
    # A shared receipt denotes one execution. Distinct receipts remain distinct,
    # even when the same test IDs run again on a retry.
    executions = {}
    for result in results:
        counts = result['counts']
        if counts is None:
            continue
        if sum(counts[k] for k in ('passed', 'failed', 'skipped', 'xfailed', 'xpassed')) > counts['collected']:
            raise ContractError('test outcomes exceed collected tests')
        if result['execution'] == 'completed' and not counts['errors'] and sum(counts[k] for k in ('passed', 'failed', 'skipped', 'xfailed', 'xpassed')) != counts['collected']:
            raise ContractError('completed test counts do not reconcile')
        if not result['receipt']:
            raise ContractError('test counts without execution receipt')
        receipt = result['receipt']
        key = receipt['id']
        entry = (receipt, counts)
        if key in executions and executions[key] != entry:
            raise ContractError('shared execution has contradictory counts or receipt')
        executions[key] = entry
    if not executions:
        return None
    return {k: sum(entry[1][k] for entry in executions.values()) for k in next(iter(executions.values()))[1]}


def project_report(evidence, plans, evidence_digest):
    """Project a validate_run result without modifying its dates, policy or outcomes.

    evidence_digest is SHA-256 of the persisted evidence bytes (which may use any
    JSON whitespace). The immutable derivation separately binds its parsed values.
    """
    if hasattr(evidence, 'model_dump'):
        evidence = evidence.model_dump(mode='json')
    _bounded(evidence)
    e = validate_record('evidence', evidence)
    evaluation = e.get('evaluation')
    if not evaluation or evaluation['assessed_evidence_digest'] != canonical_digest({k: v for k, v in e.items() if k != 'evaluation'}):
        raise ContractError('projection requires an unchanged evaluated evidence record')
    if evaluation['policy_digest'] != e['provenance']['policy_digest'] or e['gate']['policy_digest'] != evaluation['policy_digest']:
        raise ContractError('evaluation policy mismatch')
    plans = [validate_record('module-plan', p.model_dump(mode='json') if hasattr(p, 'model_dump') else p) for p in plans]
    _bounded(plans)
    _unique([p['module_id'] for p in plans], 'module ID')
    _unique([p['plan_id'] for p in plans], 'plan ID')
    by_id = {p['module_id']: p for p in plans}
    if {p['plan_id'] for p in plans} != {a['id'] for a in e['plans']}:
        raise ContractError('frozen plan reference mismatch')
    artifacts = e['artifacts'] + e['plans']
    _unique([a['id'] for a in artifacts], 'artifact ID')
    _unique([a['path'] for a in artifacts], 'artifact path')
    known = {a['id'] for a in artifacts}
    if not set(_refs(e)) <= known or not set(_refs(plans)) <= known:
        raise ContractError('unknown artifact reference')
    caps = {c['id']: c for c in e['capabilities']}
    for p in plans:
        if (p['run_id'] != e['run_id'] or p['candidate_digest'] != e['candidate']['snapshot_digest']
                or p['policy_digest'] != e['provenance']['policy_digest']):
            raise ContractError('frozen plan identity mismatch')
        if p['module_id'] not in caps[p['capability_id']]['module_ids'] or not set(p['depends_on']) <= by_id.keys():
            raise ContractError('unknown plan reference')
    for c in caps.values():
        _unique(c['module_ids'], 'capability module ID')
        if any(mid not in by_id or by_id[mid]['capability_id'] != c['id'] for mid in c['module_ids']):
            raise ContractError('capability module mismatch')
    _unique([(r['module_id'], r['attempt']) for r in e['results']], 'module attempt')
    requirements = {q for p in plans for q in p['requirement_ids']}
    _unique([f['id'] for f in e['findings']], 'finding ID')
    for finding in e['findings']:
        if not set(finding['module_ids']) <= by_id.keys() or not set(finding['requirement_ids']) <= requirements:
            raise ContractError('unknown finding reference')
    for behaviour in e['change_impact']['behaviours']:
        if not set(behaviour['module_ids']) <= by_id.keys() or not set(behaviour['requirement_ids']) <= requirements:
            raise ContractError('unknown change-impact reference')
    modules = []
    for result in e['results']:
        p = by_id.get(result['module_id'])
        if p is None or result['plan_id'] != p['plan_id']:
            raise ContractError('result references unknown plan')
        definitions = {c['id']: c for c in p['criteria']}
        _unique([c['criterion_id'] for c in result['criteria']], 'criterion result')
        for c in result['criteria']:
            if c['criterion_id'] not in definitions:
                raise ContractError('unknown criterion result')
            if c['outcome'] != 'unknown' and evaluate_criterion(definitions[c['criterion_id']], c) != c['outcome']:
                raise ContractError('contradictory criterion outcome')
        if result['assessment'] == 'PASSED' and {c['criterion_id'] for c in result['criteria']} != definitions.keys():
            raise ContractError('passing module lacks criterion result')
        receipt = result['receipt']
        modules.append({k: copy.deepcopy(result[k]) for k in ('module_id', 'attempt', 'execution', 'assessment', 'reason', 'criteria', 'artifact_ids')}
                       | {'capability_id': p['capability_id'], 'required': p['required'] or caps[p['capability_id']]['required'],
                          'tool': receipt['tool'] if receipt else None,
                          'duration_seconds': receipt['duration_seconds'] if receipt else None,
                          'criterion_definitions': p['criteria'], 'execution_contract': p['execution_contract'],
                          'static_contract': p['static_contract'],
                          'execution_evidence': receipt['execution_evidence'] if receipt else None,
                          'static_evidence': receipt['static_evidence'] if receipt else None})
    scientific = []
    for m in modules:
        p = by_id[m['module_id']]
        for definition in p['criteria']:
            if definition['type'] != 'metric':
                continue
            scientific.append({'claim': definition['id'], 'requirement_id': definition['requirement_id'],
                               'module_ids': [m['module_id']], 'subtype': ', '.join(p['subtypes']) or 'metric',
                               'units': [definition['unit']] if definition['unit'] else [],
                               'oracle_refs': [a['id'] for a in p['inputs']],
                               'tolerance_justification': definition['justification'], 'outcome': m['assessment'],
                               'artifact_ids': m['artifact_ids'],
                               'limitations': ['Metric outcome is shown with its frozen criterion; no convergence or baseline is inferred.']})
    limitations = list(e['limitations'])
    for p in plans:
        if not any(m['module_id'] == p['module_id'] for m in modules):
            limitations.append('No attempt recorded for frozen module ' + p['module_id'] + '.')
    limitations.append('Raw artifacts require the original evidence bundle; copying this HTML alone does not copy those files.')
    sections = [{'id': s, 'title': s.replace('_', ' ').title(), 'availability': 'present',
                 'explanation': 'Recorded evidence for this run.'} for s in SECTIONS]
    for s in sections:
        if s['id'] == 'scientific' and not scientific:
            s.update(availability='unavailable', explanation='No numerical metric criteria were recorded.')
        if s['id'] == 'performance':
            s.update(availability='unavailable', explanation='No typed comparable baseline or sample series is available. Durations are descriptive process measurements, not performance acceptance evidence.')
    report = {k: copy.deepcopy(e[k]) for k in ('schema_version', 'run_id', 'candidate', 'focus', 'profile', 'gate',
                'capabilities', 'findings', 'independence', 'provenance', 'environment', 'adoption', 'change_impact')}
    report.update(evidence_digest=evidence_digest, rendered_at=evaluation['evaluated_at'],
                  run_started_at=e['started_at'], run_finished_at=e['finished_at'],
                  summary=_summary(e['capabilities'], modules, _counts(e['results']), len(plans)),
                  sections=sections, modules=modules, scientific_checks=scientific, charts=[],
                  artifact_links=artifacts, limitations=limitations)
    return validate_report(report)


def validate_report(report):
    _bounded(report)
    r = validate_record('report', report)
    if [s['id'] for s in r['sections']] != list(SECTIONS):
        raise ContractError('report must retain the nine ordered sections')
    logical = len({mid for c in r['capabilities'] for mid in c['module_ids']})
    if r['summary'] != _summary(r['capabilities'], r['modules'], r['summary']['test_counts'], logical):
        raise ContractError('report summary contradicts its rows')
    if r['gate']['outcome'] == 'ACCEPTED' and r['summary']['required_failed']:
        raise ContractError('accepted gate contradicts required module failure')
    counts = r['summary']['test_counts']
    if counts and sum(counts[k] for k in ('passed', 'failed', 'skipped', 'xfailed', 'xpassed')) > counts['collected']:
        raise ContractError('summary test outcomes exceed collected tests')
    _unique([(m['module_id'], m['attempt']) for m in r['modules']], 'report attempt')
    known = {a['id'] for a in r['artifact_links']}
    _unique([a['id'] for a in r['artifact_links']], 'report artifact')
    if not set(_refs(r)) <= known:
        raise ContractError('unknown report artifact reference')
    caps = {c['id']: c for c in r['capabilities']}
    _unique([c['id'] for c in r['charts']], 'chart ID')
    _unique([f['id'] for f in r['findings']], 'finding ID')
    module_ids = {mid for c in r['capabilities'] for mid in c['module_ids']}
    for finding in r['findings']:
        if not set(finding['module_ids']) <= module_ids:
            raise ContractError('unknown report finding module')
    for m in r['modules']:
        if m['module_id'] not in caps[m['capability_id']]['module_ids']:
            raise ContractError('report module capability mismatch')
        definitions = {d['id']: d for d in m['criterion_definitions']}
        _unique([d['id'] for d in m['criterion_definitions']], 'report criterion definition')
        _unique([c['criterion_id'] for c in m['criteria']], 'report criterion result')
        for c in m['criteria']:
            if c['criterion_id'] not in definitions or (c['outcome'] != 'unknown' and evaluate_criterion(definitions[c['criterion_id']], c) != c['outcome']):
                raise ContractError('report criterion mismatch')
        if m['assessment'] == 'PASSED' and (m['execution'] != 'completed' or len(m['criteria']) != len(definitions) or any(c['outcome'] != 'satisfied' for c in m['criteria'])):
            raise ContractError('report passing module lacks satisfied criteria')
    return r


def _text(value):
    if value is None:
        return 'Not captured / not applicable; no evidence inferred'
    if isinstance(value, (dict, list, bool)):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return str(value)


def _escape(value):
    return html.escape(_text(value), quote=True)


def _table(caption, headers, rows):
    return '<div class="table-scroll"><table><caption>' + _escape(caption) + '</caption><thead><tr>' + ''.join('<th scope="col">' + _escape(h) + '</th>' for h in headers) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + _escape(c) + '</td>' for c in row) + '</tr>' for row in rows) + '</tbody></table></div>'


def _record(title, record):
    if record is None:
        return '<h3>' + _escape(title) + '</h3><p>Not captured / not applicable; no evidence inferred.</p>'
    return _table(title, ['Field', 'Recorded value'], record.items())


def _chart(chart):
    """Accessible exact values plus a descriptive plot; no invented interpolation."""
    points = [(s, p) for s in chart['series'] for p in s['points']]
    table = _table(chart['title'] + ' — exact plotted values',
                   ['Series', 'Meaning', chart['x_label'] + ' (' + chart['x_unit'] + ')', chart['y_label'] + ' (' + chart['y_unit'] + ')'],
                   [(s['name'], s['meaning'], p['x'], 'Missing measurement' if p['y'] is None else p['y']) for s, p in points])
    measured = [p for _, p in points if p['y'] is not None]
    if not measured:
        return table + '<p>No finite measurements; plot unavailable.</p>'
    xmin, xmax = min(p['x'] for p in measured), max(p['x'] for p in measured)
    ymin, ymax = min(p['y'] for p in measured), max(p['y'] for p in measured)
    circles = ''.join(f'<circle cx="{40 + 500 * (p["x"] - xmin) / (xmax - xmin or 1):.3f}" cy="{210 - 180 * (p["y"] - ymin) / (ymax - ymin or 1):.3f}" r="4"><title>{_escape(s["name"])}: {_escape(p)}</title></circle>' for s, p in points if p['y'] is not None)
    return '<figure><figcaption>' + _escape(chart['title']) + '</figcaption><svg viewBox="0 0 600 260" role="img" aria-label="' + _escape(chart['title'] + '; exact values in following table') + '"><path d="M40 25 V210 H560" fill="none" stroke="currentColor"/>' + circles + '<text x="40" y="245">' + _escape(chart['x_label'] + ' (' + chart['x_unit'] + ')') + '</text><text x="40" y="15">' + _escape(chart['y_label'] + ' (' + chart['y_unit'] + ')') + '</text></svg></figure>' + table + _record('Chart provenance and limitations', {k: chart[k] for k in ('source_artifact_ids', 'limitations')})


def render_report(report):
    r = validate_report(report)
    css = (ASSETS / 'report.css').read_text()
    js = (ASSETS / 'report.js').read_text()
    content = {}
    content['overview'] = '<p class="gate">Gate: ' + _escape(r['gate']['outcome']) + '</p>'
    if r['gate']['outcome'] != 'ACCEPTED' or r['adoption']['completion'] != 'verified':
        content['overview'] += '<p class="warning">Incomplete assurance: this report does not establish verified completion.</p>'
    content['overview'] += _record('Run identity', {k: r[k] for k in ('run_id', 'focus', 'profile', 'run_started_at', 'run_finished_at', 'rendered_at', 'evidence_digest')})
    content['overview'] += '<p>Presentation timestamp is the saved evaluation time; rendering does not rerun tests.</p>'
    content['overview'] += _record('Candidate and scope', r['candidate']) + _record('Gate decision', r['gate'])
    content['overview'] += _record('Counts: capabilities, logical checks, attempts and test cases', r['summary'])
    content['overview'] += _record('Adoption and enforcement', r['adoption']) + _record('Changed behaviour mapping', r['change_impact'])
    content['capabilities'] = _table('All 43 capability dispositions', ['Capability', 'Assessment', 'Required', 'Selection', 'Reason', 'Module count', 'Module IDs'],
        [(c['id'], c['assessment'], c['required'], c['disposition'], c['reason'], len(c['module_ids']), c['module_ids']) for c in r['capabilities']])
    checks = []
    for index, m in enumerate(r['modules']):
        checks.append('<article class="check" data-state="' + m['assessment'] + '" data-required="' + str(m['required']).lower() + '" data-capability="' + m['capability_id'] + '"><h3 id="check-' + str(index) + '">' + _escape(m['module_id']) + ' · attempt ' + str(m['attempt']) + '</h3>')
        checks.append(_record('Execution and assessment', {k: m[k] for k in ('capability_id', 'required', 'execution', 'assessment', 'duration_seconds', 'tool', 'reason', 'artifact_ids')}))
        observations = {c['criterion_id']: c for c in m['criteria']}
        checks.append(_table('Frozen acceptance criteria and observations', ['Criterion / requirement', 'Type / predicate', 'Expected', 'Observed', 'Unit (expected / observed)', 'Outcome', 'Justification', 'Rationale / evidence'],
            [(d['id'] + ' / ' + d['requirement_id'], d['type'] + ' / ' + d['predicate'], d['expected'],
              observations.get(d['id'], {}).get('observed'), [d['unit'], observations.get(d['id'], {}).get('unit')],
              observations.get(d['id'], {}).get('outcome', 'unknown — no observation'), d['justification'],
              observations.get(d['id'], {})) for d in m['criterion_definitions']]))
        checks.append('<details open><summary>Execution identity and static scope</summary>')
        checks.extend(_record(k.replace('_', ' ').title(), m[k]) for k in ('execution_contract', 'execution_evidence', 'static_contract', 'static_evidence'))
        checks.append('</details></article>')
    content['capabilities'] += '<p>Recorded attempt links: ' + (' · '.join('<a href="#check-' + str(i) + '">' + _escape(m['module_id'] + ' / attempt ' + str(m['attempt'])) + '</a>' for i, m in enumerate(r['modules'])) or 'No attempts recorded') + '</p>'
    content['checks'] = '<div id="controls" hidden><label>Search checks <input id="search" type="search"></label><label>Assessment <select id="state"><option value="">All states</option>' + ''.join('<option>' + s + '</option>' for s in STATES if s != 'NOT_APPLICABLE') + '</select></label><label>Requirement <select id="required"><option value="">Required and optional</option><option value="true">Required</option><option value="false">Optional</option></select></label><label>Capability <select id="capability"><option value="">All capabilities</option>' + ''.join('<option>' + s + '</option>' for s in CAPABILITY_IDS) + '</select></label><p id="filter-count" role="status"></p></div>' + (''.join(checks) or '<p>No attempts recorded; see required gaps and capability dispositions.</p>')
    severity = {s: i for i, s in enumerate(('critical', 'high', 'medium', 'low', 'informational'))}
    content['findings'] = _table('Defects and gaps', ['ID', 'Severity', 'Claim', 'Requirements', 'Modules', 'Evidence', 'Remediation', 'Blocking', 'Resolution', 'Resolution evidence'],
        [(f['id'], f['severity'], f['claim'], f['requirement_ids'], f['module_ids'], f['artifact_ids'], f['remediation'], f['blocking'], f['resolution'], f['resolution_artifact_ids']) for f in sorted(r['findings'], key=lambda f: (severity[f['severity']], f['id']))]) if r['findings'] else '<p>No findings recorded. Required gaps remain visible in the gate decision.</p>'
    content['scientific'] = ''.join(_record('Scientific check', s) for s in r['scientific_checks']) + ''.join(_chart(c) for c in r['charts'])
    content['independence'] = _record('Independent verification', r['independence'])
    content['performance'] = _record('Environment and hardware', r['environment'])
    content['provenance'] = _record('Pinned digests', r['provenance']) + '<p>Raw artifact links require the evidence bundle. Availability is not rechecked by this offline page.</p><ul>'
    for a in r['artifact_links']:
        relative_path(a['path'])
        label = _escape(a['id'] + ' — ' + a['path'])
        if a['access'] == 'local' and a['sensitivity'] == 'ordinary':
            # Prefix and quote every segment: percent escapes and fragments cannot
            # become navigation outside the bundle. Download prevents active HTML.
            href = './' + '/'.join(quote(part, safe='') for part in a['path'].split('/'))
            label = '<a download rel="noopener" href="' + html.escape(href, quote=True) + '">' + label + '</a> (bundle required; may be unavailable)'
        else:
            label += ' (unavailable: ' + _escape(a['access']) + '; ' + _escape(a['sensitivity']) + ')'
        content['provenance'] += '<li>' + label + ' · SHA-256 ' + _escape(a['sha256']) + ' · ' + str(a['bytes']) + ' bytes</li>'
    content['provenance'] += '</ul>'
    content['limitations'] = '<ul>' + ''.join('<li>' + _escape(x) + '</li>' for x in r['limitations'] + r['environment']['limitations'] + r['independence']['limitations']) + '</ul>'
    data = json.dumps(r, ensure_ascii=False, allow_nan=False).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    page = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; base-uri \'none\'; form-action \'none\'; connect-src \'none\'"><title>Evidence report — ' + _escape(r['run_id']) + '</title><style>' + css + '</style></head><body><header><h1>Test suite evidence report</h1><p>' + _escape(r['run_id']) + '</p><nav aria-label="Report sections">' + ' '.join('<a href="#' + s + '">' + s.title() + '</a>' for s in SECTIONS) + '</nav></header><main>'
    page += ''.join('<section id="' + s['id'] + '"><h2>' + _escape(s['title']) + '</h2><p>' + _escape(s['explanation']) + '</p>' + content[s['id']] + '</section>' for s in r['sections'])
    page += '</main><script id="report-data" type="application/json">' + data + '</script><script>' + js + '</script></body></html>'
    if len(page.encode()) > 4 * MAX_REPORT_BYTES:
        raise ContractError('rendered report exceeds output bound')
    return page


def save_report(report, path):
    """Render completely, then replace one destination atomically; propagate errors."""
    page = render_report(report)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=destination.parent, prefix='.report-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(page)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return destination
