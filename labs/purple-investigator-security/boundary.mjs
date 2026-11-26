// Isolated synthetic investigator boundary. No network, subprocess, or tenant access.
export function createInvestigator(config) {
  const TOPICS = ["path_context","identity_tier_evidence","posture_evidence","collection_quality"];
  const STATES = {
    path_context: ["historical_membership_reported","membership_reported"],
    identity_tier_evidence: ["eligible_assignment_reported","active_assignment_reported","permanent_assignment_reported","assignment_state_unknown"],
    posture_evidence: ["check_passed_reported","check_failed_reported","check_skipped_reported","check_not_run_reported","check_error_reported","check_investigate_reported"],
    collection_quality: ["receipt_claims_complete","receipt_claims_incomplete","producer_authentication_unverified"]
  };
  const token = v => typeof v==="string" && /^[a-zA-Z0-9_-]{1,80}$/.test(v);
  const plain = v => v!==null && typeof v==="object" && !Array.isArray(v) && Object.getPrototypeOf(v)===Object.prototype;
  const keys = (v, expected) => plain(v) && Object.keys(v).length===expected.length && expected.every(k=>Object.hasOwn(v,k));
  const parse = (raw,max) => {
    if(typeof raw!=="string"||raw.length>max) return null;
    try { return JSON.parse(raw); } catch { return null; }
  };
  let {scope,evidence,topics,authorized,budget=8}=config;
  if(!keys(scope,["run","tenant","dataset","finding","snapshot","asOf"]) ||
     !["run","tenant","dataset","finding","snapshot"].every(k=>token(scope[k])) ||
     !Number.isSafeInteger(scope.asOf)||scope.asOf<0 ||
     !Array.isArray(topics)||!topics.length||topics.length>4||
     new Set(topics).size!==topics.length||!topics.every(t=>TOPICS.includes(t))||
     typeof authorized!=="boolean" || !Number.isSafeInteger(budget)||budget<1||budget>32 ||
     !Array.isArray(evidence)||evidence.length>256) throw Error("invalid host configuration");
  scope=Object.freeze({...scope});
  const run=scope.run, selected=[...topics], limit=budget;
  const byTopic=new Map(TOPICS.map(t=>[t,[]]));
  const events=[], received=new Map(), lineage=new Map(), lineageKeys=new Set();
  let rejected=0, overflow=0, closed=false;
  // Host records are parsed JSON data, not JavaScript supplied by the model.
  // Evidence state is an assertion made by the adapter; this does not authenticate a producer.
  for(const r of evidence){
    if(!plain(r)||!TOPICS.includes(r.topic)||r.tenant!==scope.tenant||
       r.dataset!==scope.dataset||r.finding!==scope.finding||r.snapshot!==scope.snapshot||
       !token(r.artifact)||!Number.isSafeInteger(r.record)||r.record<0||
       r.sourceTenant!==scope.tenant||!Number.isSafeInteger(r.observed)||
       !Number.isSafeInteger(r.received)||r.observed<0||r.received<r.observed||
       r.received>scope.asOf||!STATES[r.topic].includes(r.state)){
      rejected++; continue;
    }
    const rows=byTopic.get(r.topic);
    // No raw descriptions, display names, object IDs, URLs, or source text cross this boundary.
    const ref="e"+(TOPICS.indexOf(r.topic)+1)+"_"+(rows.length+1);
    const key=JSON.stringify([r.topic,r.artifact,r.record]);
    if(lineageKeys.has(key))throw Error("duplicate evidence lineage");
    lineageKeys.add(key);
    lineage.set(ref,{artifact:r.artifact,record:r.record});
    rows.push({ref,state:r.state,observed:r.observed});
  }
  for(const t of TOPICS){
    if(!byTopic.get(t).length) byTopic.set(t,[{ref:"e"+(TOPICS.indexOf(t)+1)+"_0",state:"no_qualified_observation",observed:null}]);
  }
  const clone=v=>JSON.parse(JSON.stringify(v));
  const allowed=()=>{
    if(!authorized||closed)return [];
    return selected.filter(t=>!events.some(e=>e.topic===t&&e.outcome==="ok"));
  };
  const dispatch=raw=>{
    if(closed) return {outcome:"denied",reason:"closed"};
    if(events.length>=limit){
      overflow=Math.min(overflow+1,Number.MAX_SAFE_INTEGER);
      return {outcome:"denied",reason:"budget"};
    }
    const call=parse(raw,2048);
    const topic=plain(call)&&TOPICS.includes(call.tool)?call.tool:null;
    const permitted=keys(call,["tool","args"])&&keys(call.args,[])&&allowed().includes(topic);
    if(!permitted){
      events.push({seq:events.length+1,topic,outcome:"denied",refs:[]});
      return {outcome:"denied",reason:"policy"};
    }
    const rows=byTopic.get(topic);
    for(const r of rows)received.set(r.ref,{...r,topic});
    events.push({seq:events.length+1,topic,outcome:"ok",refs:rows.map(r=>r.ref)});
    return {outcome:"ok",run,topic,evidence:clone(rows)};
  };
  const receipt=()=>clone({run,snapshot:scope.snapshot,events,overflow,rejected_input_records:rejected,closed});
  // Candidate is intentionally not a prose channel: only enumerated, exact evidence claims.
  // The host owns the actual dispatch history, and never accepts a model-supplied trace.
  const finalize=raw=>{
    if(closed)return {released:false,reason:"closed"};
    closed=true;
    if(!authorized)return {released:false,reason:"unauthorized"};
    if(overflow||events.some(e=>e.outcome!=="ok"))return {released:false,reason:"denied_attempt"};
    const answer=parse(raw,65536);
    if(!keys(answer,["run","claims"])||answer.run!==run||!Array.isArray(answer.claims)||
       answer.claims.length>260)return {released:false,reason:"schema"};
    const required=selected.flatMap(t=>byTopic.get(t).map(r=>r.ref));
    if(required.some(ref=>!received.has(ref)))return {released:false,reason:"missing_read"};
    if(answer.claims.length!==required.length)return {released:false,reason:"coverage"};
    const seen=new Set();
    for(const claim of answer.claims){
      if(!keys(claim,["ref","state"])||typeof claim.ref!=="string"||seen.has(claim.ref)||
         !received.has(claim.ref)||received.get(claim.ref).state!==claim.state)
        return {released:false,reason:"unsupported_claim"};
      seen.add(claim.ref);
    }
    if(required.some(ref=>!seen.has(ref)))return {released:false,reason:"coverage"};
    // Re-render from trusted dispatcher records, never from model-controlled prose/order.
    return {released:true,report:{run,scope:{tenant:scope.tenant,dataset:scope.dataset,finding:scope.finding,snapshot:scope.snapshot,asOf:scope.asOf},
      assessment:"source_observations_only",claims:required.map(ref=>({...clone(received.get(ref)),lineage:lineage.has(ref)?clone(lineage.get(ref)):null})),
      limitations:["receipt_claims_are_not_producer_authentication","membership_is_not_compromise","eligibility_is_not_activation","posture_is_not_remediation"],
      next_step:"verify_current_evidence_with_authorized_owner"}};
  };
  const deterministic=()=>{
    const claims=[];
    for(const tool of allowed()){
      const r=dispatch(JSON.stringify({tool,args:{}}));
      if(r.outcome!=="ok")break;
      for(const e of r.evidence)claims.push({ref:e.ref,state:e.state});
    }
    return finalize(JSON.stringify({run,claims}));
  };
  return Object.freeze({dispatch,finalize,receipt,deterministic,topics:()=>[...allowed()]});
}
