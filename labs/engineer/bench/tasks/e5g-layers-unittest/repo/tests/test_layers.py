import unittest

from conf.layers import DEFAULTS, load
from conf.merge import deep_merge


class MergeTest(unittest.TestCase):
    def test_lists_replace(self):
        self.assertEqual(deep_merge({"a": [1]}, {"a": [2]}), {"a": [2]})

    def test_inputs_untouched(self):
        base = {"x": {"y": 1}}
        deep_merge(base, {"x": {"y": 2}})
        self.assertEqual(base, {"x": {"y": 1}})


class LoadTest(unittest.TestCase):
    def test_layers_do_not_leak(self):
        a = load({"server": {"port": 9000}, "plugins": ["auth"]})
        b = load({"debug": True})
        self.assertEqual(a["server"], {"host": "127.0.0.1", "port": 9000})
        self.assertEqual(a["plugins"], ["auth"])
        self.assertEqual(b["server"]["port"], 8080)
        self.assertEqual(b["plugins"], ["core"])
        self.assertEqual(DEFAULTS["debug"], False)
