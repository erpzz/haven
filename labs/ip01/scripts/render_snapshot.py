"""Render the explicitly sanitized last-run receipt as a standalone offline page.

This reads no runtime DB, credentials, private oracle or session logs. It is a
static result viewer, never a substitute for the runnable application.
"""
import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "campaigns/IP-01/ip01-v2-20260929/results"


def esc(value):
    return html.escape(str(value))


def render(data):
    rows = "".join(
        f"<tr><td>{esc(row['name'])}</td><td><strong>{esc(row['result'])}</strong></td>"
        f"<td>{esc(row.get('evidence', 'No evidence supplied'))}</td></tr>"
        for row in data.get("journeys", [])
    )
    limits = "".join(f"<li>{esc(item)}</li>" for item in data.get("limitations", []))
    budgets = "".join(f"<tr><td>{esc(key)}</td><td>{esc(value)}</td></tr>" for key, value in data.get("budgets", {}).items())
    return f"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; base-uri 'none'; form-action 'none'">
<title>Haven · last run</title>
<style>
:root{{font-family:system-ui,sans-serif;color:#263c37;background:#f4f5ed}}*{{box-sizing:border-box}}
body{{margin:0;padding:40px 24px}}main{{max-width:1050px;margin:auto}}header{{padding:28px 0 32px;border-bottom:1px solid #bfcac1}}
.eyebrow{{letter-spacing:.15em;text-transform:uppercase;font-size:12px;font-weight:700;color:#4e7060}}
h1{{font-size:clamp(32px,5vw,54px);font-weight:600;letter-spacing:-.04em;margin:12px 0}}h2{{font-size:22px;margin:32px 0 14px}}
p,li{{line-height:1.65}}.badge{{display:inline-block;border:1px solid #9caf9f;padding:6px 10px;border-radius:8px;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:16px;margin:24px 0}}
.card{{background:#fffdf7;border:1px solid #d5dbd1;border-radius:14px;padding:20px;overflow-wrap:anywhere}}
.card small{{display:block;color:#597364;margin-bottom:8px}}.mono{{font-family:ui-monospace,monospace;font-size:12px}}
table{{width:100%;border-collapse:collapse;background:#fffdf7;font-size:14px}}td,th{{padding:14px;border-bottom:1px solid #dce2d9;text-align:left;vertical-align:top;overflow-wrap:anywhere}}th{{color:#47614f}}
.scroll{{overflow:auto}}footer{{margin-top:36px;color:#536a5d;font-size:13px}}a{{color:#285747}}
</style><main>
<header><div class="eyebrow">Haven / IP-01</div><h1>A record of the last run.</h1>
<span class="badge">{esc(data.get('status','UNPROVEN'))}</span>
<p>This is an offline evidence snapshot. The application is started separately with the README commands.</p></header>
<div class="grid">
<section class="card"><small>Observed</small>{esc(data.get('observed_at','UNKNOWN'))}</section>
<section class="card"><small>Evaluated candidate</small><span class="mono">{esc(data.get('candidate_sha','NOT_FROZEN'))}</span></section>
<section class="card"><small>Model</small>{esc(data.get('model','NOT_EXECUTED'))}</section>
<section class="card"><small>Owned process shutdown</small>{esc(data.get('process_shutdown','UNKNOWN'))}</section>
</div>
<h2>Executed journeys</h2><p>{esc(data.get('scope','No qualification is implied.'))}</p>
<div class="scroll"><table><thead><tr><th>Journey</th><th>Observed result</th><th>Evidence</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Budgets</h2><table><tbody>{budgets}</tbody></table>
<h2>Limits and unresolved work</h2><ul>{limits}</ul>
<footer>Synthetic local development evidence. No canonical CORE/MF/P03, production, real-account, enrolled-device or physical qualification follows. See README and the candidate-bound MORNING_REPORT for the runnable handoff.</footer>
</main></html>"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default=str(RESULTS / "last-run.json"))
    parser.add_argument("--output", default=str(RESULTS / "last-run.html"))
    args = parser.parse_args()
    source = Path(args.input).resolve()
    target = Path(args.output).resolve()
    if RESULTS.resolve() not in target.parents:
        raise ValueError("Snapshot output must stay under the campaign results directory")
    if not (ROOT / "campaigns/IP-01/ip01-v2-20260929").resolve() in source.parents and RESULTS.resolve() not in source.parents:
        raise ValueError("Input must be an explicitly sanitized campaign/result receipt")
    data = json.loads(source.read_text(encoding="utf-8"))
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(data), encoding="utf-8")
    print(str(target))


if __name__ == "__main__":
    main()
