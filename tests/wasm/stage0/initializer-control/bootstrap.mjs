// Stage 0 bootstrap harness. No test-mutation parameter enters this module.
import {createHash} from 'node:crypto';
export async function bootstrap(manifest,fetchBytes,{memory,failure,diagnostic=false,publish}) {
  const report={status:'FAIL',diagnostic,first_failure:null,errors:[],modules:[],steps:[],published:false};
  const noteFailure=error=>{
    report.errors.push(error);
    report.first_failure ??= error;
  };
  const finish=()=>report;
  const ids=new Set();
  if(manifest.version!==1||!Array.isArray(manifest.modules)||!Array.isArray(manifest.initializers)||!manifest.initializers.length) {
    noteFailure({phase:'manifest',code:'INVALID_MANIFEST',module:null,index:null,step:null});return finish();
  }
  for(const m of manifest.modules) {
    if(ids.has(m.id)){noteFailure({phase:'manifest',code:'DUPLICATE_MODULE',module:m.id,index:null,step:null});return finish();}
    ids.add(m.id);
  }
  for(const [index,init] of manifest.initializers.entries()) {
    if(init.index!==index||!Array.isArray(init.requires)||init.requires.some(n=>!Number.isInteger(n)||n<0||n>=index)) {
      noteFailure({phase:'manifest',code:'INVALID_INITIALIZER',module:init.module,index,step:init.id});return finish();
    }
    report.steps.push({index,id:init.id,module:init.module,state:'NOT_RUN',result:null,blocked_by:[]});
  }
  for(const init of manifest.initializers) {
    if(!ids.has(init.module)) {noteFailure({phase:'manifest',code:'REQUIRED_MODULE_MISSING',module:init.module,index:init.index,step:init.id});return finish();}
  }
  const modules=new Map(),instances=new Map();
  for(const m of manifest.modules) {
    try {
      const bytes=await fetchBytes(m);
      const digest=createHash('sha256').update(bytes).digest('hex');
      if(digest!==m.sha256)throw Object.assign(Error('digest mismatch'),{code:'MODULE_DIGEST'});
      modules.set(m.id,new WebAssembly.Module(bytes));report.modules.push({id:m.id,sha256:digest});
    } catch(error) {
      noteFailure({phase:'module',code:error.code==='ENOENT'?'REQUIRED_MODULE_MISSING':error.code==='MODULE_DIGEST'?'MODULE_DIGEST':'MODULE_INVALID',module:m.id,index:null,step:null});return finish();
    }
  }
  for(const m of manifest.modules) {
    try {instances.set(m.id,new WebAssembly.Instance(modules.get(m.id),{host:{memory,failure}}));}
    catch(error){noteFailure({phase:'install',code:'MODULE_INSTALLATION',module:m.id,index:null,step:null});return finish();}
  }
  for(const init of manifest.initializers) {
    const step=report.steps[init.index];
    const blocked=init.requires.filter(n=>report.steps[n].state!=='COMPLETED');
    if(blocked.length){step.state='BLOCKED';step.blocked_by=blocked;continue;}
    step.state='RUNNING';
    try {
      step.result=instances.get(init.module).exports[init.export]();
      if(step.result!==init.expected)throw Error('initializer result mismatch');
      step.state='COMPLETED';
    } catch(error) {
      step.state='FAILED';
      const expected=error instanceof WebAssembly.Exception&&error.is(failure);
      noteFailure({phase:'initializer',code:expected?'INITIALIZER_EXCEPTION':'UNEXPECTED_INITIALIZER_ERROR',
        module:init.module,index:init.index,step:init.id,payload:expected?error.getArg(failure,0):null});
      if(!diagnostic)break;
    }
  }
  if(report.errors.length||report.steps.some(s=>s.state!=='COMPLETED'))return finish();
  publish({scope:'STAGE0_HAND_BUILT_BOOTSTRAP',completed:report.steps.map(s=>s.id)});
  report.published=true;
  report.status='PASS';
  return finish();
}
