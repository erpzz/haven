# Resilient communications and an emergency gateway

**User target:** make local coordination and, when a backhaul exists, internet access available in remote or disrupted areas. Preserve both portable ground equipment and possible drone/robot relay roles. An open-access assistance interface must not become an open control plane.

## Three services, three honest promises

**Offline local assistance:** an accessible local portal with stored maps/information, availability status, opt-in check-ins and short messages. It explicitly says there is no internet when upstream connectivity is absent. Stored guidance has a version/date and may be stale.

**Low-bandwidth relay:** short status/location messages across compatible ground radio nodes, with expiry, deduplication and delivery state. Meshtastic is a candidate to evaluate [R20], not a guarantee of range or a broadband replacement.

**Internet gateway:** a working ground upstream connection—cellular, satellite or other authorized network—feeds a guest access network. No drone or mesh creates internet merely by being aloft. Provider terms, region, power, sky/terrain and actual link performance must be verified for chosen equipment.

## Network separation

Create distinct conceptual zones for operator/control, private household data, sensing/robots, management and public guests. Public guests get a narrow local portal and, when explicitly enabled, rate-limited upstream access. They never receive drone/printer/admin API access, raw health records or household shared secrets. A control packet must not share a generic forwarding service with arbitrary public traffic.

Guests should not need a personal Haven account just to view non-sensitive emergency information. Do not impersonate public emergency networks or imply affiliation/guaranteed assistance. Captive portal behavior and offline certificate trust must be tested on real phones; do not make fake-browser security instructions a prerequisite to obtaining basic public information.

A public help-request form needs rate limits, spam/abuse controls, minimal data collection and human triage. It is a local communication service, not a dispatch console. Separate acknowledged-by-Haven from acknowledged-by-a-human/authorized provider.

## Delivery semantics

Record CREATED, STORED_LOCALLY, ASSIGNED_TO_RELAY, TRANSFERRED, DESTINATION_ACCEPTED, RECIPIENT_ACKNOWLEDGED, EXPIRED, CANCELLED and UNKNOWN when appropriate. These are message states, not responder-dispatch states. Encrypt sensitive payloads end-to-end where the selected protocol supports the intended threat model; link encryption alone is not enough to claim that relay operators cannot read content.

Persist an outbox for explicitly authorized emergency messages with a known recipient and expiry. Do not confuse this legitimate store-and-forward workflow with forbidden automatic replay of flight launches. Restored old messages must respect cancellation, expiry and privacy revocation before delivery. Deduplicate at receiving endpoints where possible.

## Mobile relay and data ferry

A later approved rover or aircraft may move a communications node to a useful permitted position, or carry stored messages between disconnected links. The first experiment is a software/bench contact schedule, not an uncontrolled long-range flight. Use R21 as a protocol precedent; do not impose a full standards stack before requirements justify it.

Plan contact windows, message size/priority, energy reserve, return/retrieval, transfer confirmations and loss behavior. A second carrier does not imply the first disappeared or that delivery occurred. The robot's movement is a separately authorized mission with its own safe operating area.

## Technology comparison framework

Evaluate existing WiFi/Ethernet for local application/video; vendor radio for supported aircraft control; BLE/Thread-like paths for small local peripherals where documented; LoRa-like links for small delayed messages; point-to-point/mesh for demonstrated relay needs; and cellular/satellite for actual backhaul. For each, record payload/overhead, latency, useful throughput, terrain, power, coexistence, encryption/authentication, licensing and offline startup. Marketing range is not a tested path.

Start with a portable ground case, suitable approved power components and documented networking. A printed carrier can hold equipment but does not confer waterproofing, thermal adequacy or RF performance. Do not power high-load communications from an unqualified printed battery assembly.

## Acceptance and graceful degradation

Demonstrate no-backhaul labeling, local portal access, ordinary message retention, expired message rejection, duplicate transfer handling, privacy-safe guest isolation, actual recipient acknowledgement, low-power modes and recovery after restart. Measure throughput/latency and battery draw under the intended loads. Keep a visible minimal status even when AI is off.

No account, cellular/satellite subscription, provider contact or public network is activated through this design. Guest internet and real external delivery need explicit operational/security approvals. Independent native emergency calling should remain usable when available and should never wait for Haven's network experiment.
