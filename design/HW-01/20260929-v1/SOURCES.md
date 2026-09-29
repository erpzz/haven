# Source register and limits

Checked 2026-09-29. Public primary documentation and direct seller/manufacturer price observations. No product purchase, local performance reproduction, complete dependency audit or safety certification. Mutable tags, version-specific API behavior, current prices and stock must be pinned/rechecked before implementation or purchase. Search snippets were used only where identified. Broad product-carousel queries returned no usable result; no product cards, stock guarantees or fabricated quotes were constructed.

## Software and models

- **S01 OpenCode providers:** https://opencode.ai/docs/providers/ — official local Ollama configuration and 16–32K troubleshooting suggestion. Current v2 documentation also exists; pin installed release before copying configuration.
- **S02 OpenCode permissions:** https://opencode.ai/docs/permissions/ — allow/ask/deny and per-agent rules. Application permissions are not hardened OS isolation.
- **S03 OpenCode server:** https://opencode.ai/docs/server/ — headless HTTP/OpenAPI, loopback default and basic authentication. API presence does not prove Haven integration.
- **S04 OpenCode MCP:** https://opencode.ai/docs/mcp-servers/ — tool integration and explicit context-overhead warning.
- **S05 Ollama OpenCode integration:** https://docs.ollama.com/integrations/opencode — states 64K+ context; preserve the mismatch with S01 rather than silently asserting a universal minimum.
- **S06 OpenHands local LLM guidance:** https://docs.openhands.dev/openhands/usage/llms/local-llms — May 21 2026 recommendation Qwen3.6-35B-A3B, 24 GB GPU or 64 GB Apple memory guidance; context and exact setup remain workload-dependent.
- **S07 OpenHands SDK:** https://docs.openhands.dev/sdk — software-agent execution/tool platform, alternative rather than selected deployment.
- **S08 Aider/Ollama:** https://aider.chat/docs/llms/ollama.html — local coding baseline; no measured performance on operator hardware.
- **S09 Ollama FAQ:** https://docs.ollama.com/faq — loaded-model versus request concurrency, cache/context memory, GPU placement and local service configuration. A selected documentation section is not verification of all runtime versions.
- **S10 Ollama Qwen3.5 registry:** https://ollama.com/library/qwen3.5 — current standard tag file sizes around 3.4 GB (4B) and 6.6 GB (9B); these are not complete runtime memory requirements or benchmark outcomes.
- **S11 Ollama Qwen3-Coder 30B:** https://ollama.com/library/qwen3-coder:30b — 19 GB Q4_K_M listing, 30.5B total / roughly 3.3B activated per token; mutable tag requires full artifact pin before use.
- **S21 Hermes toolsets:** https://hermes-agent.nousresearch.com/docs/user-guide/features/tools/ — optional framework/tool-catalogue reference, not a replacement for Haven's coordinator.
- **S19 Docker Engine security:** https://docs.docker.com/engine/security/ — daemon control/host mounts and configuration risks; containers are not an absolute security boundary.

## Hardware and price observations

- **S12 NVIDIA RTX 3090/3090 Ti:** https://www.nvidia.com/en-us/geforce/graphics-cards/30-series/rtx-3090-3090ti/ — reference specifications including 24 GB memory and 3090 FE power, connectors and dimensions. Do not confuse 3090 Ti values with 3090 values. No used listing inspected.
- **S13 NVIDIA RTX 5090:** https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/ — 32 GB GDDR7 verified; parsed page showed a price placeholder, so no live purchase price is claimed.
- **S14 Apple Mac mini:** https://www.apple.com/mac-mini/specs/ and https://www.apple.com/shop/buy-mac/mac-mini — current M6/M5 Pro listing; M5 Pro up to 64 GB. A base price is not a configured 64 GB price; checkout not performed.
- **S15 NVIDIA DGX Spark specs:** https://www.nvidia.com/en-us/products/workstations/dgx-spark/ — 128 GB memory, 273 GB/s, 4 TB storage, GB10 TDP; vendor capacity claims do not establish interactive throughput.
- **S16 NVIDIA price change notice:** https://forums.developer.nvidia.com/t/2-23-2026-price-change-announcement/361713 — official February 2026 announcement: Founders Edition MSRP $3,999 → $4,699. This is dated MSRP evidence, not a guaranteed current retailer cart.
- **S17 Logitech C920s specs:** https://www.logitech.com/en-us/shop/p/c920s-pro-hd-webcam.960-001257 ; direct retailer price observation https://www.lg.com/us/computer-accessories/lg-960001257-webcam — $59.99 observed in indexed LG seller page; prices/stock can change. No compatibility/runtime test performed.
- **S18 Seeed XIAO ESP32S3 Sense:** https://www.seeedstudio.com/XIAO-ESP32S3-Sense-p-5639.html — manufacturer indexed listing $13.99, SKU 113991115; small camera/mic/MCU board, not a large local model host. Complete experiment needs accessories.
- **S20 Samsung T7 price examples:** https://www.bestbuy.com/product/samsung-t7-1tb-external-usb-3-2-gen-2-portable-ssd-with-hardware-encryption-titan-gray/J3ZYGCQG8H — indexed price observations differed around $229.99–$249.99. Samsung's own where-to-buy page showed an inconsistent lower direct figure; not used as a guaranteed current quote. Storage allowance is not tied to buying this premium model.
- **S22 NVIDIA Jetson Orin Nano Super:** https://www.nvidia.com/en-sg/autonomous-machines/embedded-systems/jetson-orin/nano-super-developer-kit/ — official page states $249 USD, 8 GB LPDDR5, 67 INT8 TOPS, 7–25 W. Region/stock and included accessories require confirmation.
- **S23 Raspberry Pi AI HAT+ 2:** https://www.raspberrypi.com/products/ai-hat-plus-2/ and https://www.raspberrypi.com/documentation/accessories/ai-hat-plus.html — current product page $200, Hailo-10H with 8 GB dedicated RAM and 40 INT4 TOPS; separate Pi 5 required. The January launch article says $130; do not use that as today's price.
- **S24 Coral model restrictions:** https://coral.ai/docs/edgetpu/models-intro/ — supported quantized TensorFlow Lite compilation/operator requirements; not arbitrary CUDA/LLM compatibility.
- **S25 UPS sizing example:** https://www.cyberpowersystems.com/cross-reference/internet900u/ — ST900U example 900 VA/500 W. Watt capacity and load-dependent runtime matter; do not treat VA as W or assume this is enough for the proposed AI workstation.

## Haven references

- PRECEDENCE and final I01–I07 contracts at 6bc1c8df1218ceb0e0d8709adee65d1e44634047; research is design evidence, not installation authority.
- IP-01 ROLE_MAP.md at 8e1304caf82c0a889eeaea7691db7b9d7b98c526, blob 849d7b6827a5b3b7f14387887a7a6784b4c7ba5c, read in full for role continuity.
- SI-01 VISION_ANCHORS at cdc32eabe847a6bb5fff1a0f69d7ba5f6b7832d5, retained earlier in this conversation; no changes made here.
- PR #21 observed at faaf8eaacca35548b816722162a15649363b3b1b during this design. Its body still described setup; do not infer runtime completion or inactivity from that stale body. This research did not inspect every current runtime artifact.

## Evidence classification

Source/API availability: documented. Hardware capacity: vendor specification. Operator hardware: reported, not currently probed. Price: dated MSRP, observed seller listing or clearly labeled allowance. Recommended architecture: author proposal. Tool execution, model reliability, memory fit, isolation, latency, deployment and physical/clinical capability: NOT_TESTED by HW-01.
