# Model Lab 0.1.0 — execution report

Prepared October 4, 2026. **Runnable-source development preview; Windows/GPU acceptance pending.** These are author-produced tests, not an independent agent review.

## Actually executed

| Check | Result / scope |
|---|---|
| Python source and test compilation | PASS, `python -m py_compile *.py tests/*.py` |
| JavaScript syntax | PASS, `node --check static/app.js` |
| Local Python test suite | **46 tests passed**, 12.668 seconds in the recorded final run |
| Real HTTP exchange with local synthetic inference server | Executed in the suite: SSE/Unicode, API argument mapping, usage attribution, partial-stream errors, cancellation, one-request concurrency and no hidden retries |
| Local API boundary | Executed: token/Host/Origin checks, rejected remote endpoints, no directory traversal, no implicit downloads, malformed request handling |
| Downloads / artifacts | Executed against synthetic transports/files: SHA mismatch, resume range handling, existing-file protection, disk guard, partial-file retention, unsafe ZIP and size rejection. No official model/binary downloaded here |
| Owned process lifecycle | Executed on **Linux with benign processes**: start/stop, duplicate launch rejection, exited-root cleanup, and old-owner stop cannot kill a newer owned process |
| Static desktop/mobile layout | Actual Chromium rendered supplied HTML/CSS **in memory**, at 1440×1000 and 390×844, with no horizontal document overflow. Both PNGs inspected visually. No network requests; no application JavaScript/API flow executed by this render |
| Live browser integration | **BLOCKED**, not passed: system Chromium rejected the initial localhost navigation with `ERR_BLOCKED_BY_ADMINISTRATOR`. No alternate network route or browser-policy bypass was attempted |

Actual test command: `python -m unittest discover -s tests -v`.
The live-browser script remains at `tests/browser_smoke.py` for a permitted development host. The separate rendering script is `tests/render_static.py`; it is not a substitute acceptance result. Its screenshots explicitly say OFFLINE LAYOUT PREVIEW.

## Retained failures and repairs

The first 43-test run passed 42 tests and failed one harness assertion: it waited a fixed 0.2 seconds for a benign Python process to exit. The harness now waits up to three seconds for an observed exit and always cleans up. No backend inference was involved. During development, one patching command had a Python string syntax error and applied no changes; it was corrected before the next test run.

Source inspection also prompted fixes for terminal-state publication before metrics were available, stale startup/old-owner cleanup races, preservation of an unconfirmed ownership guard, active-request reconnect rejection, and truthful TEST_DOUBLE benchmark labels. Added tests exercise the available paths. The Windows implementations are still unexecuted. A subsequent 46-test run passed in 12.548 seconds, followed by the final 46-test pass above after additional cleanup/reporting changes.

The live-browser attempt stopped at its first navigation. Consequently no live-browser form, cancellation, download, or export assertions were reached. Their existence in a script is not execution evidence.

## Not executed / not established

- Windows PowerShell bootstrap, downloaded portable Python execution, upstream Strata setup, runtime DLL loading or Windows Job Object behavior on the user's PC.
- NVIDIA/CUDA kernel execution, GGUF loading, Qwen inference, Strata inference, actual offload, real tokens/second, energy efficiency, temperatures, peak GPU memory, or desktop responsiveness.
- Live Hugging Face/model downloads, llama.cpp release downloads, or hosted model requests.
- A universal GPU-memory-fit guarantee, “fastest engine” result, model quality ranking or measured improvement from speculative decoding/quantized KV.
- Any changes to the user's PC, driver, accounts, firewall, pagefile, services or existing Haven campaign.

Fixture token counts and decode rates are intentionally synthetic and must not be quoted as performance. Runtime usage from a real engine is marked BACKEND_REPORTED; stream chunks are not tokens. Public benchmark artifacts created by this package should still be reviewed for private host paths/inventory before sharing.

## Shutdown observations

Each test owns and closes its HTTP services and sockets. The Linux process tests stop their exact owned group/root. The blocked browser attempt closed Chromium and both test HTTP services in `finally`; the independent static-render browser was also closed. No resident inference service, model process or scheduled job was created by this delivery. This is scoped test cleanup, not a host-wide process census.

## First-PC qualification

Run the launcher, verify the folder-local runtime, then load the starter 4B model. Confirm the NVIDIA name/VRAM and inspect the llama.cpp log for actual CUDA layers. Generate a short answer, explicitly run one benchmark, cancel a longer response, unload and confirm GPU memory is released. Test Strata separately after its large-download approval. Do not interpret a successful UI launch alone as successful GPU inference. Keep the error/log if a step fails; no automatic fallback or repeated heavy restart should hide it.
