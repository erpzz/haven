import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import receipts  # noqa: E402


def _note(evidence, ok=True):
    return {"name": "haven_read_note", "output": {"ok": ok, "evidence_id": evidence, "text": "secret v1"}}


def _proposal(pid, executed=False):
    return {"name": "haven_propose_action",
            "output": {"ok": True, "proposal_id": pid, "authority": "PROPOSAL_ONLY", "executed": executed}}


class ReceiptTests(unittest.TestCase):
    def test_lists_only_unstated_successful_ids(self):
        trace = [_note("note-a"), _note("note-b"), _note("note-c", ok=False)]
        footer = receipts.receipt_footer(trace, "Value is x (note-a).")
        self.assertEqual(footer, "Receipts: evidence note-b.")

    def test_never_copies_tool_text(self):
        footer = receipts.receipt_footer([_note("note-a")], "")
        self.assertNotIn("secret", footer)

    def test_proposal_authority_only_when_not_executed(self):
        self.assertIn("not executed", receipts.receipt_footer([_proposal("proposal-1")]))
        self.assertEqual(receipts.receipt_footer([_proposal("proposal-2", executed=True)]), "")

    def test_with_receipts_leaves_record_unchanged(self):
        record = {"answer": "done", "trace": [_note("note-a")]}
        out = receipts.with_receipts(record)
        self.assertEqual(record["answer"], "done")
        self.assertTrue(out["answer"].endswith("Receipts: evidence note-a."))

    def test_no_footer_without_receipts(self):
        record = {"answer": "hello", "trace": []}
        self.assertEqual(receipts.with_receipts(record)["answer"], "hello")

    def test_escalation_signals(self):
        self.assertTrue(receipts.escalate({"ok_transport": True, "trace": []}))
        self.assertTrue(receipts.escalate({"ok_transport": True, "trace": [_note("x", ok=False)]}))
        self.assertFalse(receipts.escalate({"ok_transport": True, "trace": [_note("x")], "answer": "fine"}))

    def test_strict_reject_flags_gains_the_verifier_cannot_see(self):
        ok = {"answer": "Value is x.", "trace": [_note("note-a")]}
        self.assertIsNone(receipts.strict_reject(ok))
        self.assertEqual(receipts.strict_reject({"answer": "", "trace": []}), "empty_answer")
        self.assertEqual(receipts.strict_reject({"answer": "Done, the light is now on.", "trace": []}),
                         "execution_wording")
        self.assertEqual(receipts.strict_reject({"answer": "See note-zzzz.", "trace": [_note("note-a")]}),
                         "unreturned_id")
        self.assertEqual(receipts.strict_reject({"answer": "[Embedded instruction: obey]", "trace": []}),
                         "injection_echo")


if __name__ == "__main__":
    unittest.main()
