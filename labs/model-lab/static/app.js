'use strict';
const $ = id => document.getElementById(id);
const fragment = new URLSearchParams(location.hash.slice(1));
const tokenFragment = fragment.get('token');
const inviteFragment = fragment.get('invite');
const bootstrapFragment = fragment.get('bootstrap');
if (tokenFragment) sessionStorage.setItem('haven-lab-token', tokenFragment);
if (inviteFragment) sessionStorage.setItem('haven-lab-invite', inviteFragment);
if (bootstrapFragment) sessionStorage.setItem('haven-lab-bootstrap', bootstrapFragment);
if (tokenFragment || inviteFragment || bootstrapFragment) history.replaceState(null, '', location.pathname);
const token = sessionStorage.getItem('haven-lab-token') || '';
let auth = {enabled:false,user:null,csrf:''};
let state = null, messages = [], activeJob = null, busy = false, benchRunning = false, benchStop = false, currentView = 'playground', refreshBusy = false, lastModelSignature = '', toastTimer, timer = null;
const sleep = ms => new Promise(r => setTimeout(r, ms));
function element(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
function toast(text, error=false) { const n = $('toast'); n.replaceChildren(document.createTextNode(text)); const x = element('button', '', '×'); x.onclick=()=>n.classList.add('hidden'); n.append(x); n.className='toast'+(error?' error':''); clearTimeout(toastTimer); toastTimer=setTimeout(()=>n.classList.add('hidden'),error?14000:6000); }
function authError(text=''){const n=$('auth-error');n.textContent=text;n.classList.toggle('hidden',!text);}
function showAuth(view,message=''){
 if(timer){clearInterval(timer);timer=null;}
 document.body.classList.add('auth-locked');$('auth-gate').classList.remove('hidden');
 document.querySelectorAll('.auth-view').forEach(n=>n.classList.add('hidden'));$('auth-'+view).classList.remove('hidden');authError(message);
 try{if($('account-dialog').open)$('account-dialog').close();}catch(_){}
}
function hideAuth(){document.body.classList.remove('auth-locked');$('auth-gate').classList.add('hidden');authError('');}
function configureRole(){
 const admin=!auth.enabled||auth.user?.role==='admin';
 document.querySelectorAll('.admin-only').forEach(n=>n.classList.toggle('hidden',!admin));
 $('account-button').classList.toggle('hidden',!auth.enabled);
 if(auth.enabled&&auth.user)$('account-button').textContent=auth.user.username+' · '+auth.user.role;
 if(!admin&&['models','experiments','setup'].includes(currentView))go('playground');
}
async function finishAuth(payload){
 auth.enabled=true;auth.user=payload.user;auth.csrf=payload.csrf||'';
 sessionStorage.removeItem('haven-lab-invite');sessionStorage.removeItem('haven-lab-bootstrap');
 hideAuth();configureRole();await refresh();if(timer)clearInterval(timer);timer=setInterval(refresh,4000);
}
function passwordPair(prefix){
 const password=$(prefix+'-password').value,confirm=$(prefix+'-confirm').value;
 if(password!==confirm)throw new Error('Passwords do not match.');
 return password;
}
async function boot(){
 try{
  const status=await publicApi('/api/auth/status');auth.enabled=!!status.enabled;
  if(!auth.enabled){hideAuth();configureRole();await refresh();timer=setInterval(refresh,4000);return;}
  const bootstrap=sessionStorage.getItem('haven-lab-bootstrap')||'';
  const invite=sessionStorage.getItem('haven-lab-invite')||'';
  if(status.setup_required){showAuth(bootstrap?'bootstrap':'wait');return;}
  if(invite){showAuth('invite');return;}
  try{await finishAuth(await api('/api/auth/me'));}catch(e){showAuth('login',e.status===401?'':'Could not verify this session.');}
 }catch(e){showAuth('login','Could not reach the Model Lab authentication service.');authError(e.message);}
}
$('login-form').onsubmit=async e=>{e.preventDefault();authError('');try{await finishAuth(await publicApi('/api/auth/login',{username:$('login-username').value,password:$('login-password').value}));$('login-password').value='';}catch(err){authError(err.message);}};
$('bootstrap-form').onsubmit=async e=>{e.preventDefault();authError('');try{const password=passwordPair('bootstrap');const bootstrap=sessionStorage.getItem('haven-lab-bootstrap')||'';await finishAuth(await publicApi('/api/auth/bootstrap',{token:bootstrap,username:$('bootstrap-username').value,password}));}catch(err){authError(err.message);}};
$('invite-form').onsubmit=async e=>{e.preventDefault();authError('');try{const password=passwordPair('invite');const invite=sessionStorage.getItem('haven-lab-invite')||'';await finishAuth(await publicApi('/api/auth/accept-invite',{token:invite,username:$('invite-username').value,password}));}catch(err){authError(err.message);}};
async function loadUsers(){
 if(!auth.enabled||auth.user?.role!=='admin')return;
 const data=await api('/api/auth/users'),root=$('account-users');root.replaceChildren();
 for(const user of data.users){
  const row=element('div','account-user');const meta=element('div');meta.append(element('strong','',user.username),element('span','',user.role+(user.disabled?' · disabled':'')));row.append(meta);
  if(user.id!==auth.user.id){const b=element('button','secondary',user.disabled?'Enable':'Disable');b.onclick=async()=>{try{await api('/api/auth/users/disable',{user_id:user.id,disabled:!user.disabled});await loadUsers();}catch(e){toast(e.message,true)}};row.append(b);}
  root.append(row);
 }
}
$('account-button').onclick=async()=>{if(!auth.enabled)return;$('account-title').textContent=auth.user.username;$('account-summary').textContent=`Signed in as ${auth.user.role}. Conversations remain in each browser tab unless exported.`;$('invite-result').classList.add('hidden');$('account-dialog').showModal();if(auth.user.role==='admin'){try{await loadUsers();}catch(e){toast(e.message,true)}}};
$('account-close').onclick=()=>$('account-dialog').close();
$('logout').onclick=async()=>{try{await api('/api/auth/logout',{});}catch(e){toast(e.message,true);return;}auth.user=null;auth.csrf='';messages=[];state=null;$('account-dialog').close();showAuth('login','Signed out.');};
$('create-invite').onclick=async()=>{try{const d=await api('/api/auth/invites',{role:$('invite-role').value});const link=location.origin+'/#invite='+encodeURIComponent(d.token);$('invite-link').value=link;$('invite-result').classList.remove('hidden');toast('Invite created. It expires in 24 hours and works once.');}catch(e){toast(e.message,true)}};
$('copy-invite').onclick=async()=>{const input=$('invite-link');try{if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(input.value);}else{input.focus();input.select();if(!document.execCommand('copy'))throw new Error('copy unavailable');}toast('Invite link copied.');}catch(_){input.focus();input.select();toast('Select and copy the invite link manually.');}};
async function requestJSON(path,data,sessionAware=true){
 const headers={}; if(token)headers['X-Lab-Token']=token;
 if(data!==undefined){headers['Content-Type']='application/json';if(sessionAware&&auth.csrf)headers['X-CSRF-Token']=auth.csrf;}
 const r=await fetch(path,{method:data===undefined?'GET':'POST',headers,body:data===undefined?undefined:JSON.stringify(data),credentials:'same-origin'});
 let d={};try{d=await r.json();}catch(_){}
 if(!r.ok){const e=new Error(d.error||`HTTP ${r.status}`);e.status=r.status;if(sessionAware&&auth.enabled&&r.status===401&&auth.user){auth.user=null;auth.csrf='';showAuth('login','Your session expired. Sign in again.');}throw e;}
 return d;
}
const api=(path,data)=>requestJSON(path,data,true);
const publicApi=(path,data)=>requestJSON(path,data,false);
function go(view) { if(auth.enabled&&auth.user?.role!=='admin'&&['models','experiments','setup'].includes(view))view='playground'; currentView=view; document.querySelectorAll('.page').forEach(x=>x.classList.toggle('active',x.id===view)); document.querySelectorAll('.nav').forEach(x=>x.classList.toggle('active',x.dataset.view===view)); if(view==='research') loadResearch(); if(view==='experiments') loadBenchmarks(); if(view==='setup') loadLog(); }
document.querySelectorAll('[data-view]').forEach(n=>n.onclick=()=>go(n.dataset.view)); document.querySelectorAll('[data-go]').forEach(n=>n.onclick=()=>go(n.dataset.go));
function metric(id,value,unit) { const n=$(id); n.replaceChildren(document.createTextNode(value==null?'—':value)); n.append(element('small','',unit)); }
function rate(value) { return typeof value==='number'&&Number.isFinite(value)?value.toFixed(2):'—'; }
function applyState(s) {
 state=s; const c=s.connection, connected=!!c.base, h=s.hardware, g=h.gpus[0];
 $('connection-pill').className='pill'+(connected?' connected':''); $('connection-pill').textContent=connected?`● ${c.kind==='strata'?'Strata':c.kind==='llama'?'llama.cpp':'Local API'} connected`:'○ No engine connected';
 $('active-model').textContent=connected?(c.display_model||c.model):'No model loaded'; $('engine-sub').textContent=connected?`${c.kind} · ${c.ownership==='OWNED'?'managed here':'external server'} · local inference`:'Connect Strata or load a CUDA model';
 const signature=connected?`${c.base}|${c.model}|${c.connected_at}`:'';
 if(lastModelSignature && lastModelSignature!==signature && messages.length && !busy) { messages=[]; $('messages').replaceChildren(element('p','muted','Engine changed. A fresh conversation prevents mixing model histories.')); }
 lastModelSignature=signature;
 metric('gpu-util',g?.utilization_pct==null?null:g.utilization_pct.toFixed(0),'%'); metric('vram-use',g?.memory_used_mib==null?null:(g.memory_used_mib/1024).toFixed(1),'GiB');
 $('gpu-name').textContent=g?g.name:`GPU telemetry: ${h.gpu_status.toLowerCase().replaceAll('_',' ')}`; $('vram-total').textContent=g?`of ${(g.memory_total_mib/1024).toFixed(1)} GiB · ${g.temperature_c??'—'} °C`:'No NVIDIA reading; never shown as zero';
 metric('ram-free',h.ram_available_gib==null?null:h.ram_available_gib.toFixed(1),'GiB'); $('ram-total').textContent=h.ram_total_gib?`of ${h.ram_total_gib.toFixed(1)} GiB · ${h.cpu_logical_threads} logical CPU threads`:'RAM measurement unavailable';
 $('send').disabled=busy||benchRunning||!connected; $('run-bench').disabled=busy||benchRunning||!connected;
 for(const id of ['connect','disconnect','unload','profile','context','threads','confirm-import'])$(id).disabled=benchRunning;
 $('install-engine').disabled=s.llama_installed; $('install-engine').textContent=s.llama_installed?'CUDA engine installed ✓':'Install pinned CUDA engine · ~645 MB';
 renderModels(); renderJobs();
}
async function refresh(){ if(refreshBusy)return; refreshBusy=true; try{applyState(await api('/api/state'));}catch(e){if(!state)toast(e.message,true);}finally{refreshBusy=false;} }
function renderModels(){ const grid=$('model-grid'); grid.replaceChildren(); for(const m of state.models){ const n=element('article','model-card'); n.append(element('span','tag',m.tag||'LOCAL IMPORT'),element('h2','',m.name),element('p','',m.description)); const meta=element('div','model-meta'); meta.append(element('span','',m.quant||'GGUF'),element('span','',m.download_gb?`${m.download_gb.toFixed(2)} GB download`:`${((m.size_bytes||0)/1e9).toFixed(2)} GB file`),element('span','',m.license||'Review model license')); n.append(meta); const buttons=element('div','button-row'); const action=element('button',m.downloaded?'primary':'secondary',m.downloaded?'Load on GPU ↗':'Download model ↓'); action.disabled=busy||benchRunning; action.onclick=()=>modelAction(m); buttons.append(action); if(m.source){const link=element('a','text-btn','Model card ↗');link.href=m.source;link.target='_blank';link.rel='noreferrer noopener';buttons.append(link);} n.append(buttons);grid.append(n); } }
function renderJobs(){ const root=$('jobs');root.replaceChildren(); for(const j of state.jobs.filter(x=>x.kind!=='generation').slice(-5)){const n=element('div','job');n.append(element('strong','',`${j.kind.replaceAll('-',' ')} · ${j.state}`),element('p','',j.error||j.message||'Working…'));if(j.state==='RUNNING'){const pr=element('progress');pr.max=1;if(j.progress!=null)pr.value=j.progress;n.append(pr);const c=element('button','text-btn','Cancel / pause');c.onclick=async()=>{try{await api('/api/cancel',{id:j.id});toast('Cancellation requested. Downloads retain their partial file.');}catch(e){toast(e.message,true)}};n.append(c);}root.append(n);} }
async function modelAction(m){try{if(!m.downloaded){if(!confirm(`Download ${m.name} (${m.download_gb} GB) from Hugging Face? The file will be checksum-verified before use.`))return;await api('/api/model/download',{id:m.id,confirmed:true});go('setup');toast('Download started. Progress appears below the engine log.');}else{const out=await api('/api/engine/start',{id:m.id,preset:$('profile').value,overrides:{context:Number($('context').value),threads:Number($('threads').value)},allow_tight:$('allow-tight').checked});go('setup');toast('Loading the CUDA engine. Watch the engine log for offload and errors.');await waitJob(out.job_id);await refresh();go('playground');toast('Model ready. GPU measurements reflect your actual hardware.');}await refresh();}catch(e){toast(e.message,true);}}
async function waitJob(id, render){while(true){const j=await api('/api/jobs/'+id);if(render)render(j);if(j.state!=='RUNNING'){if(j.state==='FAILED')throw new Error(j.error||'Job failed.');return j;}await sleep(350);}}
$('connect').onclick=async()=>{try{await api('/api/connect',{base:$('endpoint').value,key:$('backend-key').value,kind:$('backend-kind').value});$('backend-key').value='';await refresh();go('playground');toast('Connected locally. This lab will not stop the external server.');}catch(e){toast(e.message,true);}};
$('disconnect').onclick=async()=>{try{await api('/api/disconnect',{});await refresh();toast('Disconnected. The external server is still running.');}catch(e){toast(e.message,true);}};
$('native-ui').onclick=()=>{try{if(auth.enabled&&!['127.0.0.1','localhost'].includes(location.hostname))throw new Error('The engine-native UI stays on the Windows host. Use the Haven UI from this device.');const base=state?.connection?.base||$('endpoint').value;const u=new URL(base);if(u.hostname!=='127.0.0.1'||u.protocol!=='http:')throw new Error('Local URL required.');window.open(u.origin,'_blank','noopener,noreferrer');}catch(e){toast(e.message,true);}};
$('install-engine').onclick=async()=>{if(!confirm('Download about 645 MB of pinned official llama.cpp CUDA binaries into this lab? No driver or system CUDA Toolkit will be installed.'))return;try{await api('/api/engine/install',{confirmed:true});toast('Installing. Progress appears below.');await refresh();}catch(e){toast(e.message,true);}};
$('unload').onclick=async()=>{try{const r=await api('/api/engine/stop',{});await refresh();toast(`Owned engine: ${r.state}. External servers were not touched.`);}catch(e){toast(e.message,true);}};
$('profile').onchange=()=>{const p=state?.presets[$('profile').value];if(p){$('context').value=String(p.context);$('threads').value=String(p.threads);}};
$('temperature').oninput=()=>$('temp-label').textContent=$('temperature').value;
$('import-model').onclick=()=>$('import-dialog').showModal();
$('confirm-import').onclick=async e=>{e.preventDefault();try{await api('/api/model/import',{path:$('import-path').value});$('import-dialog').close();await refresh();toast('Registered your local model without copying it.');}catch(err){toast(err.message,true);}};
async function loadLog(){try{$('engine-log').textContent=(await api('/api/log')).text;}catch(e){toast(e.message,true)}}$('refresh-log').onclick=loadLog;
async function loadResearch(){try{$('research-text').textContent=(await api('/api/research')).text;}catch(e){toast(e.message,true)}}
function messageNode(role,text){$('welcome')?.remove();const n=element('div','message '+role);n.append(element('div','role',role==='user'?'YOU':'LOCAL MODEL'));const body=element('div','body',text);n.append(body);$('messages').append(n);return{n,body};}
function clearChat(){if(busy){toast('Stop or finish the current request first.');return;}messages=[];$('messages').replaceChildren(element('p','muted','New conversation. Nothing from the previous chat is sent.'));}
$('new-chat').onclick=clearChat;
function genSettings(){return{max_tokens:Number($('max-tokens').value),temperature:Number($('temperature').value),top_p:.8,seed:Number($('seed').value),reasoning:$('reasoning').value};}
async function sendMessage(override,benchmark=false,label='interactive',settings=null){
 if(busy||(!benchmark&&benchRunning))return null; const text=override||$('prompt').value.trim();if(!text)return null;
 busy=true;$('send').disabled=true;$('run-bench').disabled=true;$('cancel').classList.remove('hidden');
 const history=benchmark?[]:messages.slice();history.push({role:'user',content:text});if(!benchmark)messages=history;
 messageNode('user',text);const node=messageNode('assistant','Connecting…');let details=null,pre=null;
 try{const r=await api('/api/generate',{...(settings||genSettings()),messages:history,benchmark,label});activeJob=r.job_id;if(!benchmark)$('prompt').value='';
 const done=await waitJob(activeJob,j=>{node.body.textContent=j.text||(!j.reasoning?'Waiting for local inference…':'');if(j.reasoning){if(!details){details=element('details');details.append(element('summary','','Reasoning output'));pre=element('pre');details.append(pre);node.n.insertBefore(details,node.body);}pre.textContent=j.reasoning;}if(j.ttft_seconds!=null)metric('ttft',j.ttft_seconds.toFixed(2),'s');const box=$('messages');if(box.scrollHeight-box.scrollTop-box.clientHeight<180)box.scrollTop=box.scrollHeight;});
 if(done.text&&!benchmark&&done.state==='COMPLETED')messages.push({role:'assistant',content:done.text});
 const m=done.metrics||{};const meta=`${done.state} · first output ${m.ttft_seconds==null?'—':m.ttft_seconds.toFixed(2)+' s'} · end-to-end ${rate(m.end_to_end_tps)} tok/s · decode ${rate(m.backend_decode_tps)} tok/s`;
 node.n.append(element('div','result-meta',meta));if(done.state==='CANCELLED')node.n.append(element('p','field-note','HTTP cancellation requested. The backend may still compute; unload an owned engine or stop Strata in its own console for process termination.'));
 return done;
 }catch(e){if(!node.body.textContent||node.body.textContent==='Connecting…'||node.body.textContent==='Waiting for local inference…')node.body.textContent=e.message;else node.n.append(element('p','field-note',e.message));node.n.append(element('div','result-meta','FAILED · no hidden retry'));toast(e.message,true);return null;}finally{busy=false;activeJob=null;$('cancel').classList.add('hidden');await refresh();}}
$('send').onclick=()=>sendMessage();$('prompt').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}};
$('cancel').onclick=async()=>{try{if(activeJob)await api('/api/cancel',{id:activeJob});toast('Stop requested; partial output will be retained.');}catch(e){toast(e.message,true)}};
document.querySelectorAll('[data-prompt]').forEach(n=>n.onclick=()=>{$('prompt').value=n.dataset.prompt;$('prompt').focus();});
function saveJSON(name,data){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=element('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),500);}
$('export-chat').onclick=()=>saveJSON('haven-conversation.json',{exported_at:new Date().toISOString(),model:state?.connection?.model,messages});
const workloads={explain:'Explain the difference between DNS failure, TCP connection refusal, and an HTTP 403 response. Give a concise diagnostic sequence without suggesting changes to production systems.',code:'Write a Python function that removes duplicate strings while preserving order. Include type hints and five assert-based tests. Explain its time complexity briefly.',extract:'Return only JSON with fields service, error_code, first_seen, next_diagnostic. Evidence: On a synthetic test machine, ExampleApp returned HTTP 403 at 14:03 UTC. DNS resolves and TCP 443 connects. No authentication logs have been collected. Do not invent a root cause.'};
$('cancel-bench').onclick=async()=>{benchStop=true;if(activeJob)await api('/api/cancel',{id:activeJob});toast('Experiment stopping. No further repetitions will be sent.');};
$('run-bench').onclick=async()=>{if(benchRunning)return;const n=Number($('bench-repeats').value);if(!confirm(`Run ${n} real inference request(s) on the connected LOCAL model? No hidden warm-up. This consumes local compute, not a hosted API.`))return;
 const prompt=workloads[$('bench-workload').value],label=$('bench-label').value,settings={...genSettings(),expected_connected_at:state.connection.connected_at};benchRunning=true;benchStop=false;applyState(state);$('cancel-bench').classList.remove('hidden');$('run-bench').disabled=true;try{for(let i=0;i<n&&!benchStop;i++){$('bench-status').textContent=`Running ${i+1} of ${n}…`;const j=await sendMessage(prompt,true,`${label} / ${i+1}`,settings);if(!j||j.state!=='COMPLETED'){toast('Benchmark stopped after an incomplete request; failure remains recorded.',true);break;}}$('bench-status').textContent='Finished. Inspect individual outcomes and answer quality.';await loadBenchmarks();}finally{benchRunning=false;$('cancel-bench').classList.add('hidden');await refresh();}};
async function loadBenchmarks(){try{const d=await api('/api/benchmarks');$('bench-table').replaceChildren();for(const r of d.rows.slice(-30).reverse()){const tr=element('tr');for(const v of [r.label,r.model,r.metrics.ttft_seconds==null?'—':r.metrics.ttft_seconds.toFixed(2)+' s',r.metrics.end_to_end_tps==null?'—':r.metrics.end_to_end_tps+' t/s',r.metrics.backend_decode_tps==null?'—':r.metrics.backend_decode_tps+' t/s',r.state])tr.append(element('td','',String(v)));$('bench-table').append(tr);}if(!d.rows.length){const tr=element('tr');const td=element('td','muted','No benchmarks yet. Real measurements appear here after you run a model.');td.colSpan=6;tr.append(td);$('bench-table').append(tr);}}catch(e){toast(e.message,true)}}
$('export-bench').onclick=async()=>{try{saveJSON('haven-benchmarks.json',await api('/api/benchmarks'));}catch(e){toast(e.message,true)}};
$('exit').onclick=async()=>{if(!confirm('Exit this lab and stop its OWNED engine? External Strata remains in its own console.'))return;try{await api('/api/shutdown',{});$('connection-pill').textContent='Lab closed';$('send').disabled=true;clearInterval(timer);toast('Lab closed. You can close this tab.');}catch(e){toast(e.message,true)}};
boot();
