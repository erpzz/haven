import {isRelease,strictJSON,ProtocolIngressError} from './security.mjs';
// These are conservative compatibility rules, not benchmark expected answers.
const rules={
  activation_gap:{requires:[['eligible_assignment_reported']],action:'request_activation_history',meaning:'An eligible assignment may have a separately recorded activation; effective access is unresolved.'},
  posture_path_link:{requires:[['membership_reported','historical_membership_reported'],['check_failed_reported']],action:'request_control_scope_mapping',meaning:'The failed control may be relevant to this path; causal or asset-level linkage is unresolved.'},
  conflicting_entitlement:{requires:[['eligible_assignment_reported'],['active_assignment_reported','permanent_assignment_reported']],action:'request_assignment_instance_history',meaning:'The modes may refer to distinct assignment instances or times; contradiction is unresolved.'},
  provenance_gap:{requires:[['receipt_claims_complete','receipt_claims_incomplete','producer_authentication_unverified']],action:'request_authenticated_collection',meaning:'Source authentication is missing or unverified.'},
  temporal_gap:{requires:[['historical_membership_reported'],['check_passed_reported','check_failed_reported']],action:'request_time_aligned_observations',meaning:'Graph and posture observations may not describe the same effective state.'}
};
const sameKeys=(o,keys)=>o&&typeof o==='object'&&!Array.isArray(o)&&Object.keys(o).length===keys.length&&keys.every(k=>Object.hasOwn(o,k));
export function hypothesisContext(release){
  if(!isRelease(release))throw Error('unauthenticated_release');
  return {version:'hare-purple/0.1',run:release.report.run,observations:release.report.claims.map(({ref,state,observed,topic})=>({ref,state,observed,topic})),coverage:release.report.coverage,allowed:Object.keys(rules)};
}
export function verifyHypotheses(release,raw){
  const ctx=hypothesisContext(release),byRef=new Map(ctx.observations.map(r=>[r.ref,r]));let input;
  try{input=strictJSON(raw,16384);}catch{return {status:'invalid_candidate',accepted:[],rejected:[]};}
  if(!sameKeys(input,['run','proposals'])||input.run!==ctx.run||!Array.isArray(input.proposals)||input.proposals.length>8)return {status:'invalid_candidate',accepted:[],rejected:[]};
  const accepted=[],rejected=[],seen=new Set();
  for(const [index,p] of input.proposals.entries()){
    if(!sameKeys(p,['kind','refs','priority'])||typeof p.kind!=='string'||!Object.hasOwn(rules,p.kind)||!Array.isArray(p.refs)||p.refs.length<1||p.refs.length>8||new Set(p.refs).size!==p.refs.length||!p.refs.every(r=>typeof r==='string'&&byRef.has(r))||!Number.isInteger(p.priority)||p.priority<1||p.priority>3){rejected.push({index,reason:'invalid_or_unscoped'});continue;}
    if(seen.has(p.kind)){rejected.push({index,reason:'duplicate_hypothesis'});continue;}seen.add(p.kind);
    const r=rules[p.kind],observations=p.refs.map(ref=>byRef.get(ref));
    if(!r.requires.every(group=>observations.some(o=>group.includes(o.state)))||!observations.every(o=>r.requires.some(group=>group.includes(o.state)))){rejected.push({index,reason:'unsupported_premises'});continue;}
    accepted.push({kind:p.kind,classification:'supported_interpretation_unresolved_hypothesis',refs:[...p.refs],suggestedPriority:p.priority,meaning:r.meaning,action:{kind:r.action,authorization:'not_granted',execution:'not_executed'}});
  }
  return {status:'advisory_only',facts:'separate_authoritative_release',accepted,rejected,escalation:rejected.length?{requested:true,reason:'verification_failure',authorization:'not_granted'}:null};
}
// Deterministic exhaustive comparator: if candidates are from a closed vocabulary,
// do not credit a model for simply discovering everything these rules enumerate.
export function enumerateHypotheses(release){const ctx=hypothesisContext(release),proposals=[];for(const [kind,r] of Object.entries(rules)){const refs=r.requires.map(g=>ctx.observations.find(o=>g.includes(o.state))?.ref);if(refs.every(Boolean))proposals.push({kind,refs:[...new Set(refs)],priority:2});}return verifyHypotheses(release,JSON.stringify({run:ctx.run,proposals}));}
export async function proposeHypotheses(release,complete,expectedModel){
  if(typeof expectedModel!=='string'||!/^[a-zA-Z0-9_.:/-]{1,128}$/.test(expectedModel)||typeof complete!=='function')throw Error('configuration');
  const ctx=hypothesisContext(release),start=performance.now();let r;
  try{r=await complete({messages:[{role:'system',content:'Propose bounded hypotheses only. Return JSON {run,proposals:[{kind,refs,priority}]}. Use allowed kinds and observed refs only. No authoritative conclusions or execution.'},{role:'user',content:JSON.stringify(ctx)}],tools:[]});}catch(e){return {status:e instanceof ProtocolIngressError?'protocol_json':'transport_error',wall_ms:performance.now()-start};}
  const m=r?.choices?.[0]?.message;
  const u=r?.usage,usage=u&&['prompt_tokens','completion_tokens','total_tokens'].every(k=>Number.isSafeInteger(u[k])&&u[k]>=0&&u[k]<=100000000)&&u.total_tokens===u.prompt_tokens+u.completion_tokens?{prompt_tokens:u.prompt_tokens,completion_tokens:u.completion_tokens,total_tokens:u.total_tokens}:null;
  const receipt={reportedModel:typeof r?.model==='string'&&/^[a-zA-Z0-9_.:/-]{1,128}$/.test(r.model)?r.model:null,expectedModel,provenance:'unverified',usage,wall_ms:performance.now()-start};
  if(r?.model!==expectedModel)return {status:'model_identity_mismatch',receipt};
  if(m?.refusal!=null&&m.refusal!=='')return {status:'explicit_refusal',receipt};
  if(!Array.isArray(r?.choices)||r.choices.length!==1||r.choices[0].finish_reason!=='stop'||m?.role!=='assistant'||!(m.tool_calls==null||Array.isArray(m.tool_calls)&&!m.tool_calls.length))return {status:'protocol_failure',receipt};
  return {...verifyHypotheses(release,m.content),receipt};
}
