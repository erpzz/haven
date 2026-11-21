"""Loopback review console over read-only SQLite snapshots."""
import json
from contextlib import closing
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .policy import REVIEWS
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
<title>Purple Copilot APM · Haven</title><style>{STYLE.read_text()}</style><main><header><b>HAVEN</b><span>Identity security</span></header>
<h1>Purple Copilot APM</h1><p>Critical assets · Official sample graphs</p><div class="cards">{''.join(cards)}</div>
<div class="layout"><article>{body}</article><aside><h2>Snapshot history</h2><ol>{timeline}</ol></aside></div></main></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Host") not in ("localhost:8134", "127.0.0.1:8134"):
            return self.send_error(403)
        url = urlsplit(self.path)
        if url.path != "/":
            return self.send_error(404)
        try:
            selected = parse_qs(url.query).get("run")
            content = page(int(selected[0]) if selected else None).encode()
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
