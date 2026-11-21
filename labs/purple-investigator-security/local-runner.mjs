import {readFile,stat} from 'node:fs/promises';
import {performance} from 'node:perf_hooks';
import {createInvestigator} from './boundary.mjs';
import {runInvestigator} from './runner.mjs';
import {makeLocalTransport} from './local-transport.mjs';
import {deriveInvestigationPlan} from './triage.mjs';

const [file,mode,port,...extra]=process.argv.slice(2);
if(!file||!mode||extra.length||(mode==="--deterministic"&&port!==undefined)){
  console.error("Usage: node local-runner.mjs <fixture.json> --deterministic OR <fixture.json> <model-id> [port]");
  process.exitCode=2;
}else{
  try{
    if((await stat(file)).size>1048576)throw Error("fixture limit");
    const raw=await readFile(file,"utf8");
    if(raw.length>1048576)throw Error("fixture limit");
    const config=JSON.parse(raw);
    const start=performance.now();
    let result;
    if(mode==="--deterministic"){
      const gate=createInvestigator(config);
      const report=gate.deterministic();
      result={status:report.released?"released":"candidate_rejected",result:report,modelCalls:0,receipt:gate.receipt()};
    }else{
      const complete=makeLocalTransport({model:mode,port:port===undefined?8080:Number(port),token:process.env.PURPLE_LOCAL_TOKEN});
      result=await runInvestigator(config,complete,createInvestigator);
    }
    console.log(JSON.stringify({...result,investigationPlan:deriveInvestigationPlan(result.result),wall_ms:Math.round(performance.now()-start)},null,2));
    process.exitCode=result.status==="released"?0:1;
  }catch{
    console.error("Local investigator failed; check the local configuration and endpoint. No private error data emitted.");
    process.exitCode=1;
  }
}
