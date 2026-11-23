# Primary-source register

Checked during the 27 September 2026 US Eastern session. URLs are live references, not pinned software or purchase approval. READ_PRIMARY means the relevant official page, paper abstract or documentation was read; it does not mean the full underlying paper/code was reproduced. Read each evidence-status and source-kind field. Original papers/code remain with their authors. Design implications are Haven proposals.

## R01 — UCSB: 3D Through-Wall Imaging with Unmanned Aerial Vehicles

[https://web.ece.ucsb.edu/~ymostofi/3DThroughWallImaging.html](https://web.ece.ucsb.edu/~ymostofi/3DThroughWallImaging.html)

**Type:** AUTHOR_RESEARCH_PAGE. **Evidence status:** READ_PRIMARY. **Version:** IPSN 2017.

The 2017 research uses coordinated UAV transmitter/receiver measurements and received signal strength to reconstruct obscured structures in a controlled arrangement.

**Boundary:** Not an unmodified consumer drone, arbitrary phone scanner, or universal live room reconstruction.

## R02 — UCSB: Wiffract / WiFi Reading Through Wall

[https://web.ece.ucsb.edu/~ymostofi/WiFiReadingThroughWall](https://web.ece.ucsb.edu/~ymostofi/WiFiReadingThroughWall)

**Type:** AUTHOR_RESEARCH_PAGE. **Evidence status:** READ_PRIMARY. **Version:** MobiCom 2022 / RadarConf 2023.

The work reconstructs edges using diffraction-related measurements and spatial scanning, including letter-shaped objects behind an obstruction.

**Boundary:** Not reading arbitrary printed documents or proof of general indoor scene understanding.

## R03 — MIT: RF-Pose

[https://rfpose.csail.mit.edu/](https://rfpose.csail.mit.edu/)

**Type:** AUTHOR_RESEARCH_PAGE. **Evidence status:** READ_PRIMARY. **Version:** CVPR 2018.

RF-Pose reports through-occlusion human-pose estimation using radio input and visual supervision during training.

**Boundary:** Not a generic router SDK, an identity detector, or qualification for medical assessment.

## R04 — Espressif ESP-CSI

[https://github.com/espressif/esp-csi](https://github.com/espressif/esp-csi)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

Espressif provides channel-state acquisition and sensing examples, including motion/presence-oriented work.

**Boundary:** Hardware, firmware, environment and algorithm performance must be qualified separately; no Haven benchmarks exist.

## R05 — IEEE 802.11 Working Group

[https://www.ieee802.org/11/](https://www.ieee802.org/11/)

**Type:** STANDARDS_BODY. **Evidence status:** READ_PRIMARY. **Version:** 802.11bf-2025.

The working group reports publication of the WLAN sensing amendment IEEE 802.11bf-2025 on September 26, 2025.

**Boundary:** Publication does not establish support or accessible measurements in a particular phone, router or driver.

## R06 — CompSLAM: Complementary Multi-Modal Sensor Fusion for Robust SLAM

[https://arxiv.org/abs/2505.06483](https://arxiv.org/abs/2505.06483)

**Type:** AUTHOR_PREPRINT. **Evidence status:** READ_PRIMARY. **Version:** 2025 preprint; verify paper revision before replication.

The authors describe complementary sensing for localization/mapping in degraded environments with subterranean robotics field experience.

**Boundary:** A research result and code lead, not turnkey Haven navigation or validated rescue reliability.

## R07 — Mobile ALOHA

[https://mobile-aloha.github.io/](https://mobile-aloha.github.io/)

**Type:** AUTHOR_RESEARCH_PAGE. **Evidence status:** READ_PRIMARY. **Version:** CoRL 2024.

The project demonstrates mobile bimanual manipulation learned from demonstrations, with a teleoperation/data-collection platform.

**Boundary:** Task demonstrations do not imply safe autonomous operation in an arbitrary occupied home.

## R08 — LeRobot SO-101

[https://huggingface.co/docs/lerobot/so101](https://huggingface.co/docs/lerobot/so101)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The documentation provides sourcing, printed-part and assembly/calibration guidance for the SO-101 platform.

**Boundary:** A buildable development arm is not a qualified assistive or rescue product.

## R09 — LeRobot LeKiwi

[https://huggingface.co/docs/lerobot/lekiwi](https://huggingface.co/docs/lerobot/lekiwi)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The documentation covers a mobile robot platform and teleoperation-oriented setup with printable hardware.

**Boundary:** Exact BOM, software, stopping behavior and integration must be qualified on the selected build.

## R10 — Physical Intelligence openpi

[https://github.com/Physical-Intelligence/openpi](https://github.com/Physical-Intelligence/openpi)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The repository exposes policy-model code and checkpoints. Its published resource table distinguishes inference, LoRA and full fine-tuning, with different GPU memory needs.

**Boundary:** No inference fit, task quality or hardware compatibility on Eric's desktop has been measured. System RAM is not GPU memory.

## R11 — Gemini Robotics On-Device

[https://deepmind.google/models/gemini-robotics/on-device/](https://deepmind.google/models/gemini-robotics/on-device/)

**Type:** VENDOR_RESEARCH_PAGE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The current On-Device 2 page presents local robot-action modeling and labels access as trusted testers.

**Boundary:** Not a generally downloadable dependency or permission to command Haven hardware.

## R12 — UZH Robotics and Perception Group: Swift drone-racing work

[https://rpg.ifi.uzh.ch/](https://rpg.ifi.uzh.ch/)

**Type:** AUTHOR_RESEARCH_PAGE. **Evidence status:** READ_PRIMARY. **Version:** Nature 2023 project; lab page checked.

The lab describes its Nature 2023 champion-level drone-racing work combining learning in simulation with real-world racing.

**Boundary:** Performance in a race setting does not transfer automatically to cluttered rescue or consumer-aircraft control.

## R13 — NIST: Modular and Autonomous Laboratory Ecosystem

[https://www.nist.gov/programs-projects/development-standards-support-modular-and-autonomous-laboratory-ecosystem](https://www.nist.gov/programs-projects/development-standards-support-modular-and-autonomous-laboratory-ecosystem)

**Type:** GOVERNMENT_RESEARCH. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

NIST describes work on standards supporting modular and autonomous laboratory systems.

**Boundary:** A standards/research direction, not a finished household engineering agent or certification.

## R14 — Berkeley autonomous experimentation / A-Lab research

[https://ceder.berkeley.edu/research-areas/autonomous-experimentation-for-accelerated-materials-discovery/](https://ceder.berkeley.edu/research-areas/autonomous-experimentation-for-accelerated-materials-discovery/)

**Type:** AUTHOR_RESEARCH_PAGE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The group describes autonomous experimentation combining planning, experimental execution and analysis in materials research.

**Boundary:** No chemistry replication is proposed here. Novel-material counts must not be repeated without reconciling the correction in R15.

## R15 — A-Lab author correction

[https://www.nature.com/articles/s41586-025-09992-y](https://www.nature.com/articles/s41586-025-09992-y)

**Type:** JOURNAL_CORRECTION. **Evidence status:** READ_PRIMARY. **Version:** Nature 650 E1 (2026).

The January 2026 correction distinguishes materials new to the prediction platform from materials new to science, revises diffraction-based success claims and removes a training-data inclusion.

**Boundary:** The corrected work remains a useful autonomous-experimentation precedent, not proof that every generated novelty/success claim is reliable. Detailed reproduction requires the corrected article and supplements.

## R16 — Drone delivery of AEDs before ambulance arrival in real-life suspected cardiac arrests

[https://pubmed.ncbi.nlm.nih.gov/38000871/](https://pubmed.ncbi.nlm.nih.gov/38000871/)

**Type:** PEER_REVIEWED_STUDY_ABSTRACT. **Evidence status:** READ_PRIMARY. **Version:** Lancet Digital Health 2023; study period 2021–2022.

A Swedish prospective observational study reports real emergency-service drone AED deliveries. Among 55 cases with comparable arrival times, 37 deliveries preceded ambulance arrival.

**Boundary:** Not a randomized survival-effect estimate, universal delivery reliability, or authorization for a home-built medical-delivery service.

## R17 — CadQuery introduction

[https://cadquery.readthedocs.io/en/latest/intro.html](https://cadquery.readthedocs.io/en/latest/intro.html)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

CadQuery supports programmatic parametric CAD and engineering/mesh exports.

**Boundary:** Generated geometry alone does not prove manufacturability, load capacity or material safety.

## R18 — OctoPrint job API

[https://docs.octoprint.org/en/main/api/job.html](https://docs.octoprint.org/en/main/api/job.html)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The documented API includes print-job state and controls such as start, pause and cancel.

**Boundary:** Not universal printer compatibility, a machine-safety controller, or approval for unattended printing.

## R19 — NIOSH: Approaches to Safe 3D Printing

[https://www.cdc.gov/niosh/docs/2024-103/pdfs/2024-103.pdf](https://www.cdc.gov/niosh/docs/2024-103/pdfs/2024-103.pdf)

**Type:** GOVERNMENT_SAFETY_GUIDANCE. **Evidence status:** READ_PRIMARY. **Version:** Publication 2024-103, November 2023.

NIOSH discusses particle/chemical emissions, thermal, mechanical and electrical hazards and approaches to exposure control for small printing workspaces.

**Boundary:** An enclosure alone is not proof of adequate ventilation or safe operation for every material.

## R20 — Meshtastic introduction

[https://meshtastic.org/docs/introduction/](https://meshtastic.org/docs/introduction/)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

Meshtastic documents off-grid LoRa-based messaging and location-related capabilities with compatible nodes.

**Boundary:** Not broadband internet, universal range or an authorized emergency dispatch interface.

## R21 — IETF Bundle Protocol Version 7

[https://www.rfc-editor.org/rfc/rfc9171.html](https://www.rfc-editor.org/rfc/rfc9171.html)

**Type:** STANDARD. **Evidence status:** READ_PRIMARY. **Version:** RFC 9171.

RFC 9171 specifies a store-and-forward bundle protocol for delay/disruption-tolerant networking.

**Boundary:** Haven need not implement the full protocol in an initial local message-outbox demonstration.

## R22 — Nous Research Hermes Agent

[https://github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

Hermes is MIT-licensed agent software with tools, memory/skills and provider options.

**Boundary:** The framework is not a free inference model or proof of safe household isolation.

## R23 — Hermes provider documentation

[https://hermes-agent.nousresearch.com/docs/integrations/providers](https://hermes-agent.nousresearch.com/docs/integrations/providers)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live provider guide checked during preparation.

The reviewed guide requires a 64,000-token configured context for tool-using agents and discusses local endpoints.

**Boundary:** A small standalone-model benchmark does not qualify the entire framework. Recheck the selected release.

## R24 — Meta: Introducing Muse

[https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/)

**Type:** VENDOR_ANNOUNCEMENT. **Evidence status:** READ_PRIMARY. **Version:** September 2026 announcement.

Meta describes a hosted personal-agent product powered by Muse Spark with free and paid use.

**Boundary:** This announcement does not establish downloadable weights, self-hosting, or a public interchangeable inference API for Haven.

## R25 — Qwen3.5-4B model card

[https://huggingface.co/Qwen/Qwen3.5-4B](https://huggingface.co/Qwen/Qwen3.5-4B)

**Type:** OFFICIAL_MODEL_CARD. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The model card identifies a compact multimodal model and its Apache-2.0 license.

**Boundary:** No Haven task quality, speed, energy or memory results have been measured.

## R26 — Gemma 3 4B serving artifact

[https://ollama.com/library/gemma3:4b](https://ollama.com/library/gemma3:4b)

**Type:** OFFICIAL_RUNTIME_CATALOG. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

Ollama publishes a Gemma 3 4B artifact under Gemma terms.

**Boundary:** Open weights are not synonymous with Apache/MIT licensing; artifact size is not total runtime memory.

## R27 — Ollama structured outputs

[https://docs.ollama.com/capabilities/structured-outputs](https://docs.ollama.com/capabilities/structured-outputs)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

Ollama documents schema-constrained outputs including use with vision inputs.

**Boundary:** Schema validity is not factual correctness, medical reliability or permission to act.

## R28 — Codex AGENTS.md guidance

[https://learn.chatgpt.com/docs/agent-configuration/agents-md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

Codex documentation describes using AGENTS.md as project instructions.

**Boundary:** An instructions file is not a technical permission boundary or evidence that an agent executed a task.

## R29 — Meta Wearables Device Access Toolkit for iOS

[https://github.com/facebook/meta-wearables-dat-ios](https://github.com/facebook/meta-wearables-dat-ios)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The developer-preview SDK lists camera, audio, display, input and motion-related features. Some capture/audio features are explicitly experimental and unavailable for production publishing.

**Boundary:** One capability does not imply all glasses models support every interface. Exact SKU, SDK, permission and release channel need qualification.

## R30 — Apple RoomPlan

[https://developer.apple.com/augmented-reality/roomplan/](https://developer.apple.com/augmented-reality/roomplan/)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

RoomPlan uses camera/LiDAR on supported Apple hardware to produce parametric room representations.

**Boundary:** It observes a scanned room; it is not through-wall sensing and does not establish present conditions from historical scans.

## R31 — DJI Matrice 4 accessory specifications

[https://enterprise.dji.com/matrice-4-series/specs](https://enterprise.dji.com/matrice-4-series/specs)

**Type:** MANUFACTURER_SPECIFICATION. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The AL1 spotlight is specified at 99 g including bracket and 32 W maximum. The platform also documents an AS1 speaker.

**Boundary:** Enterprise accessory specs do not establish compatibility, safe payload or performance on a Mini, Tello or EC120.

## R32 — FAA operating restrictions / TFRs

[https://www.faa.gov/uas/getting_started/where_can_i_fly/airspace_restrictions/tfr](https://www.faa.gov/uas/getting_started/where_can_i_fly/airspace_restrictions/tfr)

**Type:** REGULATOR_GUIDANCE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

FAA describes operating restrictions and temporary flight restrictions, including emergency-related contexts.

**Boundary:** Calling a mission an emergency does not establish an exception or flight authorization for a private operator.

## R33 — FCC through-wall UWB imaging requirements

[https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-F/section-15.510](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-F/section-15.510)

**Type:** REGULATION. **Evidence status:** READ_PRIMARY. **Version:** eCFR displayed current through September 24, 2026.

47 CFR 15.510 imposes operator/use restrictions on through-wall UWB systems operating under that section, including government-authorized emergency/public-safety contexts.

**Boundary:** Do not generalize this section to a blanket ban on all WiFi sensing. Equipment category, authorization and jurisdiction must be resolved before purchase/transmission.

## R34 — NASA Evolved Structures Guide

[https://ntrs.nasa.gov/citations/20240005675](https://ntrs.nasa.gov/citations/20240005675)

**Type:** GOVERNMENT_TECHNICAL_REPORT. **Evidence status:** READ_PRIMARY. **Version:** 2024 technical report.

NASA's guide addresses engineering requirements and generative design for evolved structures in mission hardware.

**Boundary:** Design optimization is not self-certification; Haven should borrow the requirements/check/test loop rather than aerospace qualification claims.

## R35 — FAA Part 107 waivers

[https://www.faa.gov/uas/commercial_operators/part_107_waivers](https://www.faa.gov/uas/commercial_operators/part_107_waivers)

**Type:** REGULATOR_GUIDANCE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

FAA documents the waiver process and operations that may require specific approval.

**Boundary:** No current operator, site or concurrent/BVLOS mission is qualified by this repository.

## R36 — FDA point-of-care 3D printing discussion paper

[https://www.fda.gov/medical-devices/3d-printing-medical-devices/3d-printing-medical-devices-point-care-discussion-paper](https://www.fda.gov/medical-devices/3d-printing-medical-devices/3d-printing-medical-devices-point-care-discussion-paper)

**Type:** REGULATOR_DISCUSSION. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

FDA discusses responsibilities and considerations for medical-device manufacturing at the point of care.

**Boundary:** A discussion paper is not device approval or a rule that any printed emergency item is suitable for clinical use.

## R37 — whisper.cpp

[https://github.com/ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The project supplies a local C/C++ inference implementation for Whisper speech-recognition models.

**Boundary:** Actual latency, microphone behavior, accents and accuracy on the target PC remain untested.

## R38 — Kokoro-82M

[https://huggingface.co/hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M)

**Type:** OFFICIAL_MODEL_CARD. **Evidence status:** READ_PRIMARY. **Version:** Live documentation; freeze exact version during qualification.

The author publishes a compact speech-generation model with Apache-licensed weights.

**Boundary:** Check the complete runtime/voice licenses and evaluate speech quality and hardware performance.

## R39 — Apple HealthKit authorization

[https://developer.apple.com/documentation/healthkit/authorizing-access-to-health-data](https://developer.apple.com/documentation/healthkit/authorizing-access-to-health-data)

**Type:** OFFICIAL_SOFTWARE. **Evidence status:** DOCUMENT_LOCATED_TEXT_LIMITED. **Version:** Live documentation; freeze exact version during qualification.

Official authorization documentation identified; detailed requirements are retained from the prior design as pending exact native-app qualification.

**Boundary:** This session retrieved a JavaScript shell rather than complete text. Do not label new API-specific claims freshly verified from that shell.
