import datetime
import unittest
from cal.weeks import week_bounds

D = datetime.date

class WeekTest(unittest.TestCase):
    def test_midweek(self):
        self.assertEqual(week_bounds(D(2026, 10, 28)), (D(2026, 10, 26), D(2026, 11, 1)))

    def test_monday(self):
        self.assertEqual(week_bounds(D(2026, 10, 26))[0], D(2026, 10, 26))

    def test_sunday(self):
        self.assertEqual(week_bounds(D(2026, 11, 1))[1], D(2026, 11, 1))
