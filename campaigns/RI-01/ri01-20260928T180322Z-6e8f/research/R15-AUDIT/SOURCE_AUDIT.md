# R15-AUDIT — pinned observatory source seams

Status: DRAFT_READY, submitted for independent review. Date: 2026-09-28 UTC. Author task: R15-AUDIT; native handle: /root/ri01_runtime_probe; researcher profile fallback. Exact model: NOT_EXPOSED.

This is completed, bounded source-audit prework. It is not the full R15 research, an integration selection, a security certification, or operational permission. Full R15 remains gated on accepted MM-FUSION and the other exact required inputs. No application code, tests, builds, package installation, devices, accounts, paid APIs, or Git commands were executed. NO_APPLICATION_CODE_CHANGED.

## Input-use receipt and source identity

The inspected fork is [erpzz/gods-eye-view at 81eb44340d90feda5b5283438f6e5fdad5cabbdd](https://github.com/erpzz/gods-eye-view/tree/81eb44340d90feda5b5283438f6e5fdad5cabbdd), identified by the supervisor's fresh main-branch receipt, committed 2026-09-27T20:14:59Z. This audit freezes that commit; it does not independently assert that main still points there at publication.

The untruncated TREE input has SHA-256 83c360ceee68a6a7375f398805124fcaba7f04561a20580672d76d81818e22b2. INPUT_AUDIT.json gives exact bytes, SHA-256, Git blob SHA-1, read extent, and downstream use for each inspected file. A hash of an entire file does not imply every line was semantically read. The 241-file private cache was an identity-verified input, not a claim that this author audited all 241 files. Eleven additional exact-commit files were fetched read-only into tool memory; no third-party source bytes were persisted by this author.

The governing researcher profile, RI authorization/protocol/vision, and R15 task card constrain this prework. The master prompt's source-audit requirements were reused; its complete architecture/opportunity survey is deferred to full R15. The input's older repository baseline does not supersede the RI frozen inputs. Accepted CORE concepts are used through the actual routed R03 consultation below, not invented implementation conformance.

## Findings

### A01 — useful source exports, private package

package.json declares private:true, version 0.1.1 and ESM. It provides explicit application, viewer, scene/control/data/tool, catalog/source, Director/scenes, search, and voice action/schema/controller/backend/session exports. Node-only build/provider exports are distinct from browser groups; docs/CODE-BOUNDARIES.md:97–127 describes the node condition without a browser fallback. This is a concrete source-level composition seam. It is not evidence of a published npm package, supported stable SDK, or arbitrary browser bundler compatibility.

package-lock.json is lockfileVersion 3. Selected resolved entries are Cesium 1.138.0, Vite 6.4.3, @jtarrio/signals 0.10.1, and @jtarrio/webrtlsdr 3.0.6. Their lock metadata is not an installation result, vulnerability audit, current release claim, or comprehensive license assessment. The package declares Node >=24.14.0 <25 or >=26 <27. No runtime upgrade is proposed here.

### A02 — constructor ownership is real; the stock composition is page-scoped

src/app/application.js is an inert lifecycle coordinator: constructing it creates lifecycle state, not a viewer or feed. start() shares its promise and constructs scene, controls, data, then tools. destroy() aborts the application lifetime, waits for a pending constructor, and cleans tools/data/controls/scene in reverse order; per-phase deferred cleanup is LIFO and collected failures do not stop later cleanup. Shallow-frozen component exposure does not make mutable component state immutable. ready means construction settled, not all feeds or restoration completed.

src/standalone/application.js has a module-level constructed latch that rejects a second construction and does not reset after destruction. Actual composition also uses fixed DOM nodes, shared layer modules, window hooks, and global provider values. src/app/scene.js owns cesiumContainer and credits; src/app/sources.js configures imported flight/vessel modules; data.js registers the shared catalog before restoration. The generic lifecycle supports separately owned components, but this does not establish that two stock composed applications safely coexist in one page.

Application tests statically inspectable at src/app/application.test.mjs:30–220 cover constructor inactivity, shared start/stop promises, cleanup order, partial failure and late constructor cleanup. They do not establish production multi-viewer isolation. No tests were run.

### A03 — a local credential broker is not two-user authority

SECURITY.md calls the product local public-data exploration, not a hardened public service. OpenAI/AIS/OpenSky secrets belong server-side; Google browser keys and Cesium tokens are deliberately client-visible and require provider restrictions. The OpenAI realtime provider exchanges a server key for an ephemeral browser secret. Its route handler has no tenant authorization check, and optional in-memory IP throttling is not a billing cap or Haven grant. A device able to reach the broker may consume owner quota.

Provider Settings is a separate, stronger local administrative seam. src/keySetupCore.mjs:188–324 rejects forwarded headers/sharing configurations, requires loopback and exact host authority, checks an exact Origin for POST, and requires JSON. server/standalone/key-setup.js:246–344 invokes admission, bounds submitted body, validates known updates, refuses externally managed key changes, persists accepted values and schedules server restart. The hardening module implements restricted credential-file permissions and verification, not encryption or tenant identity. Its helper subprocesses were read as source and never executed.

build/vite.js defaults to localhost. Explicit wildcard binding broadens allowed hosts; headers set X-Frame-Options DENY and CSP frame-ancestors none. Thus an iframe sidecar is blocked by the default server configuration. A separate top-level view is a more literal sidecar candidate; weakening those headers would need its own justified change and review. CORS/Origin defenses on Provider Settings cannot be assumed to protect every feed or token route.

### A04 — proxy defenses are route-specific

The code contains request cancellation, fixed provider endpoints and bounded-response helpers, but their presence does not prove universal SSRF or resource controls. The weather route inspected at server/providers/weather.js:415–499 restricts methods, query shape, URL length, products and timestamp/tile fields, and connects client close to abort. src/layers/weather/source.js rejects redirects and limits the manifest body.

Conversely, server/providers/firms.js:84–90 fetches a fixed NASA endpoint with a timeout and reads res.text(); that inspected call has no explicit redirect:error and no streaming response cap. This is a concrete review gap, not a demonstrated exploit or evidence of arbitrary user-supplied target access. SECURITY.md itself describes unequal provider protections, including the CCTV unknown-length stream limit gap. Radio DNS pinning and other provider protections are documented but were not exhaustively traced here. Full R15 needs a route-by-route exposure inventory before any LAN/private-data bridge.

### A05 — typed voice dispatch still contains effects and advisory cancellation

actionSchemas.js supplies named tools, argument restrictions, coordinate/range bounds, enums, and additionalProperties:false declarations. gevActions.js is a large executor with injected viewer, manager, search, Director and annotation dependencies. The runner's initial object guard is not a substitute for an independent schema-and-authority admission boundary.

Read-only view/context and scene-list/status operations coexist with camera motion, visibility changes, style/map mutations, annotation persistence, route queries, Director playback and stop/next. Annotation dispatch at gevActions.js:1194–1305 bounds batches and strings, can persist results, and records partial failures/direct-route fallback. A route drawn on a map is not safe-route evidence. Director play returns initiation, not completion.

realtimeTurns.js:355–436 passes signal/isCurrent plus local radio epochs. realtimeController.js:323–353 explicitly acknowledges that in-flight actions may finish map mutations after abort; the cap stops new dispatch, not rollback. stop closes transport/releases media and marks incomplete active response accounting, but this is not proof of remote computation termination, exact final cost, or revoked private-output suppression.

realtimeBackend.js implements the OpenAI Realtime token/SDP protocol: token GET, no-store/redirect rejection, combined timeout/lifetime signals, expiry checks, and SDP POST using the ephemeral credential. Merely changing URLs does not make an incompatible backend work. A Haven adapter must preserve the chosen protocol or replace the controller/backend contract. This source inspection does not verify contemporary provider availability, model names, pricing or API policy.

For later design, separately classify: local read; network read; view mutation; durable annotation/project mutation; download/share export; paid voice session; and any device/media acquisition. Exports and model-generated tool arguments authorize none of these on their own.

### A06 — import and replay restore presentation, not grants

DIRECTOR-SHARING.md and the inspected implementation distinguish UI preview from applying a project. Preview validation does not itself load assets into the viewer. Applying replaces the active project after playback cleanup. The programmatic importProjectFile path is documented for trusted callers and directly applies; it does not inherit the UI review step automatically.

Selected-scene JSON does not contain referenced bytes. Bundles include declared assets, not arbitrary live feeds, streamed tiles or registered media. Pack/bundle validation rejects traversal/URLs where paths must be relative, disallows unsupported fields, validates base64 and SHA-256, matches manifest sizes, and rejects unreferenced/missing assets. Attribution fields carry provenance; they do not confer rights.

The documented bundle limits include 50 MiB JSON, 64 assets, 8 MiB per asset and 32 MiB aggregate. Exact lower-level checks exist in manifest.js and bundle.js; no adversarial runtime validation was performed. Bundle byte owners can clear held bytes; playback stopping and retaining imported project assets are distinct. Browser storage of scene JSON does not guarantee the assets survive reload.

src/sharelink.js:268–377 uses generation and navigation tokens so late camera/view restoration can lose to newer user/voice intent. These are local UI ownership tokens, not CORE privacy authority vectors. src/director/sharing/lifetime.js cancels publication of late asynchronous values; it cannot compel an underlying uncancellable operation to terminate.

Actual consultation Q-R15AUDIT-H04-01 was routed by root to the R03 author. Their clarified answer is adopted as a proposed Haven boundary: imported scene/view/Director documents are untrusted presentation intent. Each new private display/replay needs current I01 influencing-source/grant/rights/purpose/session/device/audience/destination/route/provider/cancel closure, plus I06 exact-output/destination admission and fresh consumption. Historical receipts never become new permits or refunded uses. Ordinary view import into intact authority does NOT itself rotate the entire authority/restore epoch. Restoring or rolling back authority/evidence persistence, or losing its continuity/trust, does require the separate authority restore protocol. Embedded grants, permits or jobs cannot resume merely because a scene imports. This is peer contract advice, not their review of Director code or approval of a new schema.

### A07 — concrete document drift

docs/SCENE-DOCUMENT.md describes write version 5 and planned interactions. Actual src/director/document.js:1–77 sets SCENE_DOCUMENT_VERSION to 6, accepts migrations from 1–6 and imports interaction validation. DIRECTOR-SHARING.md also describes version 6. Pin the actual parser/writer and fixtures in later integration; copying the older document schema would be an avoidable incompatibility. This finding does not imply that every accepted migration or interaction was audited.

### A08 — preserve four distinct evidence classes

| Representative source | Honest classification and boundary |
| --- | --- |
| FIRMS source/provider | External satellite-derived detection records, not a live on-site thermometer or confirmed local fire. Provider aggregation/staleness and multiple satellite detections need provenance; no independent-evidence count from duplicate views. |
| Weather manifest/source/clock | Provider observation products with explicit timestamps, availability, latest/history modes and bounded image/tile requests. A selected historical frame must remain historical; no inference that every displayed pixel was contemporaneously sensed. |
| USGS/WFIGS/bundled cable factories in sources/reference.js | Reference/source adapters. The group name does not certify truth, precision or current validity. |
| Road traffic | Individual moving vehicle positions are simulated. src/layers/traffic/model.js:215–279 distinguishes configuration, errors and flow coverage; available flow samples may inform simulation but do not turn rendered cars into live tracked vehicles. |
| Thermal style | GLSL transforms rendered color/luminance. src/styles/thermal.js:261–263 computes a simulated temperature from image luminance. Its Celsius-looking HUD is not a measured thermal signal. |
| Annotations and routes | User/model presentation artifacts and resolver results with partial-failure/fallback states; not automatically observed objects, verified incidents or navigable geometry. |

The later MM-FUSION/R07 bridge needs explicit observed/reference/simulated/stylized/inferred/unknown tags, source time and lineage. A visual layer alone is insufficient to satisfy that bridge; this audit does not design or accept it.

### A09 — MIT code grant has explicit asset exceptions

LICENSE grants MIT terms to original code with notice preservation and an as-is disclaimer. Its exclusions explicitly cover third-party datasets/media and even some coordinates embedded in JavaScript. Examples named in the pinned inventory include TeleGeography CC BY-NC-SA 3.0, OSM-derived datasets under ODbL, and Bhote Koshi imagery plus derived coordinates in src/data/bhoteKoshiFloodPath.js under CC BY-NC 4.0. Removing only public assets would therefore not establish an unrestricted code-only redistribution.

THIRD_PARTY_NOTICES records the two Apache-2.0 browser SDR dependencies; it is not a complete dependency/asset license audit. DATA_SOURCES records provider-specific conditions, attribution and cache distinctions, including transient live-provider content versus committed decode fixtures. README also distinguishes promotional imagery from independently licensed reusable assets.

These are findings about the exact repository's declarations, not a fresh legal determination that all upstream licenses/terms remain unchanged or apply to a particular intended reuse. Full R15 must verify primary provider/dataset terms for the selected subset, preserve attribution and separate online access, offline caching, derived data and redistribution. No blanket MIT data-rights conclusion is supported.

## Viable seams, without selecting one before MM-FUSION

| Candidate | Source-backed viability | Material unresolved boundary |
| --- | --- | --- |
| Separate top-level sidecar | Existing one-page app can own its own lifecycle and public layers. | Default iframe denial, cross-origin bridge schema, separate output/audience admission, provider exposure and resource accounting. No automatic private feed injection. |
| Source-pinned composed application | Application constructors, shared catalog and explicit source injection are real. | One-page globals, provider lifetime disposal, dependency/build compatibility, license-selected assets and private-action mediation need bounded qualification. |
| Thin custom Haven view using selected modules | Pure schemas/backend interfaces, lifecycle helpers and selected adapters can be evaluated independently of stock shell. | More UI/viewer integration work; do not assume all exports are pure or generic. Preserve source provenance and test exact imported boundaries. |

None replaces CORE, introduces a new orchestration framework, or authorizes provider/device use. Existing 102-requirement scope, M0/R1 separation and M4 qwen2.5vl:3b are unaffected.

## Evidence limits and next decisions

Static tests read include lifecycle failures and cleanup, realtime token/expiry/abort transport mocks, bundle validation/cancel/late-read rejection, annotation transient-versus-definitive resolver misses, and share-link parsing/malformed-state assertions. These are useful falsifiable intended contracts. They were not executed. They do not test Haven dual-principal grants, audience revocation, actual provider billing, browser performance, microphone/network privacy, multi-viewer integration, or successful real-world sensing. Some share-link assertions inspect source-string ordering rather than an end-to-end browser.

The required independent R15 reviewer should verify load-bearing A02–A06 and A09 against exact bytes. Full R15 should consume accepted MM-FUSION/R07/CORE/R01 and then choose the smallest seam. Proposed implementation experiments remain AUTHORIZATION_REQUIRED: source-selected import/build qualification; mocked action-effect classification and revocation races; isolated public-only lifecycle/restore test; provider egress and quota-boundary tests; and a rights-reviewed offline asset subset. No such experiment was run or silently approved here.

Reused: explicit exports/lifecycle, validated presentation formats and public-source adapters. Amended: broad reuse assumptions into one-page, protocol-specific and rights-specific boundaries. Rejected: stable-public-SDK inference, local-broker-as-multiuser-auth, shader-as-sensor, stop-as-termination and scene-as-grant. Unresolved: full route audit, source/API rights refresh, exact MM-FUSION admission mapping, performance/resource measurements and operational qualification.

## Validation receipt

Only original audit documents and identity records were written in research/R15-AUDIT. No application files or source cache/manifests were changed. Whole-file hash verification was performed on inspected cached sources; fetched sources were checked against the pinned tree using exact Git blob bytes. Read extents are explicit in INPUT_AUDIT.json. One mistyped CODEBOUNDARIES path was corrected to CODE-BOUNDARIES before writing; no missing-file receipt was promoted to a source. No additional source content was persisted. Manifest hashes cover the final authored artifacts and exclude the manifest itself.

