# Runtime preparation

Native Python 3.12.3 was used to create the clone-local virtual environment. The initial install used published wheels only for the work-package packages plus python-multipart (required for forms); 32 resolved packages are pinned with actual wheel SHA256 values in `labs/ip01/requirements.lock` and URLs in DEPENDENCIES.json. `pip check` passed. This lock records the actual Windows CPython 3.12 wheel selection; cross-platform lock compatibility is not claimed.

Playwright 1.63.0 acquired Chromium 153.0.8010.12 build 1243, headless shell 1243, FFmpeg 1011 and Winldd 1007 through its official distribution, into the clone-local cache. Browser archive sizes reported by the installer total about 311.6 MiB. Total initial Python/browser acquisition is conservatively debited 1 GiB against the 12 GiB ceiling; exact network transfer bytes including metadata are unavailable. Actual runtime storage observed after install was 979,742,337 bytes. No host package, service, firewall or security setting changed.

Installed native Ollama reports version 0.34.4. The exact selected model manifest is absent from the default user models directory. No model call or model download occurred during this preflight. A dedicated owned server/model directory and verified lifecycle remain prerequisites.

Primary documentation retrieved 2026-09-29:

- https://ollama.com/library/qwen2.5vl:3b identifies the intended tag as Q4_K_M, approximately 3.2 GB; a full local manifest/blob digest must replace this mutable-tag description before inference.
- https://docs.ollama.com/faq documents process environment configuration including OLLAMA_NO_CLOUD=1, OLLAMA_MODELS, OLLAMA_CONTEXT_LENGTH, OLLAMA_MAX_LOADED_MODELS and OLLAMA_NUM_PARALLEL. Configuration is not proof of OS egress containment. Only child-process environment is allowed here.
- https://huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct is the upstream checkpoint/license source; the actual downloaded artifact license chain must be pinned before model admission.

The browser-verification skills were read for page-load, screenshot, interactive-element and error checks. Their agent-browser CLI is absent; the package explicitly permits installed Playwright, which will perform these checks without installing an additional browser automation framework. This is an IP-01 browser test, not a Vercel deployment.
