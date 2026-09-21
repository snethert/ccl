from pathlib import Path
import json,subprocess,sys,shutil
h=Path(__file__).resolve().parent;r=h.parents[3];p=h.parent/'bootstrap-values';o=Path(sys.argv[1]).resolve();d=o/'driver'
sys.path.insert(0,str(d));import encode
encode.Encoder.__init__.__defaults__=(r/'doc/WASM/contracts/wasm32-layout.v1.json',16*1024*1024)
from pool import compile_pool
owners=json.loads((o/'compiled/symbols.json').read_text());pool=compile_pool(json.loads((o/'compiled/pools.json').read_text()),{x['id']:600006+32*i for i,x in enumerate(owners)})
mat=pool.at(2097152);(o/'compiled/materialized.json').write_text(json.dumps(dict(image=mat.image.hex(),roots=mat.roots)))
(o/'compiled/moving-pools.json').write_text(json.dumps({str(b):dict(image=pool.at(b).image.hex(),roots=pool.at(b).roots) for b in [262144,2147483648]}))
sys.path.insert(0,str(h));import backend
runtime=o/'runtime';runtime.mkdir(exist_ok=True)
for f in (r/'runtime/wasm32').glob('*.mjs'):shutil.copy(f,runtime/f.name)
for name,text in backend.runtime_files().items():(runtime/name).write_text(text)
s=(p/'install.mjs').read_text().replace('result,collect}', 'result,collect,calculateI,calculateF}')
s=s.replace('initial:128','initial:1024').replace('put(registry,128)','put(registry,1024)').replace('610000','650000').replace('620000','850000').replace('length:256','length:1024').replace('i<256','i<1024').replace('put(tcr+108,256)','put(tcr+108,1024)')
s=s.replace('4*(i+1)', 'row.package===null?0:4*(i+1)')
s=s.replace('const compiled=[];', "const eql=(await WebAssembly.instantiate(fs.readFileSync(dir+'/eql.wasm'),{env:{memory}})).instance.exports;const hash={run:eql.ht_eql,collect:()=>{throw Error('unexpected EQL collection');},config:0,operation:3,scratch:1800000,scratch_end:1860000,result:1169504};\n const compiled=[];")
s=s.replace('probe:{collect},symbols:', 'hash,probe:{collect},integer:{calculate:calculateI},floating:{calculate:calculateF},symbols:')
s=s.replace('return {keywords,', 'return {call_error,imageEnd:cursor,symbolEnd:symbolNext,ownerEnd:600000+32*owners.length,keywords,')
s=s.replace('extraRoots.push(p+8);', 'for(const offset of [4,8,12,16,24])extraRoots.push(p+offset);')
s=s.replace("if(row.package==='KEYWORD')", "if(row.package===null)value=51;if(row.package==='CCL'&&row.name==='%TYPE-ERROR-TYPESPECS%')value=mat.roots[mods.length];if(row.package==='CCL'&&row.name==='*PRINT-STRING-LENGTH*')value=44;\n    if(row.package==='CCL'&&row.name==='$NHASH.VECTOR_OVERHEAD')value=56;\n    if(row.package==='KEYWORD')")
s=s.replace("try{pair=entry.fn(entry.self,args.length);}catch(e){throw Error(name+': '+(e.is?.(call_error)?'checked '+e.getArg(call_error,0):e));}", "let failure;try{pair=entry.fn(entry.self,args.length);}catch(e){failure=e;}")
s=s.replace("assert.equal(pair[1]>>>0,get(tcr+116)", "if(failure){assert.equal(get(tcr+116),before[29],name+' failed MV count');throw Error(name+': '+(failure.is?.(call_error)?'checked '+failure.getArg(call_error,0):failure));}assert.equal(pair[1]>>>0,get(tcr+116)")
# Use the accepted condition registry layouts, populated from native class slots.
registry=(h/'conditions.mjs').read_text()
s=s.replace('for(const {row,wasm,id} of compiled)', registry+'\n for(const {row,wasm,id} of compiled)')
s=s.replace('extraRoots.push(p+8);', 'for(const offset of [4,8,12,16,24])extraRoots.push(p+offset);')
s=s.replace("if(row.package==='KEYWORD')", "if(row.package==='CCL'&&row.name==='*PATHNAME-ESCAPE-CHARACTER*')value=92*256+75;put(600000+32*i+24,NIL);if(row.package==='KEYWORD')")
s=s.replace("failure.is?.(call_error)?'checked '+failure.getArg(call_error,0):failure", "failure.is?.(call_error)?'checked '+failure.getArg(call_error,0):failure.is?.(type_error)?'type_error '+failure.getArg(type_error,0):failure")
(o/'install.mjs').write_text(s)
s=(p/'check.mjs').read_text()
s=s.replace("import {install} from './install.mjs';",f"import {{install}} from './install.mjs';\nimport {{CollectorOwner}} from './runtime/collector-owner.mjs';\nimport {{integerService}} from './runtime/integer-service.mjs';\nimport {{floatService}} from './runtime/float-service.mjs';\nimport {{sha256}} from './runtime/sha256.mjs';")
s=s.replace('const gen=await install({dir,memory,tcr,get,put,collect});','''let integer,floating,integerCalls=0,floatCalls=0,fastChecks=0;
  const gen=await install({dir,memory,tcr,get,put,collect,calculateI:(...a)=>{integerCalls++;return integer(...a);},calculateF:(...a)=>{floatCalls++;return floating(...a);}});
  const ci=fs.readFileSync(dir+'/integer.wasm'),cf=fs.readFileSync(dir+'/float.wasm'),cd=fs.readFileSync(dir+'/detector.wasm'),cb=fs.readFileSync(dir+'/collector.wasm');
  put(NIL-1,NIL);put(NIL+3,NIL);
  function services(){
   const regions=[['tcr',1024,1280],['vstack',131064,196608],['temp',700000,780000],['control',900000,1000000],['c-stack',1048576,1114112],['scratch',1200000,1800000],['root-list',1114112,1169000],['external',1170000,1174096],['bindings',650000,654096]].map(([role,start,end])=>({name:role,role,start,end}));
   for(const [i,[start,end]] of [[77824,77896],[600000,gen.ownerEnd],[850000,gen.symbolEnd],[2097152,gen.imageEnd]].entries())regions.push({name:'image'+i,role:'image',start,end});
   const owner=CollectorOwner.create(memory,cb,sha256(cb),{version:1,collector:'copying',workers:1,egc:false,maximumPages:32769,tcr,logCapacity:32768,regions,spaces:[{name:'a',start:base,end:base+size},{name:'b',start:other,end:other+size}],groups:['module-constants','callbacks','registry','host'].map(kind=>({kind,slots:[]}))});
   const common={memory,tcr,owner,callError:gen.call_error,pinned:regions.filter(r=>r.role==='image')};
   integer=integerService({...common,bytes:ci,digest:sha256(ci)});
   floating=floatService({...common,bytes:cf,digest:sha256(cf),detectorBytes:cd,detectorDigest:sha256(cd)});
  }''')
s=s.replace('[84,900000],[120,100000],[124,100064],[104,610000]', '[84,780000],[88,900000],[92,900000],[96,1000000],[120,132352],[124,132512],[104,650000]')
s=s.replace('gen.reset(movingPools[base]);','gen.reset(movingPools[base]);services();')
s=s.replace("if(typeof x==='number')return (x*4)>>>0;",'''if(typeof x==='number')return (x*4)>>>0;
    if(x.character!==undefined)return (x.character*256+75)>>>0;
    function vector(tag,words,n=words.length){const p=get(tcr+48),bytes=8*Math.ceil((4+words.length*4)/8);put(p,n*256+tag);words.forEach((w,i)=>put(p+4+4*i,w));if((1+words.length)%2)put(p+4+words.length*4,NIL);put(tcr+48,p+bytes);return p+6;}
    if(x.function)return get(gen.ownerWords.get(x.function)+6);\n    if(x.single!==undefined)return vector(15,[x.single]);\n    if(x.double)return vector(23,[0,x.double[1],x.double[0]]);\n    if(x.vector)return vector(250,x.vector.map(encode));
    if(x.string!==undefined)return vector(191,Array.from(x.string).map(c=>c.codePointAt(0)));
    if(x.bits!==undefined){let word=0;x.bits.split('').forEach((b,i)=>word|=Number(b)<<i);return vector(255,[word],x.bits.length);}
    if(x.ratio)return vector(10,x.ratio.map(encode));if(x.complex)return vector(26,x.complex.map(encode));
    if(x.integer!==undefined){let v=BigInt(x.integer),n=1;while(v<-(1n<<BigInt(32*n-1))||v>=(1n<<BigInt(32*n-1)))n++;let u=BigInt.asUintN(32*n,v),words=[];for(let i=0;i<n;i++){words.push(Number(u&0xffffffffn));u>>=32n;}return vector(7,words);}''')
s=s.replace('assert.equal(x&7,1);return [decode(get(x+3)),decode(get(x-1))];', '''if((x&255)===75)return {character:x>>>8};
    if((x&7)===6){const h=get(x-6),n=h>>>8,tag=h&255;
     if(tag===42){for(const [id,word] of gen.ownerWords)if(get(word+6)===x)return {function:id};throw Error('unowned function');}\n     if(tag===15)return {single:get(x-2)};\n     if(tag===23)return {double:[get(x+6),get(x+2)]};\n     if(tag===130)return {node:{tag,fields:Array.from({length:n},(_,i)=>decode(get(x-2+4*i)))}};\n     if(tag===250)return {vector:Array.from({length:n},(_,i)=>decode(get(x-2+4*i)))};
     if(tag===191)return {string:String.fromCodePoint(...Array.from({length:n},(_,i)=>get(x-2+4*i)))};
     if(tag===255)return {bits:Array.from({length:n},(_,i)=>(get(x-2+4*(i>>>5))>>>(i%32))&1).join('')};
     if(tag===10||tag===26)return {[tag===10?'ratio':'complex']:[decode(get(x-2)),decode(get(x+2))]};
     if(tag===7){let u=0n;for(let i=n-1;i>=0;i--)u=(u<<32n)|BigInt(get(x-2+4*i));return {integer:String(BigInt.asIntN(32*n,u))};}
    }
    assert.equal(x&7,1);return [decode(get(x+3)),decode(get(x-1))];''')
s=s.replace('const values=gen.invoke(expected.name,actualArgs).map(decode);', "const priorIntegerCalls=integerCalls,priorFloatCalls=floatCalls;const values=gen.invoke(expected.name,actualArgs).map(decode);if(['MAX-2','MIN-2','/=-2','>=-2','<=-2'].includes(expected.definition)&&expected.args.every(x=>typeof x==='number'&&Number.isInteger(x)&&Math.abs(x)<536870912)){assert.equal(floatCalls,priorFloatCalls,'fixnum comparison left Wasm');fastChecks++;}if(['1+','1-','CORE-INTEGER-DIVIDE'].includes(expected.definition)&&expected.args.every(x=>typeof x==='number')&&expected.values.every(x=>typeof x==='number'&&x>=-536870912&&x<=536870911)){assert.equal(integerCalls,priorIntegerCalls,'fixnum arithmetic left Wasm');assert.equal(floatCalls,priorFloatCalls,'fixnum arithmetic left Wasm');fastChecks++;}")
s=s.replace('if(move){', "if(move){for(const row of JSON.parse(fs.readFileSync(dir+'/compiled/symbols.json')))if(row.package===null)put(gen.ownerWords.get(row.id)+2,51);")
s=s.replace('parentPort.postMessage({base,comparisons:', 'parentPort.postMessage({integerCalls,floatCalls,fastChecks,base,comparisons:')
s=s.replace("expected.name+' moved='+move", "expected.definition+' '+JSON.stringify(expected.args)+' moved='+move")
s=s.replace('parentPort.postMessage({integerCalls,floatCalls,fastChecks,base,comparisons:', "const layout=JSON.parse(fs.readFileSync(dir+'/compiled/target-layout.json'));const layoutValues=gen.invoke(layout.name,[]).map(decode);assert.deepEqual(layoutValues,layout.target,'target node size');assert.notDeepEqual(layoutValues,layout.native,'host node size leaked');\n  parentPort.postMessage({layout:{...layout,values:layoutValues},integerCalls,floatCalls,fastChecks,base,comparisons:")
s=s.replace("parentPort.postMessage({layout:", """const refusals=[];
  function refused(name,args,code){assert.throws(()=>gen.invoke(name,args),new RegExp('checked '+code+'$'));refusals.push({name,code});}
  const v=encode({vector:[1,2]}),raw=encode({string:'bad'});
  refused('core_logical',[encode({integer:'1152921504606846976'}),0],32);
  refused('core_ldb',[encode({integer:'1152921504606846976'})],32);
  refused('core_integer_divide',[4,8],45);
  refused('core_integer_divide',[28,12],45);
  refused('core_access',[0,0],4);
  refused('core_access',[raw,0],4);
  refused('core_access',[v,8],4);
  refused('core_access',[v,75],4);
  refused('core_access',[v,0xfffffffc],4);
  refused('core_access',[encode({vector:[]}),0],4);
  refused('core_struct_access',[v],4);
  const end=memory.buffer.byteLength;put(end-8,3*256+250);
  refused('core_access',[(end-8+6)>>>0,0],4);
  refused('core_access',[(end+6)>>>0,0],4);
  const slot=get(tcr+48);put(slot,256+106);put(slot+4,83);put(tcr+48,slot+8);
  refused('core_slot_access',[slot+6],4);
  parentPort.postMessage({refusals,layout:""")
s=s.replace('1180000' ,'1114112').replace('for(const expected of native){', "for(const expected of native){ fs.writeSync(2,expected.definition+' '+JSON.stringify(expected.args)+'\\n');")
s=s.replace("if(x.string!==undefined)", "if(x.octets){const words=Array.from({length:Math.ceil(x.octets.length/4)},()=>0);x.octets.forEach((b,i)=>words[i>>>2]|=b<<((i%4)*8));return vector(199,words,x.octets.length); }\n    if(x.string!==undefined)")
s=s.replace("if(tag===191)", "if(tag===199)return {octets:Array.from({length:n},(_,i)=>new Uint8Array(memory.buffer)[x-2+i])};\n     if(tag===191)")
s=s.replace("parentPort.postMessage({refusals,layout:", """
  const bad=get(tcr+48);put(bad+1,506);put(bad+5,NIL);
  refused('core_access',[bad+7,0],4);
  refused('core_ilognot',[75],5);
  refused('core_schar',[0,0],4);
  refused('core_schar',[raw,12],4);
  refused('core_code_char',[4456448],5);
  const padded=gen.invoke('core_gvector',[NIL])[0];assert.equal(get(padded+6),0,'node-vector padding');
  parentPort.postMessage({refusals,layout:""")
s=s.replace('for(const expected of native){', "for(const expected of native.filter(x=>!process.env.CCL_LIBRARY_CASE||x.definition===process.env.CCL_LIBRARY_CASE)){")
s=s.replace('Math.max(64,','Math.max(80,')
s=s.replace('let collections=0;', 'let collections=0;const originalRootCount=gen.extraRoots.length;const initialSymbolFields=[...gen.ownerWords.values()].flatMap(p=>[10,14,18].map(d=>[p+d,get(p+d)]));')
s=s.replace('function encode(x){', """let nodeNext=4194304;const nodeDescriptions=new Map(),rawDescriptions=new Map(),flaggedSymbols=new Set();
  const ownerNames=JSON.parse(fs.readFileSync(dir+'/compiled/symbols.json'));
  const registryOwner=ownerNames.find(x=>x.name==='*ISTRUCT-CELLS*'&&x.package==='CCL');
  function addRoot(slot){gen.extraRoots.push(slot);put(1114112+4*(gen.extraRoots.length-1),slot);put(config+76,gen.extraRoots.length);}
  function encode(x){
    if(x&&x.symbol&&x.flags!==undefined){const p=gen.ownerWords.get(x.symbol);put(p+14,x.flags*4);flaggedSymbols.add(p);return p;}
    if(x&&x.raw){const {tag,words}=x.raw,p=nodeNext;nodeNext+=(4+4*words.length+7)&~7;assert(nodeNext<4500000);put(p,(words.length<<8)|tag);words.forEach((v,i)=>put(p+4+4*i,v));rawDescriptions.set(p+6,x.raw);return p+6;}
    if(x&&x.node){
      const {tag,fields}=x.node,words=fields.map(encode),p=nodeNext;
      nodeNext+=(4+4*words.length+7)&~7;assert(nodeNext<4500000);
      put(p,(words.length<<8)|tag);words.forEach((v,i)=>{put(p+4+4*i,v);addRoot(p+4+4*i);});
      if(tag===130&&registryOwner){
        const symbol=gen.ownerWords.get(registryOwner.id),cell=words[0],q=nodeNext;nodeNext+=8;
        put(q,get(symbol+2));put(q+4,cell);put(symbol+2,q+1);addRoot(q);addRoot(q+4);
      }
      nodeDescriptions.set(p+6,x.node);return p+6;
    }""")
s=s.replace('function decode(x){', """function decode(x){
    if(rawDescriptions.has(x)){const d=rawDescriptions.get(x);return {raw:{tag:d.tag,words:d.words.map((_,i)=>get(x-2+4*i))}};}
    if(flaggedSymbols.has(x))return {symbol:gen.wordOwners.get(x).symbol,flags:(get(x+14)|0)>>2};
    if(nodeDescriptions.has(x)){const d=nodeDescriptions.get(x);return {node:{tag:d.tag,fields:d.fields.map((_,i)=>decode(get(x-2+4*i)))}};}""")
s=s.replace('gen.reset(movingPools[base]);', 'initialSymbolFields.forEach(([p,v])=>put(p,v));gen.extraRoots.length=originalRootCount;gen.reset(movingPools[base]);nodeNext=4194304;nodeDescriptions.clear();rawDescriptions.clear();flaggedSymbols.clear();')
s=s.replace('const args=expected.args.map(encode);', 'function globals(){for(let xs=expected.globals;xs;xs=xs[1]){const [symbol,value]=xs[0];put(gen.ownerWords.get(symbol.symbol)+2,encode(value));}}globals();const args=expected.args.map(encode);')
s=s.replace('const fresh=expected.args.map(encode);', 'globals();const fresh=expected.args.map(encode);')
s=s.replace('rows.push({name:expected.name,moved:move,values,after});', "const state=[];for(let xs=expected.globalsAfter;xs;xs=xs[1]){const [symbol,value]=xs[0],actual=decode(get(gen.ownerWords.get(symbol.symbol)+2));assert.deepEqual(actual,value,expected.definition+' global '+symbol.symbol);state.push([symbol,actual]);}rows.push({name:expected.name,moved:move,values,after,globals:state});")
(o/'check.mjs').write_text(s)
sys.path.insert(0,str(h.parent/"bootstrap-core"));import probe;probe.build(o/'compiled')
clang='/usr/local/opt/llvm/bin/clang';baseflags=['--target=wasm32','-O2','-nostdlib','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--max-memory=2147549184','-Wl,-z,stack-size=65536']
for name,extra in [('collector',['-matomics','-mbulk-memory','-Wl,--shared-memory','-Wl,--global-base=1048576','-Wl,--export=collect','-Wl,--export=__stack_pointer']),('integer',['-Wl,--global-base=65536','-Wl,--export=integer_calculate','-Wl,--export=integer_workspace_bytes']),('float',['-Wl,--global-base=65536','-ffp-contract=off','-fno-jump-tables','-Wl,--export=float_calculate_lisp'])]:
 subprocess.run([clang,*baseflags,*extra,(runtime/'collector.c' if name=='collector' else r/f'runtime/wasm32/{name}.c'),'-o',o/f'{name}.wasm'],check=True)
subprocess.run(['/usr/local/bin/wat2wasm',r/'runtime/wasm32/float-detector.wat','-o',o/'detector.wasm'],check=True)
shutil.copy(r.parent/'ccl-evidence/2026-09-21-stage1-population-pushnew-r1/execution/eql.wasm',o/'eql.wasm')
with (o/'execution.log').open('w') as log:subprocess.run(['/usr/local/bin/node',o/'check.mjs',o,o/'execution.json'],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=120)

shutil.copy(h/'istruct-check.mjs',o/'istruct-check.mjs')
subprocess.run(['/usr/local/bin/node',o/'istruct-check.mjs',o/'collector.wasm',o/'istruct-checks.json'],check=True)
