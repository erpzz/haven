# R06 primary-source register and research assessment

**Checked:** 2026-09-28 (UTC), through public primary sources. “Read” means retrieved source text or the stated source section; it does not mean code executed, hardware inspected, full normative standards acquired, or research independently reproduced. No third-party datasets, papers or software are redistributed in this package.

This is a bounded decision survey, not an exhaustive literature review or a claim to identify the universal best system. `DOCUMENTED_EXTERNAL` means a source establishes what its authors/vendor report. All corresponding Haven capabilities remain unqualified. Access/version limits below are material to future reproduction.

## Acquisition, platforms and standards

### R06-S01 — IEEE 802.11 publication status

- Primary: [IEEE 802.11 working group](https://www.ieee802.org/11/) and [official timeline](https://www.ieee802.org/11/Reports/802.11_Timelines.htm).
- Class/version: standards-body status; 802.11bf-2025. Primary page/status retrieved.
- Finding: publication date September 26, 2025; 802.11bk-2025 positioning amendment is separately listed for September 5, 2025.
- Limit: standard availability does not identify a compatible installed phone/router, measurement API or imaging capability. Do not describe bf as still merely forthcoming. Crosswalk: starter R05.

### R06-S02 — Espressif ESP-CSI

- Primary: [official ESP-CSI repository](https://github.com/espressif/esp-csi).
- Class/version: vendor software; `master` documentation checked, exact commit not pinned. README/license metadata read.
- Finding: documented CSI acquisition examples include an ESP32 with a router and multi-device arrangements; repository identifies Apache-2.0 licensing.
- Limit: repository examples and accuracy language are not an independent home benchmark. Do not adopt broad packet capture, channel switching or claimed precision without a permitted profile. Pin source, firmware and dependencies before implementation. Crosswalk: starter R04.

### R06-S03 — ESP-IDF raw CSI representation

- Primary: [ESP32 Wi-Fi vendor features](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-guides/wifi-driver/wifi-vendor-features.html).
- Class/version: official API documentation; retrieved page identifies v6.1. CSI section read.
- Finding: CSI comprises per-subcarrier complex samples; representation/LTF availability and invalid leading bytes depend on received packet/hardware details. RX metadata includes reception time and signal information. A short callback should queue work.
- Limit: `stable` is mutable; pin the exact implementation's documentation. Output is not a calibrated synchronized multi-radio phase reference, metric ranging output, or proof of a 3×3 MIMO sensor.

### R06-S04 — Stock iOS Wi-Fi access boundary

- Primary: [Apple TN3111](https://developer.apple.com/documentation/technotes/tn3111-ios-wifi-api-overview).
- Class/version: official technote, current indexed excerpt; full page/Markdown retrieval unavailable in this review.
- Finding supported by the indexed primary excerpt: iOS lacks a general-purpose Wi-Fi scanning/configuration API and provides specific APIs instead.
- Limit: this alone does not prove the absence of every present/future CSI interface. No supported stock-iPhone raw CSI acquisition route was established here. Exact entitlement/SDK support remains a qualification question, not permission to use private APIs or jailbreak firmware.

### R06-S05 — Apple Nearby Interaction

- Primary: [framework documentation](https://developer.apple.com/documentation/nearbyinteraction) and [Apple WWDC22 technical session](https://developer.apple.com/videos/play/wwdc2022/10008/).
- Class/version: official platform documentation; framework indexed, WWDC22 transcript read. Historical API behavior, rechecked as a reference; not a test of today's OS.
- Finding: cooperative distance/direction and camera assistance are documented; results can be unavailable. The described accessory background mode requires BLE integration and delivers measurements to the accessory while the app lacks ordinary foreground callbacks.
- Limit: exact current SKU/OS capabilities, accessory firmware, lifecycle and callback behavior need native testing. No raw RF imaging access, universal direction support, or continuous two-person tracking is established.

### R06-S06 — Apple RoomPlan

- Primary: [RoomPlan overview](https://developer.apple.com/augmented-reality/roomplan/).
- Class/version: official API/product overview, read; no SDK pin selected.
- Finding: camera/LiDAR-based parametric room scans can include dimensions and furniture categories.
- Limit: supported hardware and actual errors need checking. This is direct-view sensing with learned interpretation; a historical scan is not live through-wall evidence or unquestionable ground truth. Crosswalk: starter R30.

### R06-S07 — Android Wi-Fi RTT

- Primary: [Android ranging documentation](https://developer.android.com/develop/connectivity/wifi/wifi-rtt).
- Class/version: official API guide, read. RTT introduced at API 28; az NTB support described from API 35 on capable devices.
- Finding: cooperative AP/peer ranging needs matching hardware, permissions and availability checks; ranges, uncertainty fields and boot-relative times are exposed. Multiple surveyed peers enable device localization.
- Limit: generic Android ownership, Wi-Fi generation or an AP brand is insufficient. Google describes typical 1–2 m positioning, not a guaranteed NLOS result or object imaging. Do not purchase an Android bridge merely because the API exists.

### R06-S08 — Qorvo DWM3001CDK

- Primary: [manufacturer development-kit page](https://www.qorvo.com/products/ek/DWM3001CDK).
- Class/version: manufacturer documentation, read; product brief Rev B (05/2022), quick-start listed 08/2024, linked SDK v1.1.1.
- Finding: an evaluation path for TWR/TDoA and NI-compatible Apple interaction is documented; one board is the kit's core content.
- Limit: full-room RTLS needs additional infrastructure. Exact software license, firmware, multi-peer behavior, antenna-delay calibration, CIR exposure and permitted use remain purchase gates. It is not a through-wall imaging kit by implication.

### R06-S09 — TI IWRL6432BOOST

- Primary: [manufacturer board page](https://www.ti.com/tool/IWRL6432BOOST).
- Class/version: product/SDK documentation, read; exact board/firmware revision not selected.
- Finding: a 57–64 GHz evaluation path with two TX/three RX antennas and point-cloud access is documented. Raw ADC capture can require DCA1000EVM and its associated setup.
- Limit: development hardware, acquisition cost and processed point-cloud outputs differ from a complete qualified reconstruction instrument. Verify allowable operation and exact chirp profile. Web inventory placeholders are inconsistent; no price/stock quotation is asserted.

### R06-S10 — Radar resolution and chirp assumptions

- Primary: [TI, Programming Chirp Parameters in TI Radar Devices, Rev A](https://www.ti.com/lit/an/swra553a/swra553a.pdf); [TI range/velocity/resolution technical FAQ](https://e2e.ti.com/support/sensors-group/sensors/f/sensors-forum/1050220/faq-computing-maximum-range-velocity-and-resolution-mmwave-system).
- Class/version: manufacturer engineering reference, retrieved.
- Finding: swept bandwidth is central to range resolution; sampling/chirp/array choices constrain usable measurements.
- Limit: ideal formulas are design scales, not achieved accuracy. The numerical bandwidth examples in this handback are our calculations, not measured performance. Angle, material, SNR, calibration and model error remain separate.

## Reconstruction and learning research

### R06-S11 — Radio Tomographic Imaging with Wireless Networks

- Primary: [Wilson and Patwari author manuscript](https://span.ece.utah.edu/uploads/RTI_version_3.pdf).
- Class/version: author manuscript of foundational research (journal publication 2010); abstract and limitations read.
- Finding: RSS attenuation on many links supports a regularized inverse image; the reported experiment used 28 nodes. The paper explicitly discusses ill-posedness and further through-wall modeling needs.
- Limit: an attenuation image of a controlled network does not establish detailed surfaces or arbitrary one-sided room reconstruction. No universal node count or performance is transferred to Haven.

### R06-S12 — Coordinated UAV RSSI reconstruction

- Primary: [Karanam and Mostofi, IPSN 2017](https://web.ece.ucsb.edu/~ymostofi/papers/IPSN17_KaranamMostofi.pdf).
- Class/version: peer-reviewed research paper, author-hosted text read.
- Finding: paired UAV transmitter/receiver sampling, planned measurement geometry and regularized inference produced controlled 3D through-wall reconstructions.
- Limit: the apparatus and path assumptions are central. This is not evidence that the EC120, one hovering drone or an ordinary phone can do the same. The source's sparse-sampling result is not a Haven performance target. Crosswalk: starter R01.

### R06-S13 — Wiffract / diffraction-based edges

- Primary: [Mostofi Lab project and paper links](https://web.ece.ucsb.edu/~ymostofi/WiFiReadingThroughWall).
- Class/version: author research page, read; MobiCom 2022 and RadarConf 2023 work.
- Finding: a spatial receiver grid and diffraction models support edge hypotheses, followed by information propagation and image improvement. Demonstrations include large letter-shaped targets; the receiver grid was synthesized with a ground vehicle/vertical mechanism.
- Limit: completion/classification is not direct measurement. This is not reading arbitrary printed text through walls, nor a stock-phone workflow. Crosswalk: starter R02.

### R06-S14 — RF-Pose

- Primary: [Zhao et al., CVPR 2018 paper](https://people.csail.mit.edu/mingmin/papers/rfpose-cvpr-zhao.pdf).
- Class/version: peer-reviewed research paper; author-hosted text retrieved, RF hardware and cross-modal method inspected.
- Finding: through-occlusion pose inference uses purpose-built RF measurements and visual supervision during training.
- Limit: this is not generic router CSI support. Learned pose, identity and clinical state are different claims; RF-Pose does not qualify any Haven capability. Crosswalk: starter R03.

### R06-S15 — DensePose From WiFi

- Primary: [Geng, Huang and De la Torre, arXiv:2301.00250v1](https://arxiv.org/html/2301.00250v1).
- Class/version: author preprint; methods, evaluation and failure sections read.
- Finding: CSI-to-dense-pose learning relies on image-derived supervision. The paper reports detection AP falling from 43.5 in its same-layout protocol to 27.3 for a different layout; rare poses and several simultaneous subjects cause failures.
- Limit: a useful domain-shift warning, not camera-equivalent perception, generalized wall imaging or a ready-made implementation. The paper's pseudo-labels are not independent metrology. Unaffiliated repositories with similar names were not accepted as author code or validated reproductions.

### R06-S16 — RISE: static-radar scene understanding

- Primary: [author preprint v1](https://arxiv.org/html/2511.14019v1); [CVPR 2026 official proceedings entry](https://openaccess.thecvf.com/content/CVPR2026/html/Zhou_RISE_Single_Static_Radar-based_Indoor_Scene_Understanding_CVPR_2026_paper.html).
- Class/version: v1 full-text sections read; CVPR 2026 venue confirmed from primary index, proceedings file retrieval failed.
- Finding: cascaded radar, moving volunteers and multipath geometry feed learned diffusion completion. The study reports 11 environments, about 16 cm mean wall-layout Chamfer distance and 58% furniture IoU.
- Limit: author-reported metrics, not independent replication. A static sensor still uses motion over time; completed structure is inference. This does not establish sensing from outside arbitrary walls. Code/data release and exact room holdout guarantees were not qualified for Haven.

### R06-S17 — GeRaF 2.0 / Seeing through boxes

- Primary: [Lu, Shanbhag and Hassanieh, arXiv:2605.29098v1](https://arxiv.org/html/2605.29098v1); [EPFL research news](https://sens.epfl.ch/blog.html).
- Class/version: May 27, 2026 author paper, methods/experiments read; CVPR 2026 venue corroborated by primary author/proceedings indexing.
- Finding: combines visible exterior geometry with RF inverse rendering for hidden object surfaces. Apparatus includes 77 GHz radar, robotic synthetic apertures, rotating objects about 0.3 m away and roughly 4 GHz chirps. Training is reported at 48 hours on an H100.
- Limit: controlled box/material/object setup and substantial computation; not live room scanning on existing personal hardware. The text's squared-distance Chamfer definition and table unit labeling warrant care, so no headline millimeter accuracy is adopted. External visual constraints remain distinct evidence.

## Datasets, permissions and regulatory boundaries

### R06-S18 — CSI-Bench current author repository and corrections

- Primary: [canonical author repository](https://github.com/guozhen-jenn-zhu/CSI-Bench-Real-WiFi-Sensing-Benchmark), [LICENSE file](https://github.com/guozhen-jenn-zhu/CSI-Bench-Real-WiFi-Sensing-Benchmark/blob/main/LICENSE), [paper v2 metadata/abstract](https://arxiv.org/abs/2505.21866).
- Class/version: author dataset/software; current README and LICENSE read; paper revised November 20, 2025. Exact code commit not pinned.
- Finding: the README reports corrected data, rerun benchmarks and Kaggle Version 12. LICENSE is MIT while README names CC BY-NC-ND 4.0; data/software rights must be distinguished.
- Limit: no files acquired or benchmarks reproduced. Access, rights and subset suitability are unresolved. Fork documentation is not authoritative. Do not reuse historical scores without version reconciliation or treat code licensing as dataset/subject permission.

### R06-S19 — UCSB Wi-Fi RSSI imaging dataset

- Primary: [author dataset page](https://web.ece.ucsb.edu/mostofi-lab/code-data/WiFiImagingData2014).
- Class/version: author-hosted 2014 dataset page, read.
- Finding: offers paired TX/RX position and RSSI files with a reference map; the page limits use to academic purposes.
- Limit: Haven's personal-project use is not automatically within that scope. No download/use authorized by this review; geometry data also cannot establish a presence false-alarm rate.

### R06-S20 — UWB through-wall category

- Primary: [47 CFR §15.510, eCFR](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-F/section-15.510).
- Class/version: regulatory primary text read; displayed current through September 24, 2026.
- Finding: operation under this section is limited to specified government-authorized law-enforcement/emergency/firefighting contexts, with additional category-specific conditions.
- Limit: an exact equipment/use classification is required; this is not a blanket statement about all Wi-Fi sensing. Consent or retail availability does not override operating restrictions. Crosswalk: starter R33.

### R06-S21 — Airborne UWB restriction

- Primary: [47 CFR §15.521, eCFR](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-F/section-15.521).
- Class/version: regulatory primary text read; displayed current through September 24, 2026.
- Finding: subsection (a) prohibits aircraft operation for UWB under this subpart; imaging categories also have defined permitted uses.
- Limit: any claimed alternative authorization or waiver must be documented for the exact configuration. No such exception was established here. Do not generalize this rule to every radio on a drone or assume a ground-ranging module can be flown.

### R06-S22 — 802.11bf technical scope background

- Primary: [Du et al., 802.11bf overview](https://arxiv.org/abs/2310.17661); [IEEE task-group record](https://www.ieee802.org/11/Reports/tgbf_update.htm).
- Class/version: standards-participant research overview (2023) and primary project record; overview abstract and group page retrieved.
- Finding: describes sensing acquisition/procedures across sub-7 GHz and 60 GHz work, rather than prescribing one application reconstruction algorithm.
- Limit: prepublication research is not the final normative standard. The IEEE final-standard PDF fetch failed; no clause-level compliance or full standard review is claimed. Use S01 for published status.

## What the evidence changes

The older controlled demonstrations justify preserving geometry/semantics as serious research goals. The 2025–2026 work adds stronger object/layout examples while exposing the importance of apparatus, priors, motion, computation and reference data. None removes the measurement-access, identifiability, evaluation or consent gates.

The recommended order follows what can be independently checked: input integrity → motion evidence → framed localization → controlled geometry → semantic hypotheses → qualified mobility. Hardware may change between stages. This order is an R06 design judgment, not a claim made by any one source.

Unresolved factual gates are narrow: exact owned SKUs/OS, accessible firmware data, permitted radio use/site, data/code licenses, independent reproduction and performance on held-out conditions. This register does not schedule ongoing monitoring, request access or authorize follow-up collection.
