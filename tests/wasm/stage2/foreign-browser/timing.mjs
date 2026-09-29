// Sparse phase timers: no per-call census or per-service timestamps.
export function startupTiming(send) {
 const now=()=>performance.timeOrigin+performance.now();
 let ready=false;
 return {
  measure(phase,run) {
   if(!['archive.compile','lisp.run'].includes(phase))return run();
   const start=now(),stage=ready?'witness':'startup';
   if(phase==='lisp.run')send({type:'startup-timing',event:'lisp-start',at:start});
   const end=()=>{
    const at=now();send({type:'startup-timing',event:phase,stage,start,at,ms:at-start});
    // The shared runner independently checks that this exit is ProcessReady.
    if(phase==='lisp.run')ready=true;
   };
   let result;try{result=run();}catch(error){end();throw error;}
   if(result instanceof Promise)return result.then(value=>{end();return value;},error=>{end();throw error;});
   end();return result;
  },
  memory(){},event(){},open(){},close(){},finish(){send({type:'startup-timing',event:'finished',at:now()});}
 };
}
