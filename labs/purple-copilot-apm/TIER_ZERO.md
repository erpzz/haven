# Tier Zero control findings

The membership catalog follows `MemberOf` and `AZMemberOf` into three designated groups. On the official SpecterOps samples, most routes to Tier Zero use other relationships. In BloodHound's own shortest paths into Tier Zero, 538 of 562 AD edges are permissions, sessions, delegation or certificate abuse rather than membership. This detector adds those routes. It reuses the lifecycle store, the dashboard and the read-only CE identity. It does not replace the membership reviews.

## Run it

Complete the [sample lab setup](README.md#start-the-sample-lab), then run the following from this directory.

```sh
python3 -m apm.tier_zero            # one JSON summary per platform; exit 2 on a collection issue
python3 -m apm.tier_zero --show RUN
python3 -m apm.dashboard            # open http://127.0.0.1:8134/tier-zero
```

The scheduler runs this detector after the membership and path jobs. To retrieve the generated CE admin password for the operator-only setup steps, use the configuration directory that `ops/ce.sh` used:

```sh
XDG_CONFIG_HOME="$APM_STATE/xdg" "$APM_STATE/bloodhound-cli" config get default_password
```

Without that variable, the CLI reads a different configuration and returns a password that CE rejects.

## What a finding is

A finding is one directed attack edge from a non-Tier Zero object into an object that BloodHound CE tags as Tier Zero (`Tag_Tier_Zero`).
- **Traversable relationships.** CE decides which relationships count through its `AD_ATTACK_PATHS` and `AZ_ATTACK_PATHS` edge sets, the same sets the [SpecterOps query library](https://github.com/SpecterOps/BloodHoundQueryLibrary/tree/ca4924e007ed8094850f980239a1f2ba2bf23b95) uses. No second list is maintained here.
- **Lifecycle.** Each edge has its own state (new, persistent, changed, missing, unavailable), so remediating one edge is visible even when its principal keeps others.
- **Dashboard grouping.** Findings are grouped by the principal that holds them.

**Exposure** is computed in Python, exactly, from CE's edges.
1. A reverse breadth-first expansion asks CE for the edges that point into objects able to reach a boundary source. It continues until no new objects appear. It never reads the whole graph.
2. The expansion never follows a Tier Zero object, so exposure counts objects that reach a source *without first passing through Tier Zero*. An object whose only route crosses Tier Zero already holds its own boundary finding.

**Priority** is the number of identities able to gain the control: users, computers and workloads, plus the source itself when it is an identity. Groups, containers and other conduits are reported but not counted. The model has no scoring or state-transition role.

**Evidence.** The stored evidence keeps:
- the two query templates and the boundary edges;
- labels for the involved objects;
- per-source exposure counts;
- the upstream edge count, object count, read count, duration and a SHA-256 digest of the sorted upstream edge list.

The upstream edges themselves are not stored, because the Entra sample alone has about 220,000.

**Fail-closed rules.**
- A boundary read over 5,000 edges, or an expansion batch over 100,000, records an unavailable observation and carries prior states.
- Object IDs outside `[A-Za-z0-9@._/()-]` stop the scan, so quotes and backslashes never reach a query.
- A boundary edge that disagrees with CE's Tier Zero tagging stops the scan.
- CE's HTTP 404 for an empty result is treated as empty. Every other error propagates.
- Archived samples always yield *limited* confidence, and a sample replay never confirms removal.

## What to fix first

Exposure per finding can mislead, because routes overlap. If nine principals give the same identities a route to Tier Zero, fixing any one of them removes nothing. The scan therefore computes a remediation order:
1. **Group.** Principals that expose exactly the same identities form one step, to be fixed together.
2. **Order.** A greedy pass orders the steps by how many identities lose *every* route to Tier Zero once that step's direct control edges are removed.
3. **Correctness.** Upstream routes do not change when boundary edges are removed, so the counts are exact for each step in sequence.

The plan is stored with the evidence. It appears on the dashboard as **Fix first** and in the Hermes overview tool as `fix_first`.

On the samples, Entra exposure falls from 7,010 identities as follows:

| Step | Fix | Identities left exposed |
| --- | --- | ---: |
| 1 | The one control edge of JohnsAutomationAccount (5,147 identities lose every route) | 1,863 |
| 2 | ThisSPOwnsTheGAGroup | 310 |
| 3 | MyCoolAutomationAccount | 183 |

That is a 97% reduction from three edges. In AD, nine principals form the first step and must be fixed together: Everyone, Authenticated Users, Domain Users and Domain Computers (ADCS), three hosts with Tier Zero sessions, a delegation host and T1_FABIAN. Their 25 edges leave 38 of 53 identities with no route.

## Executed evidence, 2026-11-22 UTC

This run used a clean Linux x86-64 container with 2 vCPUs, 7 GB of RAM and Docker 29.10. Codex's install path ran unchanged: `ops/fetch.sh`, `ops/ce.sh install` (CE 9.10.1, PostgreSQL graph driver), `apm.setup ingest` and `reader`, `apm.collect`, `apm.path_history`. It reproduced the handback: 12 AD and 1 Entra membership, 21/1/5 paths and the AD count warning. The community MCP tarball was taken from a git checkout of the same pinned commit, because this sandbox cannot download GitHub API tarballs.

| Platform | Principals with direct Tier Zero control | Control edges | Identities able to reach Tier Zero | CE reads | Scan time |
| --- | ---: | ---: | ---: | ---: | ---: |
| AD (5 domains) | 39 | 154 | 53 (35 users, 18 computers) | 5 | 0.2 s |
| Entra (1 tenant) | 54 | 2,393 | 7,010 (151 users, 6,859 workloads) | 19 | 90 s |

The highest-ranked AD findings put Everyone, Authenticated Users, Domain Users and Domain Computers into Tier Zero through ADCS ESC1, ESC3, ESC6, ESC9 and ESC10. They also show Tier Zero accounts with sessions on three ordinary hosts. In Entra, an automation account whose managed identity is Tier Zero is reachable by 151 users. A repeat scan reported every AD edge as persistent.

`tests/live_tier_zero.py` checks the detector against two independent oracles. Both passed.
1. **Containment.** Every non-Tier Zero to Tier Zero edge returned by 18 pinned SpecterOps library queries is a recorded finding: 147 crossing edges and zero missing. The library's many-to-many Entra application query returns HTTP 500 inside CE, and the library itself warns about such queries. It is not in the pinned set.
2. **Exposure.** For all 39 AD sources and 8 sampled Entra sources, every counted object reaches its source in CE's own shortest-path search. Every object CE finds that is not counted routes through Tier Zero and appears in another finding's exposed population.

The unit suite now has 39 tests (32 existing, 7 new). Five deliberate mutations each fail it:
- reverting the rank hook;
- counting a source in its own exposure;
- removing the Tier Zero tagging check;
- removing the object ID allowlist;
- removing the expansion budget.

The `/tier-zero` page was checked at 1280 and 390 CSS pixels.

## Limits

These are synthetic samples, and Tier Zero membership is BloodHound's default classification. Exposure counts reachability under BloodHound's traversal model. Some relationships carry prerequisites that BloodHound evaluates when it creates the edge rather than at query time. The Entra workload counts include Microsoft first-party service principals, so the per-class breakdown matters more than the total. Removal still requires the corroboration contract in [PHASE2.md](PHASE2.md). This page reports exposure; it does not remove anything.
