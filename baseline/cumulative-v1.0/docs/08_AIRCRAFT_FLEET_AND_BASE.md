# Aircraft, multiple vehicles and the base

The original aircraft vision remains intact: consumer equipment where practical, coordinated multiple aircraft, evidence gathering, preauthorized bounded observation in mature scenarios, and eventual readiness/docking. It is one physical branch of Haven, not the whole product and not discarded by the newer engineering ideas.

## Keep the approved Generation-0 baseline

M0 is being implemented elsewhere. M1–M5 add the specified isolated simulator, evidence/approval, bounded simulated execution, advisory model and fault qualification. M6 adds the manual Watch entry. The exact pins and namespace restrictions are in `baseline/PROJECT_ASTRA_Generation_0_Implementation_Validation_Plan.md`. This chapter does not authorize installing or substituting any component.

The simulator validates application behavior, not DJI/EC120 SDK behavior. Real telemetry and camera acceptance comes later. Simulation success never changes a real aircraft's qualification flag.

## Budget-conscious physical entry

| Candidate path retained | Role to investigate | Purchase/integration gate |
|---|---|---|
| Existing EC120/controller | Potential manual evidence source or documented interface | Four-hour official-documentation dossier; current programmability unverified |
| Mini 3 + compatible controller/Android bridge | Lower-cost outdoor camera/SDK candidate from earlier research | Recheck exact model/controller/OS/SDK/firmware, video, takeover, support and complete kit cost |
| Mini 4 Pro candidate | Earlier reference with broader features | Not default purchase merely because architecture named it |
| Tested Tello / Tello EDU | Low-cost indoor communications/video experiment | Exact variant/SDK, batteries, available app and useful video/control validated; not outdoor emergency platform |
| CoDrone EDU | Educational controls/sensors branch | Verify exact model's camera capability; do not assume EDU Plus features in standard EDU |
| Crazyflie | Open indoor sensing/control laboratory | Complete radio/positioning/payload cost; not an equivalent stabilized outdoor camera kit |
| Supported PX4/ArduPilot assembled airframe | Payload/control flexibility when justified | Complete integration/maintenance/manual recovery qualification, not just kit price |

The historical dollar figures live in archived research only. There is no refreshed live quote or purchase authorization in this bundle. A required Android bridge, charger, batteries, spare parts, compliant radio setup and maintenance can change the total more than the advertised aircraft price.

## Capability contract

For each aircraft record exact identity, firmware/controller/OS/SDK, permitted interfaces, observed telemetry, capture timestamps, supported command semantics, home/navigation health, containment, recovery/manual takeover, payload limits and evidence for every qualified feature. Use supported/unsupported/unknown, not a Boolean inferred from marketing.

Investigate whether a mission is uploaded onboard or depends on continuous external commands. Document what happens if the app, bridge, radio, internet and autopilot fail independently. A healthy radio does not guarantee a live command bridge. No one generic return-home promise covers every platform and fault.

## Flight authority and state

Natural language proposes a purpose/template. A deterministic planner selects a reviewed template and binds route, bounds, aircraft/run/configuration, evidence basis and recovery behavior. Explicit approval or a separately qualified standing policy authorizes one execution. The adapter receives no arbitrary address, raw motor command or LLM-generated firmware setting.

Maintain requested, acknowledged, observed and unknown states. Preserve durable intent before side effects. Lost acknowledgement requires reconciliation; it never automatically issues another takeoff. Authenticated recovery is a controlled request, not an unconditional midair motor stop.

Manual pilot takeover and independent configured failsafes must be tested on the chosen configuration. Do not equate a props-off API test with an airborne recovery test. Physical deployment requires its own site, permissions, weather, airspace and competent operational review [R32, R35]. This does not narrow simulated concurrent or incapacitation goals.

## Concurrent aircraft

Start sequentially, then validate two simultaneous simulated aircraft with distinct identities, routes and recovery areas. Reservations include time, spatial corridor and landing capacity. An aircraft with unknown location retains a conservative exclusion/reservation until reconciled; do not free its space because telemetry disappeared.

Battery handoff needs a verified replacement observation and safe staggered recovery, not “send another” on an unreviewed route. A fleet scheduler owns resource allocation; one LLM per aircraft is not required. Distinct processes/credentials may still be appropriate for fault containment. Test wrong-target commands, duplicate reservations, occupied pads, competing returns and one link failing while another stays healthy.

## Base and readiness

Begin with a supervised launch/recovery area and manual batteries. Treat battery condition, charger, firmware status, inspection and maintenance as system resources. An aircraft that exists but fails readiness is unavailable.

An eventual base may include protected storage, local networking, weather/occupancy sensing, measured UPS endurance, charging/dock status and a controller gateway. DIY enclosure success is not autonomous docking qualification. Confirm repeated approach/landing, charging, thermal/environment behavior, pad occupancy, failed recovery and manual retrieval before any standing launch policy.

## Radios and payloads

Keep control/telemetry/video links separate conceptually from the home network and public emergency internet. Dedicated mesh or relay aircraft require a demonstrated coverage need and complete energy/radio budget. Initial RF reconstruction should not depend on a flying scanner when a safe fixture can test the method.

Lighting, speaker, thermal or sampling payloads enter only after their standalone bench tests and configuration-specific aircraft review. R31 is an example of an established spotlight/speaker category, not an accessory recipe for an unsupported drone. Preserve the option to keep a consumer drone as a manual camera while a different platform handles specialized research.
