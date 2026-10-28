# R14 — Human Augmentation, Cybernetics, New Senses & Emerging Human–Machine Interfaces

**Revision:** 1.0 · **Prepared:** 2026-09-28 · **Status:** Research prompt ready for a future assignment; research not started by publishing this file.

**Purpose:** Explore technologies that once sounded like science fiction and identify credible, affordable ways Haven could extend human perception, communication, memory, dexterity and independence. Preserve ambitious goals while separating demonstrated mechanisms, accessible components, research hypotheses and speculative outcomes.

---

## 1. Your role and the question to answer

Act as a cross-disciplinary research team covering neurotechnology, human–computer interaction, wearable robotics, assistive technology, signal processing, sensor fusion, embedded systems, human factors and experimental engineering.

The central question is:

> What useful new abilities could two ordinary people gain by combining a personalized AI assistant with wearable, handheld, environmental and robotic technologies—and which parts could we responsibly prototype with existing computers, off-the-shelf components and custom fabrication?

This is not merely a shopping survey of smartwatches or an essay about implanted brain chips. Explore the space between those extremes: subtle muscle interfaces, deliberate silent communication, artificial senses, embodied telepresence, haptic feedback, spatial memory, extra effectors, smart textiles and other promising combinations we have not anticipated.

Be imaginative before narrowing. Do not reject an idea merely because it is unfamiliar, commercially immature or an open research problem. Identify the missing evidence, propose a falsifiable intermediate experiment, and make uncertainty explicit. Equally, do not call a plausible story a demonstrated capability or claim novelty without checking prior art.

**Design and research only.** Do not implement, install, purchase, recruit participants, collect personal signals, operate devices or start additional agents.

## 2. Haven is cumulative: preserve the whole project

Haven is an everyday assistant for two independently consenting adults. Its retained scope includes conversation, planning, reminders, projects, authorized personal tools, private and deliberately shared memories, phones, Apple Watches, smart glasses and cost-aware local/hosted inference.

PROJECT ASTRA supplies protective observation and physical-world capabilities: drones, ground robots, sensors, emergency assistance and resilient communications. Other retained branches include RF/Wi-Fi presence and localization as bridges toward geometry and semantic spatial understanding; multimodal world models and active perception; parametric CAD, 3D printing, and bounded design–experiment–improve campaigns.

This assignment adds **human augmentation**. It does not replace the daily assistant with a BCI project, turn the whole system into a medical device, or cancel other branches. External sensors and robots may extend a person's effective perception without changing their body. Implants are not a prerequisite for meaningful cybernetic capability.

The household values practical independence, learning, creative engineering, affordability and reliable support. Do not import sensitive biography, diagnoses, employer information or real health records into this public research packet.

Reuse reported existing computing and Apple devices where useful, but verify actual models and access before claiming compatibility. A printer, neural interface, exoskeleton, qualified drone or new GPU is not assumed purchased. Real signal acquisition, account enrollment and hardware qualification remain separate approvals.

Preserve the active ASTRA M0 application, the separate NIGHT-01 synthetic laboratory, the R1 lifecycle repair and the approved M4 advisory baseline. Do not reopen their implementation or assume their latest status from an old document.

## 3. Source context and integration ownership

Repository: https://github.com/erpzz/haven

At the start, record the actual repository commit and the files you successfully read. Read root `START_HERE.md`, `AGENTS.md`, `CURRENT_STATUS.md`, `PRECEDENCE.md` and `coordination/PROTOCOL.md`.

Then inspect the relevant available material, selectively:

- `baseline/cumulative-v1.0/scope/COVERAGE.md` and `baseline/cumulative-v1.0/agents/HANDOFF_TEMPLATE.md`.
- Baseline design chapters on privacy, wearables/health/glasses, intelligence/cost, wireless spatial research, sensors/active perception, ground robotics, emergency support, engineering/fabrication and scientific method.
- R02 intelligence proposals under `design/H02/R02/v1/` and H00's review at `design/H00/reviews/R02_v1.md`.
- R06 spatial proposals under `design/H08/R06/v1/` and R08 engineering proposals under `design/H09/R08/v1/`; inspect their actual directory structure rather than guessing nested filenames.
- Any subsequently published R03 privacy, R04 wearables, R07 world-model, R09 robotics or R13 validation handbacks that materially affect this assignment.

**Repository-import qualification:** the complete source migration was not verified when this prompt was prepared. A missing document is not permission to invent its contents. Record missing paths, use the self-contained project context above to continue independent public research, and mark affected integration decisions provisional. Do not spend the research task repairing the repository import.

Use R14 as this research-task ID. Proposed coordinating ownership is H12 frontier research, reviewed by H00, with H07 wearables, H04 privacy/authority, H06 validation, H02 intelligence, H08 spatial research, H09 engineering and H10 robotics as appropriate. Do not create a competing H14 authority service or renumber existing owners. Final ownership is an integration decision.

## 4. Explore ten technology areas

For each area, investigate recent primary research, obtainable hardware, real developer access, human usability and the path from demonstration to everyday benefit. Include both assistive uses and optional enhancement for users without a diagnosed impairment. Do not transfer results between those populations without evidence.

### A. Neural, muscle and other biosignal interfaces

Compare scalp EEG, surface EMG, eye-movement/EOG interfaces, camera-based gaze, inertial sensing, mechanomyography and research sonomyography. Include fNIRS, fMRI, MEG and implanted interfaces for scientific comparison, while distinguishing laboratory infrastructure and clinical access from household feasibility.

Consider deliberate discrete inputs, low-effort gestures, text selection, cursor control, accessibility and personalized calibration. Ask whether a button, touch ring, camera gesture or voice command actually performs better for the intended task.

Separate brain activity, muscle activation, eye movement, motion artifact and software inference. Do not label every biosignal product a brain–computer interface. Audit actual channel access, sampling, synchronization, electrical safety provisions, placement sensitivity, training burden, motion contamination and day-to-day drift.

For EEG, distinguish controlled selection paradigms, motor imagery, coarse state estimation and unrestricted language decoding. Investigate open research software and developer platforms, but verify licenses and current API access. An attention score is not established mind reading, diagnosis or reliable emotional truth.

### B. Silent speech and discreet intentional communication

Investigate facial/neck EMG, minimally voiced speech, contact microphones, lip/gesture interfaces, subvocal or articulatory approaches and hybrid methods. Separate open-vocabulary communication from recognition among trained commands. Separate personalized calibration from across-user generalization and prompted offline classification from a live interaction.

Explore a private Haven input/output channel combining an intentional signal with text, open-ear audio or bone-conduction output. Test privacy leakage rather than assuming an output device is inaudible to others.

Ask exactly what the wearer must intentionally do. Language-model autocomplete must not become words attributed to the person without a way to inspect and correct them. Distinguish decoded signal content from model-completed content. No involuntary-thought reading or telepathy claims.

### C. New senses and sensory substitution

Investigate haptic belts, wristbands, skin-stretch devices, tactile displays, spatial audio and visual overlays. Could direction, proximity, temperature differences, sound events, mapped obstacles or network availability be encoded into a learnable feedback vocabulary?

Include a sense-of-direction belt, tactile translation of selected sounds, qualified range information as distance cues, and remote-camera or robot observations as optional feedback. Investigate training, retention and generalization—not merely whether a wearer can notice vibration.

Separate a symbolic alert from an intuitive learned mapping and from evidence of a more deeply incorporated perceptual skill. Measure information bandwidth, false signals, adaptation, habituation, sensory overload and interference with normal vision/hearing/touch.

Explicitly explore translating R06/R07 uncertainty into feedback: how would the wearer feel or see an approximate region, stale observation or unknown area without mistaking it for an object definitely present? A new output channel cannot improve the truth of weak input evidence.

### D. Augmented vision, hearing and spatial cognition

Explore camera/audio/display glasses, eye tracking, thermal and depth accessories, directional microphones, live captions, translation, object finding, workshop overlays and permissioned spatial memory. Distinguish seeing through a sensor from inference about an occluded region.

Research hands-free coaching, revisiting a prior observation, orientation prompts and private incident summaries. Separate camera-only glasses from display-equipped glasses and body-fixed notifications from spatially registered AR.

For emergency or low-visibility ideas, characterize actual sensor and display limits. A thermal image, remembered map or RF estimate must not be sold as proof of a safe route. Initial tests use harmless, controlled environments—not smoke, fire, traffic or dangerous navigation.

### E. Dexterity, additional effectors and wearable robotics

Investigate supernumerary fingers such as Third Thumb research, wearable additional arms, soft grippers, passive assist devices, hand-support gloves, tremor-assistance research, exosuits and powered exoskeletons.

Compare tools worn on the body with tools mounted on a bench or separate rover. Ask whether an extra device genuinely expands capability or merely shifts work to another hand, foot or cognitive channel.

Evaluate range of motion, pinch/entanglement risks, load paths, fit, skin pressure, heat, fatigue, battery failure, emergency removal and effects on balance or ordinary movement. A CAD model or successful render is not evidence of safe body loading.

Choose only detachable, low-risk, non-load-bearing mockups or bench simulations for an initial hobby experiment. Powered body assistance and rehabilitation are separate professional-review tracks, not casual extensions of a 3D-printing project.

### F. Embodied telepresence and remote perception

Explore control through gaze, deliberate gestures, motion capture or EMG; force/tactile feedback; robotic avatars; and receiving a rover or drone's viewpoint through compatible displays.

Examine shared autonomy: the user specifies intent while the robot's qualified controller enforces constraints. Compare it against normal teleoperation and scripted tasks. Investigate ownership confusion, motion sickness, latency, feedback delay and losing awareness of the local environment.

A useful target might be operating a small bench robot while receiving a limited tactile signal. That is not proof of a natural extra limb or permission to transfer the same controller to aircraft. Wearer intent, authentication, action approval and physical execution remain separate.

### G. Cognitive offloading and everyday agency

Explore an external memory aid, project-decision recall, contextual task cues, deliberate focus support, skill-learning assistance and real-time explanations. Prefer concrete outcomes such as less time finding information or fewer missed steps over vague claims of intelligence enhancement.

Consider interfaces that reduce screen dependence and manipulation of a phone. Protect the ability to pause, correct or ignore Haven. Study dependency, distraction and skill retention as well as task speed.

Do not infer a diagnosis, emotion, incapacity or permission from EEG/heart-rate proxies. Compare any adaptive attention feature with a user-chosen schedule or simple setting; the more complex interface must earn its cost and burden.

### H. Health-adjacent sensing and emergency assistance

Survey credible advances in skin patches, smart textiles, physiological sensing, wearable imaging, accessibility communication and clinician-supported remote assessment. Separate consumer wellness, research instrumentation, cleared medical uses, investigational devices and clinical trials.

Preserve the two-person Watch/HealthKit branch rather than assuming arbitrary continuous PC access. Distinguish sample time, delivery time, missing data, quality and intended use. Signals do not automatically become diagnoses or emergency confirmation.

Explore improved communication during a reported problem, hands-free access to instructions from authorized professionals, finding supplies, and consented summaries for a helper. Existing native or professional emergency mechanisms remain independent of optional models and robots.

### I. Smart textiles, materials, fabrication and power

Explore e-textiles, flexible sensors, detachable modular wearables, compliant structures, low-power processing, local inference and repairable housings. Treat energy harvesting and improved batteries as hypotheses requiring a whole-system budget, not permission to omit charging.

For printed wearables, assess contact materials, cleaning, sweat, adhesives, pressure, snagging, breakaway design, ventilation, wiring and charging. Identify what can reasonably be printed, purchased, outsourced or only developed in a specialist laboratory.

Use the engineering agent to propose fixtures, measurement plans and bounded design revisions. It cannot certify skin compatibility, body loading, medical performance or its own design. Preserve CAD source, units, revisions, bill of materials and inspection evidence.

### J. The frontier we have not thought to ask about

Actively seek overlooked developments: ultrasound-based input, electronic skin, tactile remote sensing, artificial vestibular cues, soft robotics, biohybrid research, wearable environmental awareness, novel assistive interfaces and distributed perception.

Discuss implanted neural interfaces, sensory prostheses, regenerative technologies and other invasive approaches at a scientific/clinical-roadmap level when relevant. Explain the capability gap and legitimate research path. Do not turn the review into DIY implantation, stimulation, drug enhancement, gene editing or human experimentation instructions.

Find at least three promising ideas outside the obvious smartwatch/AR/EEG list. Explain how each connects to Haven and the cheapest experiment that would genuinely test its central premise.

## 5. Evidence discipline: distinguish impressive from useful

For every important claim, identify the original paper, official technical documentation or primary trial record, date/version and access limits. Prioritize the last 24 months while retaining older foundational work. Check corrections, follow-ups, source-code availability and current commercial status. A news release or trial listing is not an efficacy result.

Record the actual task, hardware, participant population, sample size when available, training/calibration, supervised versus unsupervised conditions, offline versus online tests, reported failures and availability outside the original laboratory.

Use separate labels for:

- Available product with verified access; obtainable development hardware; research apparatus; clinically restricted system; unsupported/speculative concept.
- Laboratory demonstration; evidence from daily settings; published independent replication; result not independently replicated in this review.
- Off-the-shelf components; substantially custom integration; bespoke fabrication; specialist-only facility.

For generative neural decoding, compare against the language model without the signal, shuffled-signal controls and held-out content. Report what information comes from measurements versus prior knowledge or guessing. Do not equate a semantically plausible reconstruction with a verbatim thought or memory.

## 6. Produce original combinations and try to falsify them

Develop 12–18 opportunity cards across the ten areas. Deepen the five strongest rather than returning an unranked product catalogue. Include at least three unusual combinations linking two or more Haven branches.

Possible starting hypotheses—not preaccepted solutions—include:

- A deliberate muscle input paired with a tactile acknowledgment for a discreet assistant interaction.
- A haptic display of robot observations that distinguishes sensor contact, absence of a reading and uncertainty.
- A wearer-requested thermal/depth view with grounded explanations rather than continuous AI video.
- A spatial-memory aid showing what was observed before versus what has been observed now.
- A workshop interface combining gaze selection, modest tactile cues and evidence-linked repair instructions.
- A detachable experimental effector controlled through a qualified input, first on a bench dummy.
- A communications-availability cue for an off-grid team, without implying successful responder delivery.

Each card must identify the human benefit, mechanism, existing prior art, proposed difference, weakest assumption, ordinary baseline, additional hardware, interface access, compute and power costs, learning burden, privacy implications, failure modes and falsifying observation.

Use explicit novelty labels: known capability in new packaging; integration hypothesis; possible research contribution requiring prior-art review; unsupported speculation. Combining fashionable technologies does not automatically create a contribution.

## 7. Economics and affordability

Compare tiers of proposed incremental spend: reuse-only, up to $150, $150–$500, $500–$1,500, and specialist/research-scale. These are evaluation bins, not verified purchase prices or spending authorization.

Quote complete candidate systems: sensors, interface electronics, documented accessories, power, host, fit/straps, fabrication, measurement, developer licenses, subscriptions, replacements and maintenance. Show both upfront cost and plausible 12-month operating cost with assumptions. Verify exact SKU, region, stock, API/raw-data access, license, return rights and date before calling something buyable.

Prefer ordinary signal processing, small dedicated models and on-demand inference where sufficient. Distinguish electronics bandwidth, model context, end-to-end latency and cloud cost. Sensitive biosignals and household media remain local by default unless the relevant person separately authorizes the exact transfer.

A $50 part inside a $50,000 laboratory arrangement is not a $50 reproducible enhancement. A free SDK is not free hardware access.

## 8. Human factors, consent and safety architecture

Define an explicit wearer-controlled session: enrollment, consented capture, ready/unavailable status, deliberate intent, tentative decoding, confirmation when warranted, permitted output/action, feedback, pause, revocation and removal.

Require abstention/no-command states. Test inadvertent activation during ordinary movement, ambiguous intent, device swapping, calibration drift and delayed feedback. Decoded words, gaze and biometrics are not authentication. No hidden background monitoring, emotion surveillance or partner-access default.

Handle data subject, audience, purpose, source revision, consent revision, calibration revision and output-device binding. Prevent raw private content from reaching shared speakers or public repository logs. State the limits of revocation for data already delivered. Do not promise privacy from a malicious administrator merely because processing is local.

Separate sensing from stimulation and passive wearables from powered body-contact devices. Initial physical proposals must use appropriate documented equipment and harmless conditions. No home implants, tissue penetration, DIY brain/nerve stimulation, dosing or treatment protocols, hazardous exposure, improvised life-support gear, or unqualified lifting/restraint. Clinical frontier topics remain in scope for research, with professional oversight rather than procedural self-experimentation.

Any human study proposal needs voluntary consent, an exit path, minimal data, appropriate review and explicit stopping conditions. Do not run tests while driving, near traffic, on stairs, at heights or during an actual emergency. A non-invasive device is not automatically risk-free.

## 9. Design experiments, not just demonstrations

Specify eight finite experiment cards: at least three software/replay-only, three low-risk interface or benchtop candidates, and two ambitious staged investigations. None runs under this prompt.

For each give the hypothesis; measurable outcome; ordinary baseline; apparatus/access; permitted data; expected labels/ground truth; training and held-out split; calibration; trials; nuisance conditions; analysis; total budget; stop conditions; retained evidence; and next gate.

Measure user benefit as well as decoding accuracy: task completion, false activations per hour, missed commands, latency distributions, throughput, energy, setup time, comfort, cognitive workload, training retention and reliability after removal/replacement. Report learning effects and within-person/cross-day/cross-person generalization separately. Avoid train/test leakage between overlapping signal windows or trials.

Compare against a phone button, touch/voice interface, normal tool or no-device condition. Safe sham/counterbalanced conditions may be useful, but do not propose deceptive or risky exposure. A device can fail by burdening the wearer despite a good classifier score.

Keep at least one protected evaluation condition out of optimization. The proposing agent cannot rewrite success after seeing results or grade its own physical eligibility. A failed trial can lead to revision, narrower claims or abandonment—not automatic escalation of hardware or bodily intervention.

## 10. Fit it into Haven without another platform rewrite

Use R02's thin coordinator and existing domain authority. Propose only the needed extensions: biosignal observation, calibration, intentional-input candidate, confirmed interaction, haptic/output request, wearer session and task-specific qualification.

For each interface specify producer, consumer, identity/subject/audience, units, timestamps, quality/uncertainty, revisions, scope, expiry, cancellation and error states. A proposed gesture never becomes direct motor, aircraft, printer or medical authority.

Map contributions to R04/H07 wearables, R03/H04 permission, R02/H02 runtime, R06/R07/H08 spatial perception, R08/H09 fabrication, R09/H10 robotics, R11/H11 emergency support and R13/H06 validation. Do not alter existing schemas, M0/M4 or source imports. Suggest only new draft requirement IDs with the `R14-PROP-` prefix pending H00 review.

## 11. Requested deliverables and finite handback

Return one coherent package, not dozens of overlapping reports:

1. `R14_HANDOFF.md`: a readable overview, technology map, 12–18 opportunity cards, top-five deep dives, maturity/affordability matrix, three overlooked opportunities, red-team findings and recommended order.
2. `EXPERIMENTS_AND_INTERFACES.md`: eight experiment cards, proposed contract deltas, cross-thread questions and no more than three future bounded work packages.
3. `SOURCES.md`: dated primary sources, exact demonstrated claims, limitations, access/licensing status, corrections and unresolved verification.
4. `INTEGRATION_SUMMARY.md`: one-page recommendations, decisions needed, preserved dependencies and explicit NOT_EXECUTED statuses. Add a 150-word plain-English explanation for a nontechnical partner, without promises of mind reading, superhuman performance or lifesaving effectiveness.

Aim for a substantive report with depth concentrated in the strongest opportunities; a decision-ready result is more valuable than exhausting a source count. Include at least 15 primary sources if accessible, identify gaps honestly and do not pad the list.

Proposed delivery directory: `design/H12/R14/v1/`, or the next unused version after checking the repository. This is a proposed research location, not a new authority owner. Follow the actual handoff template and add metadata for source commits and checksums. If a required imported template is missing, use the headings Decisions, Evidence, Interface changes, Acceptance, Risks and open questions, Next package, and One-page integration summary, clearly noting the fallback.

Repository writes require a separately stated assignment. When authorized, use a dedicated branch and PR; do not merge yourself or overwrite imported documents. Otherwise return the files as a packet marked NOT_UPLOADED. Do not collect private inputs in this public repo.

End with: what we can learn without spending; what might justify the first modest purchase; what needs a specialist/clinical collaboration; what is not supported yet; and which experiment would most change the next decision. Do not start coding or another thread.

## 12. Primary-source starting points, not a completed R14 review

The following pages/abstracts were checked while preparing this prompt. They are seeds, not the newest or exhaustive evidence, procurement advice, or reproduced benchmarks. Read the underlying methods and current follow-ups before extending any claim.

- **2025 — Wrist surface-EMG interface:** Kaifosh, Reardon and CTRL-labs, *A generic non-invasive neuromotor interface for human-computer interaction*, Nature. Research on gesture/navigation/handwriting input from sEMG; not general thought reading or proof of access through arbitrary consumer hardware. https://www.nature.com/articles/s41586-025-09255-w
- **2018 — Deliberate silent communication:** Kapur, Kapur and Maes, *AlterEgo: A Personalized Wearable Silent Speech Interface*, MIT Media Lab/IUI. Starting point for articulatory/neuromuscular communication, with task-specific evaluation to inspect; not evidence of involuntary mental access. https://www.media.mit.edu/publications/alterego-IUI/
- **2024 — Haptic sensory substitution:** Flavin et al., *Bioelastic state recovery for haptic sensory substitution*, Nature. Research on skin-coupled haptic interfaces; investigate apparatus and training rather than assuming a general new sense. https://www.nature.com/articles/s41586-024-08155-9
- **2024 — Audio-to-tactile research:** Fletcher et al., *Improved tactile speech perception and noise robustness using audio-to-tactile sensory substitution with amplitude envelope expansion*, Scientific Reports. Task-specific tactile speech-discrimination work; do not generalize to full everyday hearing restoration. https://www.nature.com/articles/s41598-024-65510-6
- **2023 — Non-invasive semantic decoding:** Tang et al., *Semantic reconstruction of continuous language from non-invasive brain recordings*, Nature Neuroscience. fMRI-based research with cooperation requirements; not a consumer EEG-headset result. https://www.nature.com/articles/s41593-023-01304-9
- **2022 — Personalized walking assistance:** Stanford's institutional report on untethered exoskeleton research. Trace its linked Nature paper and compare population and conditions before discussing home use. https://engineering.stanford.edu/news/untethered-exoskeleton-walks-out-real-world
- **2026 — Wearable ultrasound acquisition:** Vostrikov et al., *WULPUS PRO: Multi-mode Ultra-Low-Power Wearable Ultrasound and Array Imaging with CMUT Support*, arXiv preprint 2607.12137. Reported platform/phantom work and projected runtime are not household clinical validation. https://arxiv.org/abs/2607.12137

**Closing directive:** Expand our imagination, then connect the best ideas to physics, evidence, actual developer access and human benefit. Keep both the ambitious horizon and an honest first experiment. Do not reduce the project to a gadget catalogue, and do not make creativity depend on pretending uncertainty has disappeared.
