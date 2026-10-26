# HS01 private worker vertical slice

This extends Model Lab and the R02 / HS01 inference gateway design. It does not
replace Haven memory, two-person privacy, robotics, RF/spatial, fabrication,
emergency-support, drone or agent responsibilities. Intelligence remains an
advisory subsystem; no model gains machine administration or physical authority.

## Source and state

- Base: diagnostic PR #41 at `50d1df9451c75b134f2945526516a0fc5c1ad5e6`.
- CPU work reused from PR #42, exact source
  `44e08d2730fad7112f0ef69a5143e964a5c5c5b5`. Its 11 tests passed on Slink before
  integration. PR #43 at `bea1b50aa99b1948a52abfe838d717438359d91a` is an overlapping
  implementation: its 55-test `test_lab` suite also passed; it was not deployed.
- Design: `design/hs01-headless-federation-20261025`, HS01 v2 and v1 federation
  intent; R02 v1 inference gateway, eligibility-before-routing and memory rules.
- Existing ecosystem research: `labs/model-lab/docs/ECOSYSTEM_AND_MODEL_SCOUT_20261005.md`.
- Implementation is committed separately. The morning receipt records actual
  deployed revisions, real inference, failures and measurements. A passing fake
  HTTP fixture is not a successful Mac inference test.

## Browser flow

Playground's **Run this conversation on** selector offers the current Slink
runtime, each explicitly enrolled private worker, and **Automatic**. Selecting a
different worker starts a fresh conversation; old conversation text is not
silently sent to a new machine. Each result identifies its actual worker,
compute mode, routing reason and measured timing. The hardware cards remain
measurements of Slink, the control host, and the browser explicitly says so.

The CPU lane from #42 is available in Setup / Model library. It uses the existing
pinned GGUF with zero GPU layers and child-only CUDA masking, with RAM admission
and an eight-thread cap. Slink still owns one GGUF process at a time. Worker
routing copies the selected connection into each job; choosing the Mac does not
disconnect or unload the Slink model. The first Lab implementation admits one
chat/benchmark request at a time, while independently owned external agent jobs
remain separate. This is not a distributed scheduler or unlimited parallel chat.

Automatic routing is a deterministic availability rule: prefer the already-ready
compact Slink model when its GPU is not reserved; otherwise try enrolled private
workers. It never cold-starts Strata, installs/downloads anything, routes to a
hosted provider, spends money, or claims task-quality qualification. It is a
text-chat prototype, not R02's complete qualified task router. Explicit selection
fails closed if that worker is offline or its credential/model identity fails.

## Registry and trust

Private mode-0600 JSON enrollments live in the private Lab `providers/` directory.
Only an owner-authored SSH enrollment may introduce a worker. The browser can
reload/probe that fixed set; it cannot enroll a URL, upload a key, or select a
principal through a model argument. Only literal loopback OpenAI-compatible
`/v1` endpoints are supported. No DNS, remote HTTP, redirects, public listener or
generic proxy is added. The existing Lab bearer/session/CSRF boundary remains.

This slice grants worker access only to administrators. Members cannot list or
probe worker inventory, reload enrollment, select an enrolled worker or invoke
the automatic route. Existing member chat uses the existing Slink backend. This
does not assert fine-grained two-person worker sharing; that needs explicit
principal grants before expansion. Logout also clears conversation DOM and
cached provider/diagnostic selection in that browser tab.

An enrollment records random node identity, label, backend type, exact installed
model digest, context bound, declared compute/RAM capability and owner trust.
Authenticated `/v1/models` probes record online/offline/auth-failed/model-mismatch,
readiness, UTC-equivalent capture time and metadata round-trip latency. Stale
observations are labeled; dispatch rechecks authentication/model identity.
Readiness does not prove good answers. Live worker resource usage, native tools,
vision, multi-model lifecycle and full task qualification remain unknown or
unsupported unless measured separately. No fake zero utilization is displayed.

## Prepared Mac worker

`mac-worker.py` operates one owner-enabled Apple Silicon worker using the pinned
Homebrew llama.cpp 0.7.0 / commit `620d2225c` binary and an explicitly prepared
SmolLM2 1.7B Instruct Q4_K_M artifact:

- Quant repository: `bartowski/SmolLM2-1.7B-Instruct-GGUF`.
- Revision: `1f03464768bfcc0319fc50da8ff5fb20b6417ba2`.
- File: `SmolLM2-1.7B-Instruct-Q4_K_M.gguf`, 1,055,609,824 bytes.
- SHA-256: `77665ea4815999596525c636fbeb56ba8b080b46ae85efef4f0d986a139834d7`.
- Original publisher: [HuggingFaceTB](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct);
  [quantizer's artifact card](https://huggingface.co/bartowski/SmolLM2-1.7B-Instruct-GGUF).
- License metadata: Apache-2.0. Native tool reliability and Haven qualification
  are not established. This is a small non-Qwen federation/compatibility sample,
  not a claim that it beats Qwen3.5 4B.

The helper does not download models or install runtime dependencies. It verifies
the prepared artifact, limits context to 2048 / one slot / four CPU threads,
requires Mac memory headroom, binds only loopback port 8890, uses a private
API-key file, disables web UI/MCP proxy, and requests offline Metal inference.
It installs its own launcher under the private application directory because
macOS does not grant LaunchAgents access to Documents. No privacy permission is
weakened. A normal user LaunchAgent supervises this fixed process, not a shell
or an agent tool executor.

`enable` opts the owner into worker mode. `enroll` creates a dedicated reverse
SSH tunnel and sends the enrollment credential over verified SSH stdin, never
chat/argv/GitHub. `disable` disables/unloads only this LaunchAgent and closes
only its dedicated tunnel. Artifacts and private receipts are preserved.
The current reverse tunnel is session-scoped; automatic tunnel recovery is a
follow-up, and an unavailable Mac is honestly offline. Client mode works without
enabling a worker. The same Mac can be a browser client and worker simultaneously.

## Evidence and rollback

Focused tests cover actual HTTP/SSE transport with an explicitly fake model,
credential isolation, URL rejection, explicit-offline no-fallback behavior,
unchanged managed connection during a worker request, and LAN member denial.
The live acceptance must instead run a real browser request through Slink's
gateway to the Mac process, record genuine output/timing/usage and the worker
process/Metal observations, then exercise authenticated disconnect/reconnection.
Prompts, answers, enrollment files and host resource logs stay private.

Rollback: select Slink again without stopping its process. Disable the owned Mac
worker/tunnel with its helper. Restore the previous Lab application branch and
restart only after its current request/owned-engine users are idle. Preserve all
model weights, SSH keys, Windows/internal volumes, research branches and private
receipts. No driver, firewall, SSH security or system-level service change is part
of this slice. Homebrew runtime dependencies are separately recorded in the
private implementation log; do not uninstall shared dependencies blindly.
