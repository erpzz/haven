import unittest
from ledger.money import split

class SplitTest(unittest.TestCase):
    def test_even(self):
        self.assertEqual(split(900, 3), [300, 300, 300])

    def test_remainder(self):
        self.assertEqual(split(1000, 3), [334, 333, 333])

    def test_sum_preserved(self):
        self.assertEqual(sum(split(1001, 7)), 1001)
