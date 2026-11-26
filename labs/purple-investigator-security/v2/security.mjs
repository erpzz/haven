import {createInvestigator} from '../boundary.mjs';
import {deriveInvestigationPlan} from '../triage.mjs';
import {makeLocalTransport} from '../local-transport.mjs';

// Validate JSON with explicit duplicate-key and nesting limits, including escaped keys.
export function strictJSON(raw, max=1048576) {
  if(typeof raw!=='string'||Buffer.byteLength(raw)>max) throw Error('json_size');
  let i=0;
  const ws=()=>{while(/[ \t\r\n]/.test(raw[i]||'!'))i++;};
  const str=()=>{const start=i++;while(i<raw.length){const c=raw[i++];if(c==='\\')i++;else if(c==='"')return JSON.parse(raw.slice(start,i));}throw Error('json_string');};
  function value(depth){
    if(depth>64)throw Error('json_depth');ws();const c=raw[i];
    if(c==='"')return str();
    if(c==='{'||c==='['){i++;ws();const obj=c==='{',end=obj?'}':']',seen=new Set();if(raw[i]===end){i++;return;}for(;;){ws();if(obj){if(raw[i]!=='"')throw Error('json_key');const k=str();if(seen.has(k))throw Error('duplicate_key');seen.add(k);ws();if(raw[i++]!==':')throw Error('json_colon');}value(depth+1);ws();const next=raw[i++];if(next===end)return;if(next!==',')throw Error('json_separator');}}
    const re=/(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/y;re.lastIndex=i;const m=re.exec(raw);if(!m)throw Error('json_value');if(/^[0-9-]/.test(m[0])&&!Number.isFinite(Number(m[0])))throw Error('json_nonfinite');i=re.lastIndex;
  }
  value(0);ws();if(i!==raw.length)throw Error('json_trailing');return JSON.parse(raw);
}
const freeze=o=>{if(o&&typeof o==='object'&&!Object.isFrozen(o)){for(const v of Object.values(o))freeze(v);Object.freeze(o);}return o;};
const releases=new WeakSet();
const topics=['path_context','identity_tier_evidence','posture_evidence','collection_quality'];
const id=x=>typeof x==='string'&&/^[a-zA-Z0-9_.:/-]{1,128}$/.test(x);
const int=x=>Number.isSafeInteger(x)&&x>=0;

// Host must authenticate before supplying the authorized flag or reading the vault.
export function openSession(config){
  if(config?.authorized!==true)return Object.freeze({denied:true,receipt:()=>({status:'unauthorized'}),topics:()=>[],dispatch:()=>({outcome:'denied'}),finalize:()=>({released:false,reason:'unauthorized'}),deterministic:()=>({released:false,reason:'unauthorized'})});
  const gate=createInvestigator(config);
  const coverage={};
  for(const topic of config.topics){const records=config.evidence.filter(r=>r?.topic===topic);const selected=createInvestigator({...config,topics:[topic],evidence:records});const rejected=selected.receipt().rejected_input_records;coverage[topic]={supplied:records.length,rejected,status:records.length===rejected?'unavailable':rejected?'partial':'observations_only'};}
  const unknown=config.evidence.filter(r=>!topics.includes(r?.topic)).length;
  const wrap=r=>{if(!r.released)return r;const report={...r.report,coverage,unclassified_rejections:unknown,assessment_completeness:'not_established',limitations:[...r.report.limitations,...(gate.receipt().rejected_input_records?['records_rejected_assessment_incomplete']:[])]};const release=freeze({released:true,report});releases.add(release);return release;};
  return Object.freeze({denied:false,topics:gate.topics,receipt:gate.receipt,dispatch:raw=>{try{strictJSON(raw,2048);}catch{return gate.dispatch('invalid');}return gate.dispatch(raw);},finalize:raw=>{try{strictJSON(raw,65536);}catch{return gate.finalize('invalid');}return wrap(gate.finalize(raw));},deterministic:()=>wrap(gate.deterministic())});
}
export function verifiedPlan(release){
  if(!releases.has(release))return {status:'unavailable',tasks:[]};
  const plan=deriveInvestigationPlan(release);
  if(release.report.limitations.includes('records_rejected_assessment_incomplete'))plan.tasks.unshift({id:'review-rejected-evidence',priority:1,action:'Resolve rejected evidence using authorized source records; assessment is incomplete.',references:[]});
  return freeze(plan);
}
export const isRelease=r=>releases.has(r);
export class ProtocolIngressError extends Error {}
export function localTransport(options){return makeLocalTransport({...options,decode:bytes=>{try{const raw=new TextDecoder('utf-8',{fatal:true}).decode(bytes);strictJSON(raw);return raw;}catch{throw new ProtocolIngressError('invalid_response_json');}}});}

// Callback returns the parsed endpoint response. Raw ingress must use strictJSON.
export async function investigate(config,complete,expectedModel){
  const gate=openSession(config),turns=[],ids=new Set();let calls=0;
  const finish=(status,result)=>({status,result,modelCalls:calls,receipt:gate.receipt(),inference:{expectedModel:expectedModel??null,provenance:'unverified',turns,usageComplete:turns.length>0&&turns.every(t=>t.usage!==null),totalTokens:turns.length>0&&turns.every(t=>t.usage!==null)?turns.reduce((s,t)=>s+t.usage.total_tokens,0):null}});
  const fail=status=>finish(status,gate.finalize('invalid'));
  if(gate.denied)return fail('unauthorized');
  if(!id(expectedModel)||typeof complete!=='function')throw Error('configuration');
  const run=config.scope.run, n=gate.topics().length;
  const messages=[{role:'system',content:'Read each available tool once. Return only JSON {run,claims}; each claim has ref and state copied exactly. Include every reference. Run: '+run},{role:'user',content:'Review scoped observations.'}];
  for(let i=0;i<=n;i++){
    const tools=gate.topics().map(name=>({type:'function',function:{name,description:'Read scoped observations.',parameters:{type:'object',properties:{},additionalProperties:false}}}));
    let r;calls++;const start=performance.now();try{r=await complete(JSON.parse(JSON.stringify({messages,tools})));}catch(e){turns.push({model:null,usage:null,wall_ms:performance.now()-start});return fail(e instanceof ProtocolIngressError?'protocol_json':'transport_error');}
    const u=r?.usage,usage=u&&['prompt_tokens','completion_tokens','total_tokens'].every(k=>int(u[k])&&u[k]<=100000000)&&u.total_tokens===u.prompt_tokens+u.completion_tokens?{prompt_tokens:u.prompt_tokens,completion_tokens:u.completion_tokens,total_tokens:u.total_tokens}:null;
    turns.push({model:id(r?.model)?r.model:null,usage,wall_ms:performance.now()-start});
    if(r?.model!==expectedModel)return fail('model_identity_mismatch');
    if(!Array.isArray(r.choices)||r.choices.length!==1)return fail('protocol_choice');
    const c=r.choices[0],m=c?.message;
    if(m?.role!=='assistant')return fail('protocol_role');
    if(m.refusal!==undefined&&m.refusal!==null&&m.refusal!=='')return fail('explicit_refusal');
    if(c.finish_reason==='length')return fail('protocol_truncated');
    if(c.finish_reason==='stop'&&(m.tool_calls==null||Array.isArray(m.tool_calls)&&!m.tool_calls.length)&&typeof m.content==='string'){const result=gate.finalize(m.content);return finish(result.released?'released':'candidate_rejected',result);}
    if(c.finish_reason!=='tool_calls'||!Array.isArray(m.tool_calls)||m.tool_calls.length!==1)return fail('protocol_tool_count');
    const t=m.tool_calls[0];if(t?.type!=='function'||!id(t.id)||!id(t.function?.name)||typeof t.function?.arguments!=='string')return fail('protocol_tool_schema');
    if(ids.has(t.id))return fail('duplicate_tool_id');ids.add(t.id);
    let args;try{args=strictJSON(t.function.arguments,2048);}catch{return fail('protocol_arguments');}
    const result=gate.dispatch(JSON.stringify({tool:t.function.name,args}));if(result.outcome!=='ok')return fail('tool_denied');
    messages.push({role:'assistant',content:null,tool_calls:[{id:t.id,type:'function',function:{name:t.function.name,arguments:'{}'}}]},{role:'tool',tool_call_id:t.id,content:JSON.stringify(result)});
  }return fail('turn_limit');
}
