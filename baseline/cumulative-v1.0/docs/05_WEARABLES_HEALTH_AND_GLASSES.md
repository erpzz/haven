# Wearables: two people, phone-first bridges and truthful availability

The goal includes Eric's and Kennedy's phones, Apple Watches and smart glasses. Their exact models, OS versions, pairing arrangements and grants are not yet inventoried. This chapter is a design/qualification plan, not evidence of accessible live vitals or a chosen glasses purchase.

## Architecture

Each person enrolls their own devices and authorizes specific data. A future native Apple app obtains permitted HealthKit information, normalizes it and transmits only eligible observations to that person's Haven scope. The current Safari M0 page does not acquire a native HealthKit role. A manual Watch Shortcut remains the later M6 experiment; health-data work is separate.

The app records device/source, measurement time range, arrival time, units, quality/availability, subject and grant revision. A missing measurement is unknown, not zero, normal health or proof of incapacitation. Earlier design requirements about HealthKit read-denial ambiguity remain mandatory; R39 identifies the official authorization reference, whose full text needs rereading during native implementation rather than claiming fresh verification from a JavaScript-only landing page.

## Qualification matrix to complete per person

| Capability | Questions before integrating | First test |
|---|---|---|
| Heart rate / resting rate | Exact quantity, device/source, sample cadence and permitted history | Synthetic late/out-of-order samples, then a consented narrow export |
| HRV / respiration / sleep | Units, interval semantics, source algorithms, gaps | Preserve interval/source; do not reinterpret as diagnosis or emotion |
| Temperature-related data | Is it baseline-relative or absolute, under which conditions? | Render available measurement semantics without inventing core temperature |
| Oxygen-related samples | Exact SKU, region, OS and accessible record type | Availability matrix; absence does not trigger a fabricated abnormality |
| ECG records | Supported recorded data and read permissions | Distinguish an existing recording from live continuous ECG |
| Fall/native alerts | API/entitlement and dispatch behavior | Synthetic event first; never assume native notification is a third-party callback |
| Location | Permission, freshness, indoor uncertainty, privacy | Old location stays old; no exact room claim from coarse data |
| Watch request UI | Network route, acknowledgement, expiry and role | Existing M6 receipt tests; no approval authority from request credential |

Do not invent blood pressure/glucose support. Do not start sham workouts to force sampling. Historical samples, opportunistic delivery, on-demand reads and legitimate workouts are different operational modes. Native emergency systems remain independent.

## Smart glasses capability matrix

Treat audio output, microphone capture, camera photos, streamed frames, display overlays, motion, touch/buttons, invocation and background lifecycle as separate capabilities. R29 documents a real preview toolkit and experimental feature boundaries; it does not select a device or guarantee all features on a model.

The first useful experience is wearer-triggered scene explanation or private audio reminders using a photo/short clip. A display-equipped pair may later show map uncertainty or directions, but audio-only glasses remain useful. The acquisition path identifies the wearer, capture indicator, original timestamp, image orientation and permitted sharing. Frame processing must not silently capture private workplace screens or bystanders for indefinite retention.

If the intended interface is unavailable, fall back to an explicit photo transfer, audio-only experience or phone display. Do not label a mock device test as actual glasses qualification. Do not bypass recording indicators or turn an undocumented route into a safety dependency.

## Shared household boundaries

Kennedy can use Haven privately even when she chooses no sharing with Eric. Allow an intentionally shared task or incident with a defined recipient audience. A spoken question in a room with guests should not trigger an audible private medical summary. Ask for private delivery when the audience is uncertain.

Borrowed/swapped glasses require reenrollment or explicit current-wearer confirmation. Revocation must stop new ingestion and pending publication; clearly explain already retained records and deletion propagation. Streaming sessions must expose recording and connection state and stop when the wearer withdraws permission.

## Nonclinical usefulness

Start with faithful displays and user-requested summaries of permitted measurements, not alerting thresholds invented by a language model. A summary can explain data gaps and link to source intervals. An emergency information packet is a different, reviewed disclosure policy; it is not implied by ordinary partner sharing.

Clinical monitoring, treatment selection and high-stakes health alarms require separate professional/regulatory evaluation. Prototype health tests use synthetic data or deliberately limited consented samples, not both people's entire histories. The system should help communication without making assistance wait for interpretation.

## Native-app roadmap

W0 inventories devices/permissions and maps official APIs. W1 uses synthetic health/glasses observations against contracts. W2 qualifies one person's native read-only bridge and explicit capture. W3 adds independent second-person enrollment, private/shared delivery and revocation tests. W4 evaluates convenient voice/display interactions and interruption. Each stage needs its own approval; none is hidden inside M0 or the existing manual Watch task.
