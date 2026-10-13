# Ukraine Civilian Cyber Defense — Windows Scheduled Task Triage

**Purpose:** a small, defensive, read-only triage tool for explicitly authorized Windows endpoints used by Ukrainian civil-society groups, humanitarian organizations, journalists and other legitimate defenders. It is **not** a complete malware scanner or incident-response substitute.

## Source and confidence

- [Digital Security Lab Ukraine, 24 August 2026: Living off GitHub — From Gmail Reply-Baiting to Fileless Exfiltration](https://dslua.org/publications/living-off-github-from-gmail-reply-baiting-to-fileless-exfiltration/).
- DSLU describes a scheduled task with a `GoogleUpdateTaskMachineUA...`-style name and VBE payloads executed from `C:\Users\Public\Music`. These are **historical example signals**, not universal indicators.
- Encoded and hidden PowerShell command checks are **generic suspicious patterns**, not attributed by DSLU to that specific intrusion.

## Run (your own or expressly authorized systems only)

1. Review `scripts/Export-ScheduledTaskReview.ps1` before executing it locally in Windows PowerShell 5.1 or newer.
2. Run: `.\scripts\Export-ScheduledTaskReview.ps1 -OutputPath .\tasks.json`.
3. With Python 3.9+ (offline), run: `python scripts/analyze_tasks.py tasks.json --output report.json`.
4. For the harmless example: `python scripts/analyze_tasks.py examples/sample-tasks.json`.
5. For automated analyzer checks: `python -m unittest discover -s tests -v`.

**Privacy:** Both tasks.json and report.json can contain usernames, identifying paths and script arguments. Never post raw evidence in GitHub issues, public chats, or AI services. Keep local and redact before sharing. There is no network access, remote command execution, quarantine, or automatic changes.

## Triage guidance

- **high**: a suspicious pattern combination. Verify publisher, signatures, task metadata, script and timeline using your organization's established incident-response process.
- **review**: weaker signal, not proof of compromise.
- **no findings**: **not** proof the endpoint is clean.
- Preserve evidence and coordinate with authorized incident responders before disabling a task or touching suspect files.

## Limitations and safeguards

- Python analyzer test suite covers benign and suspicious fixtures; **Windows collector has not been executed on a Windows endpoint by this project**. Technical review required before production use.
- No unauthorized scanning, exploit attempts, live attacker infrastructure interactions, automatic blocking, credentials collection, or PII uploads.
- Useful follow-ups: Pester tests of the collector; Windows VM validation; Ukrainian-language operating guide validated by native speaker; additional carefully sourced detections; integration with trusted civilian SOC workflow.
- This package supports civilian cyber defense only. It is not affiliated with CERT-UA or Digital Security Lab Ukraine.

## Existing bundle

A packaged ZIP with full source code and tests is also available in the ChatGPT working conversation where this branch was authored; repository code should be reviewed independently.
