# Current status — coordination baseline

Assembled 2026-09-28 from supplied documents. Not a live inspection of the PC or any running agent.

| Work | Supported status | Next gate |
|---|---|---|
| Repository publication | Authorized by operator; see import receipt for actual completed verification | Complete source/remote hash checks |
| ASTRA M0 | Separate application; supplied NIGHT-01 report says code existed and operator/iPhone acceptance was pending | Actual M0 owner report and operator acceptance; no merge here |
| NIGHT-01 N0/N1/N2 | Producer reports complete synthetic laboratory; independent review retained baseline with R1 gap | Review latest R1 evidence |
| R1 worker lifecycle | Issue documented; no accepted completion evidence supplied to this hub | Python 3.12 reproduction, fix, regression and review |
| R02 intelligence | v1 design delivered; H00 review recommends acceptance in principle | P01 reconciliation and R03/H04 semantics |
| R06 RF/spatial | Saved v1 design handback available | H00/H04/H06 and R07 contract review; no live sensing |
| R08 engineering | Saved v1 design handback available | P00 reconciliation; H04/H06 and R06 interface alignment |
| R03 privacy | No completed handback in the material imported | Next priority assignment |
| R13 validation | No completed handback in the material imported | Focused crosswalk and acceptance review |
| R07 world model | No completed handback in the material imported | Next wave after initial RF/privacy review |
| R01/R04/R05/R09/R10/R11/R12 | Retained scope and original prompts; completion not established | Schedule bounded waves, not all at once |
| Models/devices/physical capabilities | Not qualified by these imports | Separate explicit benchmark or device campaign |

Do not mark a thread running or done from a filename or this index. Actual agent status requires a task receipt. All imported tests retain their original environment and stated limits. Source research dates are not current product verification.

## Foundation preserved

The original M0 stack is Python 3.12, FastAPI, Pydantic 2, Jinja2, one Uvicorn worker and local SQLite under Ubuntu 24.04/WSL2. The current N1/N2 snapshot is a separate offline test-double library. The M4 advisory baseline remains `qwen2.5vl:3b`; model-research candidates do not replace it.

## Coding queue

R1 repair remains a separate narrow task. Finish/review M0 separately. Do not begin M1, live model integration, a framework migration or a physical campaign merely because a handback recommends it.

## R15 publication update — 2026-09-28

The original R15 Observatory prompt is now on main through [PR #10](https://github.com/erpzz/haven/pull/10), merge `bff72a5e8a2faf86a6ded43649e0a098e80337a6`; its content blob remains `28942162876c96d2c92c020ade1e5f59cca4ff02`. [The R15 entry point](coordination/R15_OBSERVATORY.md) links the supporting brief, source notes, opportunity backlog, starting message and optional R15A–F assignments. [Issue #12](https://github.com/erpzz/haven/issues/12) tracks the research handback.

This records publication of instructions and proposed ideas, not a completed R15 study, deployed Observatory, runtime test, model evaluation or device capability. No research or background agent is started by adding the files. No new PC, M0, NIGHT-01 or R1 completion state is asserted. R14 remains referenced at its pinned original prompt; no completion evidence is reviewed here.

The older full-source migration and its temporary importer are not verified or repaired by this addition. The existence of the earlier workflow is not proof that it ran. Imported baseline completeness and any remaining historical broken links stay separate from the new R15 documentation.
