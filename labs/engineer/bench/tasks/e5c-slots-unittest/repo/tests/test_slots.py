import unittest

from slots.intervals import merge
from slots.scheduler import free_slots


class MergeTest(unittest.TestCase):
    def test_touching_merge(self):
        self.assertEqual(merge([(1, 3), (3, 5)]), [(1, 5)])

    def test_nested(self):
        self.assertEqual(merge([(2, 3), (1, 10), (11, 12)]), [(1, 10), (11, 12)])


class FreeSlotsTest(unittest.TestCase):
    def test_day(self):
        busy = [(13, 14), (9, 10), (9, 11), (16, 17)]
        self.assertEqual(free_slots(busy, 8, 18), [(8, 9), (11, 13), (14, 16), (17, 18)])

    def test_min_len(self):
        self.assertEqual(free_slots([(10, 12), (14, 15)], 9, 16, min_len=2), [(12, 14)])
