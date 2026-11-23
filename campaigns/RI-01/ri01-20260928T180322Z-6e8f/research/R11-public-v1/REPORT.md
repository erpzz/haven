# R11 — Emergency support and resilient communications

## Metadata and one-page result

Author `/root/ri01_privacy`, role `haven_researcher`, H11; public research on 2026-09-28. Status: **AUTHOR HANDOFF; INDEPENDENT REVIEW REQUIRED**. This is documentary design, not implemented capability or operational authorization. All proposed experiments are **NOT_EXECUTED**. Campaign base reported by the supervisor: `376031e182c57495912baf6727093b0b188da568`; exact working-tree inputs are separately hashed. The unavailable source-era R11 prompt has not been reconstructed. The actual RI-01 R11 card and supervisor assignment govern.

The first useful slice is an offline, public-safe help card plus a manually reviewed incident draft, explicit location uncertainty, and a truthful transport ledger. Ordinary phone help remains reachable through the phone's native facilities without waiting for Haven, a model, a map, a robot or an aircraft. A local portal can remain useful without Internet. A mesh node can exchange small messages without providing Internet. A confirmed network transfer does not establish human receipt or a rescue response. These distinctions should be visible in the product, not buried in an operator log.

Recommended documentary decisions:

| ID | Decision | Why useful / retained limit |
|---|---|---|
| D11-01 | Phone-first, independent help; optional AI and vehicle budgets cannot consume its reserved capacity | User can use a familiar native pathway immediately. No third-party automatic emergency integration is qualified. |
| D11-02 | Separate public offline material, private incident draft and externally sent incident | Public help remains available while a private dependency is unavailable; no laundering through encryption or emergency labels. |
| D11-03 | Preserve four CORE output records and add typed domain transport observations | Lost ACK, cancellation and historical delivery can coexist truthfully. |
| D11-04 | Select a no-worker, synthetic replay before hardware | A small positive utility slice and failure oracle can be reviewed with no service charge or device access. |
| D11-05 | Keep ground light, phone/speaker and manually accessible kit as baselines | Useful logistics do not require solving flight, autonomy or payload qualification first. |
| D11-06 | Defer disconnected private admission and operational standing-policy dispatch | They require explicit transport, authority, provider and professional review beyond P0. |
| D11-07 | Compare direct/star paths before mesh or moving data ferries | Add relays only when measured deadline coverage justifies energy, exposure and complexity. |

These are proposed synthesis choices, not self-acceptance. CONTRACTS.md contains domain extensions through existing CORE I01–I07. PATHWAYS_AND_COSTS.md identifies exact public compatibility evidence and unknown owned tuples. EXPERIMENTS_AND_PACKAGES.md freezes finite positive and adversarial cases and three future packages. REQUIREMENT_MAP.json preserves the canonical H11 IDs, text, owner and AT references.

## 1. Useful human flow

For this document only, the United States is an explicitly labeled emergency-communications research scenario. The user's timezone establishes no jurisdiction. Other jurisdictions, local call-center capabilities, operator/region restrictions and the owned phone/OS/service tuple remain **UNKNOWN**.

The native phone path is primary. A Haven screen may offer a reviewed local instruction card explaining how to use the phone's native emergency facilities and show an editable draft with the location, callback information if voluntarily supplied, and observed incident facts. It must not imply its own website or chat is an emergency service. A tap that opens a native interface is not a completed call. Text accessibility and local support must be verified; a generic messaging API is not a qualified emergency gateway. The National 911 Program explicitly distinguishes local app technical/legal capability from mere app availability. [911.gov FAQ](https://www.911.gov/calling-911/frequently-asked-questions/).

A useful synthetic draft could say: “Exercise only. A reports a blocked doorway. Last location sample 14 seconds ago; reported horizontal accuracy 18 m, meaning not independently validated. Building/floor not known. User-entered landmark: east entrance. No responder receipt recorded.” This is an invented fixture, not a current incident, location, diagnosis or accuracy claim. Typed facts, source labels and editable corrections precede any model summarization. No output demands that a person troubleshoot Haven before seeking help.

Two independently enrolled users remain distinct. A may share an incident involving A without thereby sharing B's health history, private notes or location. A joint summary requires the full influencing-source intersection; omitting B's citation does not remove B's influence. A controlled output destination is selected explicitly. Audio may not fall back from private earphones to a speaker; a loudspeaker instruction is a new audience and operation. Lock-screen notifications, clipboard, screenshots and exports are disclosure surfaces with their own admission/retention limits.

## 2. Observation and interpretation

R04 supplies the distinction between historical health records, presently sampled measurements, OS permission visibility and medical interpretation. An absent Watch sample is not a normal vital sign, proof of incapacity or proof of withdrawal. No threshold here diagnoses a condition. The first draft contains user statements and exact sourced observations; model interpretation is excluded by default and, in a later reviewed profile, visibly labeled rather than promoted to a measurement.

R07 supplies source-time, frame, uncertainty and lineage rules. Preserve capture interval, receipt and processing times independently. A newer arrival may contain an older location. Report the source clock/boot and nullable UTC mapping with uncertainty; no received-at substitution for captured-at. WGS84 horizontal position does not establish altitude datum or a building floor. Retain vendor-native values, explicit units, invalid/unknown accuracy and vertical datum, home/geoid/map revision where applicable. Conflicting GNSS, user-entered address and map associations remain separate until reviewed. A local map never proves global location or a safe route.

Image crops, transcripts, video frames and a model description of those inputs are correlated derivatives, not corroborating witnesses. Noise, ambiguous names/numbers and untranslated terms can damage a useful incident description. The soft MM-AV input supports preserving original language, uncertain critical tokens, typed fallback and an accessible local stop. Its accepted ADDENDUM-1 overrides the old ASR study denominator; R11 conducts no ASR study and does not silently create a second one.

## 3. Three communications services

**Public local information.** Pre-reviewed, versioned, rights-cleared static help, a clear local-only indicator, and the date of last verified public information can remain available when upstream connectivity is lost. Stale notices say stale; generated directions are not official instructions. Even status metadata must be public-safe: a device nickname, private home coordinates, participant presence or an incident counter can expose someone. No camera, microphone, private identity or emergency-contact enrollment is a condition of reading public material. A local check-in, if later authorized, is an explicitly optional human-triaged message, not dispatch.

**Short-message relay.** A small immutable message may move between authorized peers over a separately qualified transport. Regional radio settings, exact firmware, interference, airtime, encryption/authentication, power, recipient identity and storage limits matter. Meshtastic is a relevant public candidate, not an installed dependency or a demonstrated rescue network. It is not LoRaWAN and is not inherently Internet access. A mesh must outperform direct or stationary relay baselines on the chosen deadline, not merely increase hop count. Its documentation exposes important privacy limits recorded in SOURCES.md. [Meshtastic radio settings](https://meshtastic.org/docs/overview/radio-settings/), [encryption](https://meshtastic.org/docs/overview/encryption/).

**Actual Internet backhaul.** Cellular, a provisioned satellite broadband terminal, wired access or another explicit provider supplies upstream connectivity. An SSID, relay ACK, strong radio signal or airborne node does not prove reachability of a required endpoint. Record each layer and the time/error of a bounded endpoint check. A provider being reachable still says nothing about a human responder. No active probing, AP, radio, broker or backhaul was used in this research.

Guest, private-user, sensor, control and administrator planes require separate authorization and network isolation in later implementation. A captive-portal protocol reports captive status; it is not evidence that all destinations work and does not implement isolation. No deceptive certificate installation or warning bypass is proposed. [RFC 8908](https://www.rfc-editor.org/rfc/rfc8908.html).

## 4. Offline authority and message truth

Loss of Internet differs from loss of trusted current local authority. A complete, current, locally resolvable authority vector may support an otherwise authorized local operation. If any required remote revocation, policy, source, session, audience or provider dependency cannot be established as current, new private release/replay is denied or unknown. This is root's actual accepted-source interpretation in Q-R11-01, not a new CORE-author endorsement or an implementation result.

An immutable encrypted envelope may be researched as a separately bounded transport profile with recipient, metadata, route, expiry and retention dependencies. **The accepted P0 whole-output permit does not already authorize disconnected forwarding.** Disconnected private admission is deferred. Encryption protects some contents but does not confer source rights, conceal every metadata field, revoke a copied plaintext, or authorize a relay provider. Public static content is useful without inventing an offline bearer exception.

Use the CORE four-record model; never replace it with one mutable SENT/CANCELLED flag. An application may know that a relay stored bytes while remaining uncertain about destination arrival, display and human acknowledgment. A lost ACK remains unknown through revoke. A past delivery report remains historical through cancel, while future consumption is denied. Cancel before admission, fencing unsent work, stopping a worker, removing queued copies and requesting remote deletion are different observable events. Unknown external writes are reconciled by exact immutable identity and never automatically replayed.

BPv7 can support delay-tolerant research, but its delivery to an application agent does not prove that application processed the payload. RFC 9713 updates administrative-record registries, not human receipt or a new universal custody guarantee. Reports and expiry have protocol-specific meanings; adapters retain them rather than relabeling them “help sent.” [RFC 9171 §5.7](https://www.rfc-editor.org/rfc/rfc9171.html), [RFC 9713](https://www.rfc-editor.org/rfc/rfc9713.html).

## 5. Standing policy and physical assistance

Record, capture, retain, summarize, disclose, send, cancel, safety-stop and physical dispatch are different scopes. A deliberate live action can authorize a bounded operation for the authenticated principal; a gesture, transcription, haptic or lack of response does not itself authenticate that principal. “Emergency” is not a global bypass.

Preserve the original later S2/T33–35 incapacitation scenario and independent mock help path. A standing policy is a previously authorized, versioned, one-use scenario with exact owner, subject, evidence eligibility, bounded validity, destination, disclosure scope, cancellation/safety behavior and separate physical capability. It is not live consent fabricated from silence. R10's 15-second no-ACK value is a synthetic fixture, not a clinical or operational threshold. No missing notification alone launches a vehicle or contacts a service. Current R11 only proposes replay of the policy; real automatic contact and real motion remain separately gated.

For lights, speakers and equipment, start with ground fixtures, ordinary manually carried equipment and an accessible kit. Availability, battery/readiness, expiry, item qualification, safe access and human usability are distinct. A kit at a coordinate is not a kit within reach, understood or used. A speaker's specified sound level is not intelligibility or safe exposure. A bright lamp can create glare or conceal a hazard. Do not rush-print critical equipment or improvisational batteries in response to an incident. Public preparedness guidance supports simple lighting, communication plans and alternative phone power as ordinary baselines. [Ready.gov](https://www.ready.gov/).

Aircraft is an optional later carrier. R10 retains control, telemetry, video and help-backhaul as four separate links, unknown EC120 identity, payload/power/thermal/flight effects, jurisdiction and professional deployment gates. R09 is a soft running input; no ground-robot agreement is claimed. An active incident area, emergency label or software API never establishes clearance. Preserve M0–M6, simulator/M4 and later S1/S2; this report completes none of them.

## 6. Real deployments and limits

The National Park Service reports a January 2025 Death Valley rescue initiated using a satellite-enabled phone. A helicopter was dispatched, but loose rock and rotor-wash risk prevented the intended hoist; rangers completed a ground rescue. This is evidence of a communication pathway and professional change of plan, not an aircraft-first prescription or a reliability estimate. [NPS account](https://www.nps.gov/deva/learn/news/sar-2025-01-15.htm).

In a Swedish observational AED-drone study, 211 suspected alerts yielded 72 deployments and 58 deliveries; paired arrival analysis covered 55, with drones first in 37. The median lead of 3m14s was conditional on drone-first cases. Weather, air-traffic approval, delivery zones and darkness constrained eligibility. These denominators and exclusions matter more than a headline suggesting general coverage. No result qualifies this owner's aircraft or proves a causal survival benefit. The institutional news summary's darkness/denominator wording is looser than the primary abstract; use the primary abstract. [Schierbeck et al., 2023, DOI 10.1016/S2589-7500(23)00161-9](https://pubmed.ncbi.nlm.nih.gov/38000871/).

## 7. Maturity and next decision

| Level | Evidence required | R11 status |
|---|---|---|
| L0 Unknown tuple | Owned hardware, OS/firmware, operator, region, entitlement, service and rights identified with permission | UNKNOWN; no inventory performed |
| L1 Documentary candidate | Primary evidence, exact limits, interfaces and falsifiable cases | This report; independent review pending |
| L2 Synthetic utility | Finite inert replay, positive baseline, current authority and honest receipts | NOT_EXECUTED; P11-01/02 proposed |
| L3 Native/bench qualification | Exact adapter and devices, guest isolation, offline restart, timing/power and output measurements | NOT_EXECUTED; P11-03 requires separate authorization |
| L4 Consented exercise | Trained participants, approved non-emergency setting, independent observations and accessible alternatives | Separately gated study; NOT_EXECUTED |
| L5 Operational professional use | Applicable operators/services/legal/professional acceptance plus maintained readiness | Unqualified; no promotion from a mock or literature example |

The highest-value next action is independent contract/evidence review of P11-01, then a separate decision whether to authorize its inert fixture implementation. It should make a public offline card and an honest synthetic incident ledger useful before any radio, health feed, native capture, model or flight. Later ambition remains a coordinated phone/ground-support/relay system with qualified mapping, accessible human communication and optional aircraft, measured against these simpler baselines.

## Actual work, acceptance and open risks

Actual: read pinned governance, recovered requirements/AT/EX and accepted peer contracts/reviews; public primary-source retrieval; directly inspected one campaign-generated static PNG; wrote research documents; performed document/JSON/hash checks. Not actual: model/SDK/application/test execution, audio listening, video interpretation, clinical evaluation, device/account access, messages, networking experiments, radio, purchases, physical measurements or rescue.

Independent reviewer should examine: (G11-1) source/price/region and license distinctions; (G11-2) transport-profile boundary and no offline private exception; (G11-3) current source/location/standing-policy semantics; (G11-4) finite experiment denominators and useful positive cases; (G11-5) exact native/physical/cost prerequisites. Source access limitations are retained in SOURCES.md. Existing acceptance belongs to the pinned upstream composites, not to R11. Hash verification proves bytes, not behavior.
