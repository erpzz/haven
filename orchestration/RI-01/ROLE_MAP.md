# Actual roles and how they cooperate

The Codex session is the root supervisor. These ten project profiles are reusable real subagent types, not ten agents that must remain running. Each distinct handback gets its own reviewer assignment and actual task receipt.

| Profile | Responsibility | Writes |
|---|---|---|
| haven_intake | Inventory main, pending PRs/branches, source editions and code availability | Read-only; returns inventory |
| haven_research_reviewer | Review one actual research addition, evidence and interfaces | Read-only; returns findings |
| haven_researcher | Complete missing Rxx research or bounded reconciliation | Only assigned report directory |
| haven_integration_manager | Separate H00 synthesis, contracts, dependency closure and coding plans | Only assigned integration directory |
| haven_vision_guardian | Independent cumulative-vision and usefulness checks | Read-only; returns coverage/findings |
| haven_code_reviewer | Independent actual-code/config/test/contract review | Read-only; no source edits or execution |
| haven_evidence_auditor | R13 source use, evidence fidelity and acceptance review | Read-only; returns audit |
| haven_vision_perception | Images/figures, recognition, segmentation, tracking and spatial vision design | Only assigned modality-report directory |
| haven_audio_video | Speech/sound, temporal video, synchronization and output design | Only assigned modality-report directory |
| haven_sensor_fusion | Cross-modal evidence, world model, memory and multimodal output | Only assigned fusion-report directory |

The root alone publishes Git commits and shared task state. Role sandbox settings are subject to actual parent runtime permissions; verify them. Filesystem prefixes do not implement adversarial isolation.

Consultation examples:
- R07 asks the actual R06 reviewer/author which calibration and support fields are required; the answer cites the exact RF contract.
- R04 asks the actual R03 author what a glasses/public-screen audience switch invalidates; the response is carried into its output-device design.
- The multimodal specialist asks R02 how cancellation fences late model output while preserving the original video/telemetry evidence.
- R08 asks R07 whether a proposed fixture changes the sensor frame/calibration assumptions; the integration manager records the consequence.
- The code reviewer challenges a proposed contract's lost-acknowledgment behavior; the relevant author revises it, and the reviewer checks the new revision.

Messages and answers must actually occur. The supervisor can relay native messages when peer-to-peer routing is not directly exposed. Recorded agreement is useful coordination, not scientific proof. The final candidate receives distinct vision, code and evidence checks before publication as a proposed design.
