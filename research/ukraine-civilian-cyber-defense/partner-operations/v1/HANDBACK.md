# Specialist handback — Ukraine civilian cyber defense partner operations v1

- Thread / task: Partner Operations / WORK_HANDOFF.md Thread B / PR #30.
- Repository: erpzz/haven.
- Main observed: `4a73a55bfc263d53b8e657403a693004e2871ef6`.
- Input PR head: `50df466c776cc535a37e413bb4480b4e1257a344`.
- Handoff blob: `39751ff62552ded55c8872dd488da7aaffba7f62`.
- Observed at: 2026-10-13T03:36:13Z (12 October evening in New York).
- Owner-authorized output: research/ukraine-civilian-cyber-defense/partner-operations/v1/.
- Classification: public-safe engineering and status records. Private mailbox identifiers/content withheld.
- Requirements/contracts: no Haven REQ/AT/EX, shared schema, M0, NIGHT-01 or other research ownership changes.
- Disposition requested: maintainer review; no self-approval.

## Actual work performed versus proposed

| Item | Actual status | Evidence / next gate |
|---|---|---|
| DSLU initial outreach | SENT previously; no reply found in mailbox search | One sent message and one older unsent draft found; neither duplicated, changed nor deleted |
| eQualitie dComms request | VERIFIED open issue, active repository | [Issue #2](https://github.com/equalitie/dcomms-docker-compose/issues/2); main a9380cae07cf11e0343c2a719689937fd1ae80a9; most recent repository push 2026-09-22 |
| dComms patch | COMPLETED locally, SUBMITTED by email | Applicable diff and send details below; upstream GitHub comment attempt failed with integration 403 |
| eQualitie review / acceptance / deployment | UNKNOWN / PENDING | No acknowledgement or review received during this session; sending is not acceptance |
| CyberPeace Builders volunteer route | VERIFIED available; NOT_SUBMITTED | Corporate identity and employer vetting required; not appropriate to enroll an independent AI agent as an employee |
| Haven existing CI | EXECUTED_PASS, observed at input head | [Run #11](https://github.com/erpzz/haven/actions/runs/38341357840), 26 tests; live watch job SKIPPED |
| Toolkit endpoint/live-feed qualification | PENDING | Windows, actual Python HTTPS feed fetch, Defender tenant execution not established by this operations work |

### Measurable outcomes

- 1 actual external engineering submission: an attached documentation patch sent to eQualitie.
- 1 concrete maintainer-created request addressed in part: dComms Compose issue #2.
- 0 successfully posted upstream GitHub comments or upstream PRs; the attempted comment was rejected.
- 0 external reviews, acceptances or deployments confirmed.
- 0 duplicate DSLU emails.
- 0 beneficiary systems or suspected malicious hosts accessed.

## Decisions

Use dComms Compose, not the archived Swarm repository linked on eQualitie's portfolio.
The Swarm README points to Compose; live GitHub metadata confirms Compose is
unarchived and recently updated. Do not send a patch to the archived project.

Address the existing issue's admin/token onboarding portion with a documentation
patch first. Installer option changes, email configuration and encryption options
remain outside this partial contribution and need maintainer direction.

Use eQualitie's verified official `info@equalitie.org` address for this one
submission because the GitHub integration returned `Resource not accessible by
integration` (403). No browser workaround was attempted.

Haven is currently PRIVATE according to live repository metadata. Existing DSLU
email described its PR as public source, but outside access cannot be assumed.
This discrepancy is recorded here; repository visibility was not changed and no
immediate duplicate follow-up was sent. Future partner submissions should attach
reviewable files or use an explicitly approved accessible publication route.
The Haven repository also has no license shown in its metadata; avoid claiming a
public open-source release of the original toolkit without a licensing decision.

## Evidence

### Existing outreach checked

Mailbox query: `in:anywhere (from:dslua.org OR to:dslua.org)`.
The sent thread was read: one outgoing message, no incoming response visible.
A separate older draft remains unsent. No delivery/read receipt or partner review
is inferred from the SENT label.

eQualitie correspondence search returned no prior matches before submission.

### Current volunteer and contribution sources

- [DSLU about/contact](https://dslua.org/about/): official Ukrainian civil-society security mission and public contact.
- [CyberPeace Builders](https://builders.protect.ngo/volunteers): currently offers bounded NGO tasks; requires private-company employment, one year of cybersecurity experience, probation completion, employer vetting and Code of Conduct.
- [Corporate registration criteria](https://aware.cyberpeaceinstitute.org/join-our-team-of-volunteers-0): corporate email required; ordinary personal-email registration is not the documented route.
- [eQualitie dComms portfolio](https://equalitie.org/portfolio/decentralized-communications/): describes civilian communications resilience and links the older Swarm repository.
- [Active Compose repository](https://github.com/equalitie/dcomms-docker-compose): unarchived; merged CryptPad contribution on 2026-09-22; no open PRs observed.
- [Request #2](https://github.com/equalitie/dcomms-docker-compose/issues/2): open, unlocked; creator aphick; registration tokens and admin creation explicitly requested. No existing comments observed.
- [Verified eQualitie contact](https://equalitie.org/contact-us/): info@equalitie.org.
- [Synapse Admin API](https://element-hq.github.io/synapse/latest/usage/administration/admin_api/index.html).
- [Registration-token API](https://element-hq.github.io/synapse/latest/usage/administration/admin_api/registration_tokens.html).
- [Shared-secret registration](https://element-hq.github.io/synapse/latest/usage/configuration/config_documentation.html#registration_shared_secret).
- [curl manual](https://curl.se/docs/manpage.html).

All current-source checks performed 2026-10-13 UTC.
The eQualitie federated-web developer job search result returned 404 when opened:
it is NOT counted as an active opening.

### Contribution provenance

Upstream base: `a9380cae07cf11e0343c2a719689937fd1ae80a9`.
Files read: README.md, install.sh, docs/synapse.md,
conf/synapse/README.md, conf/compose/docker-compose.yml,
conf/compose/synapse.docker-compose.yml. No CONTRIBUTING.md or AGENTS.md appeared
in the recursive repository tree. No open PR duplicates or issue comments found.

The installer sets token-gated registration. Compose defines service `synapse`
and publishes its client listener on 127.0.0.1:8008. The patch supplies the exact
service command and a one-use/24-hour invitation example, protects the
administrator token from argv/history, rejects curl-config control characters,
avoids proxies/redirects, and explains token revocation and MAS differences.
Bootstrap flags checked against the Synapse v1.140.0 CLI source, which the
installer uses for generation; Compose's runtime image is v1.160.0. That runtime
was not executed or certified.

## Interface changes

Documentation-only patch to upstream docs/synapse.md. No API, installer defaults,
database, infrastructure, repository visibility or original Haven code changed.
No scope granted for beneficiary infrastructure or private data.

## Acceptance

| Check | Expected | Actual |
|---|---|---|
| `bash -n` on both Bash blocks | Syntax valid | PASS |
| `git apply --check` against fetched base documentation | Applicable diff | PASS |
| Apply diff and compare resulting bytes | Exact proposed file | PASS |
| Stubbed curl, synthetic admin token | No token in argv/stdout/stderr | PASS |
| Stubbed request payload | One use, approximately 24h future milliseconds | PASS |
| Stubbed request target | Fixed HTTP loopback, curlrc ignored, no redirects | PASS |
| Empty / quote / backslash / space token inputs | Exit before curl | PASS (4 cases) |
| Stubbed curl failure | Nonzero status propagated | PASS (22) |
| Docker/Synapse real admin creation and token registration | Working end-to-end on disposable authorized host | NOT_EXECUTED |
| Independent maintainer review | External review evidence | PENDING |

Environment: Linux scratch workspace, Python3 and Bash; Docker unavailable.
No real passwords, admin tokens, registrations or live API requests were used.
Local checks qualify the snippet's construction, not production behavior.

Patch SHA-256:
`89cbc1fba03e6353fda7c0b7e3a2b3ac3dbaea5fe6c080a7271dcb614ec5dc2d`.

## Submission record

- Recipient: info@equalitie.org, verified on official contact page.
- Channel: Gmail, one outgoing email, SENT label verified by reading the sent thread.
- Subject: dComms issue #2 — admin / finite-invitation documentation patch for review.
- Sent: 2026-10-13T03:35:50Z.
- Attachment: dcomms-synapse-admin-registration.patch, text/x-diff, 5338 bytes.
- Body disclosed AI assistance, independent status, partial issue scope, lack of
  Docker/live validation and failed GitHub-comment attempt; requested review,
  current bounded work and their AI-contribution policy.
- Reviewed: not observed. Accepted: not observed. Deployed: not observed.

No unnecessary same-day follow-up is scheduled or sent.

## Risks and open questions

- Does eQualitie accept this partial documentation contribution or prefer installer work?
- Their AI-contribution policy is unknown; the submission explicitly asks.
- A maintainer or authorized disposable VM must verify real Synapse behavior.
- Outside reviewers cannot assume access to private Haven PR links.
- Human/corporate eligibility must be satisfied for CyberPeace Builders; no employer account, identity or resources were used.
- The automation/watch described in the handoff was not changed or represented as this agent running in the background.
- A repeated Stripe Directory shell fetch was rejected by automatic approval
  review as unrelated/untrusted; it was stopped. Direct official-source checks
  and the authorized contribution were completed without bypassing that action.

## Next package

Check the existing DSLU and eQualitie threads in a future active session before
sending anything. On a genuine maintainer response, record the requested scope,
acceptance criteria and preferred contribution route; implement the selected
request on an owned branch and submit a PR when the integration permits it.
If no response, retain this submission as pending. Do not repeatedly resend or
claim it accepted. Stop this package at the documented review gate.
