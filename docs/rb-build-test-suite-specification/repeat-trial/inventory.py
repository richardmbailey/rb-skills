"""Count retained project source separately from generated execution evidence."""
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
records = []
excluded = {'artifacts', 'evidence', '__pycache__', '.pytest_cache', '.hypothesis', '.ruff_cache', '.mypy_cache'}
for path in sorted(root.rglob('*')):
    rel = path.relative_to(root)
    if not path.is_file() or any(part in excluded for part in rel.parts) or path.name.startswith('.coverage'):
        continue
    data = path.read_bytes()
    if rel.as_posix() == 'model.py':
        category = 'model'
    elif rel.as_posix() in ('tests/test_model.py', 'tests/test_independent.py'):
        category = 'substantive_tests'
    elif path.suffix in ('.py', '.sh'):
        category = 'support_tests' if path.name.startswith('test_') and 'tests' in rel.parts else 'support_code'
    elif 'contracts' in rel.parts:
        category = 'schemas'
    elif path.suffix in ('.md', '.html'):
        category = 'documentation'
    else:
        category = 'configuration'
    lines = data.decode().splitlines()
    records.append({'path': str(rel), 'category': category, 'lines': len(lines),
                    'nonblank_lines': sum(bool(line.strip()) for line in lines),
                    'sha256': hashlib.sha256(data).hexdigest()})
totals = {}
for record in records:
    total = totals.setdefault(record['category'], {'files': 0, 'lines': 0, 'nonblank_lines': 0})
    total['files'] += 1
    for key in ('lines', 'nonblank_lines'):
        total[key] += record[key]
print(json.dumps({'files': records, 'totals': totals,
                  'count_scope': 'Retained authored project source; generated evidence/candidate copies excluded. Disclose unretained orchestration separately.'}, indent=2))
