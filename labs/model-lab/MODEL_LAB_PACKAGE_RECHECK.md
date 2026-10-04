# Haven Model Lab — pre-setup recheck

Date: 2026-10-04. Scope: supplied source ZIP in this chat's Linux development environment, not the operator's Windows PC. No PC installation, official runtime/model download, GPU inference, Strata start, native agent launch, GitHub publication or background watch was performed.

## Exact input

`Haven-Model-Lab-v0.1.0-Windows.zip`

SHA-256: `e1896c14a8a6513cd1a7f24754684b224099a80af87547f2e13166f8d833f6c0`

All 29 entries of the included `MANIFEST.sha256` matched the extracted source bytes. The original ZIP and source were not patched by this recheck.

## Executed recheck

Command: `python -m unittest discover -s tests -v`

Result: **46 tests passed in 12.644 seconds on Linux**. This rechecks software behavior with local synthetic inference fixtures and benign process tests, not real model performance or Windows support. The original code author also performed this review; no independent certification is implied.

## Specific Windows qualification gaps observed in source

`tests/test_lab.py` decorates `ProcessTests` with `@unittest.skipIf(os.name=='nt', ...)`. Its three lifecycle tests therefore do not qualify the Windows Job Object implementation. A successful Windows invocation must report skips and add actual benign Windows evidence, not carry forward 46/46 Linux acceptance.

`tests/browser_smoke.py` waits for the GPU label to contain `GPU telemetry`, reflecting its original missing-GPU test environment. A real detected GPU may legitimately replace that text, so this needs a deliberate hardware-fixture/real-hardware split rather than deletion of the startup assertion. The script also passes `--no-sandbox` to Chromium; do not blindly carry that container-style option onto the PC. Use normal supported browser sandboxing. Cleanup should cover missing-browser and failed-launch paths as well as navigation outcomes.

`bootstrap.ps1` and `strata-setup.ps1` were inspected but not executed. Verify their runtime/archive layout, SSL/import paths, venv/pip support, exact flags and upstream installer side effects on the target PC. The reviewed Python official index lists both full amd64 and embeddable archives; do not confuse them or infer that their features are interchangeable.

## Next admissible action

Have a Windows-local agent inspect the selected extracted folder, verify relevant hardware/resource facts, repair narrowly justified test/installer issues with recorded diffs, and return a sanitized preflight checkpoint before approved downloads. Establish one real small-model CUDA baseline before separately approving the large Strata installation. Keep Strata as an explicit goal, not an unreported substitution.

See `MODEL_LAB_AGENT_HANDOFF.md` for the complete operator-launchable assignment. Providing that file is not itself a started agent session.
