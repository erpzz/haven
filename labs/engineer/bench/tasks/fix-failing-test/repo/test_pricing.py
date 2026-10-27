import unittest

from pricing import apply_discount, line_total, order_total


class PricingTest(unittest.TestCase):
    def test_line_total(self):
        self.assertEqual(line_total(250, 4), 1000)

    def test_no_discount(self):
        self.assertEqual(apply_discount(1000, 0), 1000)

    def test_ten_percent(self):
        self.assertEqual(apply_discount(1999, 10), 1799)

    def test_order_total(self):
        self.assertEqual(order_total([(250, 2), (1000, 1)], 20), 1200)


if __name__ == "__main__":
    unittest.main()
