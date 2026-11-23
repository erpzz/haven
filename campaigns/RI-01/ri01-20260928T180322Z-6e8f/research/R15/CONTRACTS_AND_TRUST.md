# Proposed Observatory contracts and trust boundaries

Status: documentary proposal reconciled to independently accepted MM-FUSION on 2026-09-29 UTC. Namespace `ri01.proposed.observatory.v1`. No deployed schema, shared-file edit, runtime acceptance or operational grant. R15 itself is submitted for independent review.

**NO_CORE_SEMANTIC_CHANGE.** This proposal adds renderer/query/export profiles over CORE I01–I07, R07 CR01–04 and accepted MM-FUSION F01–F08. It does not narrow or widen CORE's first finite-use profile, change accounting, invent a second authority vector or replace existing domain owners. Consumer impacts are explicit below.

## Accepted MM-FUSION reconciliation and retained review gate

Read the full candidate CONTRACTS, REPORT, DELTAS, MODALITY_REGISTRY, NEXT_PACKAGES and INPUT_RECEIPT, then the full independently accepted review. Exact manifest c5fd20410d718bea5a1e02141b53ef925cfec0948e7e73be0a1f0045142ce7a9 is unchanged. Candidate advice was provisional at drafting; this final section consumes accepted bytes. R15-AUDIT remains author prework awaiting this packet's independent review.

F01 EvidenceAtom, F02 AlignmentDecision and F03 FusionSet are conserved into F08 `ri01.proposed.mmfusion.scene-projection.v1`; the other profile IDs are `ri01.proposed.mmfusion.evidence-atom.v1`, `ri01.proposed.mmfusion.alignment-decision.v1` and `ri01.proposed.mmfusion.fusion-set.v1`. R15 adds presentation/query constraints, not replacement wire schemas. Native capture intervals and clock error determine operation-specific ordering; strict BEFORE requires latest possible A < earliest possible B, never causal inference. Unknown dependence precludes independent-weight fusion. Eligibility applies before ranking/counting/context, including hidden metadata and influencing derivatives.

**MF-L01 retained:** before any MF-P0 execution, H06 freezes missing-sidecar, mismatched-sidecar-digest, stripped-essential-metadata and changed-authority-reimport assertions in its existing MF16/MF32/MF35 allocation within76 invocations, or versions the allocation first. R15-T export/import cases must independently name those mutations in their own fixture freeze; they are not additional MMF invocations and no cross-packet budget is pooled. A test summary cannot stand in for these assertions.

The public fixture proposal exercises inert/mock projections and UI decisions only. Passing it would not qualify the actual CORE authority store, model adapters, perception, media decoder, device or physical runtime. Actual MM-VISION/AV pilots retain their existing48-attempt allocations and independent lifecycle/rights/semantic-oracle gates. No model is installed, benchmarked or selected here; M4 remains qwen2.5vl:3b.

## Controlling inputs and admission

CORE CONTRACTS SHA256 df19f37926b33851236aca230859adfef332a85120380ea04c24294237c2e6d0 controls I01–I07. R07 CONTRACTS9185653cdd0f24f73c7312710aae20f53d848a3fa622bcd68c17fc4489011ac3 supplies frames/support/correlation/replay. R01's accepted amendment0f1acb6fb6dbcd9d1a39a39d083275a82eb57e56175f71c235ab99e385c56535 controls truthful delivery wording. R03 author consultation Q-R15AUDIT-H04-01 is actual routed advice distinguishing presentation import from authority-store restoration.

A producer carries exact source and transformation references; a consumer declares a supported profile/version. Reject missing/unsupported schema, nonfinite numbers, duplicate IDs with conflicting content, missing required lineage, unresolved authority, over-budget payload and incompatible units/frames. An opaque original may remain retained under its own rights even when no qualified projection can be built. “Cannot project” is not evidence the underlying event did not occur.

All records have immutable ID/revision, canonicalization profile, raw-byte versus canonical-metadata digest distinction, producer/version, exact parent references, correction/tombstone links, and complete influencing dependencies. Hash correctness is identity/integrity evidence, not truth or authenticity. References use canonical public repository URLs in research artifacts and relative paths; production opaque IDs never accept arbitrary filesystem paths.

## Proposed adapter-facing records

| Record / producer → consumer | Minimum additional fields and behavior | Existing authority |
|---|---|---|
| SourceDescriptor / curated registry → adapter | Provider identity; endpoint template ID; API/product edition; terms/attribution/version/date; operation/cache/export/derived-use eligibility; credential class; fixed host/redirect policy; response/schema/byte/time limits; spatial/temporal support; outage/quota rules; metadata egress and retention. A public URL is not automatic fetch permission. | I01operation/provider policy; I02source identity; I05budget |
| ObservationEnvelope / source adapter → evidence store | Native source/event IDs; immutable raw bytes/digest; content type; source fields/units; origin and claim/support axes; native time interval/clock/boot and mapping uncertainty; receive/process time; geometry/support/frame/datum/calibration; quality/correction; lineage/correlation. Preserve original rather than silently repair. | I02 plus R07 CR01, later MMF F01 |
| SceneEntityProjection / projection → view | Exact view/entity/source revision; claim/observation class; support geometry/mask; native and display coordinates with transform identity; uncertainty; valid/knowledge time; status; current output identity; denied details removed. Entity is a representation, not necessarily enrolled physical identity. | R07 MapView plus I01/I06; MMF conservation requirement |
| TimelineSlice / temporal query → replay | Valid-time interval, knowledge cutoff, selected revisions, source-local/UTC basis, clock uncertainty, gaps, corrections, interpolation policy, ordered/indeterminate relations, actual retained coverage. No synthetic events in a measured layer. | R07 CR04; I02/I03/I06 |
| Annotation / user or admitted tool → store/view | Attributed author role; selected source/geometry/time; text-only payload; USER_ASSERTED/INFERRED/SCENARIO classification; revision; scope; parents; rights/expiry; expected revision for edit. A pin is not a physical observation or verified identity. | I01/I02 plus typed digital write; later I06share |
| ViewIntent / user → view dispatcher | Selected exact scene/record/time, requested camera/filter/highlight operation, audience/destination and mode. Split local view state from any network fetch or persistence. | Existing view ownership; I01if retrieval/egress/release follows |
| AnalysisRequest / sponsor → H02 coordinator | Question, immutable context and profile, exact source closure, deterministic/model/simulation route, budget/deadline/attempt/lease/cancel, expected result schema. Screenshots may supplement, never replace structured evidence. | I03/I04/I05/I06 unchanged |
| ScenarioSpec / user → isolated analysis | Base refs, branch ID, assumptions and modifications with provenance, model/code profile/seed, finite input/output/time bounds, connector capability set EMPTY, allowed synthetic resource namespace, result limitations. | I04/I05; current I01for copied evidence; no I07execution capability |
| DomainActionProposal / view → domain owner | Exact real/simulated resource identity, goal, input evidence, qualification refs, expected config/revision/boot, sensing versus carrier-motion distinction, sponsor and deadline. Starts PROPOSED_NOT_AUTHORIZED. | I07/R09/R10/R08/R11 only; no generic execute URL |
| PublicationPolicy / projection → authority | Requested operation/purpose, audience/destination/route/provider, complete dependency vector reference, expiry and required current checks; no client-supplied allow Boolean. | I01canonical vector and I06admission |
| ExportManifest / export gate → recipient/importer | Exact output/scene and source-sidecar digests, profile/version, ordered included assets and hashes, omitted categories, attribution/rights, times/support/frames/lineage/uncertainty, destination/purpose and receipts where appropriate. Receipts explain history, never grant future import/replay. | I01/I02/I06; fresh import/output checks |

Native multi-axis meaning is conserved: modality/measurement kind; observed/inferred/historical/generated/simulated/stylized/reference; occupied/free/occluded/unobserved/conflict support; source/receive/knowledge times; and certainty are not one overloaded “confidence” field. A historical measurement can remain measurement-origin while not current. A caption, crop, tracked frame and parent image are dependent evidence; do not count them as independent votes.

## CR-R15-01 — exact projection semantics

Owner H08 with MM-FUSION and H00; consumers GEV adapter, table, question-context builder and export.

Geographic horizontal input preserves WGS84longitude/latitude ordering and declared CRS; reject swapped/out-of-range coordinates rather than normalize silently. A map's displayed viewport is not sensor uncertainty. Preserve altitude unit and datum ELLIPSOID/AMSL/RELATIVE_HOME/UNKNOWN, geoid/home origin revision and device boot/config where applicable. Unknown vertical datum permits a clearly2D marker only when the profile authorizes it; it cannot yield ground clearance, route safety or a3D collision claim.

Local metric data requires exact frame/map/calibration and paired SpatialSemantics ID/hash/version from R06/R07, not bare triples. The accepted convention p_parent=R*p_child+t, normalized xyzw and specified left-parent covariance stays unchanged. Unsupported SE3/Sim3, scale or covariance fails closed; use a source-local nonmetric pane when allowed. R08 scalar-only profile cannot become6DoF because it is rendered in3D. Coordinate conversion preserves original precision and records approximation introduced solely for rendering; precision is not accuracy.

Antimeridian-spanning extents split for rendering under a declared transform; preserve original extent in evidence. Pole/wrap tests reject self-crossing or grossly enlarged footprints. Coarse detections remain footprints/resolution bands; no street-address association without separate evidence.

Required proposed renderer result: QUALIFIED_PROJECTION, SOURCE_LOCAL_NONMETRIC, TABLE_ONLY or UNAVAILABLE, plus reasons visible only when allowed. Missing essential semantics cannot become a simplified confident marker. The source-linked table is a valid useful result. `supports_safe_route_claim=false` persists.

## CR-R15-02 — temporal query and correction

Owner H08/H02/H04; consumers replay, brief, scenario, caches.

Keep event/capture intervals, provider publication/updated time, native sample/PTS/ticks/clock/boot, receive/process and knowledge cutoff separate. UTC mapping includes uncertainty and provenance. One source-local sequence can remain inspectable when global alignment is unknown; it cannot support synchronized causal claims. Do not insert or interpolate data through a gap as observed. Any permitted interpolation/extrapolation has its own derived class/profile and support interval.

“As known then” selects only records available by the chosen knowledge cutoff; “corrected now” uses currently eligible revisions for that valid time. Both apply present rights and tombstones. Immediate ineligibility propagates to all derivatives/caches; if reverse lineage cannot resolve, deny the materialization wholesale until trusted recomputation. Erasure receipts separately report requested/acknowledged/verified/unknown per copy. Linkable hashes are not automatically exempt from retention controls.

Cache identity binds query/profile, full exact source/map/transform/calibration/authority dependencies and output identity. A browser/service-worker cache is never a fresh authority oracle. Public offline fixtures can be replayed within rights; no disconnected private/shared exception is invented.

## CR-R15-03 — projection/export conservation

Owner H00/H08/H04; consumers GEV Director/import/export, MCAP/Rerun adapters and field packs.

Accepted MM-FUSION F08 requires a mandatory digest-bound evidence sidecar carrying F01/F02/F03 meaning. CONTRACTS SHA256 fed1ad340e9d45b95d71252e25ce183ac89cfbdd4449d74025d29ceb5454dfb9 and independent review c244ac41c7a443839c66725356db434f4b4da73d36811362654cd067c73ae9dd are the controlling exact inputs. An exporter unable to preserve essential source class, support, time/frame/uncertainty/correlation/lineage/authority context returns UNSUPPORTED_PROFILE or emits only a safe explicitly limited table. Reimport cannot promote a bare geometry/scene into qualified evidence. Media references do not exempt actually delivered bytes from the whole-output bound.

P0 export is one public-only JSON document ≤256KiB, with source metadata included and no private media/assets or executable attachments. The embedded sidecar and ordered projection content are separately digest-bound under a versioned canonicalizer inside that single document; the whole document has its own output digest. It obeys the smaller CORE limits despite Director accepting larger bundles. Do not split one private payload into multiple files/chunks to bypass finite-use whole-output rules. Future rich media streams/multiple destinations need separately accepted profiles; they are retained research, not silently enabled.

Imports parse inert data with allowlisted fields, bounded nesting/counts/bytes, text-safe labels and fixed asset IDs. No arbitrary URL, HTML/script, shell, plugin, custom shader or network fetch from imported fields. ZIP/traversal/expansion-bomb tests apply before any later archive support; the first profile needs no ZIP. Scene IDs, grants, receipts, jobs and resource links supplied by an import cannot activate or authenticate anything.

Ordinary camera/view/Director import into intact authority does NOT rotate the whole authority instance or restore epoch. Restoration/rollback/lost continuity of authority or evidence persistence is different: new epochs, review-only reconciliation and no resumed permits/outbox/jobs. This distinction is actual R03 author clarification, not a new CORE exemption.

## CR-R15-04 — operation catalog and egress

Owner H00/H04/H02 and each domain owner; consumers UI, voice tool adapter, source adapters.

| Operation | Concrete effect | Required boundary |
|---|---|---|
| VIEW_NAVIGATE | Camera/filter/highlight on already admitted data | Local view ownership; any tile/geocode request is a separate network read |
| READ_QUERY | Retrieve stored source/projection | I01read and current source eligibility; scoped query |
| REFRESH_SOURCE | Fixed provider request | Specific source/provider/network admission, rate/byte/time budget and metadata exposure |
| WRITE_ANNOTATION | Persistent user assertion/new revision | Typed write, expected revision and lineage; no qualification inference |
| ANALYZE/SIMULATE | Deterministic or qualified model job | I03–I05 exact context/route/remaining budget; scenario capability isolation |
| SHARE/EXPORT | New destination disclosure | Full I01and I06 current release/consumption; every influencing parent |
| DIGITAL_EFFECT | Reminder/message/account operation | R05/COREI07 separate domain contract; unavailable in first slice |
| PROPOSE_PHYSICAL | Inert observation/mission/fabrication intent | Domain proposal only; exact resource evidence and missing conditions |
| EXECUTE_DOMAIN | Actual acquisition/motion/print/output effect | Separately qualified domain authority, sealed tuple, supervision/resource lease; no Observatory generic endpoint |

Geocoding strings, viewport extents, tile coordinates, URL fragments/referrers, attribution links, thumbnails, source counts, telemetry, browser caches, logs and export manifests can reveal private context. P0 uses local-only search, original public geometry, no third-party tiles/scripts/fonts and no model/voice. A future private view cannot automatically reuse a public provider map; reviewed egress must explicitly cover coordinate/viewport disclosure. Clearing visible controls is not sanitizing a public projection. Default GEV keyless fallback is denied in private/offline routes.

Future source fetchers allow only registered HTTPS hosts/ports/templates; enforce DNS/IP/private-network protections, redirects and response/expansion bounds at the actual transport boundary. Imported URLs/LLM text never configure a new provider. Endpoint availability checks themselves are scoped operations, not harmless automatic probes. Browser CSP/CORS help but do not replace authorization or server-side egress checks.

## CR-R15-05 — UI truth and independent output records

Owner H01/H04/H02; consumers desktop/mobile/glasses/director.

I06 remains four orthogonal records: immutable ReleaseAuthorizationReceipt; immutable ConsumptionPermitReceipt; append-only DeliveryObservation; current PermitEligibilityDecision. Bind exact whole-output digest/canonicalization, destination/route/audience/session/device revisions, release/consume sequences and full vector. P0 finite grant count stays ONE_RELEASE_ONE_DESTINATION_WHOLE_OUTPUT, charged atomically once at release; consumption redeems its existing slot without a second debit or requiring unused parent quota. Duplicate/unknown replies do not remint/refund/replay.

Example: release authorized → consumed → ACKlost → revoke. Show “Earlier delivery unknown; further sharing blocked,” retain immutable receipts and no automatic resend. Example: displayed historical output → cancel. Historical display report remains; future eligibility changes. Authentication of a report does not prove human perception. SUPPRESSED requires positive prevention of an unsent/unconsumed future operation, not an absent ACK.

“Saved here; not sent” is allowed only with positive authoritative no-dispatch evidence for that exact tuple. Otherwise use unknown. Stop narration, cancel analysis, request acquisition stop and physical recovery are separate controls/outcomes. GEV controller abort and application teardown do not prove remote computation/physical cessation or zero cost. No private draft leaks via progress labels.

## CR-R15-06 — isolated scenario and resource identity

Owner H00/H08 with H05/H09/H10/H11; consumers branch editor and proposal adapters.

ScenarioSpec has no executable connector capability, credential or live resource alias. All resources have explicit namespace/origin and exact config; synthetic resource cannot become real by toggling exercise_only. Base evidence is copied by eligible immutable reference, with current rights; assumptions are branch-local, never overwrite source facts. A scenario result may produce a separately reviewed inert proposal, not execute an action.

Readiness is a domain observation with freshness and qualifications. Ownership, visible icon, heartbeat or platform name does not establish readiness. Missing outcome after dispatch remains UNKNOWN and retains exclusion/reservation; no duplicate motion. Independent help does not wait for map/model/aircraft readiness. All sensing/movement/contact/fabrication and stop/recovery qualification remains outside R15.

## Bounded first profile and precise change request disposition

First profile uses two synthetic principals,≤32sources,≤16grants,≤128lineage edges/depth16,≤64KiBmetadata closure and≤256KiBwhole output; stricter than raw source storage limits. Twelve event fixtures and three simulated resources fit only if actual complete closure also fits; never truncate ancestry to meet bounds. Raw public snapshot limit2MiB is a storage/ingest limit, not permission to release2MiB or silently admit more independent sources.

CR01–06 are proposed profile additions for H00/H08/H04/H01 review. No CORE vector field, ordering point, finite-use rule, spend truth or operation qualification changes. There is no authority exception for public-looking data, imported scene, learned completion, offline cache or administrator POV. Remaining implementation choices are schema/canonicalizer versions, exact adapter module paths, source transport/rate qualification and renderer capability checks. The small public fixture can succeed without solving private streaming, robotics or all-world mapping.
