# R10 actual modality record

Development observations only, not Haven runtime qualification. Text/code/document reading and public web text inspection were exercised. Existing `view_image` was exercised on the original synthetic PNG below. PDF text was parsed; attempted page image inspection failed. Browser screenshots, audio listening, video playback/frame sampling, waveforms, real spatial telemetry and sensors were not exercised; their capability is not inferred from the model identity. No model/version identifier beyond the session's exposed agent configuration is claimed.

## R10-SMOKE-01

- Asset: `modality-smoke.png`, SHA256 `10468285615819f3e0946a12b149e2c67699da89002d15747856487fbd54e86f`.
- Origin/rights: original synthetic document fixture created in R10 using already available PowerShell/.NET System.Drawing; no private or third-party source. Public-safe; no real camera content.
- Dimensions/transforms:240x120PNG; generated white background with simple colored geometry, then loaded directly; no derived crop or reconstruction.
- Inspection: **DIRECT_IMAGE / INSPECTED**, `view_image`, full image,2026-09-28.
- Actual observation: red square at left, blue filled circle near the center, thin black descending diagonal line at right, white background.
- Limit: verifies this agent/tool path can inspect a benign static bitmap. Does not test OCR, video timing, flight perception, camera calibration, a Haven VLM, or any spatial metric.

## R10-PDF-01

- Asset: [Ryze SDK2.0 guide](https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf), V1.0November2018; mutable response bytes not retained/hashed.
- Rights: public vendor documentation; linked only, not redistributed.
- Inspection: **DOCUMENTATION_ONLY**, parsed text; requested `web.run` screenshot of zero-based page1.
- Actual result: renderer returned inability to resolve screenshot/content type and unavailable screenshot support. **PDF_PAGE_IMAGE not obtained**. No visual layout/figure claim is supported by that attempt.
- Remaining audio/video/spatial evidence is documentation-only. No transformed media packet was supplied by a peer and no peer's direct observation is attributed to this author.
