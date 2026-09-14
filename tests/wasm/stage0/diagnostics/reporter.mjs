// V8's Wasm exception locations identify the fault; observer events are context.
const MAX_ERRORS=3, MAX_FRAMES=4, MAX_MESSAGE=160;
export function reporter(build, map) {
  const report={version:1,limits:{errors:MAX_ERRORS,frames:MAX_FRAMES,message:MAX_MESSAGE,bytes:8192},
    first_failure:null,errors:[],failures:0,dropped:0};
  function capture(error,lastObserved) {
    const frames=[];
    if(error instanceof WebAssembly.RuntimeError){
      const lines=String(error.stack??'').split('\n').slice(1,17);
      for(const line of lines){
        const match=/^\s+at wasm:\/\/wasm\/[a-zA-Z0-9]+:wasm-function\[(\d+)\]:0x([a-fA-F0-9]+)$/.exec(line);
        if(!match)break;
        const index=Number(match[1]),offset=parseInt(match[2],16);
        const fn=map.functions.find(f=>f.index===index),op=fn?.operations.find(p=>p.offset===offset);
        if(!fn||!op){frames.length=0;break;}
        frames.push({function_index:index,logical_code_id:fn.logical_code_id,entry_kind:fn.entry_kind,
          signature:fn.signature,slot:fn.slot,operation:op.name,binary_offset:offset});
        if(frames.length===MAX_FRAMES)break;
      }
    }
    const fault=frames[0]??null;
    const diagnostic={phase:'execution',build,classification:fault?'WASM_FAULT':'UNAVAILABLE',
      error_name:String(error.name).slice(0,40),message:String(error.message).slice(0,MAX_MESSAGE),
      fault,frames,last_observed:lastObserved?{...lastObserved,attribution:'CONTEXT_ONLY'}:null};
    report.failures++;
    report.first_failure ??= diagnostic;
    if(report.errors.length<MAX_ERRORS)report.errors.push(diagnostic);else report.dropped++;
    return diagnostic;
  }
  return {capture,report};
}
