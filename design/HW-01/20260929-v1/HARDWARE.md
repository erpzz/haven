# Minimum hardware and purchase ladder

2026-09-29 • proposal, not a shopping order. Sources [Sxx] in SOURCES.md. Tax, shipping, energy and warranties are excluded unless stated. Planning allowances are deliberately distinguished from observed prices. Exact component fit, stock and thermal validation remain outstanding.

## What is already enough to start

Use the operator-reported desktop class: modern 12-core x86 CPU, 64 GB system RAM and an NVIDIA GPU with 8 GB VRAM; also an Apple Silicon laptop with 16 GB unified memory, a phone and existing display/network peripherals. These are reported inventory classes, not a current host inspection. Do not publish hostnames, network maps, serials or secrets in this public packet.

For a no-new-purchase engineering MVP, propose reserving 4–6 CPU cores, 12–16 GB RAM and about 100 GB of free SSD workspace for the coding lab, while keeping measured headroom for the desktop and Haven. Those are proposed allocations, not a claim all current storage or free memory exists and not a change to IP-01's smaller existing storage grant.

The phone supplies selected images, an existing screen supplies the interface, and existing headphones can provide private audio later. Initial two-user testing can use two synthetic browser sessions before real enrollment. A camera stream, wearable application, live sensor or physical-device test requires an appropriate future assignment.

**Mandatory new hardware cost can be $0, conditional on available disk/runtime capacity.** Software integration, tests and the actual model's limits still remain work. Zero hardware spend does not mean zero electricity, labor or optional hosted cost.

## Model fit: file size is only the first line

| Candidate tier | Published artifact indication | Proposed use / limitation |
|---|---|---|
| Qwen3.5 4B | Ollama lists about 3.4 GB for its standard tag [S10] | Small tool/edit experiment; do not promise reliable long-horizon software engineering |
| Qwen3.5 9B | About 6.6 GB [S10] | Marginal on an 8 GB GPU once context/runtime/display use are included; test before assigning unattended work |
| Qwen3-Coder 30B-A3B | Ollama Q4_K_M tag about 19 GB [S11] | Candidate for a 24 GB-class GPU with a measured context budget; 64K harness context may still require a smaller model, more memory or a different tested setup |
| Qwen3.6-35B-A3B | OpenHands recommends a 24 GB GPU or 64 GB Apple memory class for quantized use [S06] | Alternative for a capable local coding setup; exact artifact/context/template still govern fit and quality |

A MoE model with 3B active parameters is not a 3B weight-memory footprint: inactive experts still have to be stored/resident or explicitly offloaded. Host 64 GB RAM is not 64 GB NVIDIA VRAM. Apple unified memory is shared with the operating system. Advertised model context is not a promise that a small machine can use that context efficiently.

Approximate inference memory = weights + per-session attention/state cache + runtime workspace + vision/other buffers. Multiple sessions usually add state/cache even when model weights are shared. Request concurrency and number of loaded models are different [S09]. No tokens/second or long-horizon success rate has been measured on the operator's machine.

## Optional first physical workbench kit

Choose a phone-based or fixed-camera path, not both by default.

| Qty | Part / minimum specification | Cost treatment | Why / caveat |
|---|---|---|---|
| 1 | Existing phone with selected-image transfer | $0 incremental | No assumed LiDAR, live AR API or background-camera access |
| 1 | Stable phone/camera clamp or tabletop stand | $15–30 planning allowance | Stable capture beats an unstable expensive sensor |
| 1 | USB cable/extension compatible with the selected device | $10–20 planning allowance | Verify data support and reach, not charge-only |
| 1 set | Printed reference markers and ruler | $0–10 planning allowance | Initial spatial scale/reference; not metrology certification |
| Optional 1 | Logitech C920s 960-001257, fixed 1080p USB camera | $59.99 observed at LG retail page; prices can change [S17] | Adds a stationary view; no depth/thermal capability |
| Optional 1 | Seeed XIAO ESP32S3 Sense, SKU 113991115 | $13.99 manufacturer listing [S18]; $25–50 complete USB-powered experiment allowance | Small camera/mic/sensor node, not a coding model host; include cable, enclosure and any storage actually needed |
| Optional 1 | Independent backup drive; 1 TB USB SSD example | $150–275 planning allowance; observed T7 retailer listings roughly $230–250 [S20] | Reuse a suitable existing backup first; a model disk is not itself a backup |
| Optional 1 | UPS selected by measured watts and runtime | $120–250 planning allowance for starter class | Small systems only after sizing; not an automatic choice for a 3090 workstation |

Phone/stand/cable/marker path: approximately $25–60 if all accessories are missing. Fixed-camera/stand/cable/marker path: approximately $85–120. Neither total includes optional sensor node, storage, UPS, taxes or shipping. A 1 TB premium portable SSD is not a mandatory MVP purchase.

No headset, AR glasses, depth camera, robot arm, 3D printer, custom neural board, rack server or replacement drone is required for this first workbench. A short-range depth camera is a later instrument chosen for a measured geometry task; it is not automatically a room scanner. Existing consumer-drone programmability remains unverified.

## Two different dedicated computers

### A. Dedicated coding worker / always-on host

Target 4 modern CPU cores and 16 GB RAM as a constrained starting point; prefer 6–8 cores, 32 GB RAM, 1 TB SSD and gigabit Ethernet for browser/build/test workloads. A refurbished business mini-PC or new small x86 host is a candidate. **$300–600 is a planning allowance, not a quoted configured SKU.** Check Linux/virtualization support, upgradeability, cooling, storage and warranty before purchase.

This machine can run the agent harness and tools while borrowing the existing desktop's model endpoint. It improves separation/availability of the worker, not necessarily inference speed. If the GPU desktop sleeps, local inference is unavailable unless a separately verified local CPU/model fallback exists. An inexpensive low-power mini-PC alone is not a powerful autonomous coding LLM computer.

### B. Dedicated inference + coding workstation

A reasonable next evaluation target is an x86 Linux workstation with one 24 GB NVIDIA GPU, 64 GB RAM and 1–2 TB SSD. A used RTX 3090 is an example of the memory class, not an unconditional purchase recommendation [S12]. Buy only after comparing an exact tested workload, returned-unit/warranty terms and total system cost. No exact used listing was validated in this research.

| Component | Minimum practical design target | Procurement note |
|---|---|---|
| CPU | Efficient modern 6–8 cores or reuse a compatible existing CPU | Compilation matters; do not pay for top-end CPU before measuring |
| Motherboard | Exact CPU socket/BIOS, GPU slot/clearance and NVMe support | No assumed compatibility with unknown existing board |
| RAM | 64 GB in a supported matched kit | Prefer expandable configuration |
| GPU | 24 GB VRAM class; exact model and runtime support verified | A 16 GB card can serve smaller tasks; 24 GB is a workload target, not universal minimum |
| SSD | 1 TB minimum; 2 TB preferred if affordable | Account for weights, containers, environments and backup separately |
| PSU | Quality unit sized to exact GPU/CPU; often 850 W class for a 3090-oriented build | NVIDIA's 3090 FE lists 350 W GPU / 750 W reference system guidance [S12]; AIB requirements vary |
| Case/cooling | Measured full GPU clearance, airflow and sustained cooling | GPU dimensions and connectors must be checked before purchase |
| Network/OS | Gigabit Ethernet; supported Linux/runtime combination | More network speed does not combine VRAM automatically |
| Backup/UPS | Separate backup and load-sized UPS | A 900 VA/500 W UPS is not automatically adequate for the whole AI workstation |

**Complete-workstation planning envelope: roughly $1,500–2,600**, depending strongly on used GPU condition, reused parts and current RAM/storage prices. This is not a current validated cart, price guarantee or spending authorization. Do not buy a card for the old desktop until its PSU, connectors, case and thermals are inventoried.

## AI chips and compact systems: which job do they actually do?

| Hardware | Verified specification / price status | Suggested role, not a benchmark claim |
|---|---|---|
| RTX 3090 class | 24 GB; power/fit requirements above [S12] | Flexible local coding/inference tier; used-hardware power/condition tradeoff |
| RTX 5090 | 32 GB GDDR7 [S13]; live purchasable price not verified | Larger/faster GPU tier to benchmark later; not an MVP requirement |
| Apple Silicon Mac with 64 GB unified memory | Current Mac mini M5 Pro configurations offer up to 64 GB; base Pro pricing does not price the 64 GB build [S14] | Compact large-memory alternative; benchmark selected MLX/Metal runtime and sustained performance; 16 GB laptop is not equivalent |
| NVIDIA DGX Spark | 128 GB unified memory, 273 GB/s bandwidth, 4 TB SSD, 140 W GB10 TDP [S15] | Large-memory local AI workstation, not evidence of a particular completion speed |
| DGX Spark price | Official February 2026 notice increased Founders Edition MSRP from $3,999 to $4,699 [S16] | Do not use old launch prices as a current buying quote |
| Jetson Orin Nano Super dev kit | NVIDIA lists $249, 8 GB shared LPDDR5, up to 67 INT8 TOPS and 7–25 W [S22] | Embedded camera/robot-side inference; add storage/camera/enclosure/power items as needed; not the first main coding purchase |
| Raspberry Pi AI HAT+ 2 | Current product page $200; Hailo-10H, 8 GB onboard memory, 40 INT4 TOPS [S23] | Selected edge LLM/VLM/vision tasks on a separately required Pi 5; launch article's $130 is stale relative to current listing |
| Older AI HAT+ / Coral Edge TPU | Different inference/model/compiler support; Coral expects supported quantized TensorFlow Lite models [S23,S24] | Useful task-specific accelerators; not arbitrary CUDA or general coding-model replacements |

TOPS figures using different numeric precision/sparsity are not directly comparable, and do not tell you agent reliability, context capacity or tokens/second. Size models by accessible memory, bandwidth, supported operators/runtime, context, concurrency and useful task throughput. A neural accelerator in a PC is not automatically used by Ollama or every downloaded model.

## Purchase gates and ongoing costs

First measure: successful small coding jobs, tool-call correctness, false completion, peak memory, time to first token, end-to-end task latency, queue wait while a user asks Haven a question, browser/test load, thermal behavior and free disk. Purchase for a named bottleneck: insufficient memory, poor latency, availability, or noisy/power-hungry shared operation. Do not replace all hardware at once.

For energy planning only, 20 W average for a year is 175.2 kWh, while 150 W average is 1,314 kWh. At an illustrative $0.25/kWh those are $43.80 and $328.50/year. These are arithmetic scenarios, not measured host draw or the operator's tariff. TDP, PSU rating and average wall power are different. Local inference avoids a per-request hosted invoice but is not economically free.
