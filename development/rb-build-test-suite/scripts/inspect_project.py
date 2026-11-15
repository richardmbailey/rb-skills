#!/usr/bin/env python3
"""Read-only discovery; JSON on stdout, no target imports or subprocesses."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rb_test_suite.project import inspect_project, snapshot, compare_snapshots
from rb_test_suite.validation import parse_json, parse_yaml, ContractError


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('--config', type=Path, help='Authoring config for control/output exclusions')
    parser.add_argument('--baseline', type=Path, help='Previously saved snapshot JSON; include exact changes')
    parser.add_argument('--exclude', action='append', default=[], help='Explicit relative path/subtree exclusion')
    args = parser.parse_args()
    try:
        result = inspect_project(args.root)
        if args.config or args.exclude:
            result['snapshot'] = snapshot(args.root, exclusions=args.exclude,
                config=parse_yaml(args.config.read_bytes()) if args.config else None)
        if args.baseline:
            result['changes'] = compare_snapshots(parse_json(args.baseline.read_bytes(), max_bytes=32*1024*1024), result['snapshot'])
        print(json.dumps(result, sort_keys=True, indent=2, default=str))
        return 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 3

if __name__ == '__main__':
    raise SystemExit(main())
