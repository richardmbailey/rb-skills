"""Generate schemas from models, or fail when committed exports have drifted."""
import argparse
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from rb_test_suite.models import schemas

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    changed = []
    for name, schema in schemas().items():
        path = ROOT / 'schemas' / name
        expected = json.dumps(schema, indent=2, sort_keys=True) + '\n'
        if args.check:
            if not path.exists() or path.read_text() != expected:
                changed.append(name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(expected)
    if changed:
        print('Schema drift: ' + ', '.join(changed), file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
