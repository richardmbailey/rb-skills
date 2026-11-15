"""Fixed artifacts exercise analytical discrimination before implementation."""
import json
import unittest
from pathlib import Path
from evaluate import evaluate


class ArtifactChecks(unittest.TestCase):
    def test_saved_healthy_and_defective_artifacts(self):
        records = json.loads(Path(__file__).with_name('artifacts.json').read_text())
        for record in records:
            with self.subTest(record['id']):
                self.assertIs(evaluate(record['artifact']), record['accepted'])

    def test_invalid_numeric_artifacts_do_not_pass(self):
        for value in (True, float('nan'), float('inf'), '1.25'):
            artifact = dict(case='O22', unit='tonnes', kg=[0, 1, 1250], values=[0, 0.001, value])
            with self.subTest(value=repr(value)):
                self.assertFalse(evaluate(artifact))

    def test_missing_and_unknown_artifacts_do_not_pass(self):
        for artifact in ({}, {'case': 'unknown'}, {'case': 'O23'}, {'case':'O22', 'unit':'tonnes', 'kg':[0,1,1250], 'values':[]}):
            with self.subTest(artifact=artifact):
                self.assertFalse(evaluate(artifact))


if __name__ == '__main__':
    unittest.main()
