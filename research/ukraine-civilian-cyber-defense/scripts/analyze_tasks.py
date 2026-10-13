#!/usr/bin/env python3
"""Offline, read-only scheduled-task triage for authorized Windows exports.

The tool does not access endpoints, modify tasks, or contact the Internet.
Signals are triage leads, not proof of compromise.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Signals grounded in the 24 August 2026 Digital Security Lab Ukraine report.
# Independent rules below also catch similar suspicious scripting patterns.
TASK_NAME_CAMPAIGN = re.compile(r"^GoogleUpdateTaskMachineUA(?:\{|$)", re.I)
PUBLIC_MUSIC_SCRIPT = re.compile(r"\\users\\public\\music\\[^\s\"']+\.(?:vbe|vbs|js|jse)\b", re.I)
PUBLIC_SCRIPT = re.compile(r"\\users\\public\\[^\s\"']+\.(?:vbe|vbs|js|jse)\b", re.I)
SCRIPT_HOST = re.compile(r"(?:^|[\\\s\"'])(?:wscript|cscript|mshta)(?:\.exe)?(?:[\s\"']|$)", re.I)
ENCODED_PS = re.compile(r"(?:^|\s)-(?:enc|encodedcommand)(?:\s|:)", re.I)
HIDDEN_PS = re.compile(r"(?:^|\s)-(?:w\s+hidden|windowstyle\s+hidden)(?:\s|$)", re.I)


def analyze_task(task: dict[str, Any]) -> dict[str, Any] | None:
    name = str(task.get("TaskName") or "")
    path = str(task.get("TaskPath") or "")
    actions = task.get("Actions") or []
    if not isinstance(actions, list):
        actions = [actions]
    findings: list[str] = []
    score = 0
    if TASK_NAME_CAMPAIGN.search(name):
        findings.append("Task name matches published DSLU 2026 campaign pattern")
        score += 3

    for action in actions:
        if not isinstance(action, dict):
            continue
        command = " ".join(str(action.get(k) or "") for k in ("Execute", "Arguments", "WorkingDirectory"))
        if PUBLIC_MUSIC_SCRIPT.search(command):
            findings.append("Script executes from Windows Public Music directory")
            score += 4
        elif PUBLIC_SCRIPT.search(command):
            findings.append("Script executes from Windows Public directory")
            score += 3
        if SCRIPT_HOST.search(command) and (PUBLIC_SCRIPT.search(command) or "http" in command.lower()):
            findings.append("Script host combined with public-path or URL execution")
            score += 2
        if ENCODED_PS.search(command):
            findings.append("Encoded PowerShell command scheduled")
            score += 2
        if HIDDEN_PS.search(command) and "powershell" in command.lower():
            findings.append("Hidden PowerShell execution scheduled")
            score += 1
    if not score:
        return None
    return {
        "task_name": name,
        "task_path": path,
        "state": str(task.get("State") or "unknown"),
        "priority": "high" if score >= 4 else "review",
        "score": score,
        "reasons": list(dict.fromkeys(findings)),
    }


def analyze_export(export: Any) -> list[dict[str, Any]]:
    if isinstance(export, dict):
        export = [export]
    if not isinstance(export, list):
        raise ValueError("Expected a JSON array or single task object")
    findings = []
    for task in export:
        if not isinstance(task, dict):
            raise ValueError("Every task must be a JSON object")
        result = analyze_task(task)
        if result:
            findings.append(result)
    return sorted(findings, key=lambda f: (-f["score"], f["task_name"].lower()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", type=Path, help="JSON created by Export-ScheduledTaskReview.ps1")
    parser.add_argument("--output", type=Path, help="Optional local report JSON path; default stdout")
    args = parser.parse_args()
    try:
        tasks = json.loads(args.json_path.read_text(encoding="utf-8-sig"))
        findings = analyze_export(tasks)
    except (ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Cannot analyze export: {error}", file=sys.stderr)
        return 2
    report = {
        "warning": "Triage leads only; not proof of compromise. Verify findings before action.",
        "source_report": "https://dslua.org/publications/living-off-github-from-gmail-reply-baiting-to-fileless-exfiltration/",
        "findings": findings,
        "count": len(findings),
    }
    serialized = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        try:
            args.output.write_text(serialized, encoding="utf-8")
        except OSError as error:
            print(f"Cannot write report: {error}", file=sys.stderr)
            return 2
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
