# Sensor strategy: solve a question, then choose the instrument

**Proposed research catalog, not a universal payload.** Each module needs a physical question, a ground alternative, a calibration method, an evidence schema and a measurable acceptance test. Avoid buying a collection of sensors and asking the model to invent significance afterward.

## Sensor decision matrix

| Class | Proposed question | Preferred initial placement | Main qualification issues |
|---|---|---|---|
| RGB / low-light camera | What is visible; has an object changed? | Phone or fixed authorized view | Lighting, blur, timestamp, field of view, privacy, uncertain interpretation |
| Thermal imaging | Is there an apparent surface-temperature anomaly? | Handheld/ground qualified module | Emissivity/reflections, calibration, useful range, weather; not through-wall vision |
| Depth / ToF / LiDAR | What nearby geometry can be directly measured? | Supported phone or rover | Reflective/transparent surfaces, occlusion, frame calibration, outdoor conditions |
| Optical flow / IMU | Has a sensor or carrier moved? | Rigidly mounted with known orientation | Drift, vibration, clock alignment; not absolute location without additional reference |
| GNSS / RTK | Where is an outdoor platform relative to a datum? | Qualified outdoor platform | Coverage, multipath, loss, reference validity; no assumed indoor solution |
| Barometer | What relative pressure/elevation change is measured? | Protected fixed or carrier mount | Environmental variation, propwash, temperature and datum |
| Acoustic/microphone array | Is there an audible event and a useful direction estimate? | Fixed/handheld first | Wind, motor noise, reverberation, consent, no reliable identity from a sound label |
| Temperature / humidity / pressure | What is the local environmental context? | Ventilated fixed node | Placement, stabilization, bias from heat/electronics or enclosure |
| Particulate / CO2 / VOC research | Are contextual concentrations changing under a defined sampling method? | Fixed ground sampler | Flow, calibration, cross-sensitivity, sensor age; not certified fire/CO alarm replacement |
| CO / smoke safety | Has an independent certified alarm activated? | Existing approved alarm installation | Documented integration and independent alarm operation; no hobby replacement |
| RF CSI / RSSI / UWB / radar | Is there detectable change, range or obscured structure? | Authorized fixed/fixture arrangement | Access, synchronization, calibration, regulations, observability and privacy |
| Radiation measurement research | Does a permitted instrument report a validated count/measurement? | Qualified instrument, ground only initially | Specialist scope, units, calibration, legal handling; no sources or hazardous experiments |
| Lighting / speaker | Can information or useful illumination reach a location? | Stand or rover first | Power/heat, glare/noise, intelligibility, approved attachment and output limits |

These categories identify questions to test, not guaranteed capabilities. Select exact modules from current datasheets before implementation. Preserve the difference between a consumer alert, a calibrated measurement and an LLM interpretation.

## Mounting is part of the measurement

Record mounting position/orientation, material, apertures, heat sources and calibration. A printed enclosure can alter airflow, optical visibility, RF propagation and temperature. It may improve repeatability while degrading signal quality. Compare bare and enclosed configurations. Use a versioned fixture ID in each dataset, not simply “sensor v1.”

Airborne integration adds mass, power, center-of-gravity, vibration, aerodynamic and interference questions. Do not assume nominal aircraft payload support. A rotor's local airflow and sound can undermine environmental/acoustic experiments; characterize the actual configuration rather than extrapolate a bench result. Prefer fixed sensors for measurements that do not benefit enough from mobility.

## Evidence packet

Every sample or chunk carries measurement type, subject/region, units, original capture interval, arrival time, sensor/firmware/calibration, location/frame if known, quality and stale/unknown flags. A model receives a derived, scoped package rather than every raw stream. Raw data retention is purpose-limited; a privacy decision may prevent collection even if storage is cheap.

Maintain separate evidence classes: observed fact, measurement, external data, user statement, model inference and assumption. Simulated/prerecorded/manual/live origins are another axis. Multiple model descriptions of the same frame are not multiple independent observations.

## Multimodal fusion

Only combine streams when timing and spatial relationships are sufficiently known for the intended claim. Record estimated clock offset/uncertainty and transform validity. Preserve conflicting readings; do not average away a faulty sensor into reassuring certainty. A view of an empty doorway does not establish an empty room.

A fusion model should beat a stated best-single-sensor baseline on a held-out test, or provide another justified benefit such as lower energy/less privacy exposure. More sensors are not automatically better. Track correlation: two derived summaries from one camera do not corroborate one another.

## Active measurement actions

Possible actions include requesting another frame, changing a permitted camera angle, varying a controlled light, moving a handheld rig to a marked position, repositioning a qualified rover, or eventually proposing a bounded aircraft observation. Each proposal states what ambiguity it hopes to resolve and why the action is worth its cost/risk.

Start with prerecorded alternatives and a human-moved fixture. The policy gate chooses whether a physical action is eligible. The action result is a new observation, not proof that the earlier hypothesis was correct. A failed or uninformative measurement is retained as useful negative evidence.

## First practical experiment families

Presence/localization repeatability; current-versus-old frame labeling; light-angle comparison; acoustic source direction in a quiet authorized room; fixed environmental placement comparison; depth-versus-tape geometry check; enclosure effect on measurement quality. Do not introduce smoke/gas, hazardous radiation sources, deliberate medical incidents, radio jamming or live aircraft faults merely to make tests look realistic.
