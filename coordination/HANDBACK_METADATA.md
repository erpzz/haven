# Metadata required on every new handback

Use the original handoff headings from `baseline/cumulative-v1.0/agents/HANDOFF_TEMPLATE.md`; add this compact preamble.

- Thread ID / ownership ID / task issue
- Repository and actual base commit
- Read inputs: exact path, revision and SHA-256 where available
- Owner-authorized output paths and new version
- Work actually performed versus proposed
- Dependencies received / still pending
- Requirements and contract change IDs retained
- Publication classification: public-safe or withheld private evidence
- Tests: exact command, environment, expected/actual, artifact reference; NOT_EXECUTED when only proposed
- Review disposition requested; no self-approval
- Verified commit/PR links, or NOT_UPLOADED

A one-page integration summary must identify decisions, affected interfaces, conflicts, the smallest next package and its stop gate. Retain raw sources and negative findings in the versioned packet, not the main-thread context.
