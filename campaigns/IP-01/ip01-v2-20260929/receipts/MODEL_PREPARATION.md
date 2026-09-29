# Model preparation and frozen callable gate

Assignment 4 / RUNTIME. Status: PREPARED_NO_INFERENCE. Artifact acquired and every blob verified; dedicated backend launch/stop demonstrated. No inference, preload or generation has run. The root MODEL-READY assignment and independent benign lifecycle observation are required before any model claim. This file defines the concrete interface so APP can wire without enabling it.

## Private paths and ownership

All relative to clone `.ip01-runtime/`:

- `model/runtime-pin.json`: preparation-owned `{ "path": "absolute installed Ollama executable", "sha256": "full executable SHA256" }`. Trusted app reads this; **LOCALAPPDATA is not required** in its environment. Worker environment remains private. No executable path comes from an HTTP request or model output.
- `model/identity.json`: preparation-owned artifact/runtime/template/preprocessor identity, described below.
- `model/models/`: owned official-registry model storage.
- `model/model-gate.json`: **root-owned**, absent/disabled by default. Root writes/replaces it only after separate MODEL-READY authorization. Runtime only reads it.
- `model/model-call.lock`: runtime-held Windows byte-range lock; at most one admitted model workload across processes. Lock spans admission through cleanup observation.
- `model/model-calls.jsonl`: runtime append-only fsynced CLAIM/SETTLE resource ledger. APP remains sole SQLite/authority writer. No claim or ledger exists merely from importing the adapter or preparation. A corrupted/partial ledger fails closed.
- `model/call-starts/<claim_id>.json`: exclusive-create, fsynced network-start marker; prevents repeating generation on the same claim even after failure.

## Gate v1 exact shape

```json
{
  "version": "ip01.model-gate.v1",
  "enabled": false,
  "root_thread_id": "01a0eb51-c8b3-7923-94ed-ea1874de843e",
  "authorizing_task": "MODEL-READY",
  "independent_benign_receipt_sha256": "full SHA256 of reviewed independent lifecycle receipt",
  "scope": "SYNTHETIC_LOCAL_TEXT_IMAGE_ONLY",
  "expires_utc": "2026-09-29T10:10:16Z",
  "identity": {
    "manifest_sha256": "full hash",
    "runtime_sha256": "full hash",
    "template_sha256": "full hash",
    "preprocessor_sha256": "full hash"
  },
  "slots": {
    "root-issued-unique-token": {"allocation": "readiness"}
  }
}
```

Root may issue `readiness`, `lifecycle`, or `final` tokens only in the corresponding task/allocation. Runtime hard caps are 16/8/72; they are not gate-configurable. Root never removes claims to recover slots. **Q-MODEL-SEAM-02 decision: root issues a bounded token pool, not prebound job IDs.** The trusted APP reads `ModelAdapter(runtime_dir).gate_snapshot()` (metadata only), then inside its serialized admission transaction selects an unused token of the permitted allocation and durably binds it to the actual immutable job/attempt/fence/cancel/request-digest tuple with a unique binding receipt. DB uniqueness prevents two APP jobs using one token. No caller/model chooses the allocation, identity or token. This needs no manual root race and no per-call gate edit. The root enables only the allocation intended for that phase, including explicit later final-pilot freeze authorization. Ordinary UI requests use the trusted APP's currently enabled readiness allocation; the trusted pilot runner selects its root-authorized allocation through APP configuration, never through a public authority field.

APP's exact admission response is SEAM section 5 with `limits.model_attempt_token` (string), `limits.model_allocation` (one of those three values), `limits.model_binding_id` (APP durable receipt ID), `limits.model_gate_sha256` (canonical hash returned by gate_snapshot), and `model_identity` carrying the four gate hashes plus `inference_authorized: true`. Runtime records the complete admitted `job` tuple and binding_id in its claim, compares the unchanged gate digest, and enforces once-only token use independently. No true flag alone authorizes inference: root gate/pool, durable APP binding, current APP admission, artifact pin, global lock and remaining budgets are all required. Worker is never an authority writer.

Runtime appends `CLAIM` **before artifact verification/backend launch/network** after validating gate/token. Every claimed failure/partial/cancel counts. The record has `claim_id`, `token`, `allocation`, `observed_at`, `reserved_seconds:120`, exact `job`, pinned `identity`, and canonical `gate_sha256`. `SETTLE` binds claim_id, charged_seconds, cleanup_confirmed and outcome. Missing/uncertain settlement charges the full 120 seconds; no slot refund. Confirmed elapsed time includes verification/start/cleanup conservatively. Sum of charged time plus next 120-second reservation must fit 5400 seconds; at least 120 seconds must remain before min(gate expiry, unchanged campaign deadline). One claim cannot use a second generation/network marker.

All model admissions use Supervisor; there is no supported ad hoc warming/preload endpoint. The worker's only model request is `/api/generate` after its one-time network marker. Version/ownership checks, registry acquisition and `/api/show` identity inspection are preparation only and never request load/generate. Root coordinates model call slots; this assignment uses **0/96**, final deterministic suites **0/3**.

## Envelope and limitations

Pinned initial envelope: 4096 context, 768 generated tokens, one reviewed image, 120 seconds total per attempt, 12 GiB Job Object committed-memory cap, one active model workload, one loaded model, CPU inference (`num_gpu:0`), cloud off in process environment. No OS egress sandbox or production security claim. Input byte bound is not tokenizer proof; final token/image/context behavior needs the later readiness task. Wrapper exit/HTTP cancellation is never backend cleanup proof. Independent running-inference cleanup is still untested and must consume lifecycle slots.

Model identity includes `manifest_sha256`, list of every `blobs[{digest,size,mediaType}]`, runtime/version/hash, template/license/preprocessor hashes, exact prompt version/hash, envelope, rights source and `cleanup_readiness`. Acquisition is confined to `qwen2.5vl:3b` in the official Ollama registry. The upstream 3B checkpoint carries the Qwen Research License, limited to noncommercial research/evaluation; this synthetic local experiment fits that declared purpose, with no weight redistribution or commercial qualification. Sources checked: https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct/raw/main/LICENSE and https://ollama.com/library/qwen2.5vl:3b .

## Executed preparation and exact identities

Official installed runtime version **0.34.4**, executable SHA256 `d571e4cf0ad4456fccd33d5b985b6d63ba5669c6e5a812391704083952aae3d5`. Windows Authenticode reported Signature verified, signer Ollama Inc. Exact installed library tree also pinned: 989 files / 2,905,039,344 existing bytes, canonical manifest SHA256 `31503c17d27d9dcfe65d51fcaf6c9d9aac0700c30708f7735c61436ce8235625`. This existing runtime was not downloaded or changed. Private model identity JSON SHA256 `2e1c3d48426655a4c3494924eb8c93873034a2b17373c9635436a1f225d805a9`.

| Pin | Full SHA256 |
|---|---|
| Official manifest (`qwen2.5vl:3b`, Q4_K_M) | `fb90415cde1ef08aa669ae74b082d49b158729b6db1ab183c941417d507e71a1` |
| Model GGUF blob (3,200,614,720 bytes) | `e9758e589d443f653821b7be9bb9092c1bf7434522b70ec6e83591b1320fdb4d` |
| Configuration blob (567 bytes) | `97a23b280c2ebb5f368f1d9eef57c1924b234e7f92e2dca7f3f38d960e9331bd` |
| Template blob (487 bytes) | `a242d8dfdc8f8c2b0586ee85fba70adb408fb633aba2836fe1b05f2c46631474` |
| System blob (28 bytes) | `75357d685f238b6afd7738be9786fdafde641eb6ca9a3be7471939715a68a4de` |
| Registry license blob (11,343 bytes) | `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e` |
| Parameters blob (23 bytes) | `52d2a7aa3a380c606bd1cd3d6f777a9c65a1c77c2e0cb091eed2968a5ef04dc3` |
| Upstream Qwen Research License | `b5c0e5cf74cf51af1ecbc4af597cfcd13fd9925611838884a681070838a14a50` |
| Final preprocessing descriptor (includes runtime library manifest) | `b6b6a5ebfa3bb4f08f1edad7ae9950d09b79facf9e1ef2be6c16761beb236ee5` |
| Application prompt prefix, ip01.synthetic-evidence.v1 | `63e51cc4647c7a738783a5c877f4e7caf6d9572d926d6b280379f7d0b685a993` |
| Read-only `/api/show` snapshot | `9833411bcbf5ae667fb2218d4e40aa9f3657ec36755d3fcebb0119015757ff61` |

Upstream commit `66285546d2b821cf421d4f5eb2576359d3770cd3` pins the inspected model config, tokenizer config, preprocessing config and license. The registry packages Apache-2.0 text whereas this upstream 3B checkpoint uses its Research License. Both exact documents are retained privately; the narrower noncommercial research/evaluation scope is applied. This is not a general commercial license determination. Weights and runtime binaries are not publication artifacts.

Preprocessor identity pins compiled Ollama/runtime libraries, native qwen25vl model blob, upstream reference configs and actual APP derivative bytes/digest in each context. It does not claim empirical equivalence between the upstream Python preprocessor and Ollama's native implementation. Actual image/context fitting remains a readiness test.

Preparation command, from clone with `PYTHONPATH=labs/ip01`, private TEMP/TMP and `PYTHONDONTWRITEBYTECODE=1`: `.ip01-runtime/venv/Scripts/python.exe -B labs/ip01/tests/runtime/prepare_model.py probe --runtime-dir .ip01-runtime`, followed only after success by the same command with `acquire`.

| Attempt / private evidence under `.ip01-runtime/model/preparation/` | Actual result |
|---|---|
| `20260929T044231Z-probe/receipt.json` | FAILED_RETAINED: listener preceded API readiness and version request timed out. Exact owned Job Object cleanup confirmed zero members/signaled handles. No generation. Individual backend identity was not retained in that failed receipt; do not claim a later PID recheck for it. |
| `20260929T044259Z-probe/receipt.json` | PASS after bounded readiness polling repair, unchanged 20-second launch deadline and 3-second stop target. Version 0.34.4, total 14 transient job members across initialization; final active0, signaled handles. |
| `20260929T044318Z-acquire/receipt.json` | PASS: owned official `/api/pull`, all manifest/blob sizes and full hashes verified, `/api/show` metadata only; final active0/signaled, peak committed Job Object memory 410,890,240 bytes. No inference/runner-memory qualification. |

Acquired model blobs total **3,200,627,168 bytes**. With the earlier 1 GiB dependency/browser debit plus conservative metadata overhead, root should record **4.1 GiB total campaign acquisition** (additional debit 3.1 GiB), below 12 GiB. Exact transport overhead is unknown. Actual runtime storage was 4,181,347,512 bytes at final observation, below 20 GiB; retained host free disk exceeded 10 GiB. Initial storage includes other agents' concurrently written private material, so this is a dated observation rather than an exclusive-attribution total.

Private GPU inventory was inspected read-only: roughly 6.8 GiB VRAM free. Selected initial envelope remains CPU-only because tested Job Object committed-memory enforcement is available; no actual GPU-inference peak/abort evidence exists. This avoids claiming a GPU resource bound from a snapshot. CPU latency/72-call feasibility is UNKNOWN until readiness; there were no comparative calls and no model switch. Root may revise a supported envelope only before pilot freeze with fresh documented gates, never silently after failed results.

Final private observation: both successfully identified owned backends no longer alive; zero listeners on 11435–11437; root gate absent; campaign model-call ledger absent. Model calls **0/96**, inference wall consumption0, final deterministic suites **0/3**. Isolated unit-ledger tests use artificial claims in `.ip01-runtime/runtime-dev/gate-test-*` only and make no backend/network calls. Unknown/unfinished real model claims block subsequent admissions until independently reconciled; the adapter does not automatically clear or refund them.

Next action: root relays the pool binding to APP, obtains independent benign lifecycle results, then issues a separate MODEL-READY assignment and creates the closed-schema gate/pool for its explicitly authorized allocation. This preparation does not enable any inference route by itself.
