# R01 primary-source register

Verified 2026-09-28. These are current public documentation findings, not Haven implementation or experimental results. No third-party media copied. S01–S07 support accessibility/platform UX choices; numerical thresholds, scenario behaviors and budget limits in REPORT are original design proposals. Links point to primary publishers. Page illustrations were not visually inspected. Exact content hashes for dynamic web pages were not frozen; reverify at implementation gate.

## S01

**W3C, Web Content Accessibility Guidelines 2.2**, Recommendation 12 December 2024. https://www.w3.org/TR/2024/REC-WCAG22-20241212/

Access: web search/open, DOCUMENTATION_ONLY. Relevant sections: keyboard 2.1.1, focus 2.4.7/2.4.11, dragging 2.5.7, target size 2.5.8, accessible authentication 3.3.8, reflow 1.4.10, status 4.1.3. Findings: testable accessibility criteria; minimum target size has enumerated exceptions; status must be programmatically determinable without forced focus. Effect: REPORT D4 and manual evaluation targets. Limit: WCAG does not cover every person's needs, and reading it establishes no product conformance. The 44-CSS-pixel preference and pilot timing targets are R01 choices, not required WCAG AA thresholds.

## S02

**Apple, Human Interface Guidelines: Notifications**, current page, publication version not stated. https://developer.apple.com/design/human-interface-guidelines/notifications

Access: official indexed full text via web search (returned URL carried `?changes=_4`); DOCUMENTATION_ONLY. Sections: Best practices, Content, watchOS short/long looks. Findings: keep notifications useful/concise; avoid repeated notifications for the same event and sensitive content; foreground changes need not interrupt. Watch short looks should not be the only essential communication. Effect: D2 caps/digest and D3 generic preview/private surfaces. Limit: behavioral guidance, not API/entitlement, guaranteed delivery or Haven watchOS capability. Proposed numeric caps are not Apple's numbers.

## S03

**W3C WAI, Cognitive Accessibility Design Pattern: Limit Interruptions**, source content 29 April 2021, interface January 2022; current page checked. https://www.w3.org/WAI/WCAG2/supplemental/patterns/o5p01-minimal-interruptions/

Access: web open full text, DOCUMENTATION_ONLY. Findings: easy interruption control, pause and selectable notification modes help people focus; includes changes in shared content as potential interruptions. Effect: D2 independent per-user pause/mute/view-later, no focus-stealing replay updates. Limit: supplemental guidance is explicitly not itself a WCAG conformance requirement; no Haven user-study evidence. A guessed URL for a different pattern returned an error and supplied no evidence.

## S04

**Apple UserNotifications, Asking permission to use notifications**, current documentation; metadataVersion 0.1.0 is document metadata, not an OS/API release. https://developer.apple.com/documentation/usernotifications/asking-permission-to-use-notifications

Official text endpoint: https://developer.apple.com/documentation/usernotifications/asking-permission-to-use-notifications.md

Access: HTML exposed linked Markdown; web renderer rejected its text/markdown content type. Read exact official Markdown using PowerShell Invoke-WebRequest; no code example executed. DOCUMENTATION_ONLY. Findings: contextual permission request, first authorization response recorded, current notification settings may change and should be checked. Provisional quiet authorization exists but is not selected as Haven's default. Effect: ask when a requested reminder has clear value, respect denial, check state rather than repeatedly prompt. Limit: authorization is neither successful scheduling nor delivery/acknowledgement; actual platform/device versions still require R04 review.

## S05

**Apple UserNotifications, Scheduling a notification locally from your app**, current documentation; no immutable OS release supplied. https://developer.apple.com/documentation/usernotifications/scheduling-a-notification-locally-from-your-app

Official text endpoint: https://developer.apple.com/documentation/usernotifications/scheduling-a-notification-locally-from-your-app.md

Access: official Markdown via Invoke-WebRequest after linked web fetch content-type failure; DOCUMENTATION_ONLY. Findings: app registers content and trigger in a notification request; system handles eligible local notification delivery when app is background/not running; pending requests can be cancelled by identifier. Effect: S3 separates local/native schedule registration from PC availability and human receipt; cancellation references exact task/request. Limit: no proof of Haven native implementation, exact delivery timing, DST semantics, cross-device sync or successful remote cancellation. No Swift code ran.

## S06

**W3C WAI, Complex Images**, updated 8 April 2026. https://www.w3.org/WAI/tutorials/images/complex/

Access: web open full text, DOCUMENTATION_ONLY; examples/images not viewed. Findings: complex graphics/maps need brief identification and a fuller textual alternative; structured descriptions can expose values/relationships. Effect: S4 object list and S5 map/event table, accessible source/uncertainty exploration. Limit: guidance does not validate correctness of AI descriptions, vision models or navigation claims.

## S07

**Apple AVFAudio, Handling audio interruptions**, current documentation; no immutable OS release supplied. https://developer.apple.com/documentation/avfaudio/handling-audio-interruptions

Official text endpoint: https://developer.apple.com/documentation/avfaudio/handling-audio-interruptions.md

Access: official linked Markdown via Invoke-WebRequest; DOCUMENTATION_ONLY. Findings: audio session interruption begin/end notifications and conditional resume information support app-specific handling. Effect: interruption state is explicit; resume requires current audience/turn eligibility and no cancellation, with a local stop control. Limit: this is not proof of ASR/barge-in timing, voice identity, guaranteed cutoff, microphone access, or Haven speech implementation. No API code executed.

## Negative and excluded evidence

Apple accessibility HIG HTML returned only a JavaScript requirement. Detailed accessibility criteria rely on S01/S03/S06, not an unread HIG. Android notification results and third-party/reddit pages surfaced in search but are not used for design claims. No current product price, hardware compatibility, sensor model, medical interpretation or model leaderboard was claimed. Framework/runtime selection remains with R02/MM/R04 owners; no benchmark duplicated from unreviewed sources.

## Local modality receipt

Campaign-owned original `inputs/runtime/synthetic-vision-probe.png`, SHA256 `12a1ed92fe078247281f01f05edbde362110a562cd759e2f8f7f7244bd66e837`. Author `/root/ri01_daily` directly viewed whole asset using view_image; no transformations. Observed light background, red rectangle left and blue circle right, no visible text. DIRECT_IMAGE/INSPECTED development tool smoke check only. Exact pixel metrology, runtime perception and every proposed media/user test NOT_EXECUTED. No claim of listening to audio or viewing continuous video.
