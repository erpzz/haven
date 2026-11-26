import {makeLocalTransport} from './local-transport.mjs';
async function runTransportTests(make){
  let observed, cancelled=false,released=false;
  const config={model:"local-model",signalFactory:ms=>({ms}),decode:bytes=>String.fromCharCode(...bytes)};
  const toBytes=s=>Uint8Array.from([...s].map(x=>x.charCodeAt(0)));
  const mock=(raw,ok=true)=>async (url,options)=>{
    observed={url,options};let i=0;const pieces=Array.isArray(raw)?raw:[toBytes(raw)];
    return {ok,body:{cancel:async()=>{cancelled=true;},getReader:()=>({read:async()=>i<pieces.length?{done:false,value:pieces[i++]}:{done:true},cancel:async()=>{cancelled=true;},releaseLock:()=>{released=true;}})}};
  };
  const req={messages:[{role:"user",content:"synthetic"}],tools:[]};
  const tests=[];
  const check=async(name,fn)=>{try{if(!await fn())throw Error("assertion");tests.push({name,pass:true});}catch(e){tests.push({name,pass:false,error:String(e)});}};
  const throws=async fn=>{try{await fn();return false;}catch{return true;}};
  await check("fixed_loopback_and_no_redirect",async()=>{await make({...config,fetchImpl:mock("{}")})(req);return observed.url==="http://127.0.0.1:8080/v1/chat/completions"&&observed.options.redirect==="error"&&observed.options.signal.ms===90000;});
  await check("exact_model_and_native_tools",async()=>{await make({...config,port:9000,fetchImpl:mock("{}")})({...req,tools:[{type:"function"}]});const p=JSON.parse(observed.options.body);return observed.url.startsWith("http://127.0.0.1:9000/")&&p.model==="local-model"&&p.tools.length===1&&p.tool_choice==="auto"&&p.stream===false;});
  await check("omit_tools_after_last_read",async()=>{await make({...config,fetchImpl:mock("{}")})(req);return !Object.hasOwn(JSON.parse(observed.options.body),"tools");});
  await check("reject_invalid_port",()=>throws(()=>make({...config,port:"https://example.invalid",fetchImpl:mock("{}")})));
  await check("reject_header_injection",()=>throws(()=>make({...config,token:"abc\r\nx:y",fetchImpl:mock("{}")})));
  await check("optional_token_stays_header_only",async()=>{await make({...config,token:"synthetic-token",fetchImpl:mock("{}")})(req);return observed.options.headers.Authorization==="Bearer synthetic-token"&&!observed.options.body.includes("synthetic-token");});
  await check("response_chunk_limit",async()=>{cancelled=false;released=false;const r=await throws(()=>make({...config,maxBytes:1024,fetchImpl:mock([new Uint8Array(600),new Uint8Array(600)])})(req));return r&&cancelled&&released;});
  await check("response_stream_reassembly",async()=>{const r=await make({...config,fetchImpl:mock([toBytes('{"a"'),toBytes(':1}')])})(req);return r.a===1;});
  await check("non_success_http_rejected",async()=>{cancelled=false;return await throws(()=>make({...config,fetchImpl:mock("{}",false)})(req))&&cancelled;});
  await check("invalid_json_rejected",()=>throws(()=>make({...config,fetchImpl:mock("{")})(req)));
  await check("oversize_request_rejected_before_fetch",async()=>{let n=0;return await throws(()=>make({...config,fetchImpl:async()=>{n++;}})({...req,messages:[{content:"x".repeat(262145)}]}))&&n===0;});
  return {total:tests.length,passed:tests.filter(x=>x.pass).length,tests};
}
const result=await runTransportTests(makeLocalTransport);
console.log(JSON.stringify(result,null,2));
process.exitCode=result.passed===result.total?0:1;
