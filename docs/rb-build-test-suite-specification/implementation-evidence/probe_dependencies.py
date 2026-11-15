"""Reproduce dependency API compatibility probes; no target project is imported."""
import importlib.metadata
import json
import platform

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel, ConfigDict, ValidationError


class Probe(BaseModel):
    model_config = ConfigDict(strict=True, extra='forbid')
    value: int


def main():
    checks = {}
    assert Probe(value=1).value == 1
    checks['strict_integer_accepts'] = True
    for label, inputs in [('string', {'value': '1'}), ('boolean', {'value': True}),
                          ('extra_field', {'value': 1, 'extra': 2})]:
        try:
            Probe(**inputs)
        except ValidationError:
            checks['rejects_' + label] = True
        else:
            raise AssertionError(label)
    Draft202012Validator.check_schema(Probe.model_json_schema())
    checks['model_schema_valid'] = True
    assert yaml.safe_load('value: 1') == {'value': 1}
    checks['safe_yaml_mapping'] = True
    try:
        yaml.safe_load('!!python/object/apply:builtins.eval ["1 + 1"]')
    except yaml.constructor.ConstructorError:
        checks['unsafe_yaml_tag_rejected'] = True
    else:
        raise AssertionError('unsafe YAML accepted')
    validator = Draft202012Validator({'type': 'string', 'format': 'date-time'},
                                    format_checker=FormatChecker())
    for value in ('yesterday', '2026-02-30T12:00:00Z'):
        assert list(validator.iter_errors(value))
    validator.validate('2026-11-15T12:00:00Z')
    checks['calendar_format_asserted'] = True
    print(json.dumps({'status': 'passed', 'python': platform.python_version(),
                      'platform': platform.platform(), 'checks': checks,
                      'versions': {name: importlib.metadata.version(name)
                                   for name in ('pydantic', 'PyYAML', 'jsonschema')}}, indent=2))


if __name__ == '__main__':
    main()
