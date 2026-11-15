"""Run original structural cases against generated schemas, preserving old fixtures."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'development/rb-build-test-suite/src'))
from rb_test_suite.models import schemas


def main():
    path = ROOT / 'docs/rb-build-test-suite-specification/checks/test_schemas.py'
    spec = importlib.util.spec_from_file_location('draft_compat', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.SCHEMAS
    generated = schemas()
    # Keep DEFS/IDS for original fixture construction. Only replace validation.
    module.SCHEMAS = generated
    module.REGISTRY = Registry().with_resources(
        (schema['$id'], Resource.from_contents(schema)) for schema in generated.values())
    result = unittest.TextTestRunner(verbosity=1).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(module.SchemaContracts))
    field_changes = []
    after = generated['contracts.schema.json']['$defs']
    for name, before in original['contracts.schema.json']['$defs'].items():
        if name not in after:
            field_changes.append({'definition': name, 'change': 'Named definition replaced or inlined.'})
        elif 'properties' in before:
            old_fields = set(before['properties'])
            new_fields = set(after[name].get('properties', {}))
            if old_fields != new_fields:
                field_changes.append({'definition': name, 'added_fields': sorted(new_fields-old_fields),
                                      'removed_fields': sorted(old_fields-new_fields)})
    report = {'schema_version': 1, 'draft_version': '1.0.0 unreleased',
              'implementation_package_version': '0.1.0', 'schema_version_retained': '1.0.0',
              'original_structural_tests_against_generated_schemas': result.testsRun,
              'result': 'passed' if result.wasSuccessful() else 'failed',
              'original_roots': sorted(original), 'generated_roots': sorted(generated),
              'public_field_changes': field_changes,
              'compatibility_notes': [
                  'Generated definitions add titles and lift some nested objects into named definitions.',
                  'EvidenceRun adds optional evaluation for producer input; evaluated output binds source and assessed digests, policy/version and preserved evaluation time.',
                  'Authoring config and control roots are new; no deployed consumer exists.',
                  'Unsupported versions and migrations are rejected; no consumer upgrade is claimed.',
                  'Initial comparison harness failed because it replaced the old fixture definition lookup with generated nested references. Corrected harness retains original fixture construction and replaces only the schema validators. No product assertion was weakened.']}
    (Path(__file__).parent / 'p1-schema-compatibility.json').write_text(json.dumps(report, indent=2)+'\n')
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
