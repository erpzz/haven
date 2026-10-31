"""Create a tiny original, verified correction seed and disjoint evaluation set.

No private traces are read. Real session failures motivated the cases; all
inputs here are new synthetic reproductions or explicitly synthetic fixtures.
This seed is not sufficient evidence to start model training.
"""
from pathlib import Path
import argparse
import json
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).parent / ".hermes/plugins/haven-forge"))
from forge_runtime.evidence import observe, digest
from forge_runtime.entra import assess, fixture
from forge_runtime.forensics import admission


EVAL_GROUPS = {"invalid-api-query", "nmap-target-resolution", "cancelled-process", "mfa-or-alternative"}


def build() -> tuple[list[dict], list[dict]]:
    training = []
    specifications = [
        ("missing-executable", "forge_nonexistent_training_utility", 127,
         "A missing executable is a tool-availability failure. Discover the installed tool before retrying."),
        ("missing-file", "cat forge_nonexistent_training_file", 1,
         "This path was absent. A missing file does not establish insufficient privilege."),
        ("short-circuit", "false && printf should-not-run", 1,
         "The earlier command failed. The final command was not reached; do not infer its result."),
    ]
    with tempfile.TemporaryDirectory() as directory:
        for group, command, expected_code, correction in specifications:
            cp = subprocess.run(["/bin/sh", "-c", command], cwd=directory,
                                text=True, capture_output=True, timeout=5)
            if cp.returncode != expected_code:
                raise RuntimeError("Synthetic reproduction differed from its expected exit code")
            if group == "short-circuit" and cp.stdout:
                raise RuntimeError("Short-circuited command unexpectedly executed")
            result = {"output": cp.stdout + cp.stderr, "exit_code": cp.returncode, "error": None}
            observed = observe("terminal", {"command": command}, result)
            target = {k: observed[k] for k in ("execution", "diagnostics", "objective_verified")}
            target["correction"] = correction
            training.append(_candidate(group, {"tool": "terminal", "arguments": {"command": command},
                                               "result": result}, target,
                                       {"method": "real_synthetic_subprocess", "exit_code": cp.returncode}))
    snapshot = fixture()
    snapshot["policies"] = snapshot["policies"][:1]
    report = assess(snapshot, "Do these Entra policies require MFA?")
    if not report["verification"]["passed"]:
        raise RuntimeError("Synthetic policy evidence reconciliation failed")
    training.append(_candidate("report-only-policy", {"snapshot": snapshot},
                               {"verdict": report["findings"][0]["verdict"],
                                "correction": "Report-only does not enforce this policy's grant requirements."},
                               {"method": report["verification"]["method"],
                                "evidence_id": report["findings"][0]["evidence_id"]}))
    evaluation = [
        {"id": "eval-api-query", "group": "invalid-api-query", "synthetic": True, "license": "CC0-1.0",
         "input": {"exit_code": 1, "output": "shodan.exception.APIError: Invalid search query"},
         "expected": {"diagnostic": "invalid_api_query", "retry_unchanged": False}},
        {"id": "eval-nmap-resolution", "group": "nmap-target-resolution", "synthetic": True, "license": "CC0-1.0",
         "input": {"exit_code": 0, "output": 'Failed to resolve "fixture-a.invalid,fixture-b.invalid".'},
         "expected": {"diagnostic": "network_failure", "host_down_verified": False}},
        {"id": "eval-cancelled", "group": "cancelled-process", "synthetic": True, "license": "CC0-1.0",
         "input": {"exit_code": None, "status": "cancelled"}, "expected": {"execution": "cancelled"}},
        {"id": "eval-mfa-or", "group": "mfa-or-alternative", "synthetic": True, "license": "CC0-1.0",
         "input": {"state": "enabled", "grantControls": {"operator": "OR", "builtInControls": ["mfa", "compliantDevice"]}},
         "expected": {"verdict": "mfa_not_required_by_policy"}},
    ]
    for row in training:
        rejected = admission(row, evaluation_groups=EVAL_GROUPS)
        if rejected:
            raise RuntimeError(f"Dataset admission failed: {rejected}")
    return training, evaluation


def _candidate(group: str, inputs: dict, target: dict, reproduction: dict) -> dict:
    return {"id": "train-" + group, "group": group, "synthetic": True,
            "license": "CC0-1.0", "privacy_review": "passed",
            "reviewer": "operator-authorized-local-review", "input": inputs, "target": target,
            "provenance": {"kind": "original-synthetic-reproduction", "reproduction": reproduction,
                           "private_session_text_included": False},
            "verification": {"passed": True, "method": "deterministic_reproduction",
                             "input_sha256": digest(inputs), "target_sha256": digest(target)}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    training, evaluation = build()
    args.output.mkdir(parents=True, exist_ok=True)
    for name, rows in (("corrected-train.jsonl", training), ("independent-eval.jsonl", evaluation)):
        with (args.output / name).open("x", encoding="utf-8") as stream:
            stream.writelines(json.dumps(row, sort_keys=True) + "\n" for row in rows)
    print(json.dumps({"admitted_training": len(training), "heldout_evaluation": len(evaluation),
                      "group_overlap": 0, "model_training_executed": False}))


if __name__ == "__main__":
    main()
