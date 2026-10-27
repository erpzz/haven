// Slinky console. Everything shown comes from the task directory, receipt ledgers and fleet probes.
'use strict';

const $ = (s, el = document) => el.querySelector(s);
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ago = (t) => { if (!t) return ''; const s = Math.max(0, Date.now() / 1000 - t); return s < 60 ? `${s | 0}s ago` : s < 3600 ? `${(s / 60) | 0}m ago` : `${(s / 3600).toFixed(1)}h ago`; };
const gb = (b) => (b == null ? '—' : `${(b / 1e9).toFixed(1)} GB`);

let TOKEN = '';
let STATE = null;
let current = null;          // selected task id
let pollGen = 0;             // invalidates an older event loop when the selection changes
let wsView = 'git';

function readToken() {
  const m = location.hash.match(/token=([^&]+)/);
  if (m) { sessionStorage.setItem('haven-console-token', m[1]); history.replaceState(null, '', location.pathname); }
  TOKEN = sessionStorage.getItem('haven-console-token') || '';
}

async function api(path, body) {
  const opt = { headers: { Authorization: `Bearer ${TOKEN}` } };
  if (body !== undefined) { opt.method = 'POST'; opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(body); }
  const r = await fetch(path, opt);
  if (r.status === 401) { $('#locked').classList.remove('hidden'); throw new Error('unauthorized'); }
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || r.statusText);
  return data;
}

// ---------- tabs ----------
document.querySelectorAll('.tabs button').forEach((b) => b.addEventListener('click', () => {
  document.querySelectorAll('.tabs button').forEach((x) => x.classList.toggle('active', x === b));
  document.querySelectorAll('main.tab').forEach((m) => m.classList.toggle('hidden', m.id !== `tab-${b.dataset.tab}`));
  if (b.dataset.tab === 'fleet') loadFleet();
  if (b.dataset.tab === 'agents') loadLineage();
  if (b.dataset.tab === 'research') loadResearch();
}));

// ---------- state & form ----------
async function loadState() {
  STATE = await api('/api/state');
  const st = $('#status');
  const sb = STATE.sandbox;
  st.innerHTML = `<span class="badge">${esc(STATE.host)}</span>
    <span class="badge ${sb.available ? 'ok' : 'bad'}">sandbox: ${esc(sb.backend)}</span>
    <span class="badge ${STATE.scope.network ? 'warn' : ''}">network ${STATE.scope.network ? 'granted by owner' : 'off'}</span>`;
  const ws = $('#f-ws'); const keep = ws.value;
  ws.innerHTML = STATE.workspaces.map((w) => `<option value="${esc(w.name)}">${esc(w.name)}${w.kind === 'disposable' ? ' (disposable)' : ''}</option>`).join('') || '<option value="">no workspace yet</option>';
  if (keep) ws.value = keep;
  $('#f-fixture').innerHTML = '<option value="">+ disposable copy of fixture…</option>' + STATE.fixtures.map((f) => `<option>${esc(f)}</option>`).join('');
  const ag = $('#f-agent'); const keepA = ag.value;
  ag.innerHTML = STATE.agents.map((a) => `<option value="${esc(a.id)}">${esc(a.label || a.id)}</option>`).join('');
  if (keepA) ag.value = keepA;
  const md = $('#f-mode'); const keepM = md.value || 'engineer';
  md.innerHTML = STATE.modes.map((m) => `<option value="${m.id}">${m.id}</option>`).join('');
  md.value = keepM;
  formHints();
}

function formHints() {
  const a = STATE.agents.find((x) => x.id === $('#f-agent').value) || {};
  const hosted = a.kind === 'cli';
  $('#f-agent-where').innerHTML = `inference: <b>${esc(a.inference_host)}</b> · tools run on: <b>${esc(STATE.host)}</b> (sandboxed)` +
    (hosted ? ' · <span class="badge warn">leaves this house</span>' : ' · <span class="badge ok">local</span>');
  $('#f-egress-row').classList.toggle('hidden', !hosted);
  const m = STATE.modes.find((x) => x.id === $('#f-mode').value);
  $('#f-mode-help').textContent = m ? m.help : '';
}
['#f-agent', '#f-mode'].forEach((s) => $(s).addEventListener('change', formHints));

$('#f-fixture').addEventListener('change', async (e) => {
  if (!e.target.value) return;
  try {
    const w = await api('/api/workspaces', { fixture: e.target.value });
    await loadState(); $('#f-ws').value = w.name; showWorkspace(w.name);
  } catch (err) { $('#f-error').textContent = err.message; }
  e.target.value = '';
});
$('#f-ws').addEventListener('change', (e) => showWorkspace(e.target.value));

$('#new-task').addEventListener('submit', async (e) => {
  e.preventDefault(); $('#f-error').textContent = '';
  const a = STATE.agents.find((x) => x.id === $('#f-agent').value) || {};
  const body = { workspace: $('#f-ws').value, agent: a.id, mode: $('#f-mode').value, prompt: $('#f-prompt').value };
  if (a.kind === 'cli') {
    if (!$('#f-egress').checked) { $('#f-error').textContent = 'Confirm that this hosted task leaves the house.'; return; }
    body.egress_ack = 'HOSTED_SUBSCRIPTION';
  }
  try {
    const r = await api('/api/tasks', body);
    $('#f-prompt').value = ''; $('#f-egress').checked = false;
    await loadTasks(); selectTask(r.task_id);
  } catch (err) { $('#f-error').textContent = err.message; }
});

// ---------- tasks ----------
let TASKS = [];
async function loadTasks() {
  TASKS = await api('/api/tasks');
  const byParent = {};
  TASKS.forEach((t) => { (byParent[t.parent_id || ''] ||= []).push(t); });
  const render = (t, depth) => {
    const kids = (byParent[t.task_id] || []).map((k) => render(k, depth + 1)).join('');
    return `<div class="t ${depth ? 'child' : ''} ${t.task_id === current ? 'sel' : ''}" data-id="${esc(t.task_id)}">
      <div class="l1"><span class="dot ${esc(t.status)}"></span><b>${esc(t.agent)}</b><span class="muted small">${esc(t.mode)} · ${esc(t.workspace_name)}</span></div>
      <div class="l2">${esc(t.prompt)}</div></div>${kids}`;
  };
  const roots = TASKS.filter((t) => !t.parent_id || !TASKS.some((x) => x.task_id === t.parent_id));
  $('#tasks').innerHTML = roots.slice(0, 60).map((t) => render(t, 0)).join('') || '<div class="empty">No tasks yet.</div>';
  $('#tasks').querySelectorAll('.t').forEach((el) => el.addEventListener('click', (ev) => { ev.stopPropagation(); selectTask(el.dataset.id); }));
}

async function selectTask(tid) {
  current = tid; const gen = ++pollGen;
  document.querySelectorAll('.tasks .t').forEach((el) => el.classList.toggle('sel', el.dataset.id === tid));
  $('#timeline').innerHTML = '';
  const d = await api(`/api/tasks/${tid}`);
  renderHead(d);
  if (d.meta.workspace_name) showWorkspace(d.meta.workspace_name, d.meta.workspace);
  let offset = 0;
  while (gen === pollGen) {
    let r;
    try { r = await api(`/api/tasks/${tid}/events?offset=${offset}`); } catch (e) { await sleep(2000); continue; }
    if (gen !== pollGen) return;
    r.events.forEach(renderEvent);
    offset = r.offset;
    if (r.status !== 'running' && !r.events.length) {
      renderHead(await api(`/api/tasks/${tid}`));
      if (d.meta.workspace_name) showWorkspace(d.meta.workspace_name);
      return;
    }
  }
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function renderHead(d) {
  const m = d.meta; const rec = d.record || {};
  const egress = m.egress === 'HOSTED_SUBSCRIPTION' ? '<span class="badge warn">hosted · subscription</span>' : '<span class="badge ok">local</span>';
  $('#task-head').innerHTML = `<div class="title">${esc(m.prompt)}</div>
    <div class="meta"><span class="dot ${esc(m.status)}"></span><b>${esc(m.status)}</b>
      <span class="badge violet">${esc(m.agent)}</span>${egress}
      <span class="badge">inference: ${esc(m.inference_host)}</span><span class="badge">tools: ${esc(m.tool_host)}</span>
      <span class="badge">${esc(m.mode)}</span>${m.network ? '<span class="badge warn">network</span>' : ''}
      ${m.parent_id ? `<span class="badge">child of <a href="#" data-goto="${esc(m.parent_id)}">${esc(m.parent_id)}</a> · depth ${esc(m.depth)}</span>` : ''}
      ${(m.leased_paths || []).length ? `<span class="badge">leases: ${esc(m.leased_paths.join(', '))}</span>` : ''}
      <span class="badge ${d.ledger_verified === false ? 'bad' : d.ledger_verified ? 'ok' : ''}">ledger ${d.ledger_verified == null ? '—' : d.ledger_verified ? 'verified' : 'TAMPERED'}</span>
      ${rec.wall_s ? `<span class="muted small">${rec.wall_s}s · ${rec.steps ?? '?'} steps · ${rec.tool_calls ?? '?'} actions</span>` : ''}
      ${m.status === 'running' ? `<button class="danger" id="cancel">Cancel</button>` : ''}
    </div>
    ${d.children.length ? `<div class="hint">children: ${d.children.map((c) => `<a href="#" data-goto="${esc(c.task_id)}">${esc(c.agent)} (${esc(c.status)})</a>`).join(', ')}</div>` : ''}`;
  $('#task-head').querySelectorAll('[data-goto]').forEach((a) => a.addEventListener('click', (e) => { e.preventDefault(); selectTask(a.dataset.goto); }));
  const c = $('#cancel'); if (c) c.addEventListener('click', async () => { await api(`/api/tasks/${m.task_id}/cancel`, {}); });
}

const live = {}; // receipt -> element
function renderEvent(e) {
  const tl = $('#timeline'); const t = e.t ? new Date(e.t * 1000).toLocaleTimeString() : '';
  if (e.type === 'model_turn') {
    const calls = (e.calls || []).filter(Boolean);
    const div = document.createElement('div'); div.className = 'ev model';
    div.innerHTML = `<div class="h"><span class="k">model</span><span class="muted">step ${esc(e.step)}${e.seconds != null ? ` · ${esc(e.seconds)}s` : ''}${e.completion_tokens ? ` · ${esc(e.completion_tokens)} tok` : ''}</span>
      <span>${calls.length ? '→ ' + calls.map(esc).join(', ') : '→ answer'}</span><span class="t">${t}</span></div>
      ${e.text ? `<div class="txt">${esc(e.text)}</div>` : ''}${e.reasoning ? `<details><summary>reasoning</summary><div class="txt muted">${esc(e.reasoning)}</div></details>` : ''}`;
    tl.appendChild(div);
  } else if (e.type === 'action') {
    let div = live[e.receipt];
    if (!div) { div = document.createElement('div'); live[e.receipt] = div; tl.appendChild(div); div._out = ''; }
    div.className = `ev act ${e.status}`;
    if (e.summary) div._summary = e.summary;
    if (e.reason) div._reason = e.reason;
    if (e.output != null) div._out = e.output;
    div.innerHTML = `<div class="h"><span class="k">${esc(e.tool)}</span><span class="rid">${esc(e.receipt)}</span>
      <span class="dot ${esc(e.status)}"></span><span>${esc(e.status)}${e.exit_code != null ? ` · exit ${esc(e.exit_code)}` : ''}${e.duration_s != null ? ` · ${esc(e.duration_s)}s` : ''}</span><span class="t">${t}</span></div>
      <div class="mono small">${esc(div._summary || '')}</div>${div._reason && e.status !== 'succeeded' ? `<div class="hint">${esc(div._reason)}</div>` : ''}
      ${div._out ? `<details ${e.status === 'failed' ? 'open' : ''}><summary>output</summary><pre>${esc(div._out)}</pre></details>` : ''}`;
  } else if (e.type === 'output') {
    const div = live[e.receipt]; if (!div) return;
    div._out = ((div._out || '') + e.text).slice(-6000);
    let pre = div.querySelector('pre');
    if (!pre) { div.insertAdjacentHTML('beforeend', '<details open><summary>live output</summary><pre></pre></details>'); pre = div.querySelector('pre'); }
    pre.textContent = div._out; pre.scrollTop = pre.scrollHeight;
  } else if (e.type === 'approval') {
    const div = document.createElement('div'); div.className = 'ev approval';
    div.innerHTML = `<div class="h"><span class="k">approval needed</span><span class="rid">${esc(e.receipt)}</span><span>${esc(e.summary)}</span><span class="t">${t}</span></div><div class="hint">${esc(e.reason)}</div>`;
    tl.appendChild(div); loadApprovals();
  } else if (e.type === 'child_started') {
    const div = document.createElement('div'); div.className = 'ev child';
    div.innerHTML = `<div class="h"><span class="k">child agent started</span><span class="badge violet">${esc(e.agent)}</span><span class="muted">${esc(e.mode)} · budget ${esc(e.budget_steps)} steps · leases ${esc((e.paths || []).join(', ') || 'none')}</span>
      <a href="#" data-goto="${esc(e.child_id)}">open ${esc(e.child_id)}</a><span class="t">${t}</span></div>`;
    div.querySelector('a').addEventListener('click', (ev) => { ev.preventDefault(); selectTask(e.child_id); });
    tl.appendChild(div);
  } else if (e.type === 'child_finished') {
    const div = document.createElement('div'); div.className = 'ev child';
    div.innerHTML = `<div class="h"><span class="k">child finished</span><span class="dot ${esc(e.status)}"></span><span>${esc(e.status)} · ${esc(e.wall_s)}s</span><span class="t">${t}</span></div>`;
    tl.appendChild(div);
  } else if (e.type === 'nudge') {
    const div = document.createElement('div'); div.className = 'ev';
    div.innerHTML = `<div class="h"><span class="k">runtime check</span><span class="muted">${esc(e.kind)}</span><span class="t">${t}</span></div>${e.problems ? `<div class="hint">${esc(e.problems.join('; '))}</div>` : ''}`;
    tl.appendChild(div);
  } else if (e.type === 'task_finished') {
    const chk = e.check; const bad = e.status !== 'completed' || (chk && !chk.ok);
    const div = document.createElement('div'); div.className = `ev final ${bad ? 'bad' : ''}`;
    div.innerHTML = `<div class="h"><span class="k">${esc(e.status)}</span>${e.wall_s ? `<span class="muted">${esc(e.wall_s)}s</span>` : ''}<span class="t">${t}</span></div>
      ${e.error ? `<div class="error">${esc(e.error)}</div>` : ''}${e.answer ? `<div class="txt">${esc(e.answer)}</div>` : ''}
      ${chk ? `<div class="hint">receipt check: ${chk.ok ? 'every cited receipt is real and supports the claims' : esc(JSON.stringify({ forged: chk.forged, misreported: chk.misreported, unsupported: chk.unsupported_claims }))}</div>` : ''}
      ${e.footer ? `<pre>${esc(e.footer)}</pre>` : ''}`;
    tl.appendChild(div);
  } else if (e.type === 'hosted_init') {
    const div = document.createElement('div'); div.className = 'ev';
    div.innerHTML = `<div class="h"><span class="k">${esc(e.agent)} connected</span><span class="muted">model ${esc(e.model)} · ${esc(e.tools)} Haven tools · plan billing verified</span><span class="t">${t}</span></div>`;
    tl.appendChild(div);
  }
  const center = $('.col.center'); center.scrollTop = center.scrollHeight;
}

// ---------- approvals ----------
async function loadApprovals() {
  const list = await api('/api/approvals');
  $('#appr-count').textContent = list.length || '';
  $('#approvals').innerHTML = list.map((a) => `<div class="ap" data-r="${esc(a.receipt)}"><div><b>${esc(a.tool)}</b> <span class="mono small muted">${esc(a.receipt)}</span></div>
    <div class="hint">${esc(a.agent)} · ${esc(a.workspace && a.workspace.split('/').pop())} · ${esc(a.mode)} — ${esc(a.reason)}</div>
    <pre>${esc(a.args.command || a.args.patch || JSON.stringify(a.args, null, 1))}</pre>
    <div class="btns"><button class="primary" data-d="approve">Approve</button><button class="danger" data-d="reject">Reject</button></div></div>`).join('') || '<div class="empty">Nothing waiting.</div>';
  $('#approvals').querySelectorAll('button[data-d]').forEach((b) => b.addEventListener('click', async () => {
    const rid = b.closest('.ap').dataset.r; await api(`/api/approvals/${rid}`, { decision: b.dataset.d }); loadApprovals();
  }));
}

// ---------- workspace ----------
let WS = null;
document.querySelectorAll('[data-ws]').forEach((b) => b.addEventListener('click', () => {
  wsView = b.dataset.ws; document.querySelectorAll('[data-ws]').forEach((x) => x.classList.toggle('active', x === b)); if (WS) showWorkspace(WS);
}));
async function showWorkspace(name) {
  if (!name) return; WS = name; $('#ws-name').textContent = name;
  try {
    if (wsView === 'git') {
      const g = await api(`/api/workspace/git?ws=${encodeURIComponent(name)}`);
      $('#ws-status').textContent = g.status;
      const lines = (g.diff || '').split('\n').map((l) => {
        const c = l.startsWith('+++') || l.startsWith('---') || l.startsWith('diff ') ? 'file' : l.startsWith('@@') ? 'hunk' : l.startsWith('+') ? 'add' : l.startsWith('-') ? 'del' : '';
        return `<span class="${c}">${esc(l)}</span>`;
      }).join('\n');
      $('#ws-body').innerHTML = `<h3>Uncommitted diff</h3><pre class="diff">${lines || '<span class="muted">clean</span>'}</pre><h3 style="margin-top:10px">Recent commits</h3><pre class="diff">${esc(g.log)}</pre>`;
    } else {
      const files = await api(`/api/workspace/tree?ws=${encodeURIComponent(name)}`);
      $('#ws-status').textContent = `${files.length} files`;
      $('#ws-body').innerHTML = `<div class="files">${files.map((f) => `<a data-f="${esc(f)}">${esc(f)}</a>`).join('')}</div><pre id="file-view" class="diff hidden"></pre>`;
      $('#ws-body').querySelectorAll('a[data-f]').forEach((a) => a.addEventListener('click', async () => {
        const r = await api(`/api/workspace/file?ws=${encodeURIComponent(name)}&file=${encodeURIComponent(a.dataset.f)}`);
        const v = $('#file-view'); v.classList.remove('hidden'); v.textContent = `── ${r.file}\n${r.text}`;
      }));
    }
  } catch (err) { $('#ws-body').innerHTML = `<div class="error">${esc(err.message)}</div>`; }
}

// ---------- fleet ----------
let FLEET = null;
async function loadFleet() {
  FLEET = await api('/api/fleet');
  $('#fleet-time').textContent = `observed ${ago(FLEET.observed_at)}`;
  const tasksOn = (n) => FLEET.running_tasks.filter((t) => t.tool_host === n.observation.host?.split('.')[0] || (n.kind === 'local' && t.tool_host === STATE.host) || t.inference_host === n.name);
  $('#nodes').innerHTML = FLEET.nodes.map((n) => {
    const o = n.observation || {}; const ok = o.status === 'ONLINE';
    const memUsed = o.mem_total && o.mem_avail != null ? 1 - o.mem_avail / o.mem_total : null;
    const gpu = (o.gpus || [])[0];
    const gpuUsed = gpu && gpu.mem_total_mb ? gpu.mem_used_mb / gpu.mem_total_mb : null;
    const models = (o.models || []).map((m) => `${esc(m.alias || m.file)}${m.port ? ` :${m.port}` : ''}`).join(', ') || 'none';
    const tk = tasksOn(n);
    return `<div class="card node" data-n="${esc(n.name)}">
      <div class="nh"><span class="dot ${ok ? 'completed' : 'error'}"></span><b>${esc(n.name)}</b><span class="badge ${n.trust === 'OWNER_SSH' || n.trust === 'LOCAL_HOST' ? 'ok' : 'bad'}">${esc(n.trust)}</span><span class="badge">${esc(o.status)}</span><span class="muted small">${esc(o.rtt_ms)} ms</span></div>
      <div class="kv"><span class="k">host</span><span>${esc(o.host)} · ${esc(o.os || '')} ${esc(o.arch || '')}</span>
        <span class="k">cpu</span><span>${esc(o.cpu)} · ${esc(o.cores)} threads · load ${esc((o.load || []).join(' '))}</span>
        <span class="k">memory</span><span>${gb(o.mem_avail)} free of ${gb(o.mem_total)}${o.mem_compressed ? ` · ${gb(o.mem_compressed)} compressed` : ''}</span></div>
      ${memUsed != null ? `<div class="meter"><i style="width:${(memUsed * 100).toFixed(0)}%"></i></div>` : ''}
      <div class="kv"><span class="k">accelerator</span><span>${gpu ? esc(gpu.name) : 'none observed'}${gpu && gpu.mem_total_mb ? ` · ${gpu.mem_used_mb}/${gpu.mem_total_mb} MiB · ${gpu.util_pct}% · ${gpu.temp_c}°C` : ''}</span></div>
      ${gpuUsed != null ? `<div class="meter"><i style="width:${(gpuUsed * 100).toFixed(0)}%;background:var(--violet)"></i></div>` : ''}
      <div class="kv"><span class="k">disk</span><span>${gb(o.disk_free)} free of ${gb(o.disk_total)}</span>
        <span class="k">models serving</span><span>${models}</span>
        <span class="k">services</span><span>${esc((o.units || []).join(', ') || '—')}</span>
        <span class="k">roles</span><span>${esc((n.roles || []).join(', '))}</span>
        <span class="k">Slinky work</span><span>${tk.length ? tk.map((t) => `${esc(t.agent)} (${esc(t.mode)})`).join(', ') : 'idle'}</span></div>
      ${o.error ? `<div class="error">${esc(o.error)}</div>` : ''}</div>`;
  }).join('');
  $('#nodes').querySelectorAll('.node').forEach((el) => el.addEventListener('click', () => nodeDetail(el.dataset.n)));
  $('#candidates').innerHTML = '<tr><th>address</th><th>MAC prefix</th><th>status</th></tr>' + (FLEET.candidates.map((c) => `<tr><td class="mono">${esc(c.address)}</td><td class="mono">${esc(c.mac_prefix)}</td><td>${esc(c.status)}</td></tr>`).join('') || '<tr><td colspan="3" class="muted">none</td></tr>');
}
function nodeDetail(name) {
  const n = FLEET.nodes.find((x) => x.name === name); const box = $('#node-detail'); box.classList.remove('hidden');
  const tasks = TASKS.filter((t) => t.tool_host === n.observation.host?.split('.')[0] || t.inference_host === n.name).slice(0, 15);
  box.innerHTML = `<h3>${esc(name)} — what it is doing for Slinky</h3>
    <div class="kv"><span class="k">enrolled</span><span>${esc(new Date(n.enrolled * 1000).toLocaleString())} · ${esc(n.kind)}${n.ssh ? ` via ${esc(n.ssh)}` : ''} · fingerprint pinned: ${esc(n.fingerprint_pinned)}</span>
    <span class="k">GPU processes</span><span>${esc(JSON.stringify(n.observation.gpu_apps || []))}</span>
    <span class="k">recent tasks</span><span>${tasks.map((t) => `${esc(t.agent)} · ${esc(t.status)} · ${esc((t.prompt || '').slice(0, 60))}`).join('<br>') || 'none'}</span></div>
    ${n.kind !== 'local' ? `<button class="danger" id="rm-node">Remove from fleet</button>` : ''}
    <details><summary>raw observation</summary><pre class="diff">${esc(JSON.stringify(n.observation, null, 1))}</pre></details>`;
  const rm = $('#rm-node'); if (rm) rm.addEventListener('click', async () => { if (confirm(`Remove ${name}?`)) { await api('/api/fleet/remove', { name }); loadFleet(); box.classList.add('hidden'); } });
}
$('#enroll').addEventListener('submit', async (e) => {
  e.preventDefault(); $('#e-msg').textContent = 'checking host key and SSH…';
  try {
    const r = await api('/api/fleet/enroll', { name: $('#e-name').value, ssh: $('#e-ssh').value, roles: $('#e-roles').value.split(',').map((s) => s.trim()).filter(Boolean) });
    $('#e-msg').textContent = `enrolled ${r.name} (${r.host_fingerprint})`; loadFleet();
  } catch (err) { $('#e-msg').textContent = err.message; }
});

// ---------- lineage ----------
async function loadLineage() {
  await loadTasks();
  const byParent = {}; TASKS.forEach((t) => { (byParent[t.parent_id || ''] ||= []).push(t); });
  const node = (t) => `<div class="lt" data-id="${esc(t.task_id)}"><span class="dot ${esc(t.status)}"></span> <b>${esc(t.agent)}</b>
    <span class="badge">${esc(t.agent_kind)}</span><span class="badge">inference ${esc(t.inference_host)}</span><span class="badge">tools ${esc(t.tool_host)}</span>
    <span class="badge">${esc(t.mode)}</span><span class="muted small">${esc(t.task_id)} · ${ago(t.created)}</span>
    <div class="hint">${esc((t.prompt || '').slice(0, 160))}</div>
    ${(byParent[t.task_id] || []).length ? `<div class="kids child">${byParent[t.task_id].map(node).join('')}</div>` : ''}</div>`;
  const roots = TASKS.filter((t) => !t.parent_id);
  $('#lineage').innerHTML = roots.map(node).join('') || '<div class="empty">No agents have run yet.</div>';
  $('#lineage').querySelectorAll('.lt').forEach((el) => el.addEventListener('click', (e) => {
    e.stopPropagation(); document.querySelector('[data-tab=work]').click(); selectTask(el.dataset.id);
  }));
}

// ---------- research ----------
async function loadResearch() {
  const r = await api('/api/research');
  const sk = r.skills.skills || [];
  $('#skills').innerHTML = `<h3>Inherited skills (${sk.length})</h3>` + (sk.map((s) => `<div class="exp"><b>${esc(s.name)}</b> <span class="badge ${s.status === 'admitted' ? 'ok' : 'bad'}">${esc(s.status)}</span>
    <span class="mono small muted">${esc((s.sha256 || '').slice(0, 12))}</span> <span class="muted small">by ${esc(s.author)} · ${ago(s.admitted_at)}</span>
    <div class="hint">${esc(s.description)}</div><div class="small">validation: ${esc(JSON.stringify(s.validation_summary || {}))}</div></div>`).join('<hr>') || '<div class="empty">No skills admitted yet.</div>');
  $('#research').innerHTML = r.research.map((x) => `<div class="card exp"><h4>${esc(x.title || x.id)}</h4>
    <span class="badge ${x.status === 'measured' ? 'ok' : x.status === 'negative' ? 'bad' : 'warn'}">${esc(x.status)}</span> <span class="muted small">${esc(x._source)}</span>
    <div class="hyp">${esc(x.hypothesis || '')}</div>
    ${x.table ? `<table><tr>${x.table.columns.map((c) => `<th>${esc(c)}</th>`).join('')}</tr>${x.table.rows.map((row) => `<tr>${row.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</table>` : ''}
    ${x.finding ? `<p>${esc(x.finding)}</p>` : ''}${x.limits ? `<p class="hint">Limits: ${esc(x.limits)}</p>` : ''}</div>`).join('');
}

// ---------- boot ----------
async function boot() {
  readToken();
  if (!TOKEN) { $('#locked').classList.remove('hidden'); $('#tab-work').classList.add('hidden'); return; }
  await loadState(); await loadTasks(); await loadApprovals();
  if (TASKS.length) selectTask(TASKS[0].task_id);
  if (STATE.workspaces.length) showWorkspace($('#f-ws').value);
  setInterval(() => { loadTasks().catch(() => {}); loadApprovals().catch(() => {}); }, 4000);
  setInterval(() => { if (!$('#tab-fleet').classList.contains('hidden')) loadFleet().catch(() => {}); }, 15000);
}
boot().catch((e) => console.error(e));
