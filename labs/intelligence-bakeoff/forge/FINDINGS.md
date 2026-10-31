# Engineering handback

Thread / owner / task: Operation Forge; isolated implementation and public review. No R-series ownership or requirements identifiers are changed.

Inputs: Haven base `53387e74a0ad90786ac3ea16753c8ad99142e9df`; installed Hermes `bf0203a794a0`; separately inspected Hermes main `c419cf7c864ac0ee511dbd9f7091a8bba0b567ee`. The preserved session and private runtime logs remain outside Git. The private dataset retains each source export hash, call/result message positions, tool-call ID and trace UUID/line. The published examples below are synthetic.

## Decisions

Use existing Hermes environment hints, shell scanners, session export, plugin hook and toolset machinery. Fix reproducible runtime defects upstream in separate PRs; keep the Haven synthetic security tool at the plugin edge. Do not train an adapter to compensate for deterministic software or tool-result failures.

The preserved Glasshouse export contains 114 messages and 47 tool calls; 46 have a correlated tool response and one has no exported result. Seven material failure patterns received private evidence-linked classifications. The session records a configured Qwythos model. The configured inference endpoint did not respond to bounded health checks during this work; its loaded weight identity and real-session model performance therefore remain unverified by those checks. A separate, explicitly bounded local model experiment has its own receipt and does not establish that the original service recovered.

## Evidence

| Finding and primary layer | Observed evidence and interpretation | Intervention and falsification |
|---|---|---|
| F01: Linux assumptions and hidden missing executable; model reasoning plus error handling | The saved prompt named macOS. A compound shell command attempted a Linux-specific utility, printed a missing-command diagnostic, and nevertheless returned zero. A zero status belongs to the shell's final status, not every earlier step. | [Hermes PR 147358](https://github.com/NousResearch/hermes-agent/pull/147358) warns on the bounded missing-command shape; [PR 147359](https://github.com/NousResearch/hermes-agent/pull/147359) adds macOS/local execution context. Falsify via a real terminal dispatch whose diagnostic is absent or incorrectly asserted on log-reading output. |
| F02: unsupported VPN prerequisite; model factual knowledge | Lack of selected VPN clients was followed by an assertion that public services could not be reached without a VPN. The available output does not establish that conclusion. | Treat VPN discovery, DNS/connectivity and authorization as distinct observations. No model replay has established that a prompt change alone fixes this reasoning error. |
| F03: privilege overclaim; model reasoning and context | A sudo password requirement was observed. It did not establish every sudo rule, remote privileges, or the meaning of a Linux-specific file on macOS. | PR 147359 adds effective local identity while explicitly separating it from sudo, authorization and remote privilege. Native local/remote isolation tests exercise the new text; model improvement remains unmeasured. |
| F04: missing Nmap; tool availability | The first attempted invocation returned 127 and a missing-executable diagnostic. This is an environment fact, not evidence that the model needs retraining. | Existing Hermes command-not-found handling is retained; PR 147358 also fixes zsh command-name extraction. |
| F05: unresolved Nmap targets with zero exit; error handling | Nmap returned zero alongside an explicit target-resolution error. Such a result does not establish that the unresolved hosts are down. | PR 147358 attaches a target-resolution warning without changing the result or retrying. The regression uses synthetic output; no scan is performed. |
| F06: rejected external search syntax; missing external knowledge | A service returned `Invalid search query`. Changing VPN state or privileges is not evidence that the syntax was corrected. | PR 147358 suggests checking the service's actual grammar and a minimal query. It neither retries nor contacts that service. |
| F07: unvalidated external response; error handling | A JSON parser failed on a response whose HTTP status and content type were not preserved. The parse error alone cannot identify authentication or network failure. | PR 147358 prompts inspection of the upstream status, content type and body. |

Two additional source-level findings are independently reproducible:

1. [`tools/terminal_tool_result.py::_interpret_exit_code`](https://github.com/NousResearch/hermes-agent/blob/c419cf7c864ac0ee511dbd9f7091a8bba0b567ee/tools/terminal_tool_result.py) guessed the final command of a shell chain. `false && grep pattern unused-file` was labeled “No matches found” although grep did not execute. A redirect can fail before the apparent command starts. [PR 147357](https://github.com/NousResearch/hermes-agent/pull/147357) uses the existing quote-aware scanner and suppresses ambiguous annotations. The prior open [PR 94360](https://github.com/NousResearch/hermes-agent/pull/94360) independently identified the same failure in an older source layout and is credited in the new PR. Scope: terminal result hints; risk: fewer explanations for compound commands; regression check: simple grep and signal annotations remain intact.
2. [`hermes_cli/prompt_size.py::_build_inspection_agent`](https://github.com/NousResearch/hermes-agent/blob/c419cf7c864ac0ee511dbd9f7091a8bba0b567ee/hermes_cli/prompt_size.py) uses a dummy URL to stay offline. That URL caused custom-endpoint context pins to be dropped: a synthetic 65,536-token configuration was inspected as 256,000, changing context-file truncation and the reported prompt. [PR 147363](https://github.com/NousResearch/hermes-agent/pull/147363) restores the configured pin on the disposable inspection agent; no endpoint is contacted. Scope: the offline diagnostic; risk: a custom context engine must support its writable context-window contract. Its initial fallback warning can still be emitted before the pin is restored.

The crash log also included an unretrieved gateway future after a disconnect. Current upstream `hermes_cli/gateway_client.py::GatewayClient.rpc` already retrieves the pending exception and has a regression test; the installed revision lacks that fix. No claim is made that an update was installed or that this warning caused the shutdown. The stream log separately records an incomplete tool-call stream; the source emits a warning, and no further defect is asserted without a reproduction.

Offline `hermes prompt-size --json` observed 12 exposed tool schemas occupying 16,519 JSON bytes in the sampled configuration. These are bytes, not a measured token count or latency. Hermes already supports toolset selection and a tool-search bridge; dynamic tool exposure must be compared against selection success and prefix-cache behavior before adoption.

## Interface changes

The optional plugin adds `forge_evidence` to terminal/process JSON results and two explicitly selected tools in the `haven-forge` toolset. Evidence contains a schema version, stable hash-bound event ID, result hash, observed execution state, optional exit code, diagnostic categories, an advisory next action, `objective_verified: false` and `OBSERVATION_ONLY` authority. Original tool fields are preserved. No approval, retry, remote-host, session-persistence or M0 contract changes.

Synthetic Entra findings name one fixture policy and source JSON pointer, bind source facts to a digest, and report whether independent truth-table reconciliation passed. The verifier is a second implementation over the same fixture and schema, not an independent Microsoft tenant or product implementation.

## Acceptance

The Hermes patches were tested on macOS ARM64 with the project's canonical per-file runner. The combined branch passed 148 tests with two host-specific skips; all 14 `scripts/check` checks passed. Each independently based PR has its own focused tests and lint receipt. The Forge local unit suite, plugin doctor, native dispatch probe, controlled local-model comparison and retrieval experiment are recorded in the experiment ledger. These results do not establish live-service model quality, a security assessment, or cross-platform acceptance.

## Risks and open questions

- Pattern-based diagnostic matches may refer to text printed from another program; warnings remain advisory.
- The Entra tool does not resolve assignments, exclusions, effective sign-in state, authentication-strength semantics or tenant-wide coverage. Unknown control combinations return `indeterminate`.
- The source repository is public. Raw traces, exported sessions, authentication data, host inventories and runtime logs remain private.
- A reproducible adapter pilot still needs verified data rights, sufficient corrected episodes, a held-out real-agent baseline, compatible training/serving versions, a fit probe and hardware-owner coordination. No model was trained or promoted.

## Next package

Review the public patches; resolve CI/reviewer feedback. Extend the synthetic comparison with independently specified cases and evaluate any production integration only in an isolated, authorized lane. If model failures remain after deterministic fixes and retrieval, expand the disjoint corrected trajectory set and validate the Qwythos adapter toolchain before considering training. Do not merge or deploy from this packet.
