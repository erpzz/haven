// Localhost-only HTTP transport. No external URL, redirects, or retry logic.
export function makeLocalTransport({model,port=8080,token,timeoutMs=90000,fetchImpl=globalThis.fetch,signalFactory=ms=>AbortSignal.timeout(ms),decode=bytes=>new TextDecoder("utf-8",{fatal:true}).decode(bytes),maxBytes=1048576}){
  if(typeof model!=="string"||!/^[a-zA-Z0-9_.:\/-]{1,128}$/.test(model)||
    !Number.isInteger(port)||port<1||port>65535||
    !Number.isInteger(timeoutMs)||timeoutMs<1000||timeoutMs>180000||
    !Number.isInteger(maxBytes)||maxBytes<1024||maxBytes>1048576||
    (token!==undefined&&(typeof token!=="string"||!/^[\x21-\x7e]{1,4096}$/.test(token)))||
    typeof fetchImpl!=="function")throw Error("invalid local transport configuration");
  const url="http://127.0.0.1:"+port+"/v1/chat/completions";
  const headers={"Content-Type":"application/json"};
  if(token!==undefined)headers.Authorization="Bearer "+token;
  return async ({messages,tools})=>{
    const payload={model,messages,temperature:0,max_tokens:2048,stream:false};
    if(tools.length){payload.tools=tools;payload.tool_choice="auto";}
    const body=JSON.stringify(payload);
    if(body.length>262144)throw Error("request limit");
    const r=await fetchImpl(url,{method:"POST",headers:{...headers},body,redirect:"error",signal:signalFactory(timeoutMs)});
    if(!r?.ok||!r.body?.getReader){if(r?.body?.cancel)await r.body.cancel();throw Error("local endpoint failed");}
    const reader=r.body.getReader();
    const chunks=[];
    let size=0,done=false;
    try{
      for(;;){
        const part=await reader.read();
        if(part.done){done=true;break;}
        if(!(part.value instanceof Uint8Array)||part.value.length===0)throw Error("invalid response chunk");
        size+=part.value.length;
        if(size>maxBytes)throw Error("response limit");
        chunks.push(part.value);
      }
    }finally{
      try{if(!done)await reader.cancel();}finally{reader.releaseLock();}
    }
    const bytes=new Uint8Array(size);
    let cursor=0;
    for(const chunk of chunks){bytes.set(chunk,cursor);cursor+=chunk.length;}
    return JSON.parse(decode(bytes));
  };
}
