import unittest
from mass import transfer


class ExistingTests(unittest.TestCase):
    def test_conserved_total(self):
        before = (10, 2)
        after = transfer(*before, 3)
        self.assertEqual(sum(before), sum(after))
