import unittest
from settings import load, parse_bool

class SettingsTest(unittest.TestCase):
    def test_bool_case_insensitive(self):
        self.assertTrue(parse_bool('TRUE'))
        self.assertFalse(parse_bool('False'))

    def test_load_skips_comments(self):
        self.assertEqual(load(['# c', 'a = 1', '', 'b=two']), {'a': '1', 'b': 'two'})

    def test_bool_rejects_other(self):
        with self.assertRaises(ValueError):
            parse_bool('maybe')
