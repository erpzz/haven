# GEV audit reuse and full-R15 delta

Owner fork: https://github.com/erpzz/gods-eye-view at 81eb44340d90feda5b5283438f6e5fdad5cabbdd. Upstream: https://github.com/bilawalsidhu/gods-eye-view. Root freshly reported unchanged main for this assignment; this child ran no Git. Haven base remains376031e182c57495912baf6727093b0b188da568.

## Exact prior work reused

R15-AUDIT/SOURCE_AUDIT.md SHA2560c09786e2c7ddaf7275840c924218f8b819b9f047d7234937f2eeb882f0a2b74 and MANIFEST.json f29e746157d7d04f5c0c9cf38210872a84ace1351b5cc63b1600c1f70eb71a1a are actual completed author prework, NOT independently accepted input. The eventual full R15 reviewer must judge their load-bearing claims. INPUT_AUDIT.json records50 exact source identities and explicit read extents; it does not claim all241 cache files were read. Eleven extra exact-commit source files totaling113508bytes were fetched only into tool memory. No third-party application copy was added to public artifacts.

## Findings retained and consequences

| Audit finding / exact seam | Verified source content | Consequence for proposed integration |
|---|---|---|
| A01 package.json/lock and docs/CODE-BOUNDARIES | Private ESM package; explicit exports; Node/build groups separate; selected lock Cesium1.138.0/Vite6.4.3. | Source pin and build/asset notice audit, no stable/npm SDK assumption or dependency upgrade by default. |
| A02 src/app/application.js; src/standalone/application.js; actual constructors | Start scene→controls→data→tools; explicit stop tools→controls→data→scene, with LIFO cleanup within each phase. Pending construction awaited; terminal destroy; stock standalone constructed latch and page/global ownership. | One top-level Observatory per page. ready is not feed-ready. Repeated mounting/multiple stock viewers not promised. |
| A03 SECURITY, build/vite.js, keySetupCore, provider OpenAI realtime | Local public exploration, client-visible restricted browser keys, local broker; settings has loopback/origin controls; default iframe denial. | No private data into stock broker or LAN exposure. Separate top-level sidecar, not iframe, if used. Settings defenses are not tenant auth. |
| A04 representative FIRMS/weather/common HTTP | Different bounds/abort/redirect protections per route. FIRMS fixed endpoint reads res.text without explicit redirect rejection/body streaming bound at inspected call. | Route-by-route egress review; no inherited universal SSRF/size guarantee. P0 excludes these default proxies. |
| A05 voice schemas/executor/controller/backend | Typed arguments; effects include persistent annotations/network routes/playback; abort may leave in-flight map changes; token/SDP speaks OpenAI Realtime. | Disable paid voice/default action executor in P0. Later allowlisted tools get fresh Haven effect admission; endpoint substitution alone is insufficient. |
| A06 Director bundles/share restoration | Validation, preview/apply distinction, content hashes and byte limits; direct programmatic import can apply; local generation tokens; cancelled late-result publication differs from stopping work. | Import presentation only. Preserve digest-bound source sidecar and fresh private release. Never import grants/jobs. |
| A07 scene document | docs/SCENE-DOCUMENT says writev5; actual document.js constv6 accepts1–6 and interactions. | Pin actual validator/migrations; reject incompatible profile, do not follow stale prose. |
| A08 layers | Weather/FIRMS are provider records with time/coverage; traffic actors simulated; thermal shader computes display temperature from luminance. | Persistent textual class labels. No thermal-sensing, building-scale fire or live vehicle claim. |
| A09 LICENSE/notices/data inventory | MIT original code; data/models/derived coordinates excluded; selected NC/share-alike/ODbL assets. | Notice/file/asset allowlist. No whole-repo redistribution before rights review. |

Source anchors and exact hashes for these findings remain in the original audit; the report is referenced rather than recopied as fresh inspection. No source/UI screenshot, app startup, performance, network capture or test execution supports these statements.

## Additional current read: search and private egress

Five exact cache files were read fully and independently matched to the same tree. New finding A10: src/search/defaults.js composes coordinate and preset matches first, then configured Google, keyless Photon and local Nominatim fallback; a default geospatial instance also reads a window key. A query that misses local names can therefore leave the host without a billing key. It is wrong to equate keyless with offline/private.

src/search/placeSearch.js has a bounded provider chain, combined12second timeout/lifetime/caller cancellation, result cache64entries, positive TTL300seconds and negative30seconds. This bounds that service's code path, not arbitrary provider side effects or Haven retention eligibility. coordinateGeocoder constructs a display viewport around parsed degrees; the viewport is not a measurement-uncertainty bound. Preset normalization is name matching, not physical identity verification. Its first duplicate name wins, so disambiguation remains an application concern.

| Path | SHA256 |
|---|---|
| src/search/index.js | a66a14e0ba245389a53efd9a9605f810647a7e99b0404160cbb5ed3a056a65e6 |
| src/search/defaults.js | 01e810ee84a1c4b883430053934eb980aabc63ab5e523980899a45e02c41bd56 |
| src/search/coordinateGeocoder.js | 5b18e27cf0639cbe0cb55652ba3ac2ffa48538a1d92663cae375e165993e869a |
| src/search/presetGeocoder.js | 63f38eba722777cef02ef9e699778df0afeb15e2c6f9a101c7289ea2ccde8b60 |
| src/search/placeSearch.js | a817bf9f3a850c4bf09a4707c3976b46feb9e4708bc29416ddf8e928d0a40511 |

Choose a caller-constructed local-only provider list, not the default chain, for private or offline profiles. Network reverse geocoding/routing/elevation are separately denied until admitted. Unknown local place returns unavailable/clarification; it must not trigger a hidden fallback.

## Rights matrix

Original MIT source: retain notice and identify modifications. Apache-2 Cesium/SDR and all lockfile dependencies: retain applicable notices; no complete dependency/license/vulnerability pass claimed. TeleGeography and Bhote Koshi material have NC/share-alike conditions in the pinned LICENSE; Bhote Koshi derived coordinates are also embedded in JavaScript. OSM-derived datasets retain ODbL obligations. Model/3D asset providers have individual terms. Browser keys, Google/Cesium content, live feed quotas, cache retention and exports are separate contracts. Public web checks for the small selected source set appear in SOURCES_AND_COSTS; no blanket clearance for all GEV layers.

## Maintenance strategy and workload estimate

Keep the owner fork pin as the integration baseline; upstream is a source of candidate fixes, not an automatically substituted version. Proposed adapter code lives in an independently owned prototype directory and imports an explicit module allowlist. Keep a ledger of upstream path/blob, adapter dependency, license/data exclusions and tests. On an intentional update, compare only affected exports/lifecycle/scene format/providers and lockfile; replay the same fixture contract tests, refresh notices, then independent review. Do not auto-merge fork/upstream, patch all modules, or let a scene bundle install plugins.

Composed-route adaptation estimate24–40engineering hours plus8review hours is a planning range, conditional on a120minute lifecycle/build/zero-egress feasibility check. Sidecar public bundle exchange is estimated8–16hours but has weaker synchronized inspection; a custom minimal2D view16–24hours preserves evidence functions with less cinematic capability. These are author estimates, not benchmarks or vendor quotes. Exact install/build/network operations require a separately approved package and rights/dependency gate. Failure of the composition proof triggers the documented fallback, not an open-ended rewrite.
