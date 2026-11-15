"""Reuse the first comparison's evaluator on a separately frozen second repeat."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location(
    'paired_evaluator', HERE.parent / 'repeat-trial' / 'compare_suites.py'
)
assert spec is not None and spec.loader is not None
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)
comparison.HERE = HERE
comparison.REPEAT = ROOT / 'examples' / 'numerical-assurance-repeat-2'

if __name__ == '__main__':
    comparison.main()
