"""Source-to-presentation contracts; browser acceptance is a separate check."""
import copy
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_contracts import fixture
from rb_test_suite.reporting import (canonical_digest, project_report, render_report,
                                     save_report, validate_report, SECTIONS)
from rb_test_suite.validation import ContractError, validate_run


class Page(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.tags = []
        self.sections = []
        self.text = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == 'section':
            self.sections.append(attrs['id'])

    def handle_data(self, data):
        self.text.append(data)


class ReportingCases(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.plan, self.source = fixture(self.root)
        self.evidence = validate_run(self.source, [self.plan], self.root)
        self.raw = json.dumps(self.evidence).encode()
        self.digest = hashlib.sha256(self.raw).hexdigest()
        self.report = project_report(self.evidence, [self.plan], self.digest)

    def stamp(self, evidence):
        evidence['evaluation']['assessed_evidence_digest'] = canonical_digest({k: v for k, v in evidence.items() if k != 'evaluation'})

    def test_exact_projection_and_determinism(self):
        before = copy.deepcopy(self.evidence)
        again = project_report(self.evidence, [self.plan], self.digest)
        self.assertEqual(again, self.report)
        self.assertEqual(self.evidence, before)
        self.assertEqual(self.report['gate'], self.evidence['gate'])
        self.assertEqual(self.report['run_started_at'], self.evidence['started_at'])
        self.assertEqual(self.report['rendered_at'], self.evidence['evaluation']['evaluated_at'])
        self.assertEqual(self.report['modules'][0]['criterion_definitions'], self.plan['criteria'])
        self.assertEqual(self.report['modules'][0]['execution_evidence'], self.evidence['results'][0]['receipt']['execution_evidence'])
        self.assertEqual(sum(self.report['summary']['capability_counts'].values()), 43)
        self.assertEqual(self.report['summary']['test_counts'], self.evidence['results'][0]['counts'])

    def test_reject_mutation_and_missing_evaluation(self):
        for mutation in ('evaluation', 'reason'):
            e = copy.deepcopy(self.evidence)
            if mutation == 'evaluation':
                e.pop('evaluation')
            else:
                e['results'][0]['reason'] = 'Changed after evaluation'
            with self.assertRaises(ContractError):
                project_report(e, [self.plan], self.digest)

    def test_crossreferences_and_contradictions(self):
        for mutate in (
            lambda e: e['results'][0]['criteria'][0].update(observed=False),
            lambda e: e['results'][0].update(plan_id='unknown'),
            lambda e: e['results'][0]['criteria'][0].update(artifact_ids=['unknown']),
            lambda e: e['results'][0]['counts'].update(passed=999),
            lambda e: e['capabilities'][0]['module_ids'].append('unknown'),
        ):
            e = copy.deepcopy(self.evidence)
            mutate(e)
            self.stamp(e)
            with self.assertRaises(ContractError):
                project_report(e, [self.plan], self.digest)

    def test_summary_mismatch(self):
        for key in ('attempts', 'logical_checks', 'required_failed', 'optional_failed'):
            report = copy.deepcopy(self.report)
            report['summary'][key] += 1
            with self.assertRaises(ContractError):
                render_report(report)
        report = copy.deepcopy(self.report)
        report['summary']['capability_counts']['PASSED'] += 1
        with self.assertRaises(ContractError):
            render_report(report)

    def test_incomplete_attempts_preserve_states_and_missing_observations(self):
        for execution, assessment in [('blocked', 'BLOCKED'), ('not_run', 'NOT_RUN'),
                                       ('cancelled', 'REQUIRES_REVIEW'), ('timed_out', 'REQUIRES_REVIEW')]:
            e = copy.deepcopy(self.evidence)
            e['results'][0].update(execution=execution, assessment=assessment, receipt=None, counts=None, criteria=[])
            e['capabilities'][0]['assessment'] = assessment
            e['gate'].update(outcome='INSUFFICIENT_EVIDENCE', required_gaps=[self.plan['module_id']])
            e['adoption']['completion'] = 'incomplete'
            self.stamp(e)
            report = project_report(e, [self.plan], self.digest)
            self.assertEqual(report['modules'][0]['assessment'], assessment)
            page = render_report(report)
            self.assertIn('unknown — no observation', page)
            self.assertIn('Incomplete assurance', page)
        e['results'] = []
        self.stamp(e)
        report = project_report(e, [self.plan], self.digest)
        self.assertEqual(report['summary']['attempts'], 0)
        self.assertEqual(report['summary']['logical_checks'], 1)
        self.assertIn('No attempt recorded for frozen module', render_report(report))

    def test_shared_execution_counted_once_and_conflict_rejected(self):
        e = copy.deepcopy(self.evidence)
        second = copy.deepcopy(e['results'][0])
        second['attempt'] = 2
        e['results'].append(second)
        self.stamp(e)
        report = project_report(e, [self.plan], self.digest)
        self.assertEqual(report['summary']['attempts'], 2)
        self.assertEqual(report['summary']['logical_checks'], 1)
        self.assertEqual(report['summary']['test_counts'], self.report['summary']['test_counts'])
        second['counts']['errors'] += 1
        self.stamp(e)
        with self.assertRaises(ContractError):
            project_report(e, [self.plan], self.digest)

    def test_failed_criteria_and_optional_failure_visible(self):
        e = copy.deepcopy(self.evidence)
        e['results'][0]['assessment'] = 'FAILED'
        e['results'][0]['criteria'][0].update(observed=False, outcome='violated')
        e['capabilities'][0]['assessment'] = 'FAILED'
        e['gate'].update(outcome='REJECTED', required_failures=[self.plan['module_id']])
        e['adoption']['completion'] = 'incomplete'
        self.stamp(e)
        report = project_report(e, [self.plan], self.digest)
        self.assertEqual(report['summary']['required_failed'], 1)
        page = render_report(report)
        self.assertIn('REJECTED', page)
        self.assertIn('violated', page)
        report['modules'][0]['required'] = False
        report['summary'].update(required_failed=0, optional_failed=1)
        self.assertIn('optional_failed', render_report(report))

    def test_core_html_requires_no_script_or_plan(self):
        page = render_report(self.report)
        parsed = Page(page)
        self.assertEqual(parsed.sections, list(SECTIONS))
        self.assertEqual(sum(tag == 'section' for tag, _ in parsed.tags), 9)
        self.assertTrue(any(tag == 'caption' for tag, _ in parsed.tags))
        for definition in self.plan['criteria']:
            self.assertIn(definition['justification'], ' '.join(parsed.text))
        self.assertIn('Expected', ' '.join(parsed.text))
        self.assertIn('Observed', ' '.join(parsed.text))
        self.assertTrue(all('src' not in attrs for _, attrs in parsed.tags))
        self.assertIn('Raw artifacts require the original evidence bundle', page)
        self.assertIn('Not captured / not applicable', page)
        self.assertIn('@media print', page)
        self.assertIn('@media(max-width:600px)', page)

    def test_hostile_text_is_inert_and_embedded_json_roundtrips(self):
        report = copy.deepcopy(self.report)
        hostile = '</script><script>alert("x")</script><img src=x onerror=alert(1)> & \u2028'
        report['limitations'].append(hostile)
        report['modules'][0]['reason'] = hostile
        page = render_report(report)
        parsed = Page(page)
        self.assertFalse(any(tag == 'img' for tag, _ in parsed.tags))
        self.assertEqual(sum(tag == 'script' for tag, _ in parsed.tags), 2)
        self.assertNotIn(hostile, page)
        data = page.split('<script id="report-data" type="application/json">', 1)[1].split('</script>', 1)[0]
        self.assertEqual(json.loads(data), report)

    def test_artifact_links_safe_and_unavailable_labeled(self):
        report = copy.deepcopy(self.report)
        report['artifact_links'][0]['path'] = '%2e%2e/name#fragment?.txt'
        page = render_report(report)
        self.assertIn('./%252e%252e/name%23fragment%3F.txt', page)
        for bad in ('../outside', '/absolute', 'javascript:alert(1)', '//remote/file'):
            report['artifact_links'][0]['path'] = bad
            with self.assertRaises(ContractError):
                render_report(report)
        report = copy.deepcopy(self.report)
        report['artifact_links'][0]['access'] = 'expired'
        self.assertIn('unavailable: expired', render_report(report))

    def test_chart_exact_table_missing_values_and_nonfinite_rejected(self):
        report = copy.deepcopy(self.report)
        report['charts'] = [{'id':'metric', 'title':'Descriptive observations', 'x_label':'Sample', 'x_unit':'index',
            'y_label':'Error', 'y_unit':'m', 'source_artifact_ids':[report['artifact_links'][0]['id']],
            'series':[{'name':'Reference difference', 'meaning':'Observed difference from reference',
                       'points':[{'x':1.0,'y':0.125}, {'x':2.0,'y':None}]}],
            'limitations':['Reference and tolerance must be interpreted using the linked source.']}]
        page = render_report(report)
        self.assertIn('<svg', page)
        self.assertIn('0.125', page)
        self.assertIn('Missing measurement', page)
        report['charts'][0]['series'][0]['points'][0]['y'] = float('inf')
        with self.assertRaises(ValueError):
            render_report(report)

    def test_atomic_write_preserves_previous_on_render_or_replace_failure(self):
        target = self.root / 'index.html'
        target.write_text('previous run and original date')
        bad = copy.deepcopy(self.report)
        bad['summary']['attempts'] += 1
        with self.assertRaises(ContractError):
            save_report(bad, target)
        self.assertEqual(target.read_text(), 'previous run and original date')
        with patch('rb_test_suite.reporting.os.replace', side_effect=OSError('permission denied')):
            with self.assertRaises(OSError):
                save_report(self.report, target)
        self.assertEqual(target.read_text(), 'previous run and original date')
        self.assertFalse(list(self.root.glob('.report-*.tmp')))
        save_report(self.report, target)
        self.assertEqual(target.read_text(), render_report(self.report))

    def test_cli_preserves_evidence_dates_and_prior_report_on_corruption(self):
        evidence_path = self.root / 'evidence.json'
        evidence_path.write_bytes(self.raw)
        output = self.root / 'index.html'
        script = Path(__file__).resolve().parents[1] / 'scripts/build_report.py'
        command = [sys.executable, str(script), str(evidence_path), '--artifact-root', str(self.root), '--output', str(output)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        original = output.read_bytes()
        self.assertEqual(evidence_path.read_bytes(), self.raw)
        (self.root / self.evidence['artifacts'][0]['path']).write_text('corrupt')
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 3)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(evidence_path.read_bytes(), self.raw)


if __name__ == '__main__':
    unittest.main()
