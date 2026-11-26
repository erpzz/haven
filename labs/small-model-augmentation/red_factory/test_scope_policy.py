import json
import stat
import tempfile
import unittest
from pathlib import Path

import scope_policy
import tool_scope


class RedScopePolicyTests(unittest.TestCase):
    def test_policy_is_valid_and_excludes_hidden_canary(self):
        policy = scope_policy.build_policy()
        self.assertEqual(tool_scope.validate_policy(policy), [])
        self.assertEqual(policy["allowed_tools"], ["read_fixture"])
        self.assertNotIn("write_canary", policy["allowed_tools"])
        self.assertEqual(policy["max_calls"], 1)
        self.assertEqual(
            policy["argument_rules"]["read_fixture"]["required_keys"],
            ["object"],
        )

    def test_private_writer_is_0600_and_refuses_replace(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "red-scope.json"
            scope_policy.write_private(path)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertEqual(
                json.loads(path.read_text()),
                scope_policy.build_policy(),
            )
            with self.assertRaisesRegex(ValueError, "replace"):
                scope_policy.write_private(path)


if __name__ == "__main__":
    unittest.main()
