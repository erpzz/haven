# R02 — Integration, retained requirements and future coding packages

**DESIGN_PROPOSAL. No package below has started through this handback.** The Rxx rabbit-hole IDs and Hxx ownership IDs are different registries. Preserve the starter's H00–H12 owners and all 102 requirements; the table below is a change-impact map, not a new scope definition.

## 1. Concrete branch handoffs

| Other branch | Incoming to R02 | Outgoing from R02 | Shared gate / separation |
|---|---|---|---|
| R03 / H04 identity, privacy and authority | Verified principal/device binding, grant revision vectors, audience/purpose policy | Minimal context requirements, cloud egress requests, memory/publication revocation events | H04 owns grants; models/frameworks cannot authenticate or approve |
| R05 / H03 personal tools and scheduling | Scoped calendar/email/file reads, exact write receipts, schedule status | Typed inert action proposal with target/account/recipient/payload/version, distinct cancel target | Timers and delivery survive model failure through separately qualified scheduler behavior; draft ≠ send |
| R04 / H07 wearables; H01 experience | Explicit capture, device/subject identity, sample/capture/receive times, output-device audience | Transcript/scene claims with uncertainty, private-audio publication request, clarification | No arbitrary PC access to native health data; no enrollment or wearer identity inferred from model output |
| R06–R07 / H08 spatial research and H05 sensors | Framed/calibrated observations with uncertainty and evidence origin | Evidence-linked interpretation and one bounded next-measurement proposal | Generative interpretation never becomes measured geometry; movement requires domain approval |
| R08 / H09 engineering and fabrication | Frozen objective, design/measurement lineage, independent evaluation result | Bounded candidate/job proposal and evidence-backed comparison | Designer cannot accept its own part or trigger printer; reuse EX28/N2 rather than recreate |
| R09–R10 / H10 ground robotics and H05 aircraft | Qualified capability snapshots and observed device/action state | Logical template proposal and resource request | Existing M0/M4 unchanged; physical leases/recovery remain domain-owned |
| R11 / H11 communications/emergency | Truthful storage/transfer/destination receipts and readiness facts | Minimal audience-appropriate draft or logistics explanation | Independent help/manual recovery not gated on inference; unknown delivery never reported as dispatch |
| R13 / H06 validation/operations; R12 / H12 research | Protected tests, outcome rubrics, source corrections and release evidence | Model/framework manifests, complete failure/cost traces and bounded research briefs | H06 owns acceptance; H12 reconciles proposed source IDs with canonical registry |

A concrete cross-domain example: A asks which sensor fixture was selected. R02 retrieves A's current project note and only explicitly shared H09 results, not B's private notes. It summarizes the measured result with design/evidence refs. A request to fabricate produces a proposal for H09; an engineering explanation cannot authorize a printer. If a shared measurement is revoked while the answer is queued, the packet and derived draft are invalidated before publication.

A second example: a selected phone image prompts “can we get a better view?” R02 labels the image's capture time and uncertainty and proposes one logical observation template. H05/H08 decide whether the data, device and motion are eligible. A stale aircraft snapshot produces UNKNOWN/unavailable while the independent H03 reminder path continues. Ordinary conversation does not create a flight incident without its separate entry/authorization path.

## 2. Retained requirement coverage

| Existing requirement(s) | R02 disposition / evidence location |
|---|---|
| REQ-CORE-01/02/03/04 | Broader daily/protective/engineering/research scope and distinct tracks retained; M0 untouched; handoff preamble and architecture |
| REQ-CORE-05/06 | Existing hardware first; source hashes and reviewable documentation package; no purchase |
| REQ-AI-01 | Deterministic handlers and readiness independent of models; R02-T03 |
| REQ-AI-02 | Task-qualified/privacy-first cost routing and EX03 expansion; R02-T04 |
| REQ-AI-03 | No change to M4 `qwen2.5vl:3b` or M0–M6 gates |
| REQ-AI-04 | Thin/Hermes/OpenClaw comparison and explicit product/model/runtime distinctions; R02-T08 |
| REQ-AI-05 | One inference lane, per-user queues/budgets and service-time fairness; R02-T07 |
| REQ-AI-06 | Atomic admission, child allocation, unknown reservations and reconciliation; R02-T05 |
| REQ-AI-07 | Evidence bindings, current/unknown states and separate abstention; R02-T04/09 |
| REQ-AI-08 | Local/hosted speech economics, push-to-talk and interruption; R02-T10 |
| REQ-AI-09 | Registry versions/digests, adapter conformance and alias drift; R02-T11 |
| REQ-PRIV-01/02/03/04 | Separate users and explicit sharing/purposes; correction/revocation/restore propagation; C01–C04/C10 and R02-T01/02 |
| REQ-PRIV-05/06/07/08/09 | Audience/device protection, employer-data exclusion, injection controls and honest host-admin limitation |
| REQ-DAILY-01/02/03/04/05/06/07/08/09/10 | Runtime supports H01/H03 daily scope; does not take ownership of scheduling, connector implementation or native clients |
| REQ-WEAR-03/06/07/08 | Capture freshness/consent/audience; native acceptance separate |
| REQ-RF-05/07/08/09 | Semantic inference separated from measurements; origin/frame/calibration preserved; permitted active perception proposal |
| REQ-DRONE-05/06/07/12 | Proposal versus authority, actual/unknown outcomes, independent recovery and baseline preservation |
| REQ-COMMS-05; REQ-EMERG-01/07 | Truthful receipt explanations, independent help and deterministic readiness |
| REQ-ENG-02/03/04/05/06/08/09/10 | Bounded candidate design, provenance, independent acceptance and separately governed fabrication |
| REQ-RESEARCH-01/02/03/04/05/06/07 | Primary evidence/limits, useful runtime jobs versus design threads, holdouts, no unsupported novelty, negative results and modular adoption |

Requirements not elaborated here remain with their listed owners; absence from this map is not deletion. Existing Gen0 T01–T35/R01 and cumulative AT-* identities remain intact. R02 local test IDs are proposed specializations, not replacements.

## 3. Future bounded packages

Effort ranges are rough planning estimates after prerequisites, not claims about how long an active agent will run. Every package ends with a reviewed artifact and an explicit stop; none automatically launches the next.

| Package | Scope and proposed paths | Prerequisites / owners | Success and stop gate | Planning effort / spend |
|---|---|---|---|---|
| R02-P01 | Reconcile actual N1/N2 reports/commits; finalize CR-R02-01–05 under `design/H02/R02/` | User-designated current workspace or supplied results; H00/H04/H06 review | Document accepted mappings and remaining blocks; no production schema edits | 0.5–1 engineering day; $0 provider spend |
| R02-P02 | Extend existing isolated N1 lab with R02-E01's 40 cases, cancellation/revocation/restore and audit output | P01; actual N1 baseline; explicit lab-write authorization; H02/H04/H06 | Reproducible invariant tests; fail on leakage, M0 access or real adapters; no duplicate N1 implementation | 1–2 days; $0; no installs/model downloads |
| R02-P03 | Formalize versioned ModelBackend contract, deterministic test double, usage/reservation ledger and conformance tests | P02 plus accepted contract design; use existing lab directory/module conventions | Fake adapters exercise malformed/refusal/cancel/unknown-billing paths; no live provider | 1–2 days; $0; standard lab runtime only |
| R02-P04 | Qualify Qwen3.5-4B then Gemma 3 4B on EX03 text/selected-image fixtures | Separate model/runtime download/install approval; measured host envelope; protected data/rubric; M0 resource separation | Named task-class qualification or honest failure; no M4 substitution | 1–3 days setup/evaluation; local energy measured, no cloud |
| R02-P05 | Bounded Hermes/OpenClaw EX04 comparison, only if decision remains material | Separate framework install/isolated-environment approval; catalog review; no hidden/background learning | Equivalent boundaries and complete overhead/maintenance evidence; incompatibility is a valid stop | 1–3 days; local-only or separately capped synthetic calls |
| R02-P06 | One read-only runtime worker (readiness first, then finite research); voice a separate subpackage | Accepted JobSpec and H03/H04/H06 interfaces; H07 only for actual native capture/output | Finite jobs and useful evidence; voice must pass EX06 before private audio | 1–3 days per selected slice; no automatic account/device access |
| R02-P07 | Cheap hosted synthetic benchmark and later second-provider conformance | Explicit paid-account/use approval, exact pricing/data policy, allowance and circuit breaker | Lowest-cost qualifying route; stop at allowance, leakage or drift | Proposed total cloud test ceiling $10 only after approval; currently $0 authorized |
| R02-P08 | EX28/R02-E02 bounded engineering campaign; reuse actual N2 notebook where present | H09/H06 frozen objective and P02/P03; physical stage separate | At most five candidates, independent acceptance, no unapproved fabrication | Simulation estimate 3–5 days; physical resources TBD |

P05 is optional, not a dependency blocking daily utility. P06 readiness can precede P04/P07 because it needs no model. P08's synthetic provenance can proceed independently of physical qualification. No package imports another branch's active implementation or introduces a universal authority agent.

Suggested branch name for documentation integration is `design/r02-intelligence-runtime`; coding branch names and lab paths are resolved by the actual owning workspace, not guessed here. No branch is created, pushed or merged by this handback. Before applying anything, inspect the current owner-approved state to avoid overwriting user or agent changes.

## 4. Documentation-only versus implementation decisions

Keep frontier claims, purchase gates, maturity distinctions, broader physical-autonomy stages and unapproved contract alternatives documentation-only. After approval, the smallest meaningful implementation is the no-model lab extension, not a full runtime, framework migration, model swap or new personal-data import.

Specifically do not modify the current M0 workspace/database, approved M4 model, M6 manual Watch gate, simulator pins, physical control interfaces, production authentication, employer accounts, router/firewall/certificates or device safety limits. Do not translate this document into permission for automatic background workers, cloud calls or installation.

## 5. Both handoff-template forms reconciled

The main `R02_HANDOFF.md` preserves the exact starter headings: Decisions, Evidence, Interface changes, Acceptance, Risks and open questions, Next package. The research-prompt archive's 11-part format is covered as follows: thread/scope in the preamble; executive conclusions and recommended design/alternatives in Decisions; interfaces in `CONTRACT_DESIGN.md`; evidence in `SOURCES.md`; risk/unknown behavior in the handoff; smallest/ambitious experiments in `BENCHMARK_AND_EXPERIMENTS.md`; unresolved decisions in Risks; coding impact here; one-page handback in `INTEGRATION_SUMMARY.md`. This avoids silently substituting one same-named template for the other.
