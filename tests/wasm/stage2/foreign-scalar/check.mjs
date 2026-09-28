// The same cases run inside Node and browser Workers. No simulated Lisp/GC claim.
import {openForeignModule,foreignFailure} from './runtime/foreign-module.mjs';
import {sha256} from './runtime/sha256.mjs';
import {inspectForeign} from './runtime/foreign-binary.mjs';

export function check(binaries,{only}={}) {
  const rows=[];
  const assert=(ok,why)=>{if(!ok)throw Error(why);};
  const equal=(a,b,why)=>assert(Object.is(a,b),why+': '+String(a)+' != '+String(b));
  const test=(name,run)=>{if(only&&name!==only)return;
    try{run();rows.push(name);}catch(error){throw Error(name+': '+error,{cause:error});}};
  const throws=(run,pattern)=>{try{run();}catch(error){
    assert(pattern.test(String(error)),'wrong refusal: '+error);return error;
  }throw Error('missing refusal: '+pattern);};
  const types=[['i32',['i32'],['i32']],['i64',['i64'],['i64']],['f32',['f32'],['f32']],['f64',['f64'],['f64']],
    ['many',['i32','i64','f32','f64'],['i32','i64','f32','f64']],['void',[],[]],['add',['i32'],['i32']],
    ['read',[],['i32']],['write',['i32'],[]],['grow',[],['i32']],['pages',[],['i32']],
    ['trap',[],[]],['oob',[],[]],['throw',[],[]],['host',[],['i32']],['__proto__',[],['i32']],
    ['initialized',[],['i32']],['initialize',[],[]],['initialize_alias',[],[]]];
  const declaration=bytes=>({version:1,name:'scalar-fixture',sha256:sha256(bytes),policy:'per-worker',
    memory:{export:'memory',minimum:1,maximum:4},tables:[{minimum:0,maximum:4}],
    initialization:{kind:'export',name:'initialize'},
    imports:[{module:'host',name:'probe',params:['i32'],results:[]},{module:'host',name:'value',params:[],results:['i32']}],
    exports:types.map(([name,params,results])=>({name,params,results}))});
  const make=(which='library',edit=()=>{},hooks={})=>{
    const bytes=binaries[which].slice(),d=declaration(bytes),events=[];
    let ownerState='running',entries=0,exits=0;
    const tag=new WebAssembly.Tag({parameters:['i32']});
    const boundary={enter(operation){
      equal(ownerState,'running','entry state');hooks.beforeEnter?.();ownerState='foreign';
      entries++;events.push(operation);return operation;
    },leave(token){equal(ownerState,'foreign','leave state');equal(token,events.at(-1),'token');
      hooks.beforeLeave?.();ownerState='running';exits++;}};
    const imports={host:{probe(value){equal(ownerState,'foreign','initializer outside FOREIGN');
      equal(value,11,'initializer witness');hooks.probe?.();},
      value(){equal(ownerState,'foreign','host import outside FOREIGN');return hooks.value?hooks.value():42;}}};
    const options={bytes,declaration:d,boundary,errorTag:tag,imports};edit(options);
    return {options,events,tag,open:()=>openForeignModule(options),
      state:()=>ownerState,entries:()=>entries,exits:()=>exits};
  };
  const balanced=f=>{equal(f.state(),'running','readmitted');equal(f.entries(),f.exits(),'balanced brackets');};
  const catchable=(f,run,kind)=>{
    let error;try{run();}catch(e){error=e;}
    assert(error instanceof WebAssembly.Exception&&error.is(f.tag),'port exception');
    equal(error.getArg(f.tag,0),{trap:1,exception:2,host:3}[kind],'failure code');
    const info=foreignFailure(error);equal(info.kind,kind,'failure classification');balanced(f);return info;
  };
  test('binary-signatures',()=>{
    const m=inspectForeign(binaries.library);
    equal(m.types[m.functions[m.exports.find(e=>e.name==='many').index]].params.join(','),'i32,i64,f32,f64','binary types');
  });
  for(const [type,values] of [
    ['i32',[-2147483648,-1,0,1,2147483647]],['i64',[-(1n<<63n),-1n,0n,1n,(1n<<63n)-1n]],
    ['f32',[-0,0,1/3,-Infinity,Infinity,NaN,1.401298464324817e-45]],
    ['f64',[-0,0,1/3,-Infinity,Infinity,NaN,Number.MIN_VALUE,Number.MAX_VALUE]]]) {
    for(let i=0;i<values.length;i++)test('scalar-'+type+'-'+i,()=>{
      const f=make(),lib=f.open(),value=values[i];
      equal(lib.call(type,[value]),type==='f32'?Math.fround(value):value,'round trip');balanced(f);
    });
  }
  test('multi-results-and-void',()=>{const f=make(),lib=f.open();
    const values=lib.call('many',[4,5n,1/3,-0]);[4,5n,Math.fround(1/3),-0].forEach((v,i)=>equal(values[i],v,'multi '+i));
    equal(lib.call('void'),undefined,'void');equal(lib.call('__proto__'),73,'object name');balanced(f);});
  for(const bad of [false,true])test('import-multiple-results-'+bad,()=>{
    let reads=0;const values=[17,5n,1/3,-0];Object.defineProperty(values,0,{get(){reads++;return reads===1?17:2147483648;}});
    const f=make('import-multi',o=>{
      o.declaration.imports[1].results=['i32','i64','f32','f64'];
      o.declaration.exports.find(e=>e.name==='host').results=['i32','i64','f32','f64'];
    },{value:()=>bad?new Array(4):values}),lib=f.open();
    if(bad)catchable(f,()=>lib.call('host'),'host');
    else{const result=lib.call('host');[17,5n,Math.fround(1/3),-0].forEach((v,i)=>equal(result[i],v,'import result'));equal(reads,1,'one read');}
    balanced(f);
  });
  test('separate-instances-and-memory-growth',()=>{const a=make().open(),b=make().open();
    equal(a.call('add',[2]),2,'a state');equal(b.call('add',[3]),3,'b state');
    a.call('write',[123]);equal(b.call('read'),0,'no memory alias');equal(a.call('grow'),1,'grow');
    equal(a.call('pages'),2,'new size');equal(a.call('read'),123,'grown memory preserved');equal(b.call('pages'),1,'b size');});
  for(const [which,kind] of [['library','export'],['start','start'],['library','none']])test('initialization-'+kind,()=>{
    let probes=0;const f=make(which,o=>{o.declaration.initialization={kind,...(kind==='export'?{name:'initialize'}:{})};},{probe(){probes++;}});
    const lib=f.open();equal(lib.call('initialized'),kind==='none'?0:1,'initialized count');equal(probes,kind==='none'?0:1,'probes');
    if(kind!=='none')for(const name of ['initialize','initialize_alias'])throws(()=>lib.call(name),/INITIALIZER_ONCE/);
    balanced(f);
  });
  test('caller-mutation-and-frozen-declaration',()=>{
    const f=make(),original=f.options.boundary.enter;f.options.boundary.enter=function(op){
      f.options.bytes.fill(0);f.options.declaration.exports.length=0;
      f.options.boundary.leave=()=>{throw Error('replaced leave');};return original.call(this,op);};
    const lib=f.open();equal(lib.call('i32',[17]),17,'snapshot survives');
    throws(()=>{lib.declaration.exports[0].params[0]='i64';},/TypeError/);balanced(f);
  });
  test('argument-snapshot',()=>{const args=[17];let mutate=false;
    const f=make('library',()=>{},{beforeEnter(){if(mutate)args[0]=2147483648;}}),lib=f.open();
    mutate=true;equal(lib.call('i32',args),17,'checked arguments captured before entry');balanced(f);
  });
  test('table-declaration-property-order',()=>{
    const f=make('library',o=>o.declaration.tables=[{maximum:4,minimum:0}]);f.open();balanced(f);
  });
  const refusals=[
    ['version',o=>o.declaration.version=2,/DECLARATION/],['name',o=>o.declaration.name='',/DECLARATION/],
    ['name-type',o=>o.declaration.name=1,/DECLARATION/],
    ['policy',o=>o.declaration.policy='funnelled',/POLICY/],['digest',o=>o.declaration.sha256='0'.repeat(64),/DIGEST/],
    ['digest-type',o=>o.declaration.sha256=1,/DIGEST/],
    ['surface',o=>o.declaration.tables=null,/SURFACE/],['boundary',o=>o.boundary={},/BOUNDARY/],
    ['imports-shape',o=>o.declaration.imports={},/SURFACE/],['exports-shape',o=>o.declaration.exports={},/SURFACE/],
    ['boundary-enter',o=>o.boundary.enter=null,/BOUNDARY/],['boundary-leave',o=>o.boundary.leave=null,/BOUNDARY/],
    ['tag',o=>o.errorTag=null,/ERROR_TAG/],['memory-min',o=>o.declaration.memory.minimum=0,/MEMORY_LIMITS/],
    ['tag-type',o=>o.errorTag=new WebAssembly.Tag({parameters:['f64']}),/ERROR_TAG_SIGNATURE/],
    ['tag-arity',o=>o.errorTag=new WebAssembly.Tag({parameters:['i32','i32']}),/ERROR_TAG_SIGNATURE/],
    ['memory-max',o=>o.declaration.memory.maximum=5,/MEMORY_LIMITS/],['memory-name',o=>o.declaration.memory.export='other',/MEMORY_EXPORT/],
    ['memory-absent',o=>o.declaration.memory=null,/MEMORY_LIMITS/],
    ['table-limits',o=>o.declaration.tables[0].maximum=5,/TABLE_LIMITS/],
    ['table-min',o=>o.declaration.tables[0].minimum=1,/TABLE_LIMITS/],['table-count',o=>o.declaration.tables=[],/TABLE_LIMITS/],
    ['export-duplicate',o=>o.declaration.exports.push(o.declaration.exports[0]),/EXPORT_DECLARATION/],
    ['export-name-type',o=>o.declaration.exports[0].name=1,/EXPORT_DECLARATION/],
    ['export-signature',o=>o.declaration.exports[0].params=['i64'],/EXPORT_SIGNATURE/],
    ['export-result-type',o=>o.declaration.exports[0].results=['i64'],/EXPORT_SIGNATURE/],
    ['export-absent',o=>o.declaration.exports[0].name='absent',/EXPORT_SIGNATURE/],
    ['export-omitted',o=>o.declaration.exports.pop(),/EXPORT_SET/],
    ['init-kind',o=>o.declaration.initialization.kind='guess',/INITIALIZATION/],
    ['init-absent',o=>o.declaration.initialization=null,/INITIALIZATION/],
    ['missing-start',o=>o.declaration.initialization={kind:'start'},/START_CONVENTION/],
    ['missing-initializer',o=>o.declaration.initialization.name='absent',/INITIALIZER_SIGNATURE/],
    ['initializer-type',o=>o.declaration.initialization.name='i32',/INITIALIZER_SIGNATURE/],
    ['import-omitted',o=>o.declaration.imports.pop(),/IMPORT_SET/],
    ['import-extra',o=>o.declaration.imports.push({module:'unused',name:'unused',params:[],results:[]}),/IMPORT_SET/],
    ['import-name',o=>o.declaration.imports[0].name='other',/IMPORT_DECLARATION/],
    ['import-duplicate',o=>o.declaration.imports[1]=o.declaration.imports[0],/IMPORT_DECLARATION/],
    ['import-type',o=>o.declaration.imports[0].params=['i64'],/IMPORT_SIGNATURE/],
    ['import-missing',o=>delete o.imports.host.value,/IMPORT_MISSING/]
  ];
  for(const [name,edit,pattern] of refusals)test('admission-'+name,()=>{
    const f=make('library',edit);throws(f.open,pattern);equal(f.entries(),0,'refused before foreign execution');balanced(f);
  });
  for(const [which,pattern] of [['start',/START_CONVENTION/],['memory-import',/FUNCTION_IMPORT_ONLY/],
    ['shared',/BOUNDED_UNSHARED_LIMITS/],['unbounded',/BOUNDED_UNSHARED_LIMITS/],['table-unbounded',/BOUNDED_UNSHARED_LIMITS/],
    ['memory64',/BOUNDED_UNSHARED_LIMITS/],['memory-export-absent',/MEMORY_EXPORT/],['memory-export-alias',/MEMORY_EXPORT/],
    ['memory-extra',/MEMORY_LIMITS/],['export-global',/EXPORT_KIND/],['table-externref',/FUNCREF_TABLE/],
    ['import-duplicate',/IMPORT_DECLARATION/],['reference-type',/SCALAR_TYPE/],['invalid-code',/CompileError/]])test('binary-refusal-'+which,()=>{
    const f=make(which,o=>{if(which==='import-duplicate')o.declaration.imports.push({...o.declaration.imports[0]});});
    throws(f.open,pattern);equal(f.entries(),0,'no publication');balanced(f);
  });
  for(const [name,args,pattern] of [['absent',[],/UNDECLARED_EXPORT/],['i32',[],/ARITY/],['i32',[1,2],/ARITY/],
    ['i32',new Array(1),/I32/],['i32',{},/ARITY/],
    ['i32',[1.5],/I32/],['i32',[2147483648],/I32/],['i32',[-2147483649],/I32/],['i32',[NaN],/I32/],
    ['i32',[1n],/I32/],['i64',[1],/I64/],['i64',[1n<<63n],/I64/],['i64',[-(1n<<63n)-1n],/I64/],
    ['f32',['1'],/FLOAT/],['f64',[1n],/FLOAT/]])test('call-refusal-'+rows.length,()=>{
    const f=make(),lib=f.open(),before=f.entries();throws(()=>lib.call(name,args),pattern);
    equal(f.entries(),before,'refusal before entry');equal(lib.state,'ready','state preserved');balanced(f);
  });
  for(const name of ['trap','oob','throw'])test('foreign-failure-'+name,()=>{
    const f=make(),lib=f.open(),kind=name==='throw'?'exception':'trap';
    const info=catchable(f,()=>lib.call(name),kind);equal(info.retired,kind==='trap','retirement');
    if(kind==='trap'){const before=f.entries();throws(()=>lib.call('void'),/RETIRED/);equal(f.entries(),before,'no later foreign call');}
    else equal(lib.call('i32',[19]),19,'recoverable instance');
  });
  for(const [name,value] of [['host-error',()=>{throw Error('original host error');}],['async',()=>Promise.resolve(2)],['bad-host-result',()=>1.5],['missing-host-result',()=>undefined]])test(name,()=>{
    const f=make('library',()=>{},{value}),lib=f.open();
    const info=catchable(f,()=>lib.call('host'),'host');assert(info.cause instanceof Error,'original error retained');
    equal(lib.call('i32',[20]),20,'recoverable host error');
  });
  test('falsy-host-failure',()=>{
    const f=make('library',()=>{},{value:()=>{throw null;}}),lib=f.open();
    const info=catchable(f,()=>lib.call('host'),'host');equal(info.cause,null,'falsy cause preserved');
  });
  for(const [which,init] of [['library',{kind:'export',name:'initialize'}],['start',{kind:'start'}]])test('initialization-failure-'+which,()=>{
    let probes=0;const cause=new WebAssembly.RuntimeError('initialization trap');
    const f=make(which,o=>o.declaration.initialization=init,{probe(){probes++;throw cause;}});
    const info=catchable(f,f.open,'trap');equal(info.cause,cause,'original cause');equal(info.retired,true,'no partial ready instance');equal(probes,1,'one attempt');
  });
  test('reentry-refused-and-recoverable',()=>{let lib;
    const f=make('library',()=>{},{value:()=>lib.call('i32',[1])});lib=f.open();
    const info=catchable(f,()=>lib.call('host'),'host');assert(/REENTRY/.test(info.cause),'nested call refused');equal(lib.call('i32',[2]),2,'later call');});
  test('close-active-refused',()=>{let lib;
    const f=make('library',()=>{},{value:()=>lib.close()});lib=f.open();
    const info=catchable(f,()=>lib.call('host'),'host');assert(/REENTRY/.test(info.cause),'active close refused');balanced(f);});
  test('close-idempotent',()=>{const f=make(),lib=f.open();lib.close();lib.close();
    throws(()=>lib.call('void'),/RETIRED/);balanced(f);});
  test('entry-failure-does-not-execute',()=>{let fail=false;
    const f=make('library',()=>{},{beforeEnter(){if(fail)throw Error('entry denied');}}),lib=f.open();
    fail=true;throws(()=>lib.call('add',[2]),/entry denied/);fail=false;equal(lib.call('add',[1]),1,'no earlier call');balanced(f);});
  test('async-entry-refused-before-foreign-code',()=>{let probes=0;
    const f=make('library',o=>o.boundary.enter=()=>Promise.resolve('token'),{probe(){probes++;}});
    throws(f.open,/ASYNC_BOUNDARY/);equal(probes,0,'no initialization');
  });
  test('async-admission-is-fatal',()=>{let fail=false;
    const f=make('library',o=>{const leave=o.boundary.leave;
      o.boundary.leave=token=>{leave(token);return fail?Promise.resolve():undefined;};}),lib=f.open();
    fail=true;throws(()=>lib.call('void'),/ADMISSION_FAILED/);equal(lib.state,'retired','retired');
  });
  test('admission-failure-is-fatal-and-preserves-primary',()=>{let fail=false;
    const f=make('library',()=>{},{beforeLeave(){if(fail)throw Error('owner admission failed');}}),lib=f.open();
    fail=true;const e=throws(()=>lib.call('trap'),/ADMISSION_FAILED/);
    assert(e instanceof AggregateError&&e.cause instanceof WebAssembly.RuntimeError,'trap remains primary');
    equal(lib.state,'retired','retire without admission');throws(()=>lib.call('void'),/RETIRED/);
  });
  for(const [name,code] of [['trap',1],['throw',2],['void',0]])test('wasm-caller-cleanup-'+name,()=>{
    const f=make(),lib=f.open();
    const caller=new WebAssembly.Instance(new WebAssembly.Module(binaries.caller),{env:{failure:f.tag,call:()=>lib.call(name)}}).exports;
    equal(caller.run(),code,'catchable inside caller');equal(caller.cleanups(),1,'one cleanup');balanced(f);
  });
  assert(rows.length>0,'no selected checks');
  return {status:'PASS',checks:rows.length,rows,scope:'scalar owner boundary; no generated Lisp, production D5, copies, callbacks or GC'};
}
