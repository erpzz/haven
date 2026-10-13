# Ukraine Civilian Cyber Defense — Work Mode Handoffs

**Owner:** Haven project. **Source of truth:** [draft PR #30](https://github.com/erpzz/haven/pull/30). **Updated:** 2026-10-13 UTC.

## Operating assumptions
- Defend Ukrainian civilians, independent media, NGOs, hospitals, and other expressly authorized beneficiaries using auditable public-source engineering.
- Do **not** claim to represent CERT-UA, DSLU or a beneficiary. Do not contact or access a third party's systems without explicit written authorization from the actual owner.
- Work against published advisory data and local synthetic inputs by default. Never probe suspected command-and-control infrastructure, run DDoS, exploit/disable servers, seize accounts, post private threat evidence to GitHub, or autodeploy unreviewed blocks.
- Prioritize **delivered value** (reviewed PRs, reproducible checks, partner-scoped changes, accepted volunteer issues) rather than hours researched, speculative attribution, or synthetic task counts.
- Keep personal/employer resources and credentials separate from this project.
- External correspondence: only truthful, addressed to verified public organizational contacts, with evidence and precise maturity claims. Avoid repetitive unsolicited follow-ups or bulk reporting.

## Current facts / do not redo
- Github: `erpzz/haven`, branch `research/ukraine-civilian-cyber-defense-20261012`, [draft PR #30](https://github.com/erpzz/haven/pull/30). Main is unchanged.
- Source includes Windows read-only scheduled-task export, offline Python triage, official CERT-UA RSS advisory monitor, manual IOC-review gate and four Defender Advanced Hunting queries.
- Local Python tests passed before PR. GitHub Actions PR check **run #7** passed following a fix for the canonical CERT-UA `/article/<id>` shape. Check latest CI again before merge.
- The public `https://cert.gov.ua/api/articles/rss` feed was fetched through a public web content tool; it includes official `https://cert.gov.ua/article/<id>` links, including `6319983`. That does **not** validate running the actual Python HTTPS fetch in GitHub Actions.
- An initial email offering this work for review was already sent to `dslua@dslua.org`; **avoid duplicate outreach**. No partner acceptance/deployment is known.
- An independent ChatGPT daily condition watch has been created for noteworthy Ukrainian civilian cybersecurity developments; it does not modify the repository automatically.

## Work Thread A — Engineering release and validation (Work + Codex)
**Goal:** move the existing package from preliminary PR into demonstrably usable, safe civilian defensive tooling.
1. Read every PR file and GitHub CI result; build a clear risks/defects list.
2. Verify the real CERT-UA RSS ingest via permitted HTTPS in a controlled environment; document the actual format and dates; preserve source provenance.
3. Validate the PowerShell exporter on an authorized disposable Windows VM; gather task metadata only, no secrets or arbitrary scripts.
4. Review KQL against current Microsoft Defender Advanced Hunting schema. Where tenant access isn't authorized, lint/test syntactically and mark operational validation pending.
5. Add security regression tests (CSV formula injection, malicious feed text, malformed state, safe path handling) and tighten fail-closed controls.
6. Commit changes on the PR branch, run tests, and publish exact evidence. Leave PR in draft until unresolved risks and review gates are satisfied.

**Exit criteria:** green CI on latest head; reproducible validations; written limitation register; no secret leakage; accurate source and compatibility claims. No autonomous merge without review.

## Work Thread B — Partner-requested delivery (Work cloud browser + GitHub + Gmail)
**Goal:** find a real Ukrainian civilian defender who requests or accepts the work.
1. Check public authorized contact and volunteer openings at DSLU, CyberPeace Builders, eQualitie, humanitarian security NGOs.
2. Track outreach status; check for an actual reply to the single DSLU message before any follow-up.
3. Seek explicit, written scope for requests involving an organization's systems or data, and verify recipient legitimacy.
4. Pick the highest-value narrowly-scoped request; implement it as a PR with tests, usage instructions, and source-linked provenance.
5. If no partner responds, contribute to a directly relevant, actively maintained security OSS repository with current issues and maintainer guidance; do not claim an unsolicited PR was accepted.

**Exit criteria:** at least one independently reviewable deliverable plus an honest partner status: proposed / submitted / reviewed / accepted / deployed. Don't conflate them.

## Work Thread C — Preventive infrastructure protection (Work + research + coding)
**Goal:** improve ability of authorized Ukrainian administrators to act **before** harm happens.
1. Use primary-source CERT-UA advisories to build a small library of defensive controls: MFA/session guidance, phishing-related detections, Windows persistence checks, backup/recovery verification, narrowly scoped validated IOCs.
2. Where malicious infrastructure is documented, create provider-ready **evidence packages for human review**: public source, timestamps, scope, ownership uncertainty, expiry and collateral-damage cautions. Do not visit malicious hosts or send abuse complaints based on unverified claims.
3. Produce portable deployment instructions with rollback for Entra/M365/Defender, Windows and NGO web hosting, scoped to approved tenant/network owners.
4. Only approved defenders deploy protections; never run attacks, unauthorized scans or destructive operations.

**Exit criteria:** reusable defensive outputs, exact source citations, tested non-destructive behavior, clear authorization boundary.

## Coordination
Use one GitHub issue or PR comment for factual progress with links to evidence, decisions and blockers. Work threads should not edit the same files concurrently without branching/coordination. Output each completed change, reviewer-needed item, and operational limitation separately. Never claim background cloud-browser or coding work is still running without a real active task or Work session.
