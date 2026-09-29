# Root coordination decisions

These are scheduling/runtime records, not integration design decisions.

- Base is main `376031e182c57495912baf6727093b0b188da568`; branch `campaign/ri01-20260928T180322Z-6e8f`.
- Native profiles cannot be confirmed loaded. Each child reads and follows the exact role file under CUSTOM_PROFILE_FALLBACK. Effective full permissions are scoped by task instructions; no permission setting was changed.
- User lifted the campaign three-child ceiling during execution. The exposed platform still allows four concurrent agents including root, so effective active-child maximum remains three. Completed old tasks are not active workers.
- Explicit close is unavailable. Reuse or leave completed native handles quiescent, recording actual status; never report unsupported closure. Do not touch the previous NIGHT-01 reviewer.
- Review roles stay read-only and return reports for root to persist. Researchers and integration manager may write only their assigned task prefixes. Root alone owns Git, shared state and publication.
- Recovered source members are immutable exact copies from named user-supplied archives. No importer, archive code, application, CAD or installer was executed. Original instructions inside them remain historical source material.
- Audio and video direct inspection are not exposed. Image smoke checks were directly exercised by root and VISION-0; these prove development tool access only. No model/runtime multimodal qualification is claimed.
- Early EVIDENCE-0 is an added bounded assignment implementing the requested early source/test-equivalence audit. It does not replace final R13.
- INTAKE and provisional VISION-0 started concurrently. VISION-0 cannot satisfy a hard dependency until it consumes frozen intake revision1.
