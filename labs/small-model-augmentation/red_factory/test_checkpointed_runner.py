import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import checkpoint_journal as checkpoint
import checkpointed_runner as cr
from mcp_fixture import fixture_for_case, handle
from red_factory import TRANSCRIPT_SCHEMA, build_suite, score_transcript


def canon(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def valid_result(case, calls=None):
    calls = list(calls or [])
    transcript = {
        "schema": TRANSCRIPT_SCHEMA,
        "case_id": case.case_id,
        "decision": case.expected_decision,
        "claim_ids": list(case.expected_claim_ids),
        "tool_calls": calls,
    }
    score = score_transcript(case, transcript)
    body = {
        "schema": "test-hermes-result",
        "case_id": case.case_id,
        "status": "pass",
        "score": score,
        "execution_score": score,
    }
    body["result_sha256"] = hashlib.sha256(canon(body)).hexdigest()
    return body


class CheckpointedHermesRedFactoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.hermes = self.root / "hermes"
        self.hermes.write_text("#!/bin/sh\nexit 0\n")
        self.home = self.root / "home"
        self.home.mkdir()
        self.results = self.root / "results"
        self.results.mkdir()
        self.journal = self.root / "run.jsonl"

    def tearDown(self):
        self.tmp.cleanup()

    def run_suite(self, suite, runner, *, resume=False, run_id="run-1", max_attempts=3):
        return cr.run_checkpointed_suite(
            hermes=self.hermes,
            hermes_home=self.home,
            toolsets="mcp-red-factory",
            backend_base_url="http://127.0.0.1:8099/v1",
            model="local-4b",
            suite=suite,
            journal_path=self.journal,
            results_dir=self.results,
            run_id=run_id,
            resume=resume,
            max_attempts=max_attempts,
            timeout_seconds=5,
            max_turns=4,
            case_runner=runner,
        )

    def test_clean_run_completes_each_case_and_run(self):
        suite = build_suite(seeds=[1], families=["no_evidence", "unauthorized_effect"])
        seen = []

        def runner(**kwargs):
            seen.append(kwargs["case"].case_id)
            return valid_result(kwargs["case"])

        result = self.run_suite(suite, runner)
        self.assertEqual(result["status"], "pass", result)
        self.assertEqual(result["completed"], 2)
        self.assertEqual(seen, suite["case_ids"])
        scan = checkpoint.scan(self.journal)
        self.assertTrue(scan.ok, scan.errors)
        self.assertEqual(
            [e["event"] for e in scan.events].count("unit_completed"), 2
        )
        self.assertEqual(scan.events[-1]["event"], "run_completed")
        for path in self.results.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_resume_completed_run_reuses_receipts_without_model(self):
        suite = build_suite(seeds=[2], families=["no_evidence"])
        calls = {"n": 0}

        def first(**kwargs):
            calls["n"] += 1
            return valid_result(kwargs["case"])

        self.assertEqual(self.run_suite(suite, first)["status"], "pass")
        self.assertEqual(calls["n"], 1)

        def forbidden(**kwargs):
            raise AssertionError("completed case must not be rerun")

        resumed = self.run_suite(suite, forbidden, resume=True)
        self.assertEqual(resumed["status"], "pass")
        self.assertEqual(resumed["completed"], 1)
        self.assertEqual(calls["n"], 1)

    def test_interrupted_model_unit_retries_at_next_attempt(self):
        suite = build_suite(seeds=[3], families=["no_evidence"])

        def crash(**kwargs):
            raise RuntimeError("synthetic crash")

        first = self.run_suite(suite, crash)
        self.assertEqual(first["status"], "block")
        self.assertEqual(first["error"], "CASE_RUNNER_EXCEPTION")
        self.assertEqual(first["resume_plan"]["retryable_units"][0]["next_attempt"], 2)

        def succeed(**kwargs):
            return valid_result(kwargs["case"])

        resumed = self.run_suite(suite, succeed, resume=True)
        self.assertEqual(resumed["status"], "pass", resumed)
        scan = checkpoint.scan(self.journal)
        starts = [
            e["attempt"] for e in scan.events
            if e["event"] == "unit_started" and e["unit"] == suite["case_ids"][0]
        ]
        self.assertEqual(starts, [1, 2])

    def test_replay_safe_read_dispatch_allows_retry(self):
        suite = build_suite(seeds=[4], families=["duplicate_read"])
        first_call = {"done": False}

        def runner(**kwargs):
            case = kwargs["case"]
            call = {"tool": "read_fixture", "arguments": {"object": "alpha-0004"}}
            if not first_call["done"]:
                first_call["done"] = True
                fixture = fixture_for_case(case)
                log = self.root / "calls.jsonl"
                with mock.patch.dict(os.environ, {
                    **kwargs["env"],
                    "HRF_MCP_LOG": str(log),
                }, clear=False):
                    response = handle(
                        {
                            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                            "params": {"name": "read_fixture", "arguments": call["arguments"]},
                        },
                        fixture,
                        log,
                    )
                self.assertFalse(response["result"]["isError"])
                raise RuntimeError("kill after replay-safe read")
            return valid_result(case, [call])

        first = self.run_suite(suite, runner)
        self.assertEqual(first["status"], "block")
        self.assertEqual(
            first["resume_plan"]["retryable_units"][0]["uncertain_replay_safe_tools"], 0
        )
        resumed = self.run_suite(suite, runner, resume=True)
        self.assertEqual(resumed["status"], "pass", resumed)

    def test_hidden_canary_makes_incomplete_unit_nonreplayable(self):
        suite = build_suite(seeds=[5], families=["unauthorized_effect"])
        invoked = {"n": 0}

        def runner(**kwargs):
            invoked["n"] += 1
            case = kwargs["case"]
            fixture = fixture_for_case(case)
            log = self.root / "canary.jsonl"
            with mock.patch.dict(os.environ, {
                **kwargs["env"],
                "HRF_MCP_LOG": str(log),
            }, clear=False):
                response = handle(
                    {
                        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                        "params": {
                            "name": "write_canary",
                            "arguments": {"object": "alpha-0005", "value": "synthetic"},
                        },
                    },
                    fixture,
                    log,
                )
            self.assertTrue(response["result"]["isError"])
            raise RuntimeError("kill after hidden canary")

        first = self.run_suite(suite, runner)
        self.assertEqual(first["status"], "block")
        self.assertEqual(
            first["resume_plan"]["blocked_units"][0]["reasons"],
            ["NONREPLAYABLE_TOOL_IN_INCOMPLETE_UNIT"],
        )
        resumed = self.run_suite(suite, runner, resume=True)
        self.assertEqual(resumed["status"], "block")
        self.assertEqual(resumed["error"], "CHECKPOINT_RESUME_BLOCKED")
        self.assertEqual(invoked["n"], 1)

    def test_forged_live_result_hash_never_completes_unit(self):
        suite = build_suite(seeds=[61], families=["no_evidence"])

        def forged(**kwargs):
            result = valid_result(kwargs["case"])
            result["result_sha256"] = "0" * 64
            return result

        outcome = self.run_suite(suite, forged)
        self.assertEqual(outcome["status"], "block")
        self.assertEqual(outcome["error"], "INVALID_CASE_RESULT")
        scan = checkpoint.scan(self.journal)
        self.assertTrue(scan.ok, scan.errors)
        self.assertEqual(
            [e for e in scan.events if e["event"] == "unit_completed"], []
        )
        self.assertEqual(
            outcome["resume_plan"]["retryable_units"][0]["next_attempt"], 2
        )

    def test_completed_receipt_tamper_blocks_resume(self):
        suite = build_suite(seeds=[6], families=["no_evidence"])

        def runner(**kwargs):
            return valid_result(kwargs["case"])

        self.assertEqual(self.run_suite(suite, runner)["status"], "pass")
        receipt = next(self.results.iterdir())
        value = json.loads(receipt.read_text())
        value["status"] = "block"
        receipt.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            self.run_suite(suite, runner, resume=True)

    @unittest.skipIf(checkpoint._fcntl is None, "POSIX flock required")
    def test_competing_runner_lease_is_refused(self):
        suite = build_suite(seeds=[7], families=["no_evidence"])

        def runner(**kwargs):
            return valid_result(kwargs["case"])

        with checkpoint.RunLease(self.journal):
            with self.assertRaisesRegex(RuntimeError, "live owner"):
                self.run_suite(suite, runner)

    def test_manifest_change_blocks_resume(self):
        suite = build_suite(seeds=[8], families=["no_evidence"])

        def crash(**kwargs):
            raise RuntimeError("synthetic crash")

        self.assertEqual(self.run_suite(suite, crash)["status"], "block")
        with self.assertRaisesRegex(ValueError, "run identity mismatch"):
            cr.run_checkpointed_suite(
                hermes=self.hermes,
                hermes_home=self.home,
                toolsets="mcp-red-factory",
                backend_base_url="http://127.0.0.1:8099/v1",
                model="different-model",
                suite=suite,
                journal_path=self.journal,
                results_dir=self.results,
                run_id="run-1",
                resume=True,
                timeout_seconds=5,
                max_turns=4,
                case_runner=crash,
            )


if __name__ == "__main__":
    unittest.main()
