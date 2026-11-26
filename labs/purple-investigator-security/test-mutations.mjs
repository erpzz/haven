import {readFileSync} from 'node:fs';
function runMutations(source,testSource){
  const run=new Function(testSource.slice(testSource.indexOf("function runTests"),testSource.indexOf("const result=runTests(createInvestigator);"))+"\nreturn runTests;")();
  const load=s=>new Function(s.replace("export function ","function ")+"\nreturn createInvestigator;")();
  const baseline=run(load(source));
  const mutants=[
    ["source_tenant_ignored","r.sourceTenant!==scope.tenant||","false||"],
    ["dataset_ignored","r.dataset!==scope.dataset||","false||"],
    ["future_receipt_allowed","r.received>scope.asOf||","false||"],
    ["raw_evidence_forwarded","rows.push({ref,state:r.state,observed:r.observed});","rows.push({...r,ref,state:r.state,observed:r.observed});"],
    ["unsupported_claim_allowed","received.get(claim.ref).state!==claim.state","false"],
    ["forged_trace_accepted",'keys(answer,["run","claims"])','plain(answer)&&Object.hasOwn(answer,"run")&&Object.hasOwn(answer,"claims")'],
    ["mutable_scope","scope=Object.freeze({...scope});","scope=scope;"],
    ["duplicates_accepted",'if(lineageKeys.has(key))throw Error("duplicate evidence lineage");',"if(false)throw Error('duplicate evidence lineage');"],
    ["authorization_bypassed","if(!authorized||closed)return [];","if(closed)return [];"]
  ];
  const details=mutants.map(([name,from,to])=>{
    if(!source.includes(from))throw Error("missing mutation anchor: "+name);
    const result=run(load(source.replace(from,to)));
    return {name,killed:result.passed<result.total,failed_tests:result.tests.filter(x=>!x.pass).map(x=>x.name)};
  });
  return {baseline:baseline.passed,baseline_total:baseline.total,mutants:details.length,killed:details.filter(x=>x.killed).length,details};
}
const load=name=>readFileSync(new URL(name,import.meta.url),'utf8');
const result=runMutations(load('boundary.mjs'),load('test-boundary.mjs'));
console.log(JSON.stringify(result,null,2));
process.exitCode=result.baseline===result.baseline_total&&result.killed===result.mutants?0:1;
