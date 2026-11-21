import {createInvestigator} from './boundary.mjs';
import {runInvestigator} from './runner.mjs';
async function runRunnerTests(run,create){
  const scope={run:"r1",tenant:"t1",dataset:"d1",finding:"f1",snapshot:"s1",asOf:10};
  const record={tenant:"t1",dataset:"d1",sourceTenant:"t1",finding:"f1",snapshot:"s1",artifact:"a1",record:0,observed:5,received:6,topic:"identity_tier_evidence",state:"eligible_assignment_reported",description:"UNTRUSTED_CANARY"};
  const config={scope,evidence:[record],topics:["identity_tier_evidence"],authorized:true};
  const completion=(message,reason)=>({choices:[{message:{role:"assistant",...message},finish_reason:reason}]});
  const call=(name="identity_tier_evidence",args="{}",content=null)=>completion({content,tool_calls:[{id:"call_1",type:"function",function:{name,arguments:args}}]},"tool_calls");
  const answer=claims=>completion({content:JSON.stringify({run:"r1",claims})},"stop");
  const good=[{ref:"e2_1",state:"eligible_assignment_reported"}];
  const tests=[];
  const check=async(name,fn)=>{try{if(!await fn())throw Error("assertion");tests.push({name,pass:true});}catch(e){tests.push({name,pass:false,error:String(e)});}};
  await check("native_tool_round_trip",async()=>{let n=0;const r=await run(config,async req=>{
    n++;if(n===1){if(req.tools.length!==1||req.tools[0].function.name!==config.topics[0])throw Error("catalog");return call();}
    const last=req.messages.at(-1);if(last.role!=="tool"||!last.content.includes("eligible_assignment_reported")||last.content.includes("UNTRUSTED_CANARY")||req.tools.length!==0)throw Error("projection");
    return answer(good);},create);return r.status==="released"&&r.modelCalls===2&&r.receipt.events.length===1;});
  await check("no_model_invocation_when_unauthorized",async()=>{let n=0;const r=await run({...config,authorized:false},async()=>{n++;return answer([]);},create);return n===0&&r.status==="unauthorized";});
  await check("early_answer_without_reads",async()=>{const r=await run(config,async()=>answer(good),create);return r.status==="candidate_rejected"&&r.result.reason==="missing_read";});
  await check("out_of_scope_native_call",async()=>{const r=await run(config,async()=>call("path_context"),create);return r.status==="tool_denied"&&r.receipt.events[0].outcome==="denied";});
  await check("argument_scope_override",async()=>{const r=await run(config,async()=>call("identity_tier_evidence",'{"tenant":"t2"}'),create);return r.status==="tool_denied";});
  await check("invalid_json_arguments",async()=>{const r=await run(config,async()=>call("identity_tier_evidence","{"),create);return r.status==="protocol_arguments_json"&&r.receipt.events.length===0;});
  await check("multiple_parallel_calls_blocked",async()=>{const c=call();c.choices[0].message.tool_calls.push(c.choices[0].message.tool_calls[0]);const r=await run(config,async()=>c,create);return r.status==="protocol_tool_count";});
  await check("truncated_response",async()=>{const r=await run(config,async()=>completion({content:"{}"},"length"),create);return r.status==="protocol_truncated";});
  await check("transport_failure",async()=>{const r=await run(config,async()=>{throw Error("private token example");},create);return r.status==="transport_error"&&!JSON.stringify(r).includes("private token");});
  await check("invented_activation_blocked",async()=>{let n=0;const r=await run(config,async()=>++n===1?call():answer([{ref:"e2_1",state:"active_assignment_reported"}]),create);return r.result.reason==="unsupported_claim";});
  await check("assistant_prose_not_forwarded",async()=>{let n=0;const r=await run(config,async req=>{if(++n===1)return call("identity_tier_evidence","{}","UNTRUSTED_ASSISTANT_TEXT");if(JSON.stringify(req).includes("UNTRUSTED_ASSISTANT_TEXT"))throw Error("leak");return answer(good);},create);return r.status==="released";});
  await check("duplicates_denied_and_stop",async()=>{const r=await run(config,async()=>call(),create);return r.status==="tool_denied"&&r.modelCalls===2&&r.receipt.events.length===2;});
  await check("model cannot manufacture receipt",async()=>{let n=0;const r=await run(config,async()=>++n===1?call():completion({content:JSON.stringify({run:"r1",claims:good,trace:[]})},"stop"),create);return r.result.reason==="schema";});
  await check("mutating model transport input cannot alter transcript",async()=>{let n=0;const r=await run(config,async req=>{if(++n===1){req.messages[0].content="CORRUPTED";return call();}if(req.messages[0].content==="CORRUPTED")throw Error("mutated");return answer(good);},create);return r.status==="released";});
  await check("model refusal explicit rejection",async()=>{const r=await run(config,async()=>completion({content:"I cannot assist"},"stop"),create);return r.status==="candidate_rejected"&&r.result.reason==="schema";});
  return {total:tests.length,passed:tests.filter(x=>x.pass).length,tests};
}
const result=await runRunnerTests(runInvestigator,createInvestigator);
console.log(JSON.stringify(result,null,2));
process.exitCode=result.passed===result.total?0:1;
