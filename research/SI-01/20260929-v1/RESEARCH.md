# Spatial intelligence as a bridge to human–AI symbiosis

SI-01 / 2026-09-29 / PROPOSED_NOT_INDEPENDENTLY_REVIEWED. Sources and inspection limits: SOURCES.json. This is a research synthesis, not a report of Haven experiments.

## 1. What the website contributes

Spatialintelligence.ai is Bilawal Sidhu's Map the World publication. Its useful common thread is moving from disconnected media and sensors to manipulable representations of places and events: reconstruction, shared coordinates, temporal replay, semantic perception, generative world building and interfaces that let people act on these representations [W1–W8]. It is a creator/research discovery source, not a single installable spatial-intelligence engine.

The strongest takeaway is not the dramatic globe or a particular model. It is shared reference: humans, software and devices can talk about the same object, region and event rather than exchanging ungrounded chat descriptions. For Haven, the opportunity is to join that shared reference with personal memory, intentional communication, engineering and task continuity. This is a synthesis recommendation, not a claim made or validated by any one source.

Read the creator material with three separations in mind. A demonstration is not a general benchmark. An available public repository is not proof every feature shown elsewhere is included or equally licensed. An appealing visual representation is not a current calibrated measurement. The newest article itself distinguishes open God's Eye View from other WorldFX/hosted work and acknowledges reconstruction errors [W1].

## 2. Shared spatial coordinates and cooperative perception

Visual positioning localizes an image against an existing map; visual-inertial odometry/SLAM tracks motion and may build or update a local map. These are related but not interchangeable tasks. Persistence adds relocalization, map versioning and change handling. Apple's ARWorldMap mechanism illustrates that shared anchors are possible without first modeling the planet [P1]. Google's Geospatial APIs illustrate a different, outdoor map-backed route with explicit pose uncertainty [P2].

The April 2026 see-through-walls example is particularly relevant, but its actual mechanism matters. The sample README describes pre-scanning/uploading a shared map, localizing participating phones, exchanging each device's own pose, and rendering an avatar through known occluding geometry. Its glasses mode delegates work to a paired iPhone. This is cooperative location sharing, not a camera measuring an unknown person through concrete [G1].

For Haven this could become a deliberately shared location or object reference, a remote annotation attached to equipment, or guidance toward a selected resource. A non-display camera wearable should not be assumed to show a world-locked overlay to its wearer. Output capability is a separate device question. The sample's pose-send cadence is also not localization accuracy or proof of a new independent measurement each frame.

Integration needs explicit coordinate conversion: the sample uses Unity's left-handed convention, while Haven's R07/SpatialSemantics profile has a different named transform convention [G1,H3]. Store map identity, frame/handedness, origin, unit, transform revision and time/quality, not just x/y/z. A display name and local-network discovery are not adequate identity or consent. The proposed shared experience should visibly distinguish current located, stale last-known, ambiguous association and unlocalized states.

A crucial human distinction follows: shared coordinates do not require shared private memory. Two users can agree which object is being discussed while seeing different source cards and notes. This is co-presence without compulsory disclosure.

## 3. Reconstruction: appearance, geometry, semantics and dynamics

Classical structure-from-motion estimates camera geometry from overlapping images; multi-view stereo can add dense geometry. COLMAP's guidance makes the capture assumptions explicit: texture, sufficient overlap, different viewpoints and manageable lighting/reflection conditions matter [P3]. A room is not solved merely because many photos exist.

Learned geometry models such as VGGT and pi3 offer useful pretrained proposals for camera/depth/point structure [P4,P5]. MegaDepth-X addresses sparse and difficult internet-photo collections, but its own pipeline includes geometry supervision and manual verification/filtering. This supports a promising estimator route, not a guarantee of accurate reconstruction anywhere from arbitrary photos [P6]. Haven should adopt a model as a replaceable estimator with known inputs and applicability, not as the authoritative world database.

Gaussian splatting is especially valuable for novel-view appearance and explorable visual memory [P7]. It is not by itself a semantic object catalog, metric survey, collision map or dynamics model. Keep an appearance representation, a geometry/support representation and a semantic object/event graph distinct but cross-linked. A photorealistic unseen surface may be a learned completion. A low-detail measured plane may be better evidence for a clearance question.

Segmentation supplies another useful layer. Meta's current SAM page documents SAM 3.1, updated March 27, 2026; the reported real-time improvement is evaluated on an H100, not a promise about any consumer device [P8]. SAM 3D has separate object/scene and body reconstruction models [P9]. Masks and inferred shapes can make a selected object inspectable, but do not establish exact dimensions, mass, material, stable identity through every occlusion, ownership or safe manipulation. Those require other evidence.

Dynamic reconstruction adds temporal association, deformation and changing visibility. Shape of Motion is one research route [P10]. The creator's IronSight work illustrates a replay concept assembled from source imagery and reconstruction [W3]. Haven's civilian transfer is an inspectable repair, workbench or environmental event: select an instant, compare source views, see what changed and preserve what was not observed. Start with sparse event records and camera poses before attempting a complete continuously reconstructed dynamic environment.

## 4. The bridge to engineering: inverse graphics

Inverse graphics asks which scene structure, materials, lighting and camera conditions could explain observed images. The September article describes an agent-assisted workflow converting a photogrammetry mesh into an editable Blender scene, retaining source-derived textures and reporting inherited errors [W1]. It is an encouraging creator result, not proof that inverse graphics is universally solved.

This is a direct bridge to Haven's engineering branch. A scan becomes a candidate model; an agent identifies editable parts; a person proposes a modification; an appropriate geometry/physics or bench test checks it; measured outcomes update the design record. The useful loop is observe → explain → edit → test → measure → revise. Preserve the raw observation and the inferred modeling decisions throughout.

An edited scene is not automatically fabrication-ready CAD. A visual match does not establish tolerances, load paths, material properties or collision correctness. A household arrangement can be rehearsed visually while a fixture requires separately measured dimensions and a task-specific checker. Blender-style scene editing and parametric engineering tools serve different jobs. They can share object identity and provenance without pretending to have interchangeable outputs.

## 5. Four different things called a world model

A durable architecture should separate these meanings rather than choose one brand as its entire brain.

| Meaning | Role in Haven | Evidence and limit |
|---|---|---|
| Persistent evidence/belief state | Objects, relations, events, task context and uncertainty over time | Existing R07/CORE direction [H2,H3]; not inherently one neural network |
| Learned predictive model | Predict likely motion or outcomes; rank candidate observations/actions | V-JEPA 2-AC reports a particular learned robotic planning setting [P11], not universal robot competence |
| Generative world model | Create explorable scenarios, imagery or alternate arrangements | Genie, Marble and Cosmos families are possible external components [P12–P15]; output is generated, not new observation |
| Explicit simulation | Evaluate declared geometry/dynamics and controlled interventions | Trust is limited by the model, parameters, numerical method and task validation; a physics engine is not reality either |

Genie 3's current page still describes limitations involving action spaces, interactions and duration [P12]. Marble's documentation distinguishes visual splats, meshes and coarse collider assets; its World API is available as a service [P13,P14]. NVIDIA describes world-action models and embodiment/task-specific post-training, rather than a generic drop-in household controller [P15]. These are worthwhile candidates for isolated rehearsal or synthetic-data work, not reasons to replace Haven's evidence store.

Recommendation: the observed-world branch and every hypothetical branch should carry different identities. A generated chair, predicted person or synthetic obstacle cannot be imported as a verified current fact. Predicted consequences can inform an explicitly authorized next measurement; only the measurement can update the corresponding observational claim. Accept model uncertainty and simulation mismatch rather than averaging them into one confidence number.

This allows ambitious imagination without contaminating memory. It also permits creativity for its own sake: proposed environments and stories need not pretend to be measurements to be useful.

## 6. RF and beyond-sight sensing

There are at least three different beyond-sight mechanisms: remembering a previously observed location, receiving an observation/pose from another authorized sensor, and inferring hidden structure or motion from penetrating/diffracting signals. Treating them as one capability is misleading.

DensePose from WiFi describes learning pose-related representations from channel-state information in its experimental setting [P16]. IEEE 802.11bf-2025 was approved May 28 and published September 26, 2025, adding WLAN sensing specifications [P17]. A standard's existence does not establish that an arbitrary router, phone API or installed firmware exposes the required sensing data.

For Haven, RF should first contribute bounded evidence: presence/motion likelihood, an uncertainty region, or an observation that another sensor can resolve. Do not attach a person's identity or a medical conclusion to that signal by default. Hidden geometry remains a distinct inverse problem; alternative scenes can explain limited measurements. Use multi-view coverage, calibration, held-out environments and independent reference measurements when testing more ambitious claims.

A visual prior may help reconstruct an RF scene, but its contribution must remain visible. A plausible body or wall supplied by a model is not directly measured simply because RF triggered it. Likewise a simulated thermal shader is not a thermal camera. The existing R06/R07 path retains geometry and semantic reconstruction as serious research goals without equating a heatmap with completion [H1,H3].

## 7. What makes this a human–AI system

Spatial intelligence is the bridge between what a person means, what the system observes and what an agent can usefully do. The fuller architecture needs at least two feedback loops: environmental learning from observations/outcomes, and interface learning from deliberate user correction and preferences. It must not use convenience as a reason to infer unlimited permission.

Consider a proposed shared-attention interaction: a user deliberately selects an object, sends a short private cue to their partner, and the recipient resolves the same object reference on their own interface. This can progress from a button plus text/earpiece, to supported gesture input, to a spatially anchored private cue. It does not require arbitrary thought decoding. It does require intentional initiation, a confirmed recipient, understandable delivery state and a quick way to decline or stop.

The non-invasive neuromotor literature makes the input direction concrete. A 2025 Nature study describes wrist sEMG models for gestures, continuous control and handwriting; its reported handwriting median is 20.9 words/minute under its study conditions [P18]. This is electrical muscle-signal input, not unspoken-thought transcription. A paper, published data and hardware demonstration do not guarantee unrestricted consumer hardware/API access or license compatibility.

The output direction is equally important. A 2023 feelSpace study reports improved spatial knowledge after training with directional tactile feedback in a particular VR evaluation, with a final sample of 53 participants [P19]. It supports taking sensory augmentation seriously, not claiming every haptic cue becomes a natural sense or a reliable navigation aid. Stable mappings, learning burden, missed cues, false cues, distraction and individual variability should be measured.

The practical target is additional understandable abilities: sense the bearing of a deliberately selected resource; recall why an object or decision matters; receive a quiet intentional message; inspect a remote scene; rehearse a design; ask for a missing measurement; delegate bounded work. A biological merger is not required for meaningful functional symbiosis. Nor does this report establish one.

## 8. Memory is not just a longer context window

A useful personal world memory needs durable entity/event identity, versioned evidence and time-specific retrieval. It should answer which observation supports an answer, whether it still applies and how a correction changed it. It must also avoid treating an unobserved interval as continuous knowledge.

S-EMBER, a July 2026 primary research report, evaluates streaming egocentric recall with temporally located supporting evidence and identifies temporal grounding as a bottleneck not fixed simply by increasing model scale [P20]. This is particularly relevant to Haven: more frames and a larger model are not a substitute for correct event indexing and source localization.

Recommendation: query small currently eligible evidence neighborhoods by object, task, time and place before escalating to expensive models. Maintain world time and knowledge time separately. Compress materialization for efficient retrieval, but preserve the source links and invalidation path. Human personal memory and project-agent continuity need related provenance discipline, but should not share a public storage boundary.

## 9. Proposed architecture: one meaning layer, multiple representations

The proposed conceptual loop is:

intent + authorized observations → source-linked entities/events/claims → current eligible context → deterministic tools or selected model → evidence answer / hypothetical branch / action proposal → authorized execution and observed outcome → revision.

This is an extension of existing I01–I07, not an eighth universal service or a new framework [H2]. Use source/evidence and context interfaces for spatial references, the authority/output interfaces for private cues, bounded jobs for estimators, and domain proposals/outcomes for actions. A renderer consumes allowed projections; it does not own truth or grant motion.

Support body, object/workbench, room, site and regional scales with explicit transformations and levels of detail. Do not require Earth alignment for a local object question. Do not mix incompatible scales or temporal precision because they can be drawn on the same globe. A private home map need not be sent to an external world-generation API.

Operationally, keep the ordinary daily assistant available while richer modules are absent. A selected-image question can succeed when 3D fails. A direction cue can be withheld without breaking text messaging. Ordinary help must not depend on a drone or generative world service.

## 10. Feasibility, costs and adoption discipline

Nearer integrations are source-linked object annotations, selected-view recognition, evidence replay, private shared references and editable local plans. Controlled AR relocalization, robust cross-session object identity, reconstruction, richer model inference and haptic interfaces require more integration and measurement. Arbitrary covert semantic perception through walls, reliable general manipulation, and free-form silent thought transmission are not established by these sources.

Do not train a frontier world model for the first Haven implementation. Reuse a pretrained estimator or hosted generator only for a narrowly defined comparison, with exact artifact, rights, resource and privacy records. Existing source availability is not equal to usable weights, permitted assets, accessible device APIs or deployment rights.

Budget for capture effort, calibration, cleanup, storage, GPU memory, inference, battery, latency, API usage, retention and ongoing revalidation—not only a model's download size. The original Gaussian-splatting optimizer documents 24 GB VRAM for paper-quality training, while explicitly discussing smaller configurations [G3]. This is not a requirement for all splat viewers or all methods. Distinguish acquisition, reconstruction/training, inference and rendering when sizing a host.

God's Eye View can be a later presentation component, but its README separates simulated traffic and estimated camera geometry from live/refreshed sources [G2]. Keyless operation can still request network services. Adopt a pinned component and its licenses, not a slogan or every current upstream feature. R15's accepted pin remains its own reviewed source; inspecting today's README here does not update that pin.

## 11. What would genuinely move the project forward

After the currently scoped IP-01 work, propose a Shared Spatial Memory / Workbench slice: a small known scene, stable object references, selected images, one useful question, two private/shared views, corrections and time-indexed evidence. Compare it to an ordinary photo gallery and notes. Add measured reconstruction or cooperative AR only when each improves the task, then add deliberate private cues and a separately labeled scenario fork.

The scientific question is not whether a demo looks futuristic. It is whether an additional representation or interface helps a person make a more correct decision with less effort, while preserving current authority and exposing uncertainty. This question retains the ambitious end state and gives it a cumulative, testable path.
