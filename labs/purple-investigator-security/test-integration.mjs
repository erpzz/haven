import {readFileSync} from 'node:fs';
import {createInvestigator} from './boundary.mjs';
import {runInvestigator} from './runner.mjs';
import {deriveInvestigationPlan} from './triage.mjs';
async function runIntegration(create,run,plan,config){
  const clone=v=>JSON.parse(JSON.stringify(v));
  const direct=create(clone(config));
  const baseline=direct.deterministic();
  const replies=async req=>{
    const next=req.tools[0];
    const message=next?{role:"assistant",content:null,tool_calls:[{id:"call_"+req.messages.length,type:"function",function:{name:next.function.name,arguments:"{}"}}]}:{role:"assistant",content:JSON.stringify({run:config.scope.run,claims:req.messages.filter(m=>m.role==="tool").flatMap(m=>JSON.parse(m.content).evidence.map(({ref,state})=>({ref,state})))})};
    return {choices:[{message,finish_reason:next?"tool_calls":"stop"}]};
  };
  const actual=await run(clone(config),replies,create);
  const baselinePlan=plan(baseline),actualPlan=plan(actual.result);
  const checks={
    deterministic_released:baseline.released===true,
    scripted_model_released:actual.status==="released",
    exact_report_parity:JSON.stringify(baseline.report)===JSON.stringify(actual.result.report),
    exact_plan_parity:JSON.stringify(baselinePlan)===JSON.stringify(actualPlan),
    four_independent_reads:actual.receipt.events.length===4&&actual.receipt.events.every(e=>e.outcome==="ok"),
    five_scripted_model_calls:actual.modelCalls===5,
    all_task_refs_present:actualPlan.tasks.every(t=>t.references.every(ref=>actual.result.report.claims.some(c=>c.ref===ref))),
    no_untrusted_description_in_report:!JSON.stringify(actual.result).includes("Untrusted synthetic administrative note")
  };
  return {checks,passed:Object.values(checks).filter(Boolean).length,total:Object.keys(checks).length,baseline_model_calls:0,scripted_model_calls:actual.modelCalls,report:baseline.report,plan:baselinePlan};
}
const config=JSON.parse(readFileSync(new URL('synthetic-config.json',import.meta.url),'utf8'));
const result=await runIntegration(createInvestigator,runInvestigator,deriveInvestigationPlan,config);
console.log(JSON.stringify(result,null,2));
process.exitCode=result.passed===result.total?0:1;
