#!/usr/bin/env python3
"""Scaffold explicit proposals, or recover/rollback the latest transaction.

apply ROOT --config CONFIG --proposals JSON maps project-relative paths to UTF-8
file contents. No target command, dependency installation or network access runs.
"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from rb_test_suite.scaffold import scaffold_project, recover_project, rollback_project
from rb_test_suite.validation import parse_json, parse_yaml


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['apply', 'recover', 'rollback'])
    parser.add_argument('root', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--proposals', type=Path)
    parser.add_argument('--upgrade', action='store_true')
    args = parser.parse_args()
    try:
        if args.action == 'apply':
            if args.config is None or args.proposals is None:
                parser.error('apply requires --config and --proposals')
            result = scaffold_project(args.root, parse_yaml(args.config.read_bytes()),
                                      parse_json(args.proposals.read_bytes()), upgrade=args.upgrade)
        else:
            if args.config or args.proposals or args.upgrade:
                parser.error('recovery/rollback do not accept proposal options')
            result = (recover_project if args.action == 'recover' else rollback_project)(args.root)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 3 if result.get('conflicts') else 0
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 3

if __name__ == '__main__':
    raise SystemExit(main())
