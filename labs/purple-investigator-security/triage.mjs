// Deterministic verification planning over trusted release output.
export function deriveInvestigationPlan(release){
  // Only accept the trusted host's release result, never the model's candidate JSON.
  if(release?.released!==true||release.report?.assessment!=="source_observations_only"||
      !Array.isArray(release.report.claims))return {status:"unavailable",tasks:[]};
  const claims=release.report.claims;
  const tasks=[];
  const add=(id,priority,action,rows)=>{
    if(!rows.length)return;
    tasks.push({id,priority,action,references:[...new Set(rows.map(r=>r.ref))].sort()});
  };
  const select=(topic,...states)=>claims.filter(r=>r.topic===topic&&states.includes(r.state));
  const p="path_context",e="identity_tier_evidence",m="posture_evidence",q="collection_quality";
  const unverified=select(q,"producer_authentication_unverified","receipt_claims_complete","receipt_claims_incomplete","no_qualified_observation");
  add("validate-provenance",1,"Establish source provenance independently; receipt completeness is not producer authentication.",unverified);
  add("restore-coverage",1,"Obtain a scoped collection or independently confirm the missing partition.",select(q,"receipt_claims_incomplete","no_qualified_observation"));
  add("collect-path",1,"Obtain a scoped graph observation; absence of qualified evidence is not path removal.",select(p,"no_qualified_observation"));
  add("collect-entitlement",1,"Obtain source-tenant-bound assignment evidence.",select(e,"no_qualified_observation","assignment_state_unknown"));
  add("collect-posture",1,"Obtain a scoped posture assessment or resolve the reason it was unavailable.",select(m,"no_qualified_observation","check_skipped_reported","check_not_run_reported","check_error_reported","check_investigate_reported"));
  add("verify-membership",2,"Verify current membership and the path's scope with the authorized identity owner.",select(p,"historical_membership_reported","membership_reported"));
  const eligible=select(e,"eligible_assignment_reported"),active=select(e,"active_assignment_reported","permanent_assignment_reported");
  if(eligible.length&&active.length)add("reconcile-modes",2,"Identify the distinct assignments and observation times before comparing eligible and active modes; these may be separate entitlements.",[...eligible,...active]);
  add("check-activation",2,"Check for a separately recorded activation and verify assignment scope; eligibility does not establish effective access.",eligible);
  add("review-assignment",2,"Review the reported assignment's scope, necessity and current status with its owner.",active);
  add("review-failed-posture",2,"Review the failed configuration assessment with its source owner; do not infer compromise.",select(m,"check_failed_reported"));
  add("confirm-remediation-separately",3,"Treat the passing test as a posture observation only; verify remediation independently.",select(m,"check_passed_reported"));
  tasks.sort((a,b)=>a.priority-b.priority||(a.id<b.id?-1:a.id>b.id?1:0));
  return {status:"verification_plan_only",tasks,limitations:["priority_is_verification_order_not_exposure_severity","no_remediation_or_external_action_authorized","references_resolve_to_host_report_claims"]};
}
