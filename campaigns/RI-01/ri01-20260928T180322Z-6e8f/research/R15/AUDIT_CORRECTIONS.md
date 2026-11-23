# Immutable prework correction A02

This file supersedes only the statement in R15-AUDIT/SOURCE_AUDIT.md A02 that application phases stop “in reverse order,” and the corresponding shorthand in initial R15 drafting. The original prework bytes remain unchanged, SHA256 0c09786e2c7ddaf7275840c924218f8b819b9f047d7234937f2eeb882f0a2b74.

Actual pinned src/app/application.js lines1–3 declare START_ORDER scene, controls, data, tools and STOP_ORDER tools, controls, data, scene. This is deliberately not strict phase reversal: controls cancel restoration while data and viewer still exist. Per-phase registered cleanup is LIFO; that does not change phase ordering. Exact source SHA256 69300438ffefd2ed7c243c77ff7e9f25f60bd3bc2ffe1a051aeb4926450da9bd; Git blob b9c37a8d229f61e119f0a3ae76fa620f0bb1e1a6 at https://github.com/erpzz/gods-eye-view/blob/81eb44340d90feda5b5283438f6e5fdad5cabbdd/src/app/application.js.

Actual independent reviewer /root/ri01_code_review identified this via root relay before freeze; the author re-read the source declaration and corrected GEV_AUDIT. No application/test ran and no general teardown-completion guarantee is introduced. Future WP-R15-0 lifecycle proof must preserve this ordering. This correction is submitted with the composite for independent verification, not self-acceptance.
