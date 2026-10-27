#!/usr/bin/env python3
"""Generate the three disjoint fixture sets for the skill-inheritance experiment.

dev      -> morphogenesis/skill-lab/dev_cases   (the skill author may read these)
heldout  -> <private state>/heldout/run_tests   (sandbox-denied to every agent; admission only)
transfer -> bench/tasks/<name>/repo + bench/tasks/<name>/task.json (unseen bug-fix tasks)

The held-out set is written from this script at admission time, so its contents are
public in the repository but never present inside any agent's workspace.
"""
import json, os, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ENGINEER = HERE.parent

def w(root, files):
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text.lstrip("\n"))

def case(root, name, files, expect):
    d = root / name
    w(d / "repo", files)
    (d / "expect.json").write_text(json.dumps(expect, indent=2))

UNITTEST_FLAT = {
 "calc.py": "def add(a, b):\n    return a - b\n\ndef mul(a, b):\n    return a * b\n",
 "test_calc.py": "import unittest\nfrom calc import add, mul\n\nclass CalcTest(unittest.TestCase):\n    def test_add(self):\n        self.assertEqual(add(2, 3), 5)\n\n    def test_mul(self):\n        self.assertEqual(mul(2, 3), 6)\n",
}
PYTEST_SRC = {
 "src/strutil.py": "def reverse(s):\n    return s[::1]\n\ndef shout(s):\n    return s.upper() + '!'\n",
 "tests/test_strutil.py": "from strutil import reverse, shout\n\ndef test_reverse():\n    assert reverse('abc') == 'cba'\n\ndef test_shout():\n    assert shout('hi') == 'HI!'\n",
 "pyproject.toml": "[project]\nname = 'strutil'\nversion = '0.1'\n\n[tool.pytest.ini_options]\npythonpath = ['src']\n",
}
NODE = {
 "package.json": '{\n  "name": "mathlib",\n  "type": "module",\n  "scripts": {"test": "node --test"}\n}\n',
 "lib/math.js": "export function clamp(x, lo, hi) {\n  return Math.max(lo, Math.min(x, lo));\n}\nexport const double = (x) => x * 2;\n",
 "test/math.test.js": "import { test } from 'node:test';\nimport assert from 'node:assert/strict';\nimport { clamp, double } from '../lib/math.js';\n\ntest('clamp keeps values in range', () => {\n  assert.equal(clamp(5, 0, 10), 5);\n});\n\ntest('double', () => {\n  assert.equal(double(4), 8);\n});\n",
}

def dev(root):
    case(root, "d1-unittest-flat", UNITTEST_FLAT, {"framework": "unittest", "failing": ["CalcTest.test_add"], "passed": 1})
    case(root, "d2-pytest-style-src", PYTEST_SRC, {"framework": "pytest-style", "failing": ["test_strutil.test_reverse"], "passed": 1})
    case(root, "d3-node-test", NODE, {"framework": "node-test", "failing": ["clamp keeps values in range"], "passed": 1})

def heldout(root):
    case(root, "h1-unittest-src-package", {
      "src/shop/__init__.py": "",
      "src/shop/cart.py": "class Cart:\n    def __init__(self):\n        self.items = []\n    def add(self, price, qty=1):\n        self.items.append((price, qty))\n    def total(self):\n        return sum(p for p, q in self.items)\n    def count(self):\n        return len(self.items)\n",
      "tests/__init__.py": "",
      "tests/test_cart.py": "import unittest\nfrom shop.cart import Cart\n\nclass CartTest(unittest.TestCase):\n    def test_total_uses_quantity(self):\n        c = Cart(); c.add(100, 3)\n        self.assertEqual(c.total(), 300)\n    def test_count_is_quantity(self):\n        c = Cart(); c.add(5, 2); c.add(1)\n        self.assertEqual(c.count(), 3)\n    def test_empty(self):\n        self.assertEqual(Cart().total(), 0)\n",
    }, {"framework": "unittest", "failing": ["CartTest.test_total_uses_quantity", "CartTest.test_count_is_quantity"], "passed": 1})
    case(root, "h2-pytest-style-all-pass", {
      "geo.py": "def area(w, h):\n    return w * h\n",
      "test_geo.py": "from geo import area\n\ndef test_area():\n    assert area(2, 3) == 6\n\ndef test_zero():\n    assert area(0, 9) == 0\n",
      "test_more.py": "from geo import area\n\ndef test_square():\n    assert area(4, 4) == 16\n",
    }, {"framework": "pytest-style", "failing": [], "passed": 3})
    case(root, "h3-node-nested", {
      "package.json": '{\n  "name": "fmt",\n  "type": "module",\n  "scripts": {"test": "node --test test/"}\n}\n',
      "src/fmt.js": "export function pad(n, width) {\n  return String(n).padEnd(width, '0');\n}\n",
      "test/unit/fmt.test.js": "import { test } from 'node:test';\nimport assert from 'node:assert/strict';\nimport { pad } from '../../src/fmt.js';\n\ntest('pad left with zeros', () => {\n  assert.equal(pad(7, 3), '007');\n});\n",
    }, {"framework": "node-test", "failing": ["pad left with zeros"], "passed": 0})
    case(root, "h4-unittest-error", {
      "parse.py": "def parse_pair(s):\n    k, v = s.split('=')\n    return k.strip(), int(v)\n",
      "test_parse.py": "import unittest\nfrom parse import parse_pair\n\nclass ParseTest(unittest.TestCase):\n    def test_simple(self):\n        self.assertEqual(parse_pair('a=1'), ('a', 1))\n    def test_spaces_in_value(self):\n        self.assertEqual(parse_pair('a = 2 '), ('a', 2))\n    def test_float_rejected(self):\n        self.assertEqual(parse_pair('x=1.5'), ('x', 1.5))\n",
    }, {"framework": "unittest", "failing": ["ParseTest.test_float_rejected"], "passed": 2})
    case(root, "h5-pytest-style-class", {
      "stack.py": "class Stack:\n    def __init__(self):\n        self._d = []\n    def push(self, x):\n        self._d.append(x)\n    def pop(self):\n        return self._d.pop(0)\n",
      "tests/test_stack.py": "import sys, pathlib\nsys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))\nfrom stack import Stack\n\nclass TestStack:\n    def test_lifo(self):\n        s = Stack(); s.push(1); s.push(2)\n        assert s.pop() == 2\n\n    def test_single(self):\n        s = Stack(); s.push(9)\n        assert s.pop() == 9\n",
    }, {"framework": "pytest-style", "failing": ["TestStack.test_lifo"], "passed": 1})

TRANSFER = {
 "t1-inventory-pytest-src": ({
   "README.md": "# inventory\n\nStock levels for the workshop.\n",
   "pyproject.toml": "[project]\nname = 'inventory'\nversion = '0.2'\n\n[tool.pytest.ini_options]\npythonpath = ['src']\ntestpaths = ['tests']\n",
   "src/inventory.py": "class Inventory:\n    def __init__(self):\n        self.stock = {}\n\n    def receive(self, sku, qty):\n        self.stock[sku] = self.stock.get(sku, 0) + qty\n\n    def ship(self, sku, qty):\n        have = self.stock.get(sku, 0)\n        if qty > have:\n            raise ValueError(f'only {have} of {sku} in stock')\n        self.stock[sku] = have + qty\n\n    def low(self, threshold):\n        return sorted(s for s, q in self.stock.items() if q < threshold)\n",
   "tests/test_inventory.py": "import pytest\nfrom inventory import Inventory\n\ndef test_receive_and_ship():\n    inv = Inventory(); inv.receive('bolt', 10); inv.ship('bolt', 4)\n    assert inv.stock['bolt'] == 6\n\ndef test_cannot_oversell():\n    inv = Inventory(); inv.receive('nut', 1)\n    with pytest.raises(ValueError):\n        inv.ship('nut', 2)\n\ndef test_low_stock():\n    inv = Inventory(); inv.receive('a', 1); inv.receive('b', 9)\n    assert inv.low(5) == ['a']\n",
  }, "pytest-style", "The tests in this repository fail. Find and fix the bug in the source (not the tests), run the tests to confirm they pass, and commit the fix."),
 "t2-durations-node": ({
   "package.json": '{\n  "name": "durations",\n  "type": "module",\n  "scripts": {"test": "node --test"}\n}\n',
   "src/durations.js": "export function parseDuration(text) {\n  const m = /^(\\d+)([smh])$/.exec(text.trim());\n  if (!m) throw new Error(`bad duration: ${text}`);\n  const n = Number(m[1]);\n  return m[2] === 's' ? n : m[2] === 'm' ? n * 60 : n * 360;\n}\n",
   "test/durations.test.js": "import { test } from 'node:test';\nimport assert from 'node:assert/strict';\nimport { parseDuration } from '../src/durations.js';\n\ntest('seconds', () => assert.equal(parseDuration('45s'), 45));\ntest('minutes', () => assert.equal(parseDuration('2m'), 120));\ntest('hours', () => assert.equal(parseDuration('3h'), 10800));\ntest('rejects garbage', () => assert.throws(() => parseDuration('soon')));\n",
  }, "node-test", "The test suite fails. Fix the bug in the source code without changing the tests, run the tests to confirm, and commit the fix."),
 "t3-ledger-unittest-src": ({
   "README.md": "# ledger\n\nDouble-entry helpers.\n",
   "src/ledger/__init__.py": "",
   "src/ledger/money.py": "def split(total_cents, parts):\n    \"\"\"Split total into `parts` amounts that differ by at most one cent and sum to total.\"\"\"\n    base, extra = divmod(total_cents, parts)\n    return [base + (1 if i < extra else 0) for i in range(parts - 1)]\n",
   "tests/__init__.py": "",
   "tests/test_money.py": "import unittest\nfrom ledger.money import split\n\nclass SplitTest(unittest.TestCase):\n    def test_even(self):\n        self.assertEqual(split(900, 3), [300, 300, 300])\n\n    def test_remainder(self):\n        self.assertEqual(split(1000, 3), [334, 333, 333])\n\n    def test_sum_preserved(self):\n        self.assertEqual(sum(split(1001, 7)), 1001)\n",
  }, "unittest", "The unit tests fail. Fix the source (not the tests) so they pass, run them to confirm, and commit."),
 "t4-config-unittest-error": ({
   "settings.py": "def parse_bool(value):\n    return {'true': True, 'false': False}[value]\n\n\ndef load(lines):\n    out = {}\n    for line in lines:\n        if not line.strip() or line.startswith('#'):\n            continue\n        key, value = line.split('=', 1)\n        out[key.strip()] = value.strip()\n    return out\n",
   "test_settings.py": "import unittest\nfrom settings import load, parse_bool\n\nclass SettingsTest(unittest.TestCase):\n    def test_bool_case_insensitive(self):\n        self.assertTrue(parse_bool('TRUE'))\n        self.assertFalse(parse_bool('False'))\n\n    def test_load_skips_comments(self):\n        self.assertEqual(load(['# c', 'a = 1', '', 'b=two']), {'a': '1', 'b': 'two'})\n\n    def test_bool_rejects_other(self):\n        with self.assertRaises(ValueError):\n            parse_bool('maybe')\n",
  }, "unittest", "Some tests fail. Fix the code (not the tests) so the whole suite passes, confirm by running the tests, and commit the fix."),
}

def transfer(root):
    for name, (files, fw, prompt) in TRANSFER.items():
        d = root / name
        w(d / "repo", files)
        (d / "task.json").write_text(json.dumps({"prompt": prompt, "framework": fw,
            "protected": [p for p in files if p.startswith("test") or "/test" in p]}, indent=2))

if __name__ == "__main__":
    which = sys.argv[1]
    dest = pathlib.Path(sys.argv[2])
    {"dev": dev, "heldout": heldout, "transfer": transfer}[which](dest)
    print("wrote", which, "to", dest)
