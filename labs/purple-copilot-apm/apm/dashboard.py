"""Loopback review console over read-only SQLite snapshots."""
import json
from contextlib import closing
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .policy import REVIEWS
from .review import clean
from .store import database

STYLE = Path(__file__).with_name("dashboard.css")


def h(text):
    return escape(str(text), quote=True)


def page(selected=None):
    with closing(database(True)) as db, db:
        db.execute("BEGIN")
        history = list(db.execute("SELECT id,scope,observed FROM runs ORDER BY id DESC LIMIT 40"))
        current = list(db.execute("SELECT * FROM runs WHERE id IN (SELECT max(id) FROM runs GROUP BY scope) ORDER BY scope"))
        cards = []
        for run in current:
            ev = json.loads(run["evidence"])
            issues = ev["issues"]
            quality = "Review coverage" if issues else "Verified sample"
            cards.append(f'<a class="card" href="/?run={run["id"]}"><small>{h(run["scope"].upper())} · MONITORED ASSET</small>'
                         f'<h2>{h(REVIEWS[run["scope"]].name)}</h2><strong>{len(ev["edges"]) if not ev.get("unavailable") else "—"}</strong> observed memberships'
                         f'<footer class="{"warn" if issues else "ok"}">{quality}</footer></a>')
        if selected is None and current:
            selected = current[0]["id"]
        run = db.execute("SELECT * FROM runs WHERE id=?", (selected,)).fetchone()
        body = ""
        if run:
            ev = json.loads(run["evidence"])
            rows = []
            for change in db.execute("SELECT * FROM changes WHERE run=? ORDER BY state,src", (selected,)):
                rows.append("<tr>" + "".join(f"<td>{h(change[k])}</td>" for k in
                            ("src", "kind", "state", "investigation")) + "</tr>")
            issues = ev["issues"]
            health = " · ".join(issues) if issues else "Graph agrees with the pinned source inventory."
            conclusions = []
            for r in db.execute("SELECT response FROM conclusions WHERE run=? ORDER BY id DESC", (selected,)):
                choice = json.loads(r[0])["choices"][0]
                label = "" if choice.get("finish_reason") == "stop" else "Incomplete model response · "
                conclusions.append(label + choice["message"]["content"])
            body = f"""<section><small>SNAPSHOT {selected} · {h(ev["scope"].upper())}</small>
<h2>{h(REVIEWS[ev["scope"]].name)}</h2><p><b>Collection health</b> · {h(health)}</p>
<p>Observed {h(ev["observed"])}<br>Source collection time · {h(ev.get("collected") or "Unavailable")}</p>
<details><summary>Query and source evidence</summary><pre>{h(json.dumps(ev, indent=2))}</pre></details></section>
<section><h2>Membership findings</h2><div class="scroll"><table><thead><tr><th>Source object ID</th><th>Relationship</th><th>Change</th><th>Investigation</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></section>
<section><h2>Analyst hypotheses</h2>{''.join('<p>'+h(c)+'</p>' for c in conclusions) or '<p>No analyst review recorded.</p>'}</section>"""
        elif selected is not None:
            raise KeyError("Unknown snapshot")
        timeline = "".join(f'<li><a href="/?run={r["id"]}">#{r["id"]} · {h(r["scope"].upper())}</a> <time>{h(r["observed"][:19])} UTC</time></li>' for r in history)
        return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Purple Copilot APM · Haven</title><style>{STYLE.read_text()}</style><main><header><b>HAVEN</b><span>Identity security</span><a href="/tier-zero">Tier Zero control</a><a href="/paths">Path history</a></header>
<h1>Purple Copilot APM</h1><p>Critical assets · Official sample graphs</p><div class="cards">{''.join(cards)}</div>
<div class="layout"><article>{body}</article><aside><h2>Snapshot history</h2><ol>{timeline}</ol></aside></div></main></html>"""


def path_page(selected=None):
    with closing(database(True)) as db:
        available = db.execute("SELECT 1 FROM sqlite_master WHERE name='path_runs'").fetchone()
        membership = "coalesce(json_extract(evidence,'$.asset.key'),'') NOT LIKE 'tier-zero-%'"
        runs = list(db.execute(f"SELECT id,observed FROM path_runs WHERE {membership} ORDER BY id DESC LIMIT 40")) if available else []
        if selected is None and runs:
            selected = runs[0]["id"]
        run = db.execute(f"SELECT * FROM path_runs WHERE id=? AND {membership}", (selected,)).fetchone() if available else None
    report = "<p>No path scans recorded.</p>"
    if run:
        evidence = json.loads(run["evidence"])
        findings = json.loads(run["findings"])
        rows = []
        for key, finding in sorted(findings.items(), key=lambda item: -item[1]["priority"]["score"]):
            path = finding["path"]
            chain = " ".join([path[0][0]] + [f"→ {kind} → {target}" for _, kind, target in path])
            detail = json.dumps(dict(finding=key, **finding), indent=2)
            rows.append(f'<tr><td><details><summary>{h(chain)}</summary><pre>{h(detail)}</pre></details></td>'
                        f'<td>{h(finding.get("observation") or finding["state"])}</td>'
                        f'<td>{h(finding["priority"]["score"])}</td></tr>')
        report = f"""<section><small>{h(evidence['origin'])} · SNAPSHOT {selected}</small>
<h2>{h(evidence['asset']['key'])}</h2><p>{h(run['observed'])}</p>
<details><summary>Collection evidence and query</summary><pre>{h(json.dumps(evidence, indent=2))}</pre></details></section>
<section><div class="scroll"><table><thead><tr><th>Directed path</th><th>State</th><th>Priority</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></section>"""
    elif selected is not None:
        raise KeyError("Unknown path snapshot")
    history = "".join(f'<li><a href="/paths?run={r["id"]}">Snapshot {r["id"]}</a><time>{h(r["observed"][:19])} UTC</time></li>' for r in runs)
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Path history · Purple Copilot APM</title><style>{STYLE.read_text()}</style><main><header><b>HAVEN</b><a href="/">Membership reviews</a><a href="/tier-zero">Tier Zero control</a></header>
<h1>Path history</h1><div class="layout"><article>{report}</article><aside><h2>Observations</h2><ol>{history}</ol></aside></div></main></html>"""


LIVE = ("new", "persistent", "changed")


def plan_html(e):
    """The computed remediation order: groups that must be fixed together, and what each fix removes."""
    items = []
    nodes = e["nodes"]
    for step in e.get("remediation") or []:
        names = [clean(nodes.get(x, {}).get("label") or x) for x in step["sources"]]
        who = ", ".join(names[:5]) + (f" and {len(names) - 5} more" if len(names) > 5 else "")
        together = " (fix together)" if len(names) > 1 else ""
        edges = "edge" if step["control_edges"] == 1 else "edges"
        items.append(f"<li><b>{h(who)}</b> — {h(step['control_edges'])} {edges}{together}; "
                     f"{h(step['identities_removed'])} {'identity loses' if step['identities_removed'] == 1 else 'identities lose'} every route, "
                     f"{h(step['identities_still_exposed'])} remain</li>")
    return f"<h3>Fix first</h3><ol class=\"plan\">{''.join(items)}</ol>" if items else ""


def tier_zero_page(selected=None):
    """Tier Zero control findings grouped by the non-Tier Zero principal that holds them."""
    with closing(database(True)) as db:
        available = db.execute("SELECT 1 FROM sqlite_master WHERE name='path_runs'").fetchone()
        latest = list(db.execute("""SELECT * FROM path_runs WHERE id IN (SELECT max(id) FROM path_runs
            WHERE json_extract(evidence,'$.asset.key') LIKE 'tier-zero-%' GROUP BY stream) ORDER BY id""")) if available else []
        if selected is not None:
            latest = [r for r in latest if r["id"] == selected] or list(db.execute(
                "SELECT * FROM path_runs WHERE id=? AND json_extract(evidence,'$.asset.key') LIKE 'tier-zero-%'", (selected,)))
            if not latest:
                raise KeyError("Unknown Tier Zero snapshot")
    sections = []
    for run in latest:
        e, findings = json.loads(run["evidence"]), json.loads(run["findings"])
        platform = e["asset"]["platform"].upper()
        if e.get("unavailable"):
            sections.append(f'<section><small>{h(platform)} · SNAPSHOT {run["id"]}</small><h2>Observation unavailable</h2>'
                            f'<p>{h(" · ".join(e["issues"]))}. Prior findings are carried unchanged.</p></section>')
            continue
        nodes, groups = e["nodes"], {}
        for key, f in findings.items():
            groups.setdefault(f["path"][0][0], []).append((key, f))
        rows = []
        for source, items in sorted(groups.items(), key=lambda kv: (-kv[1][0][1]["priority"]["score"], kv[0])):
            live = [(k, f) for k, f in items if (f.get("observation") or f["state"]) in LIVE]
            states = sorted({f.get("observation") or f["state"] for _, f in items})
            factors = items[0][1]["priority"].get("factors", {})
            kinds = {}
            for _, f in live:
                kinds[f["path"][0][1]] = kinds.get(f["path"][0][1], 0) + 1
            edges = "".join(f'<li>{h(f["path"][0][1])} → {h(clean(nodes.get(f["path"][0][2], {}).get("label") or f["path"][0][2]))}'
                            f' <small>{h(f.get("observation") or f["state"])} · {h(k[:12])}</small></li>'
                            for k, f in sorted(items, key=lambda kf: kf[1]["path"][0][1]))
            label = nodes.get(source, {})
            rows.append(f'<tr><td><details><summary><b>{h(clean(label.get("label") or source))}</b> <small>{h(label.get("kind"))}</small></summary>'
                        f'<p><small>{h(source)}</small></p><ul>{edges}</ul></details></td>'
                        f'<td data-label="Identities able to gain it"><b>{h(items[0][1]["priority"]["score"])}</b><br><small>{h(factors.get("users", 0))} users · '
                        f'{h(factors.get("computers", 0))} computers · {h(factors.get("workloads", 0))} workloads</small></td>'
                        f'<td data-label="Control edges">{h(", ".join(f"{k} ×{n}" if n > 1 else k for k, n in sorted(kinds.items(), key=lambda kv: -kv[1])) or "—")}</td>'
                        f'<td data-label="State">{h(" / ".join(states))}</td></tr>')
        pop = e.get("population", {})
        identities = sum(pop.get(k, 0) for k in ("users", "computers", "workloads"))
        live_count = sum((f.get("observation") or f["state"]) in LIVE for f in findings.values())
        health = ". ".join(e["issues"] + e.get("notes", [])) + "." if e["issues"] or e.get("notes") else "Sample ingest complete."
        sections.append(f"""<section><small>{h(platform)} · SNAPSHOT {run['id']} · {h(run['observed'][:19])} UTC</small>
<h2>{len([g for g in groups.values() if any((f.get('observation') or f['state']) in LIVE for _, f in g)])} principals hold direct control of Tier Zero</h2>
<p><b>{live_count}</b> control edges · <b>{identities}</b> identities can reach Tier Zero
({h(pop.get('users', 0))} users, {h(pop.get('computers', 0))} computers, {h(pop.get('workloads', 0))} workloads)</p>
<p><b>Collection</b> · {h(health)} Confidence is limited: an archived sample cannot attest a fresh collection.</p>
{plan_html(e)}
<details><summary>Queries and receipts</summary><pre>{h(json.dumps({k: e.get(k) for k in ('query', 'expansion', 'upstream', 'receipt', 'issues', 'notes')}, indent=2))}</pre></details>
<div class="scroll"><table class="t0"><thead><tr><th>Non-Tier Zero principal</th><th>Identities able to gain it</th><th>Control edges</th><th>State</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div></section>""")
    body = "".join(sections) or "<p>No Tier Zero scans recorded. Run <code>python3 -m apm.tier_zero</code>.</p>"
    return f"""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tier Zero control · Purple Copilot APM</title><style>{STYLE.read_text()}</style><main><header><b>HAVEN</b><a href="/">Membership reviews</a><a href="/paths">Path history</a></header>
<h1>Tier Zero control</h1><p>Attack edges from non-Tier Zero objects into BloodHound's Tier Zero, ranked by the number of identities able to gain each control.</p>
<article>{body}</article></main></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Host") not in ("localhost:8134", "127.0.0.1:8134"):
            return self.send_error(403)
        url = urlsplit(self.path)
        if url.path not in ("/", "/paths", "/tier-zero"):
            return self.send_error(404)
        try:
            selected = parse_qs(url.query).get("run")
            render = {"/": page, "/paths": path_page, "/tier-zero": tier_zero_page}[url.path]
            content = render(int(selected[0]) if selected else None).encode()
        except (ValueError, KeyError):
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(content)


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8134), Handler).serve_forever()
