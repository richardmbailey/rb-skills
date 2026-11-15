#!/usr/bin/env python3
"""Build an offline report from an unchanged evaluated evidence bundle."""
import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rb_test_suite.reporting import MAX_REPORT_BYTES, project_report, save_report
from rb_test_suite.validation import ContractError, contained_path, parse_json, validate_run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--artifact-root', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.evidence.stat().st_size > MAX_REPORT_BYTES:
            raise ContractError('evidence exceeds report input bound')
        raw = args.evidence.read_bytes()
        evidence = parse_json(raw, max_bytes=MAX_REPORT_BYTES)
        if not evidence.get('evaluation'):
            raise ContractError('save an evaluated record before building its report')
        plans = []
        for artifact in evidence['plans']:
            path = contained_path(args.artifact_root, artifact['path'])
            if path.stat().st_size > MAX_REPORT_BYTES:
                raise ContractError('plan exceeds report input bound')
            plans.append(parse_json(path.read_bytes(), max_bytes=MAX_REPORT_BYTES))
        validated = validate_run(evidence, plans, args.artifact_root)
        report = project_report(validated, plans, hashlib.sha256(raw).hexdigest())
        save_report(report, args.output)
    except (OSError, ValueError, KeyError) as exc:
        print('Report build failed; existing report and evidence preserved: ' + str(exc), file=sys.stderr)
        return 3
    print(str(args.output))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
