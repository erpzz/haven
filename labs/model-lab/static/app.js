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
let auth = {enabled:false,user:null,csrf:'',lanUrls:[]};
let state = null, messages = [], activeJob = null, busy = false, benchRunning = false, benchStop = false, currentView = 'playground', refreshBusy = false, lastModelSignature = '', toastTimer, timer = null;
const sleep = ms => new Promise(r => setTimeout(r, ms));
const CONTINUE_PROMPT = 'Continue exactly where you stopped. Do not restart, recap, or repeat text already written. Pick up with the next unfinished thought.';
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
  const status=await publicApi('/api/auth/status');auth.enabled=!!status.enabled;auth.lanUrls=Array.isArray(status.lan_urls)?status.lan_urls:[];
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
$('logout').onclick=async()=>{try{await api('/api/auth/logout',{});}catch(e){toast(e.message,true);return;}auth.user=null;auth.csrf='';messages=[];state=null;$('messages').replaceChildren();$('provider-controls')?.remove();providerSelection='managed';sessionStorage.removeItem('haven-provider');sessionStorage.removeItem('haven-diagnostic-job');diagnosticResumed=false;$('account-dialog').close();showAuth('login','Signed out.');};
$('create-invite').onclick=async()=>{try{const d=await api('/api/auth/invites',{role:$('invite-role').value});let origin=location.origin;if(['127.0.0.1','localhost'].includes(location.hostname)&&auth.lanUrls.length){try{origin=new URL(auth.lanUrls[0]).origin;}catch(_){}}const link=origin+'/#invite='+encodeURIComponent(d.token);$('invite-link').value=link;$('invite-result').classList.remove('hidden');toast('Invite created. It expires in 24 hours and works once.');}catch(e){toast(e.message,true)}};
$('copy-invite').onclick=async()=>{const input=$('invite-link');try{if(navigator.clipboard&&window.isSecureContext){await navigator.clipboard.writeText(input.value);}else{input.focus();input.select();if(!document.execCommand('copy'))throw new Error('copy unavailable');}toast('Invite link copied.');}catch(_){input.focus();input.select();toast('Select and copy the invite link manually.');}};
let linkExpired=false;
function linkExpiredBanner(){
 if(linkExpired)return;linkExpired=true;
 const b=element('div','callout','This tab\u2019s private link no longer works: the Haven Lab restarted and issued a new one. Nothing you type here will be sent. Reopen Haven from your Mac (Open Haven.command).');
 b.id='link-expired';b.setAttribute('role','alert');Object.assign(b.style,{borderColor:'var(--warn)',color:'var(--warn)',position:'sticky',top:'0',zIndex:'3',background:'var(--card)'});
 document.querySelector('main')?.prepend(b);$('send').disabled=true;$('chat-hint').textContent='Link expired \u2014 reopen Haven from your Mac.';
}
async function requestJSON(path,data,sessionAware=true){
 const headers={}; if(token)headers['X-Lab-Token']=token;
 if(data!==undefined){headers['Content-Type']='application/json';if(sessionAware&&auth.csrf)headers['X-CSRF-Token']=auth.csrf;}
 const r=await fetch(path,{method:data===undefined?'GET':'POST',headers,body:data===undefined?undefined:JSON.stringify(data),credentials:'same-origin'});
 let d={};try{d=await r.json();}catch(_){}
 if(!r.ok){const e=new Error(d.error||`HTTP ${r.status}`);e.status=r.status;if(r.status===401&&!auth.enabled&&token)linkExpiredBanner();if(sessionAware&&auth.enabled&&r.status===401&&auth.user){auth.user=null;auth.csrf='';showAuth('login','Your session expired. Sign in again.');}throw e;}
 return d;
}
const api=(path,data)=>requestJSON(path,data,true);
const publicApi=(path,data)=>requestJSON(path,data,false);
function go(view) { if(auth.enabled&&auth.user?.role!=='admin'&&['models','experiments','setup'].includes(view))view='playground'; currentView=view; document.querySelectorAll('.page').forEach(x=>x.classList.toggle('active',x.id===view)); document.querySelectorAll('.nav').forEach(x=>x.classList.toggle('active',x.dataset.view===view)); if(view==='research') loadResearch(); if(view==='experiments') loadBenchmarks(); if(view==='setup') loadLog(); }
document.querySelectorAll('[data-view]').forEach(n=>n.onclick=()=>go(n.dataset.view)); document.querySelectorAll('[data-go]').forEach(n=>n.onclick=()=>go(n.dataset.go));
function metric(id,value,unit) { const n=$(id); n.replaceChildren(document.createTextNode(value==null?'—':value)); n.append(element('small','',unit)); }
function rate(value) { return typeof value==='number'&&Number.isFinite(value)?value.toFixed(2):'—'; }
let providerSelection=sessionStorage.getItem('haven-provider')||'managed', providerProbeBusy=false, providerProbeAt=0;
let modelSearch='', favoritesOnly=false;
let favorites=new Set();
try{favorites=new Set(JSON.parse(localStorage.getItem('haven-model-favorites')||'[]'));}catch(_){}
$('model-search').oninput=()=>{modelSearch=$('model-search').value.trim().toLowerCase();if(state)renderModels();};
$('model-favorites-only').onchange=()=>{favoritesOnly=$('model-favorites-only').checked;if(state)renderModels();};
const cloudProvider=(s,id)=>(s?.providers||[]).find(p=>p.id===id&&p.kind==='cloud');
function planText(p){const o=p?.observed?.plan||{};const used=o.daily_cap?`${o.daily_used??'?'}/${o.daily_cap} today`:'';
 const reset=o.resets_text||(o.resets_at?new Date(o.resets_at*1000).toLocaleTimeString([],{hour:'numeric',minute:'2-digit'}):'');
 return [used,o.status==='LIMITED'?`plan limit${reset?' until '+reset:''}`:''].filter(Boolean).join(' · ');}
const readyCloud=s=>(s?.providers||[]).filter(p=>p.kind==='cloud'&&p.observed.state==='READY'&&p.observed.plan?.status!=='LIMITED');
function selectedConnection(s){
 if(providerSelection==='managed')return s.connection;
 if(providerSelection==='auto'&&s.connection?.base&&(!s.prepared_runtime?.peer_busy||s.connection.compute==='cpu')&&s.connection.kind==='llama')return s.connection;
 const p=providerSelection==='auto'?(s.providers||[]).find(x=>x.observed.state==='READY'&&x.automatic!==false):(s.providers||[]).find(x=>x.id===providerSelection);
 return p?{base:'provider:'+p.id,kind:p.kind,ownership:'EXTERNAL',model:p.model,display_model:p.display_model,compute:p.compute,worker_label:p.label,connected_at:p.id}:{};
}
function setProvider(value){
 if(busy||benchRunning){toast('Finish or stop the current request before changing workers.');return;}
 providerSelection=value;sessionStorage.setItem('haven-provider',value);lastModelSignature='';
 if(messages.length)clearChat();
 if(value!=='managed'&&!cloudProvider(state,value)&&Number($('max-tokens').value)>1024){$('max-tokens').value='512';toast('Short-context worker selected: output limit set to 512 tokens.');}
 if(state)applyState(state);
}
function providerControls(s){
 const admin=!auth.enabled||auth.user?.role==='admin';
 if(!admin){providerSelection='managed';return;}
 if(!$('provider-select')){
  const box=element('div','admin-only');box.id='provider-controls';
  const label=element('label','','Run this conversation on');const select=element('select');select.id='provider-select';select.setAttribute('aria-label','Inference worker');label.append(select);box.append(label);
  const note=element('p','field-note');note.id='provider-note';box.append(note);
  const button=element('button','secondary','Refresh workers');button.id='provider-refresh';button.onclick=async()=>{try{await api('/api/providers/reload',{});await api('/api/providers/probe',{});await refresh();}catch(e){toast(e.message,true);}};box.append(button);
  // First-party artifact picker: never confuse the provider route with a real GGUF.
  const quick=element('div','model-quick-select');quick.id='model-quick-select';
  const modelLabel=element('label','','Installed Slink artifact');
  const modelSelect=element('select');modelSelect.id='artifact-select';
  modelSelect.setAttribute('aria-label','Select installed Slink artifact');modelLabel.append(modelSelect);quick.append(modelLabel);
  const load=element('button','secondary','Load selected artifact');load.id='artifact-load';
  load.onclick=()=>{
   const m=(state?.models||[]).find(x=>x.id===modelSelect.value&&x.downloaded);
   if(!m){toast('Model is not installed; open the Models page to review and download.',true);return;}
   if(!confirm('Load '+m.name+' on Slink? This uses the selected CPU/GPU profile. Haven will enforce active job and resource guards.'))return;
   modelAction(m);
  };quick.append(load);box.append(quick);
  document.querySelector('.card-heading').after(box);select.onchange=()=>setProvider(select.value);
 }
 const select=$('provider-select');const rows=[{id:'managed',label:`Slink · ${s.connection?.compute==='cpu'?'CPU':s.connection?.kind==='strata'?'Strata':'GPU'} · current runtime`},{id:'auto',label:'Automatic · ready private worker'},...(s.providers||[]).map(p=>({id:p.id,label:p.kind==='cloud'?`☁ ${p.label} · leaves this house · ${p.observed.state}${planText(p)?' · '+planText(p):''}`:`${p.label} · ${p.compute.toUpperCase()} · ${p.display_model} · ${p.observed.state}`}))];
 const signature=JSON.stringify(rows);if(select.dataset.signature!==signature){select.replaceChildren(...rows.map(p=>{const o=element('option','',p.label);o.value=p.id;return o;}));select.dataset.signature=signature;}
 select.value=providerSelection;select.disabled=busy||benchRunning;
 const cloud=cloudProvider(s,providerSelection);$('provider-note').style.color=cloud?'var(--warn)':'';
 $('provider-note').textContent=cloud?`Leaves this house: every turn of this conversation is sent to ${cloud.vendor} through your own plan (${cloud.route_class}). No tools, files or Haven memory; never chosen by Automatic; no paid API fallback.${planText(cloud)?' Plan: '+planText(cloud)+'.':''}`:providerSelection==='managed'?'Using the current Slink runtime. CPU/GPU loading is available in Model library.':providerSelection==='auto'?'Uses an already-ready private worker. No model starts, downloads, paid calls or cloud fallback. The actual worker is shown with each result.':'Inference runs on the selected machine. The cards above measure Slink, the control host. New worker selections start a fresh conversation.';
 const quick=$('model-quick-select'),artifact=$('artifact-select'),load=$('artifact-load');
  const installed=(s.models||[]).filter(m=>m.downloaded);
  const artifactSignature=JSON.stringify(installed.map(m=>[m.id,m.name,m.quant]));
  if(artifact.dataset.signature!==artifactSignature){
   const before=artifact.value;
   artifact.replaceChildren(...installed.map(m=>{const o=element('option','',m.name+' · '+(m.quant||'GGUF'));o.value=m.id;return o;}));
   artifact.dataset.signature=artifactSignature;
   if(installed.some(m=>m.id===before))artifact.value=before;
  }
  quick.classList.toggle('hidden',providerSelection!=='managed');
  load.disabled=busy||benchRunning||!installed.length;
  load.textContent=installed.length?'Load selected artifact on Slink':'No installed artifacts — open Models';
  $('provider-refresh').disabled=providerProbeBusy||busy;
 if((s.providers||[]).length&&!providerProbeBusy&&Date.now()>providerProbeAt){providerProbeBusy=true;providerProbeAt=Date.now()+30000;api('/api/providers/probe',{}).then(()=>refresh()).catch(()=>{}).finally(()=>{providerProbeBusy=false;});}
}
function applyState(s) {
 const firstLoad=!state;
 state=s;providerControls(s);const c=selectedConnection(s), connected=!!c.base, h=s.hardware, g=h.gpus[0];
 if(firstLoad&&c.compute==='cpu'){$('compute-lane').value='cpu';syncComputeLane();}
 $('connection-pill').className='pill'+(connected?' connected':''); $('connection-pill').textContent=connected?`● ${c.compute==='cpu'?'CPU-only':c.compute==='gpu'?'GPU · CUDA':c.kind==='strata'?'Strata':c.kind==='llama'?'llama.cpp':'Local API'} connected`:'○ No engine connected';
 $('active-model').textContent=connected?(c.display_model||c.model):'No model loaded'; $('engine-sub').textContent=connected?`${c.worker_label||'Slink'} · ${c.kind} · ${c.compute||'GPU'} · private inference`:'Select a ready worker or load a prepared model';
 const signature=connected?`${c.base}|${c.model}|${c.connected_at}`:'';
 if(lastModelSignature && lastModelSignature!==signature && messages.length && !busy) { messages=[]; $('messages').replaceChildren(element('p','muted','Engine changed. A fresh conversation prevents mixing model histories.')); }
 lastModelSignature=signature;
 metric('gpu-util',g?.utilization_pct==null?null:g.utilization_pct.toFixed(0),'%'); metric('vram-use',g?.memory_used_mib==null?null:(g.memory_used_mib/1024).toFixed(1),'GiB');
 $('gpu-name').textContent=g?g.name:`GPU telemetry: ${h.gpu_status.toLowerCase().replaceAll('_',' ')}`; $('vram-total').textContent=g?`of ${(g.memory_total_mib/1024).toFixed(1)} GiB · ${g.temperature_c??'—'} °C`:'No NVIDIA reading; never shown as zero';
 metric('ram-free',h.ram_available_gib==null?null:h.ram_available_gib.toFixed(1),'GiB'); $('ram-total').textContent=h.ram_total_gib?`of ${h.ram_total_gib.toFixed(1)} GiB · ${h.cpu_logical_threads} logical CPU threads`:'RAM measurement unavailable';
 const switching=!!s.prepared_runtime?.switch_job;
 const sw=switching?(s.jobs||[]).find(j=>j.id===s.prepared_runtime.switch_job):null;
 const swText=sw?`${(sw.message||'Switching prepared runtimes\u2026').replace(/\u2026$/,'')} \u2014 ${Math.floor((sw.elapsed_seconds??(Date.now()/1000-(sw.created_at||Date.now()/1000)))/60)} min elapsed${sw.target==='strata'?' of about 15 (Strata reads 33 GB of experts over the slow disk)':''}.`:'';
 if(!linkExpired)$('chat-hint').textContent=switching?swText:'Text-only \u00b7 Enter to send \u00b7 Shift+Enter for a new line';
 $('send').disabled=busy||benchRunning||switching||!connected; $('run-bench').disabled=busy||benchRunning||switching||!connected;
 for(const id of ['connect','disconnect','unload','profile','context','threads','confirm-import'])$(id).disabled=benchRunning||switching;
 const linux=h.platform==='linux';
 const starting=(s.jobs||[]).some(j=>j.kind==='engine-start'&&j.state==='RUNNING');
 $('compute-lane').disabled=benchRunning||busy||starting||switching||!linux;
 $('install-engine').disabled=s.llama_installed||!s.engine_install_supported;
 const engineMB=Math.round((s.engine_download_bytes||645000000)/1e6);
 $('install-engine').textContent=s.llama_installed?'CUDA engine installed ✓':s.engine_install_supported?`Install pinned CUDA engine · ~${engineMB} MB`:'Automatic engine setup unavailable';
 if(linux){
  let runtimeControls=$('prepared-runtime-controls');
  if(!runtimeControls){
   runtimeControls=element('div','button-row admin-only');runtimeControls.id='prepared-runtime-controls';
   for(const [target,label] of [['strata','Use Strata'],['fast4b','Use fast 4B']]){
    const button=element('button','secondary',label);button.id='runtime-'+target;
    button.onclick=async()=>{try{const result=await api('/api/runtime/switch',{target});toast('Switch started. Progress appears in Setup; cancellation is available there.');go('setup');await refresh();const done=await waitJob(result.job_id,undefined,3000);await refresh();go('playground');toast(done.state==='COMPLETED'?'Runtime ready. Chat here in Haven.':'Switch stopped. '+(done.fast4b_restored?'Fast 4B was restored.':''));}catch(e){toast(e.message,true);}};
    runtimeControls.append(button);
   }
   const note=element('p','field-note');note.id='runtime-note';runtimeControls.append(note);
   const investigate=element('button','secondary','Investigate host');investigate.id='diagnose-host';investigate.onclick=()=>startDiagnostic();runtimeControls.append(investigate);
   document.querySelector('.card-heading').after(runtimeControls);
  }
  runtimeControls.classList.toggle('hidden',auth.enabled&&auth.user?.role!=='admin');
  const runtime=s.prepared_runtime||{};
  for(const target of ['strata','fast4b'])$('runtime-'+target).disabled=busy||benchRunning||!!runtime.switch_job||runtime.peer_busy===true||s.connection?.compute==='cpu';
  $('diagnose-host').disabled=busy||benchRunning||switching||runtime.peer_busy===true||providerSelection!=='managed'||c.kind!=='llama'||c.ownership!=='OWNED';
  $('runtime-note').textContent=runtime.peer_busy?'An engineering experiment has reserved the GPU. Your current job will be preserved.':runtime.switch_job?swText+' Cancel from Setup.':s.connection?.compute==='cpu'?'CPU inference is active. Unload it explicitly before starting a prepared GPU runtime.':'Prepared models · no downloads · Strata cold startup can take about 15 minutes.';
  $('install-note').textContent='Pinned Ubuntu CUDA runtime. SHA-256 verified; installed only in this lab. The NVIDIA driver is managed separately.';
  document.querySelector('footer span:last-child').textContent='Haven Core · Linux';
  document.querySelector('.strata-panel ol').classList.add('hidden');
  document.querySelector('.strata-panel > p').textContent='Strata runs large models using GPU and RAM expert caching. The prepared Linux service uses the pinned official release and stays separate from llama.cpp.';
  document.querySelector('.strata-panel .field-note').textContent='Use the runtime buttons in Playground to start and switch the prepared models. No terminal command, second browser page or API key is needed. This attachment-only button is for an already-running service.';
  if(!$('connect-haven-strata')){
   const prepared=element('button','primary','Connect Haven Strata ↗');prepared.id='connect-haven-strata';
   prepared.onclick=async()=>{try{await api('/api/connect/haven-strata',{});await refresh();go('playground');toast('Connected to Haven Strata. Its private credential stays on the server.');}catch(e){toast(e.message,true);}};
   $('connect').parentElement.append(prepared);
  }
  $('connect-haven-strata').disabled=busy||benchRunning;
 }
 renderModels(); renderJobs();
 if(!diagnosticResumed&&sessionStorage.getItem('haven-diagnostic-job')&&(!auth.enabled||auth.user?.role==='admin')){diagnosticResumed=true;showDiagnostic(sessionStorage.getItem('haven-diagnostic-job'));}
}
async function refresh(){ if(refreshBusy)return; refreshBusy=true; try{applyState(await api('/api/state'));}catch(e){if(!state)toast(e.message,true);}finally{refreshBusy=false;} }
function renderModels(){
 const grid=$('model-grid');grid.replaceChildren();
 const all=state?.models||[];
 const rows=all.filter(m=>(!favoritesOnly||favorites.has(m.id))&&(!modelSearch||[m.name,m.description,m.id,m.quant,m.tag,m.license].filter(Boolean).join(' ').toLowerCase().includes(modelSearch)));
 $('model-count').textContent=rows.length+' of '+all.length+' prepared models';
 if(!rows.length)grid.append(element('p','muted','No matching models in the prepared catalog. Search public model metadata above.'));
 for(const m of rows){
  const n=element('article','model-card'),top=element('div','model-card-top');
  top.append(element('span','tag',m.downloaded?'INSTALLED · NOT NECESSARILY RUNNING':'CATALOG · NOT INSTALLED'));
  const fav=element('button','secondary model-favorite',favorites.has(m.id)?'★ Saved':'☆ Favorite');
  fav.setAttribute('aria-label',(favorites.has(m.id)?'Remove favorite ':'Add favorite ')+m.name);
  fav.onclick=()=>{if(favorites.has(m.id))favorites.delete(m.id);else favorites.add(m.id);
   try{localStorage.setItem('haven-model-favorites',JSON.stringify([...favorites]));}catch(_){}renderModels();};
  top.append(fav);n.append(top,element('h2','',m.name),element('p','',m.description));
  const meta=element('div','model-meta');
  meta.append(element('span','',m.quant||'GGUF'),element('span','',m.download_gb?m.download_gb.toFixed(2)+' GB download':((m.size_bytes||0)/1e9).toFixed(2)+' GB file'),element('span','',m.license||'Review model license'));n.append(meta);
  const buttons=element('div','button-row');
  const action=element('button',m.downloaded?'primary':'secondary',m.downloaded?'Load on '+($('compute-lane').value==='cpu'?'CPU':'GPU')+' ↗':'Download model ↓');
  action.disabled=busy||benchRunning;action.onclick=()=>modelAction(m);buttons.append(action);
  if(m.source){const link=element('a','text-btn','Model card ↗');link.href=m.source;link.target='_blank';link.rel='noreferrer noopener';buttons.append(link);}
  n.append(buttons);grid.append(n);
 }
}
function renderJobs(){ const root=$('jobs');root.replaceChildren(); for(const j of state.jobs.filter(x=>x.kind!=='generation').slice(-5)){const n=element('div','job');n.append(element('strong','',`${j.kind.replaceAll('-',' ')} · ${j.state}`),element('p','',j.error||j.message||'Working…'));if(j.state==='RUNNING'){const pr=element('progress');pr.max=1;if(j.progress!=null)pr.value=j.progress;n.append(pr);const c=element('button','text-btn','Cancel / pause');c.onclick=async()=>{try{await api('/api/cancel',{id:j.id});toast('Cancellation requested. Downloads retain their partial file.');}catch(e){toast(e.message,true)}};n.append(c);}root.append(n);} }
async function modelAction(m){try{if(!m.downloaded){if(!confirm(`Download ${m.name} (${m.download_gb} GB) from Hugging Face? The file will be checksum-verified before use.`))return;await api('/api/model/download',{id:m.id,confirmed:true});go('setup');toast('Download started. Progress appears below the engine log.');}else{const compute=$('compute-lane').value;const out=await api('/api/engine/start',{id:m.id,preset:$('profile').value,compute,overrides:{context:Number($('context').value),threads:Number($('threads').value)},allow_tight:$('allow-tight').checked});go('setup');toast(`Loading the ${compute==='cpu'?'CPU-only':'CUDA'} engine. Watch the engine log for real startup status.`);const job=await waitJob(out.job_id);if(job.state!=='COMPLETED')throw new Error(job.error||`Engine start ${job.state.toLowerCase()}.`);await refresh();go('playground');toast(`Model ready on ${compute==='cpu'?'CPU':'GPU'}.`);}await refresh();}catch(e){toast(e.message,true);}}
async function waitJob(id, render,interval=350){while(true){const j=await api('/api/jobs/'+id);if(render)render(j);if(j.state!=='RUNNING'){if(j.state==='FAILED')throw new Error(j.error||'Job failed.');return j;}await sleep(interval);}}
$('connect').onclick=async()=>{try{await api('/api/connect',{base:$('endpoint').value,key:$('backend-key').value,kind:$('backend-kind').value});$('backend-key').value='';await refresh();go('playground');toast('Connected locally. This lab will not stop the external server.');}catch(e){toast(e.message,true);}};
$('disconnect').onclick=async()=>{try{await api('/api/disconnect',{});await refresh();toast('Disconnected. The external server is still running.');}catch(e){toast(e.message,true);}};
$('native-ui').onclick=()=>{try{if(auth.enabled&&!['127.0.0.1','localhost'].includes(location.hostname))throw new Error('The engine-native UI stays on the Windows host. Use the Haven UI from this device.');const base=state?.connection?.base||$('endpoint').value;const u=new URL(base);if(u.hostname!=='127.0.0.1'||u.protocol!=='http:')throw new Error('Local URL required.');window.open(u.origin,'_blank','noopener,noreferrer');}catch(e){toast(e.message,true);}};
$('install-engine').onclick=async()=>{const mb=Math.round((state?.engine_download_bytes||645000000)/1e6);if(!confirm(`Download about ${mb} MB of pinned official llama.cpp CUDA binaries into this lab? No driver or system CUDA Toolkit will be installed.`))return;try{await api('/api/engine/install',{confirmed:true});toast('Installing. Progress appears below.');await refresh();}catch(e){toast(e.message,true);}};
$('unload').onclick=async()=>{if(state?.connection?.ownership==='OWNED'&&state.connection.compute!=='cpu'&&!confirm('Unload the Lab-owned GPU model? Another agent or user may be using this Lab connection. Independent external services will NOT be stopped.'))return;try{const r=await api('/api/engine/stop',{});await refresh();toast(`Owned engine: ${r.state}. External servers were not touched.`);}catch(e){toast(e.message,true);}};
$('profile').onchange=()=>{const p=state?.presets[$('profile').value];if(p){$('context').value=String(p.context);$('threads').value=String(p.threads);}};
function syncComputeLane(){
 const cpu=$('compute-lane').value==='cpu';
 for(const option of $('profile').options)option.disabled=(option.value==='cpu')!==cpu;
 $('profile').value=cpu?'cpu':'balanced';$('profile').onchange();
 $('allow-tight').checked=false;$('allow-tight').disabled=cpu;
 $('compute-note').textContent=cpu?'CPU-only: 0 GPU layers, no visible CUDA devices in the engine process. Limited to 8 threads and checked against available system RAM; keep headroom for other agents.':'GPU: existing CUDA fast path, subject to the RTX 2070 Super VRAM gate.';
 if(state)renderModels();
}
$('compute-lane').onchange=syncComputeLane;
for(const option of $('profile').options)if(option.value==='cpu')option.disabled=true;
$('temperature').oninput=()=>$('temp-label').textContent=$('temperature').value;
$('import-model').onclick=()=>$('import-dialog').showModal();
$('confirm-import').onclick=async e=>{e.preventDefault();try{await api('/api/model/import',{path:$('import-path').value});$('import-dialog').close();await refresh();toast('Registered your local model without copying it.');}catch(err){toast(err.message,true);}};
async function loadLog(){try{$('engine-log').textContent=(await api('/api/log')).text;}catch(e){toast(e.message,true)}}$('refresh-log').onclick=loadLog;
async function loadResearch(){try{$('research-text').textContent=(await api('/api/research')).text;}catch(e){toast(e.message,true)}}
function messageNode(role,text,who){$('welcome')?.remove();const n=element('div','message '+role);n.append(element('div','role',role==='user'?'YOU':who||'LOCAL MODEL'));const body=element('div','body',text);n.append(body);$('messages').append(n);return{n,body};}
let diagnosticResumed=false;
async function startDiagnostic(){
 if(busy||benchRunning)return;
 try{const question=$('prompt').value.trim();const result=await api('/api/diagnostics',question?{question}:{});sessionStorage.setItem('haven-diagnostic-job',result.job_id);diagnosticResumed=true;$('prompt').value='';await showDiagnostic(result.job_id);}catch(e){toast(e.message,true);}
}
async function showDiagnostic(id){
 busy=true;activeJob=id;$('cancel').classList.remove('hidden');const node=messageNode('assistant','Loading the saved diagnostic…');
 try{let job;while(true){job=await api('/api/diagnostics/'+id);node.body.textContent=job.text||job.message||job.state;if(job.state!=='RUNNING')break;await sleep(1500);}
  node.n.append(element('div','result-meta',`${job.state} · saved diagnostic ${id} · ${job.trace?.length||0} observed tools`));
  node.n.append(element('p','field-note','Request status describes execution. The diagnosis still needs checking against its evidence.'));
  for(const warning of job.citation_check?.warnings||[])node.n.append(element('p','field-note',warning));
  if(job.error)node.n.append(element('p','field-note',job.error));
  const details=element('details');details.append(element('summary','','Observed evidence and command exit codes'));
  details.append(element('pre','',JSON.stringify(job.trace||[],null,2)));node.n.append(details);
 }catch(e){node.body.textContent=e.message;toast(e.message,true);}finally{busy=false;activeJob=null;$('cancel').classList.add('hidden');await refresh();}
}
function clearChat(){if(busy){toast('Stop or finish the current request first.');return;}messages=[];$('messages').replaceChildren(element('p','muted','New conversation. Nothing from the previous chat is sent.'));}
$('new-chat').onclick=clearChat;
function genSettings(){return{...(cloudProvider(state,providerSelection)?{egress_ack:'HOSTED_SUBSCRIPTION'}:{}),max_tokens:Number($('max-tokens').value),temperature:Number($('temperature').value),top_p:.8,seed:Number($('seed').value),reasoning:$('reasoning').value,provider_id:providerSelection};}
function offerEscalation(node){
 const admin=!auth.enabled||auth.user?.role==='admin',lanes=readyCloud(state);if(!admin||!lanes.length)return;
 const row=element('div','button-row');
 for(const p of lanes){const b=element('button','secondary escalate',`Ask ${p.label.replace('Cloud · ','')} instead ☁`);b.title=`Re-asks the same question in the ${p.vendor} cloud lane after you confirm.`;b.onclick=()=>escalate(p);row.append(b);}
 node.n.append(row);
}
async function escalate(p){
 if(busy||benchRunning){toast('Finish or stop the current request first.');return;}
 const i=messages.map(m=>m.role).lastIndexOf('user');if(i<0)return;
 const prior=messages.slice(0,i),question=messages[i].content,sending=[...prior,messages[i]];
 const chars=sending.reduce((n,m)=>n+m.content.length,0);
 if(!confirm(`Send this conversation to ${p.vendor} through your own plan (${p.route_class})?\n\n${sending.length} message${sending.length>1?'s':''}, ${chars.toLocaleString()} characters will leave this house. No tools, files or Haven memory are shared.${planText(p)?'\n\nPlan: '+planText(p)+'.':''}`))return;
 // The cloud answer replaces the local one in the conversation; later turns go back to the selected worker.
 messages=prior;
 await sendMessage(question,false,'escalation',{...genSettings(),provider_id:p.id,egress_ack:'HOSTED_SUBSCRIPTION',reasoning:'none',max_tokens:Math.min(Number($('max-tokens').value)||1024,4096)},true);
}
async function sendMessage(override,benchmark=false,label='interactive',settings=null,silentUser=false){
 if(busy||(!benchmark&&benchRunning))return null; const text=override||$('prompt').value.trim();if(!text)return null;
 busy=true;$('send').disabled=true;$('run-bench').disabled=true;$('cancel').classList.remove('hidden');
 const history=benchmark?[]:messages.slice();history.push({role:'user',content:text});if(!benchmark)messages=history;
 const sent=settings||genSettings(),cloud=cloudProvider(state,sent.provider_id),waiting=cloud?`Waiting for ${cloud.vendor} (cloud lane)…`:'Waiting for local inference…';
 if(!silentUser)messageNode('user',text);const node=messageNode('assistant','Connecting…',cloud?'CLOUD · '+cloud.vendor.toUpperCase():null);let details=null,pre=null;
 try{const r=await api('/api/generate',{...sent,messages:history,benchmark,label});activeJob=r.job_id;if(!benchmark)$('prompt').value='';
 const done=await waitJob(activeJob,j=>{node.body.textContent=j.text||(!j.reasoning?waiting:'');if(j.reasoning){if(!details){details=element('details');details.append(element('summary','','Reasoning output'));pre=element('pre');details.append(pre);node.n.insertBefore(details,node.body);}pre.textContent=j.reasoning;}if(j.ttft_seconds!=null)metric('ttft',j.ttft_seconds.toFixed(2),'s');const box=$('messages');if(box.scrollHeight-box.scrollTop-box.clientHeight<180)box.scrollTop=box.scrollHeight;});
 const outputLimited=done.state==='OUTPUT_LIMIT'||done.finish_reason==='length';
 if(done.text&&!benchmark&&(done.state==='COMPLETED'||outputLimited))messages.push({role:'assistant',content:done.text});
 const outcome=outputLimited?'OUTPUT LIMIT REACHED':done.state==='CANCELLED'?'STOPPED':done.state;
 const m=done.metrics||{},reason=done.finish_reason?` · finish ${done.finish_reason}`:'';const meta=`${outcome}${reason} · first output ${m.ttft_seconds==null?'—':m.ttft_seconds.toFixed(2)+' s'} · end-to-end ${rate(m.end_to_end_tps)} tok/s · decode ${rate(m.backend_decode_tps)} tok/s`;
 node.n.append(element('div','result-meta',`${done.worker_label||'Slink'} · ${done.compute||'GPU'} · ${meta}`));
// Report observed, not assumed, routing. A provider selector isn't an artifact.
  const route=element('details','route-inspector');
  route.append(element('summary','','Routing & model identity · inspect this response'));
  const trace={requested:{selector:sent.provider_id,mode:sent.provider_id==='auto'?'automatic':'manual'},
    observed:{provider_id:done.provider_id??null,worker:done.worker_label??null,reported_model:done.model??null,
      model_sha256:done.model_sha256??null,digest_provenance:done.digest_provenance??null,
      compute:done.compute??null,egress:done.egress??null,route_reason:done.route_reason??null},
    execution:{job_id:done.id??null,state:done.state,finish_reason:done.finish_reason??null},
    fallback:'UNDETERMINED',identity_attestation:'NOT_VERIFIED'};
  route.append(element('pre','',JSON.stringify(trace,null,2)));node.n.append(route);
 if(done.digest_provenance==='WORKER_DECLARED')node.n.append(element('p','field-note','Model digest: verified on worker; declared to Haven.'));
 if(done.route_reason)node.n.append(element('p','field-note',done.route_reason));
 if(outputLimited&&!benchmark){const actions=element('div','button-row');const cont=element('button','secondary continue-generation','Continue ↗');cont.onclick=async()=>{cont.disabled=true;cont.textContent='Continuing…';await sendMessage(CONTINUE_PROMPT,false,'continue',null,true);};actions.append(cont);node.n.append(actions);}
 if(!benchmark&&!cloud)offerEscalation(node);
 if(done.state==='CANCELLED')node.n.append(element('p','field-note','HTTP cancellation requested. The backend may still compute; unload an owned engine or stop Strata in its own console for process termination.'));
 return done;
 }catch(e){if(!node.body.textContent||node.body.textContent==='Connecting…'||node.body.textContent===waiting)node.body.textContent=e.message;else node.n.append(element('p','field-note',e.message));node.n.append(element('div','result-meta','FAILED · no hidden retry'));if(!benchmark&&!cloud&&!linkExpired)offerEscalation(node);toast(e.message,true);return null;}finally{busy=false;activeJob=null;$('cancel').classList.add('hidden');await refresh();}}
$('send').onclick=()=>sendMessage();$('prompt').onkeydown=e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage();}};
$('cancel').onclick=async()=>{try{if(activeJob)await api('/api/cancel',{id:activeJob});toast('Stop requested; partial output will be retained.');}catch(e){toast(e.message,true)}};
document.querySelectorAll('[data-prompt]').forEach(n=>n.onclick=()=>{$('prompt').value=n.dataset.prompt;$('prompt').focus();});
function saveJSON(name,data){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=element('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),500);}
$('export-chat').onclick=()=>saveJSON('haven-conversation.json',{exported_at:new Date().toISOString(),model:state?.connection?.model,messages});
const workloads={explain:'Explain the difference between DNS failure, TCP connection refusal, and an HTTP 403 response. Give a concise diagnostic sequence without suggesting changes to production systems.',code:'Write a Python function that removes duplicate strings while preserving order. Include type hints and five assert-based tests. Explain its time complexity briefly.',extract:'Return only JSON with fields service, error_code, first_seen, next_diagnostic. Evidence: On a synthetic test machine, ExampleApp returned HTTP 403 at 14:03 UTC. DNS resolves and TCP 443 connects. No authentication logs have been collected. Do not invent a root cause.'};
$('cancel-bench').onclick=async()=>{benchStop=true;if(activeJob)await api('/api/cancel',{id:activeJob});toast('Experiment stopping. No further repetitions will be sent.');};
$('run-bench').onclick=async()=>{if(benchRunning)return;const n=Number($('bench-repeats').value);if(!confirm(`Run ${n} real inference request(s) on the connected LOCAL model? No hidden warm-up. This consumes local compute, not a hosted API.`))return;
 const prompt=workloads[$('bench-workload').value],label=$('bench-label').value,settings={...genSettings(),...(providerSelection==='managed'?{expected_connected_at:state.connection.connected_at}:{})};benchRunning=true;benchStop=false;applyState(state);$('cancel-bench').classList.remove('hidden');$('run-bench').disabled=true;try{for(let i=0;i<n&&!benchStop;i++){$('bench-status').textContent=`Running ${i+1} of ${n}…`;const j=await sendMessage(prompt,true,`${label} / ${i+1}`,settings);if(!j||j.state!=='COMPLETED'){toast('Benchmark stopped after an incomplete request; failure remains recorded.',true);break;}}$('bench-status').textContent='Finished. Inspect individual outcomes and answer quality.';await loadBenchmarks();}finally{benchRunning=false;$('cancel-bench').classList.add('hidden');await refresh();}};
async function loadBenchmarks(){try{const d=await api('/api/benchmarks');$('bench-table').replaceChildren();for(const r of d.rows.slice(-30).reverse()){const tr=element('tr');for(const v of [r.label,r.model,r.metrics.ttft_seconds==null?'—':r.metrics.ttft_seconds.toFixed(2)+' s',r.metrics.end_to_end_tps==null?'—':r.metrics.end_to_end_tps+' t/s',r.metrics.backend_decode_tps==null?'—':r.metrics.backend_decode_tps+' t/s',r.state])tr.append(element('td','',String(v)));$('bench-table').append(tr);}if(!d.rows.length){const tr=element('tr');const td=element('td','muted','No benchmarks yet. Real measurements appear here after you run a model.');td.colSpan=6;tr.append(td);$('bench-table').append(tr);}}catch(e){toast(e.message,true)}}
$('export-bench').onclick=async()=>{try{saveJSON('haven-benchmarks.json',await api('/api/benchmarks'));}catch(e){toast(e.message,true)}};
$('exit').onclick=async()=>{if(!confirm('Exit this lab and stop its OWNED engine? External Strata remains in its own console.'))return;try{await api('/api/shutdown',{});$('connection-pill').textContent='Lab closed';$('send').disabled=true;clearInterval(timer);toast('Lab closed. You can close this tab.');}catch(e){toast(e.message,true)}};
boot();

// Public metadata is rendered only as text, never HTML or executable model cards.
$('discovery-form').onsubmit=async event=>{
 event.preventDefault();const button=$('discovery-search');button.disabled=true;
 $('discovery-status').textContent='Searching public metadata…';$('discovery-results').replaceChildren();$('discovery-detail').replaceChildren();
 try{const result=await api('/api/discovery/search',{query:$('discovery-query').value,author:$('discovery-author').value,format:$('discovery-format').value,task:$('discovery-task').value});
  $('discovery-status').textContent=`${result.models.length} results · Discoverable only · compatibility and qualification unverified.`;
  for(const m of result.models){const card=element('article','model-card');card.append(element('h3','',m.repo),element('p','',`${m.task||'Task unknown'} · ${m.license} · gated: ${String(m.gated)}`));
   const inspect=element('button','secondary','Inspect files & revision');inspect.onclick=()=>inspectDiscovery(m.repo);card.append(inspect);$('discovery-results').append(card);}
 }catch(error){$('discovery-status').textContent=error.message;}finally{button.disabled=false;}
};
async function inspectDiscovery(repo){
 const root=$('discovery-detail');root.replaceChildren(element('p','','Reading public artifact metadata…'));
 try{const d=await api('/api/discovery/detail',{repo});root.replaceChildren(element('h3','',d.model.repo),element('p','',`Revision: ${d.model.revision||'unknown'} · License: ${d.model.license}`),element('p','field-note',d.notice));
  const link=element('a','text-btn','Review publisher model card ↗');link.href=d.model.source;link.target='_blank';link.rel='noopener noreferrer';root.append(link);
  for(const file of d.files){const row=element('div','soft-note');row.append(element('strong','',file.filename),element('p','',`${file.format} · ${file.quantization} · ${file.size_bytes?(file.size_bytes/1e9).toFixed(2)+' GB':'size unknown'} · ${file.integrity}`));
   if(file.sha256)row.append(element('p','field-note','SHA-256: '+file.sha256));root.append(row);}
  if(!d.files.length)root.append(element('p','','No GGUF or safetensors artifacts reported within this bounded metadata response.'));
 }catch(error){root.replaceChildren(element('p','',error.message));}
}
