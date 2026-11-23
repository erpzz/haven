# Source-inspection notes — not a completed integration audit

Recorded 2026-09-28 from the read-only inspection used to prepare R15. No dependency installation, build, provider call or runtime test was performed. These notes preserve that inspection; they are not a fresh survey of every tool listed in the prompt.

## Exact source identities

Owner's fork: [erpzz/gods-eye-view](https://github.com/erpzz/gods-eye-view).
Inspected commit: `81eb44340d90feda5b5283438f6e5fdad5cabbdd`.
Upstream identified by repository metadata: [bilawalsidhu/gods-eye-view](https://github.com/bilawalsidhu/gods-eye-view).

| Source at the pinned fork commit | Inspected scope | Recorded Git blob |
|---|---|---|
| [README.md](https://github.com/erpzz/gods-eye-view/blob/81eb44340d90feda5b5283438f6e5fdad5cabbdd/README.md) | Opening feature/setup sections, lines 1–175 | `88690d52f4ad5581d5b1d0a25171bc2831969238` |
| [LICENSE](https://github.com/erpzz/gods-eye-view/blob/81eb44340d90feda5b5283438f6e5fdad5cabbdd/LICENSE) | Full source/data/asset license notice | `4f01699a2afc703093fcf07181129c3724aae9ff` |
| [package.json](https://github.com/erpzz/gods-eye-view/blob/81eb44340d90feda5b5283438f6e5fdad5cabbdd/package.json) | Manifest and exported entry points | `e48881c6d28de7af1b760cdf52561ddc99cb6916` |
| [docs/APPLICATION.md](https://github.com/erpzz/gods-eye-view/blob/81eb44340d90feda5b5283438f6e5fdad5cabbdd/docs/APPLICATION.md) | Application composition, lifecycle, search, sources and voice seams | `deafe916892ee13e1cbf8542a1a2eeb38329b1bf` |
| [src/app/application.js](https://github.com/erpzz/gods-eye-view/blob/81eb44340d90feda5b5283438f6e5fdad5cabbdd/src/app/application.js) | Full lifecycle controller source | `b9c37a8d229f61e119f0a3ae76fa620f0bb1e1a6` |
| [SECURITY.md](https://github.com/erpzz/gods-eye-view/blob/81eb44340d90feda5b5283438f6e5fdad5cabbdd/SECURITY.md) | Key handling, proxy boundaries, exposure and responsible-use sections | `718c43778156e172abbe981962468520fa8a1638` |

## Findings supported by those sources

**Code and data are different licensing subjects.** The LICENSE grants MIT rights over source code but expressly excludes third-party data and models from that grant. The notice lists examples of noncommercial, share-alike and attribution conditions. The exact datasets, assets and provider terms need their own eligibility review; neither the fork nor this brief changes their license.

**Presentation is not measurement.** The inspected README calls traffic simulated and describes sensor-like visual styles. Any Observatory design must retain the distinction between a rendered style, an interpolated/estimated representation and an actual observation. The README also describes public feeds and scene features; those descriptions have not been independently runtime-tested here.

**Composition seams exist, with limits.** The manifest exposes source/application/UI/voice modules and marks the package private. APPLICATION.md describes explicit construction, startup and teardown, but also a page-scoped standalone composition and one-application-per-page limitation. Exported paths do not establish a published package, a stable API, arbitrary multi-viewer use or a qualified embedding.

**A visual front end is not household authority.** SECURITY.md positions GEV as a local public-data exploration tool, not a hardened multi-user service, and explains its development server/key-broker assumptions. Preserve private Haven context and action authority behind separately reviewed boundaries. Do not attach real household data to the default app merely because it runs locally.

## Work still required by R15A/C/D

Read the exact lockfile, relevant tests and layer/provider implementation; determine build consumption from the source-pinned fork; inspect Director imports/sharing and model/tool seams; verify the current complete per-source data terms; compare current upstream changes; evaluate concrete authentication/egress/cost requirements. No security, license compatibility, performance or production-readiness pass is recorded here.

The alternative tools and source URLs in the master prompt are candidates for the researcher to verify. This note does not independently certify their current pricing, licenses, API behavior, support or suitability. No copied third-party datasets or assets are added to Haven by this packet.
