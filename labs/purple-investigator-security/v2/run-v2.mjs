import {readFileSync} from 'node:fs';
import {openSession,strictJSON,verifiedPlan,localTransport,investigate} from './security.mjs';
import {enumerateHypotheses,proposeHypotheses} from './hypotheses.mjs';
const [mode,variant='base',model,port,...extra]=process.argv.slice(2);
const variants=['base','conflict','partial','missing','passing_posture'];
if(!['deterministic','observe','hypotheses'].includes(mode)||!variants.includes(variant)||extra.length||(mode==='deterministic'?(model!==undefined||port!==undefined):(!model||!port)))throw Error('Usage: node run-v2.mjs deterministic CASE | observe CASE MODEL PORT | hypotheses CASE MODEL PORT');
const c=strictJSON(readFileSync(new URL('../synthetic-config.json',import.meta.url),'utf8'));
c.scope.run='synthetic-'+variant+'-'+crypto.randomUUID();
if(variant==='conflict')c.evidence.push({...c.evidence[1],record:1,state:'active_assignment_reported'});
if(variant==='partial')c.evidence.push({...c.evidence[0],sourceTenant:'foreign'});
if(variant==='missing')c.evidence=c.evidence.filter(r=>r.topic!=='identity_tier_evidence');
if(variant==='passing_posture')c.evidence[2].state='check_passed_reported';
const start=performance.now(),gate=openSession(c),release=gate.deterministic(),plan=verifiedPlan(release),enumeration=enumerateHypotheses(release);
const baseline_ms=performance.now()-start;
let actual=null,responses=[];
if(mode!=='deterministic'){
  // Explicit approved, already-running endpoint only. No discovery, loading or service management.
  const transport=localTransport({model,port:Number(port),token:process.env.PURPLE_LOCAL_TOKEN});
  const capture=async q=>{const r=await transport(q);responses.push(r);return r;};
  actual=mode==='observe'?await investigate(c,capture,model):await proposeHypotheses(release,capture,model);
}
console.log(JSON.stringify({mode,variant,baseline_ms,baseline:{release,plan,enumeration},actual,responses,process_peak_rss_kib:process.resourceUsage().maxRSS,backend_memory:null,model_artifact_provenance:'unverified',wall_ms:performance.now()-start},null,2));
process.exitCode=mode==='deterministic'||(mode==='observe'?actual?.status==='released':actual?.status==='advisory_only'&&actual.rejected.length===0)?0:1;
