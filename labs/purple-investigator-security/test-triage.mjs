import {deriveInvestigationPlan} from './triage.mjs';
function runPlanTests(plan){
  const row=(topic,state,ref)=>({topic,state,ref});
  const release=claims=>({released:true,report:{assessment:"source_observations_only",claims}});
  const p="path_context",e="identity_tier_evidence",m="posture_evidence",q="collection_quality";
  const tests=[];
  const check=(name,fn)=>{try{if(!fn())throw Error("assertion");tests.push({name,pass:true});}catch(err){tests.push({name,pass:false,error:String(err)});}};
  const ids=r=>r.tasks.map(t=>t.id);
  check("closed_release_has_no_plan",()=>plan({released:false}).tasks.length===0);
  check("historical_path_not_current",()=>ids(plan(release([row(p,"historical_membership_reported","p1")]))).includes("verify-membership"));
  check("eligible_requires_activation_review",()=>{const r=plan(release([row(e,"eligible_assignment_reported","e1")]));return ids(r).includes("check-activation")&&!ids(r).includes("review-assignment");});
  check("active_still_requires_owner_review",()=>ids(plan(release([row(e,"active_assignment_reported","e1")]))).includes("review-assignment"));
  check("mixed_mode_not_assumed_same_entitlement",()=>{const r=plan(release([row(e,"active_assignment_reported","e1"),row(e,"eligible_assignment_reported","e2")]));return r.tasks.find(t=>t.id==="reconcile-modes").references.length===2;});
  check("passing_check_not_remediation",()=>ids(plan(release([row(m,"check_passed_reported","m1")]))).includes("confirm-remediation-separately"));
  check("failing_check_not_compromise",()=>ids(plan(release([row(m,"check_failed_reported","m1")]))).includes("review-failed-posture"));
  check("inapplicable_or_error_no_pass",()=>ids(plan(release([row(m,"check_error_reported","m1")]))).includes("collect-posture"));
  check("source_claim_not_provenance",()=>ids(plan(release([row(q,"receipt_claims_complete","q1")]))).includes("validate-provenance"));
  check("coverage_priority",()=>{const r=plan(release([row(e,"eligible_assignment_reported","e1"),row(q,"receipt_claims_incomplete","q1")]));return r.tasks[0].priority===1&&r.tasks.at(-1).priority===2;});
  check("missing_data_explicit",()=>{const claims=[p,e,m,q].map((topic,i)=>row(topic,"no_qualified_observation","unknown"+i));return plan(release(claims)).tasks.length===5;});
  check("all_task_refs_exist",()=>{const cs=[row(q,"receipt_claims_incomplete","q1"),row(e,"eligible_assignment_reported","e1")];return plan(release(cs)).tasks.every(t=>t.references.every(ref=>cs.some(c=>c.ref===ref)));});
  check("arbitrary_text_not_rendered",()=>{const r=plan(release([{...row(e,"eligible_assignment_reported","e1"),description:"CANARY"}]));return !JSON.stringify(r).includes("CANARY");});
  return {total:tests.length,passed:tests.filter(x=>x.pass).length,tests};
}
const result=runPlanTests(deriveInvestigationPlan);
console.log(JSON.stringify(result,null,2));
process.exitCode=result.passed===result.total?0:1;
