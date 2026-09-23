import {processOwner} from './process.mjs';
import {imageArguments} from './image-input.mjs';
import {checkBootClasses} from './class-boot.mjs';
import {encodeGraph,decodeGraph} from './graph.mjs';
import {checkKeywordMetadata} from './metadata-check.mjs';
import fs from 'node:fs';
import {checkBignums} from './bignum-check.mjs';
import {checkFuncallables} from './gf-check.mjs';
import {checkInstaller} from './installer-check.mjs';
import assert from 'node:assert/strict';
import {parentPort,workerData} from 'node:worker_threads';
import {install} from './install.mjs';
import {CollectorOwner} from './runtime/collector-owner.mjs';
import {integerService} from './runtime/integer-service.mjs';
import {floatService} from './runtime/float-service.mjs';
import {sha256} from './runtime/sha256.mjs';
  const {base,dir}=workerData,NIL=77825,T=77838,tcr=1024,root=131064;
  const imageLoads=[];let loadedImage,saveReady;
  const config=12582912,size=1048576,other=10485760;
  const memory=new WebAssembly.Memory({initial:Math.max(320,Math.ceil((base+size)/65536)),maximum:32769,shared:true});
  const view=new DataView(memory.buffer),get=p=>view.getUint32(p,true),put=(p,n)=>view.setUint32(p,n,true);
  const bytes=(p,n)=>new Uint8Array(memory.buffer,p,n);
  const collector=(await WebAssembly.instantiate(fs.readFileSync(dir+'/collector.wasm'),{env:{memory}})).instance.exports;
  let internalCollections=0;
  function collect(){const old=get(tcr+56),dest=old===other?base:other;
    put(config+16,dest);put(config+20,dest+size);
    assert.equal(collector.collect(config),0,'internal collection');
    bytes(old,size).fill(0xda);internalCollections++;
  }
  let serviceOwner,integer,floating,integerCalls=0,floatCalls=0,fastChecks=0,retryCollections=0,activeCase='';
  const gen=await install({dir,memory,tcr,get,put,collect,calculateI:(...a)=>{integerCalls++;return integer(...a);},calculateF:(...a)=>{floatCalls++;return floating(...a);},ensure:bytes=>{collect();retryCollections++;if(get(tcr+52)-get(tcr+48)<bytes)throw new WebAssembly.Exception(gen.call_error,[6]);}});
  const ci=fs.readFileSync(dir+'/integer.wasm'),cf=fs.readFileSync(dir+'/float.wasm'),cd=fs.readFileSync(dir+'/detector.wasm'),cb=fs.readFileSync(dir+'/collector.wasm');
  put(NIL-1,NIL);put(NIL+3,NIL);
  function services(){
   const regions=[['tcr',1024,1280],['vstack',131064,196608],['temp',700000,780000],['control',900000,1000000],['c-stack',1048576,1114112],['scratch',12582912,20971520],['root-list',4600000,5648576],['external',1170000,1174096],['bindings',680000,696384]].map(([role,start,end])=>({name:role,role,start,end}));
   for(const [i,[start,end]] of [[77824,77896],[7000000,gen.ownerEnd],[1200000,gen.symbolEnd],[2097152,gen.imageEnd]].entries())regions.push({name:'image'+i,role:'image',start,end});
   const owner=CollectorOwner.create(memory,cb,sha256(cb),{version:1,collector:'copying',workers:1,egc:false,maximumPages:32769,tcr,logCapacity:262144,regions,spaces:[{name:'a',start:base,end:base+size},{name:'b',start:other,end:other+size}],groups:['module-constants','callbacks','registry','host'].map(kind=>({kind,slots:[]}))});
   serviceOwner=owner;const boundary=owner.atSafepoint.bind(owner);
   owner.atSafepoint=fn=>boundary(o=>{if((activeCase.startsWith('CORE-LIBM-')||activeCase.startsWith('CORE-TRANSCEND-')))collect();return fn(o);});
   const common={memory,tcr,owner,callError:gen.call_error,pinned:regions.filter(r=>r.role==='image')};
   integer=integerService({...common,bytes:ci,digest:sha256(ci)});
   floating=floatService({...common,bytes:cf,digest:sha256(cf),detectorBytes:cd,detectorDigest:sha256(cd)});
  }
  const movingPools=JSON.parse(fs.readFileSync(dir+'/compiled/moving-pools.json'));
  const signedZero=[],libmRows=[],shiftRows=[];
  function floatBits(v){if(v.single!==undefined)return {width:32,bits:BigInt(v.single)};
    assert.ok(v.double);return {width:64,bits:(BigInt(v.double[0])<<32n)|BigInt(v.double[1])};}
  function distance(a,b){const x=floatBits(a),y=floatBits(b);assert.equal(x.width,y.width);
    const sign=1n<<BigInt(x.width-1),mask=(sign<<1n)-1n;
    if((x.bits&~sign)===0n||(y.bits&~sign)===0n){assert.equal(x.bits,y.bits,'signed zero');return 0;}
    const ordered=z=>z&sign?(~z)&mask:z|sign;
    const d=ordered(x.bits)-ordered(y.bits);return Number(d<0n?-d:d);}

  const native=JSON.parse(fs.readFileSync(dir+'/compiled/native.json')),rows=[];
  const caseIds=JSON.parse(fs.readFileSync(dir+'/case-ids.json'));
  const selected=workerData.indices.map(i=>({...native[i],caseId:caseIds[i]}));
  const conditionCallers=new Set(JSON.parse(fs.readFileSync(dir+'/compiled/condition-callers.json')));
  let nodeNext=4194304;const nodeDescriptions=new Map(),rawDescriptions=new Map(),flaggedSymbols=new Set();
  const ownerNames=JSON.parse(fs.readFileSync(dir+'/compiled/symbols.json'));
  const registryOwner=ownerNames.find(x=>x.name==='*ISTRUCT-CELLS*'&&x.package==='CCL');
  function addRoot(slot){gen.extraRoots.push(slot);put(4600000+4*(gen.extraRoots.length-1),slot);put(config+76,gen.extraRoots.length);}
  const conditionClasses=new Map(JSON.parse(fs.readFileSync(dir+'/compiled/native-condition-classes.json')).map((row,i)=>{
    const entry=get(gen.symbols.condition_registry-2+4*i),wrapper=get(entry-2);return [row.name,wrapper+6];
  }));
  const initialRegistry=Array.from({length:28},(_,i)=>get(gen.symbols.condition_registry-2+4*i));
  const initialConditionClasses=[...conditionClasses.values()].map(p=>[p,get(p)]);
  let currentGraph;
  const graphIO={get,put,bytes,tcr,encode,decode,hash:gen.eqTable,registerCell:cell=>{
    if(!registryOwner)return;
    const symbol=gen.ownerWords.get(registryOwner.id);let list=get(symbol+2);
    for(let at=list;at!==NIL;at=get(at-1))if(get(at+3)===cell)return;
    const p=get(tcr+48);put(tcr+48,p+8);put(p,list);put(p+4,cell);put(symbol+2,p+1);
  },conditionWord:name=>get(gen.classCells.get(name)??conditionClasses.get(name)),bindCondition:(name,word)=>{const slot=conditionClasses.get(name);if(slot!==undefined){put(slot,word);addRoot(slot);}const cell=gen.classCells.get(name);if(cell!==undefined)put(cell,word);},bindValue:(name,word)=>put(gen.ownerWords.get(ownerNames.find(x=>x.package+'::'+x.name===name).id)+2,word),bindFunction:(id,word)=>put(gen.ownerWords.get(id)+6,word),functionWord:id=>id.startsWith('SYMBOL:')?gen.ownerWords.get(id.slice(7)):get(gen.ownerWords.get(id.startsWith('s') ? id : ownerNames.find(x=>x.package+'::'+x.name===id).id)+6)};
  function encode(x){
    if(x?.graph){assert.notEqual(workerData.imageMode,'read','cold loader cannot project graphs');currentGraph=x.graph;return encodeGraph(x.graph,graphIO);}
    if(x&&x.classFixture){
      const [name,names,value,cell,count]=x.classFixture.vector;
      const a=encode(name),b=encode(names),c=encode(value),d=encode(cell);
      function node(tag,fields){const p=get(tcr+48),size=8*Math.ceil((fields.length+1)/2);put(p,fields.length*256+tag);fields.forEach((x,i)=>put(p+4+4*i,x));if(fields.length%2===0)put(p+4+4*fields.length,0);put(tcr+48,p+size);return p+6;}
      const instance=node(114,[0,NIL,NIL]),slots=node(106,[instance,c]),cls=node(114,[0,NIL,NIL]);
      const fields=Array(count).fill(NIL);fields[0]=cls;fields[3]=a;
      const classSlots=node(106,fields);
      const wrapper=node(130,[d,0,cls,b,NIL,NIL,NIL,NIL,NIL,NIL,NIL,0,NIL]);
      put(instance+2,wrapper);put(instance+6,slots);put(cls+6,classSlots);put(classSlots-2+5*4,wrapper);
      return instance;
    }
    if(x&&x.instance){
      const slots=encode(x.instance.slots),p=get(tcr+48);
      put(slots-6,(get(slots-6)&0xffffff00)|106);
      [882,0,NIL,slots].forEach((word,i)=>put(p+4*i,word));put(tcr+48,p+16);if(x.instance.backpointer)put(slots-2,p+6);return p+6;
    }
    if(x&&x.funcallable){
      const fields=x.funcallable.vector.map(encode),slots=get(tcr+48),side=slots+40,fn=side+32;
      [2298,NIL,...fields,NIL,NIL,NIL,NIL,0].forEach((w,i)=>put(slots+4*i,w));
      [2042,NIL,NIL,slots+6,NIL,NIL,NIL,NIL].forEach((w,i)=>put(side+4*i,w));
      const template=gen.functions.get('core_gf_identity')-6;
      bytes(fn,32).set(bytes(template,32));put(fn,1834);put(fn+28,side+6);put(tcr+48,fn+32);
      return fn+6;
    }
    if(x&&x.marker){assert(['unbound','slot-unbound'].includes(x.marker));return x.marker==='unbound'?51:83;}
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
    }
    if(x===null)return NIL;if(x===true)return T;
    if(x&&x.symbol)return gen.ownerWords.get(x.symbol);
    if(typeof x==='number')return (x*4)>>>0;
    if(x.character!==undefined)return (x.character*256+75)>>>0;
    function vector(tag,words,n=words.length){const p=get(tcr+48),bytes=8*Math.ceil((4+words.length*4)/8);put(p,n*256+tag);words.forEach((w,i)=>put(p+4+4*i,w));if((1+words.length)%2)put(p+4+words.length*4,NIL);put(tcr+48,p+bytes);return p+6;}
    if(x.function)return get(gen.ownerWords.get(x.function)+6);
    if(x.integers){const {tag,width,signed,values}=x.integers,p=get(tcr+48),n=8*Math.ceil((4+width*values.length)/8);bytes(p,n).fill(0);put(p,values.length*256+tag);const method='set'+(signed?'Int':'Uint')+(width*8);values.forEach((v,i)=>view[method](p+4+width*i,v,true));put(tcr+48,p+n);return p+6;}
    if(x.fixnums)return vector(183,x.fixnums.map(n=>(n*4)>>>0));
    if(x.single!==undefined)return vector(15,[x.single]);
    if(x.double)return vector(23,[0,x.double[1],x.double[0]]);
    if(x.vector)return vector(250,x.vector.map(encode));
    if(x.octets){const words=Array.from({length:Math.ceil(x.octets.length/4)},()=>0);x.octets.forEach((b,i)=>words[i>>>2]|=b<<((i%4)*8));return vector(199,words,x.octets.length); }
    if(x.string!==undefined)return vector(191,Array.from(x.string).map(c=>c.codePointAt(0)));
    if(x.bits!==undefined){let word=0;x.bits.split('').forEach((b,i)=>word|=Number(b)<<i);return vector(255,[word],x.bits.length);}
    if(x.ratio)return vector(10,x.ratio.map(encode));if(x.complex)return vector(26,x.complex.map(encode));
    if(x.integer!==undefined){let v=BigInt(x.integer),n=1;while(v<-(1n<<BigInt(32*n-1))||v>=(1n<<BigInt(32*n-1)))n++;let u=BigInt.asUintN(32*n,v),words=[];for(let i=0;i<n;i++){words.push(Number(u&0xffffffffn));u>>=32n;}return vector(7,words);}
    assert(Array.isArray(x)&&x.length===2);
    const car=encode(x[0]),cdr=encode(x[1]),p=get(tcr+48);
    assert(p+8<=get(tcr+52));put(p,cdr);put(p+4,car);put(tcr+48,p+8);return p+1;
  }
  function decode(x){
    if(x===51||x===83)return {marker:x===51?'unbound':'slot-unbound'};
    if(rawDescriptions.has(x)){const d=rawDescriptions.get(x);return {raw:{tag:d.tag,words:d.words.map((_,i)=>get(x-2+4*i))}};}
    if(flaggedSymbols.has(x))return {symbol:gen.wordOwners.get(x).symbol,flags:(get(x+14)|0)>>2};
    if(nodeDescriptions.has(x)){const d=nodeDescriptions.get(x);return {node:{tag:d.tag,fields:d.fields.map((_,i)=>decode(get(x-2+4*i)))}};}
    if(x===NIL)return null;if(x===T)return true;
    if(gen.wordOwners.has(x))return gen.wordOwners.get(x);
    if((x&3)===0)return (x|0)>>2;
    if((x&255)===75)return {character:x>>>8};
    if((x&7)===6){const h=get(x-6),n=h>>>8,tag=h&255;
     if(tag===114&&n===3&&get(x+2)!==NIL){
       const wrapper=get(x+2),cls=get(wrapper+6),slots=get(cls+6);
       return {classFixture:{vector:[decode(get(slots+10)),decode(get(wrapper+10)),decode(get(get(x+6)+2)),decode(get(wrapper-2)),get(slots-6)>>>8]}};
     }
     if(tag===114&&n===3){const slots=get(x+6);
       if(get(slots-2)===x)return {instance:{slots:{vector:Array.from({length:get(slots-6)>>>8},(_,i)=>i?decode(get(slots-2+4*i)):null)},backpointer:true}};
       return {instance:{slots:decode(slots)}};
     }
     if(tag===42&&n===7){const side=get(x+22),slots=get(side+6);return {funcallable:{vector:[1,2,3].map(i=>decode(get(slots-2+4*i)))}};}
     if(tag===42){for(const [id,word] of gen.ownerWords)if(get(word+6)===x)return {function:id};throw Error('unowned function');}
     if(tag===183)return {fixnums:Array.from({length:n},(_,i)=>(get(x-2+4*i)|0)>>2)};
     if(tag===15)return {single:get(x-2)};
     if(tag===23)return {double:[get(x+6),get(x+2)]};
     if(tag===130)return {node:{tag,fields:Array.from({length:n},(_,i)=>decode(get(x-2+4*i)))}};
     if(tag===250||tag===106)return {vector:Array.from({length:n},(_,i)=>decode(get(x-2+4*i)))};
     if([207,215,223,167,175].includes(tag)){const width=tag===207?1:[215,223].includes(tag)?2:4,signed=[207,223,175].includes(tag),method='get'+(signed?'Int':'Uint')+(width*8);return {integers:{tag,width,signed,values:Array.from({length:n},(_,i)=>view[method](x-2+width*i,true))}};}
     if(tag===199)return {octets:Array.from({length:n},(_,i)=>new Uint8Array(memory.buffer)[x-2+i])};
     if(tag===191)return {string:String.fromCodePoint(...Array.from({length:n},(_,i)=>get(x-2+4*i)))};
     if(tag===255)return {bits:Array.from({length:n},(_,i)=>(get(x-2+4*(i>>>5))>>>(i%32))&1).join('')};
     if(tag===10||tag===26)return {[tag===10?'ratio':'complex']:[decode(get(x-2)),decode(get(x+2))]};
     if(tag===7){let u=0n;for(let i=n-1;i>=0;i--)u=(u<<32n)|BigInt(get(x-2+4*i));return {integer:String(BigInt.asIntN(32*n,u))};}
    }
    assert.equal(x&7,1);return [decode(get(x+3)),decode(get(x-1))];
  }
  const growthChecks=[];let collections=0;const originalRootCount=gen.extraRoots.length;const initialSymbolFields=[...gen.ownerWords.values()].flatMap(p=>[6,10,14,18].map(d=>[p+d,get(p+d)]));
  // Restore every mutable memory region, including pinned objects, before
  // each case and movement variant. Instances and code tables stay installed.
  const resetRegions=[[0,196608],[680000,1000000],[1048576,1174096],
    [1200000,gen.symbolEnd],[1800000,1940000],[2097152,gen.imageEnd],
    [4194304,5648576],[7000000,gen.ownerEnd],[base,base+size],
    [other,other+size],[12582912,20971520]].map(([start,end])=>
      ({start,data:Uint8Array.from(bytes(start,end-start))}));
  for(const expected of selected){
    activeCase=expected.definition;
    function resetCase(){
    for(const region of resetRegions)bytes(region.start,region.data.length).set(region.data);
    bytes(tcr,256).fill(0);bytes(config,96).fill(0);
    put(tcr+200,7); // Native CCL default, independent of the case name.
    initialRegistry.forEach((word,i)=>put(gen.symbols.condition_registry-2+4*i,expected.definition.startsWith('CORE-CONDITION-IMPLICIT-')?NIL:word));
    for(const [offset,value] of [[48,base],[52,base+size],[56,base],[68,131072],[72,196608],
       [128,root],[80,700000],[76,700000],[84,780000],[88,900000],[92,900000],[96,1000000],[120,132352],[124,132512],[104,680000]])put(tcr+offset,value);
    put(config,tcr);put(config+16,other);put(config+20,other+size);
    put(config+68,262144);put(config+72,4600000);put(config+80,20971520);
    initialConditionClasses.forEach(([p,v])=>put(p,v));initialSymbolFields.forEach(([p,v])=>put(p,v));gen.extraRoots.length=originalRootCount;gen.reset(movingPools[base],conditionCallers.has(expected.definition)||expected.definition.startsWith('CORE-CPL-'));nodeNext=4194304;nodeDescriptions.clear();rawDescriptions.clear();flaggedSymbols.clear();services();
    gen.classCells.clear();
    put(config+76,gen.extraRoots.length);
    gen.extraRoots.forEach((slot,i)=>put(4600000+4*i,slot));
    }
    function globals(){for(let xs=expected.globals;xs;xs=xs[1]){const [symbol,value]=xs[0];put(gen.ownerWords.get(symbol.symbol)+2,encode(value));}}
    function initializeArguments(){
      currentGraph=expected.args.find(x=>x?.graph)?.graph;
      const loaded=imageArguments({memory,base,limit:base+size,tcr,root,get,put,gen,
        conditionSlots:initialConditionClasses.map(([p])=>p),expected,
        materialize:()=>{globals();return expected.args.map(encode);},dir,
        mode:workerData.imageMode,imageDir:workerData.imageDir,codeDigest:workerData.codeDigest,bootstrap:workerData.bootstrap});
      loadedImage=loaded.image;
      saveReady=loaded.saveReady;
      put(config+76,gen.extraRoots.length);
      gen.extraRoots.forEach((slot,i)=>put(4600000+4*i,slot));
      imageLoads.push({caseId:expected.caseId,digest:loaded.record,bytes:loaded.bytes,objects:loaded.objects});
      return loaded.args;
    }
    const owner=processOwner(memory,gen,base,size);
    try { owner.process(0,()=>{
    resetCase();
    const args=initializeArguments();
    put(root,0);put(root+4,args.length);args.forEach((x,i)=>put(root+8+4*i,x));
    // The same untouched definitions run with their arguments in both spaces.
    for(const move of [workerData.move]){
      if(move){resetCase();for(const row of JSON.parse(fs.readFileSync(dir+'/compiled/symbols.json')))if(row.package===null)put(gen.ownerWords.get(row.id)+2,51);
        // Start with fresh original arguments; the first call may mutate them.
        const fresh=initializeArguments();put(root,0);put(root+4,fresh.length);fresh.forEach((x,i)=>put(root+8+4*i,x));
        const old=get(tcr+56),dest=old===other?base:other;
        put(config+16,dest);put(config+20,dest+size);
        assert.equal(collector.collect(config),0,'collect '+expected.name);
        bytes(old,size).fill(0xda);collections++;
      }
      if(expected.definition.startsWith('CORE-RETRY-')&&expected.args[0]>0){
        for(let p=get(tcr+48);p<get(tcr+52);p+=8){put(p,NIL);put(p+4,NIL);}put(tcr+48,get(tcr+52));
      }
      const actualArgs=args.map((_,i)=>get(root+8+4*i));
      if(workerData.bootstrap){
        const values=checkBootClasses({gen,owners:ownerNames,get,put,root,collect});
        assert.deepEqual(values,expected.values);
        loadedImage.initialize(()=>true);
        rows.push({caseId:expected.caseId,name:expected.name,moved:move,values,ready:loadedImage.state});
        continue;
      }
      assert.equal(loadedImage.state,'INSTALLED','image loaded before entry');
      assert.equal(conditionCallers.has(expected.definition),true,'READY uses class mode');
      // The legacy mask registry is not an accepted fallback at READY.
      initialRegistry.forEach((_,i)=>put(gen.symbols.condition_registry-2+4*i,NIL));
      if(workerData.fault==='no-entry')throw Error('READY_ENTRY_REQUIRED');
      const priorIntegerCalls=integerCalls,priorFloatCalls=floatCalls;const rawValues=gen.invoke(expected.name,actualArgs);if(expected.definition==='CORE-TRANSCEND-DESTINATION')assert.equal(rawValues[0],rawValues[1],'target destination identity');const values=rawValues.map(decode);if(['MAX-2','MIN-2','/=-2','>=-2','<=-2'].includes(expected.definition)&&expected.args.every(x=>typeof x==='number'&&Number.isInteger(x)&&Math.abs(x)<536870912)){assert.equal(floatCalls,priorFloatCalls,'fixnum comparison left Wasm');fastChecks++;}if(['1+','1-','CORE-INTEGER-DIVIDE'].includes(expected.definition)&&expected.args.every(x=>typeof x==='number')&&expected.values.every(x=>typeof x==='number'&&x>=-536870912&&x<=536870911)){assert.equal(integerCalls,priorIntegerCalls,'fixnum arithmetic left Wasm');assert.equal(floatCalls,priorFloatCalls,'fixnum arithmetic left Wasm');fastChecks++;}
      const after=args.map((_,i)=>expected.after[i]?.graph ? decodeGraph(get(root+8+4*i),expected.after[i].graph,graphIO) : decode(get(root+8+4*i)));
      let expectedValues=expected.values;
      if(expected.definition==='CORE-SIGNED-ZERO-LITERAL'&&expected.args[0].double[0]===0x80000000){
        assert.deepEqual(expected.args,[{double:[0x80000000,0]}]);
        assert.deepEqual(expected.values,[{double:[0,0]}],'pinned native literal-zero quirk');
        expectedValues=[{double:[0x80000000,0]}];
      }
      if(expected.definition.startsWith('CORE-SIGNED-ZERO-'))
        signedZero.push({definition:expected.definition,args:expected.args,native:expected.values,target:values,moved:move});
      if(expected.definition.startsWith('CORE-SHIFT-')&&expected.definition.endsWith('-DOMAIN')){
        const [n,x]=expected.args;
        function shifted(width){const v=BigInt(x),bits=BigInt(n);if(n===0)return v;
          return expected.definition.includes('-LEFT-')?BigInt.asIntN(width,v<<bits):
            expected.definition.includes('-RIGHT-')?BigInt.asUintN(width,v)>>bits:v>>bits;}
        function integer(v){return v>=-536870912n&&v<=536870911n?Number(v):{integer:String(v)};}
        assert.deepEqual(expected.values,[integer(shifted(61))],'native 61-bit shift domain');
        expectedValues=[integer(shifted(30))];
        shiftRows.push({definition:expected.definition,args:expected.args,native:expected.values,target:expectedValues,moved:move});
      }
      if(expected.definition.startsWith('CORE-LIBM-')){
        assert.equal(values.length,1);assert.equal(expectedValues.length,1);
        const ulps=distance(values[0],expectedValues[0]);
        const operation=expected.definition.slice(10,-2);
        const isZero=a=>{const v=floatBits(a);return (v.bits&((1n<<BigInt(v.width-1))-1n))===0n;};
        if((['COS','COSH','EXP'].includes(operation)&&isZero(expected.args[0]))||
           (operation==='EXPT'&&isZero(expected.args[1])))assert.equal(ulps,0,'exact libm identity');
        assert.ok(ulps<=2,expected.definition+' exceeds adopted 2-ULP comparison envelope: '+ulps);
        libmRows.push({definition:expected.definition,args:expected.args,native:expectedValues,target:values,ulps,moved:move});
        assert.deepEqual(after,expected.after);
      }else {
        const actual={values,after}, reference={values:expectedValues,after:expected.after};
        function difference(a,b,path='root') {
          if(Object.is(a,b))return null;
          if(a===null||b===null||typeof a!=='object'||typeof b!=='object')return {path,actual:a,expected:b};
          if(JSON.stringify(Object.keys(a).sort())!==JSON.stringify(Object.keys(b).sort()))return {path,actualKeys:Object.keys(a),expectedKeys:Object.keys(b)};
          for(const key of Object.keys(a)){const found=difference(a[key],b[key],path+'.'+key);if(found)return found;}
          return null;
        }
        const mismatch=difference(actual,reference);
        assert.equal(mismatch,null,expected.definition+' moved='+move+' '+JSON.stringify(mismatch));
      }
      const state=[];for(let xs=expected.globalsAfter;xs;xs=xs[1]){const [symbol,value]=xs[0],actual=decode(get(gen.ownerWords.get(symbol.symbol)+2));assert.deepEqual(actual,value,expected.definition+' global '+symbol.symbol);state.push([symbol,actual]);}const recordedAfter=after.map(value=>value?.graph ? {
        graph_sha256:sha256(JSON.stringify(value.graph,(_key,item)=>
          item&&typeof item==='object'&&!Array.isArray(item)
            ? Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])) : item)),
        nodes:value.graph.nodes.length} : value);
      if(workerData.controls&&expected.definition==='CORE-CONDITION-TABLE-GROW'&&!move&&expected.values[1]===1500){
        const module=gen.mods.find(m=>m.name==='core_condition_eq_vector');
        assert(module,'constructor probe compiled in class mode');
        // Independent size, alignment, parity and power-of-two checks.
        for(const [label,count] of [['tag',91],['small',72],['large',262200],['odd',92],['power',104]]){
          const before=get(tcr+48);
          assert.throws(()=>gen.invoke(module.name,[count]),/checked 6$/);
          assert.equal(get(tcr+48),before,'constructor refusal before allocation');
          growthChecks.push(label);
        }
        for(const capacity of [4,8,16,16384]){
          const vector=gen.invoke(module.name,[4*(14+2*capacity)])[0],start=vector-6,end=start+64+8*capacity;
          assert.equal(get(start),(14+2*capacity)*256+74);
          const prefix=[NIL,1073741824,0,NIL,NIL,0,NIL,0,0,0xfffffffc,243,NIL,4*capacity,0];
          prefix.forEach((word,i)=>assert.equal(get(start+4+4*i),word,'EQ prefix '+i));
          for(let i=0;i<capacity;i++){assert.equal(get(start+60+8*i),243);assert.equal(get(start+64+8*i),NIL);}
          assert.equal(get(end-4),0,'EQ padding');
          assert.equal(gen.eqTable.ht_run(vector,end,3,0,0,1800000,1940000,1169504),0);
          assert.deepEqual([0,4,8,12].map(d=>get(1169504+d)),[0,NIL,1,0]);
          growthChecks.push('capacity '+capacity);
        }
        function entry(name){const owner=ownerNames.find(row=>row.package==='CCL'&&row.name===name);assert(owner,name);
          const module=gen.mods.find(row=>row.cplMode&&row.function===owner.id);assert(module,name);return module.name;}
        const make=entry('%WASM-MAKE-CLASS-TABLE'),set=entry('%WASM-CLASS-PUTHASH'),remove=entry('%WASM-CLASS-REMHASH');
        for(const size of [-4,65540,NIL]){
          assert.throws(()=>gen.invoke(make,[size]),/checked [0-9]+$/,'owner size refusal, never a trap');
          growthChecks.push('owner size '+size);
        }
        const table=gen.invoke(make,[65536])[0];put(root+4,2);put(root+12,table);
        let vector=get(table+14),start=vector-6,end=start+64+8*16384;
        for(let i=0;i<16384;i++)assert.equal(gen.eqTable.ht_run(vector,end,1,4*i,4*i,1800000,1940000,1169504),0);
        // Updating a full table must neither grow nor refuse.
        assert.deepEqual(gen.invoke(set,[12,table,88]),[88]);
        const saved=Uint8Array.from(bytes(start,end-start));
        assert.throws(()=>gen.invoke(set,[4000000,get(root+12),92]),/checked [0-9]+$/,'capacity refusal, never a trap');
        vector=get(get(root+12)+14);start=vector-6;end=start+64+8*16384;
        assert.deepEqual(bytes(start,end-start),saved,'full refusal preserves table');
        assert.deepEqual(gen.invoke(remove,[12,get(root+12)]),[T]);
        assert.deepEqual(gen.invoke(remove,[12,get(root+12)]),[NIL]);
        assert.deepEqual(gen.invoke(set,[4000000,get(root+12),92]),[92]);
        vector=get(get(root+12)+14);assert.equal(get(vector+46),65536);assert.equal(get(vector+30),65536);
        growthChecks.push('full update','full refusal preservation','tombstone reuse at limit');
        put(root+4,1);
      }
      if(expected.definition==='CORE-CONDITION-OWN-TABLE'){
        assert.deepEqual(checkBootClasses({gen,owners:ownerNames,get,put,root,collect,initialize:true}),expected.values);
        if(workerData.imageMode==='write')saveReady();
      }
      loadedImage.initialize(()=>true);
      assert.equal(loadedImage.state,'READY');
      const value=name=>get(gen.ownerWords.get(ownerNames.find(x=>x.package==='CCL'&&x.name===name).id)+2);
      assert.equal(value('*ENABLE-AUTOMATIC-TERMINATION*'),NIL);
      assert.equal(value('*%PERIODIC-TASKS%*'),NIL);
      const population=value('%ALL-GFS%');
      assert.equal(get(population-6),3*256+90);
      assert.equal(get(population-2),0,'strong population GC link');
      assert.notEqual(get(population+6),NIL,'live generic functions');
      if(workerData.fault==='early-ready')put(1174208,2);
      assert.equal(get(1174208),1,'process READY must be published last');
      rows.push({caseId:expected.caseId,name:expected.name,moved:move,values,after:recordedAfter,globals:state});
    }
    }); } catch(error) {
      assert.equal(get(1174208),3,'failed bootstrap cannot publish READY');
      if(!workerData.fault)throw error;
      parentPort.postMessage({rejected:workerData.fault,reason:error.message,state:get(1174208)});
      process.exit(0);
    }
    assert.equal(get(1174208),2,'process READY');
    assert.equal(owner.process(0,()=>{throw Error('bootstrap ran twice');}),false);
  }
  if(!workerData.controls){
    parentPort.postMessage({processReady:get(1174208),classMode:true,scheduler:false,imageLoads,base,rows,comparisons:rows.length,collections,internalCollections,growthChecks});
  }else if(process.env.CCL_DISPATCH_METADATA){
    const keywordMetadata=checkKeywordMetadata({gen,memory,tcr,root,get,put,encode});
    parentPort.postMessage({processReady:get(1174208),classMode:true,scheduler:false,imageLoads,growthChecks,base,comparisons:rows.length,keywordMetadata});
  }else if(process.env.CCL_LIBRARY_CASE){
    parentPort.postMessage({processReady:get(1174208),classMode:true,scheduler:false,imageLoads,focused:true,base,comparisons:rows.length,collections,internalCollections,growthChecks,rows,...gen.summary()});
  }else{
  const layout=JSON.parse(fs.readFileSync(dir+'/compiled/target-layout.json'));const layoutValues=gen.invoke(layout.name,[]).map(decode);assert.deepEqual(layoutValues,layout.target,'target node size');assert.notDeepEqual(layoutValues,layout.native,'host node size leaked');
  const refusals=[];
  function refused(name,args,code){assert.throws(()=>gen.invoke(name,args),new RegExp('checked '+code+'$'));refusals.push({name,code});}
  // Nearest conversion refuses, without a Wasm trap, at both sides of the
  // fixnum range and at the magnitudes that would round to 2^31.
  {const nearest=native.find(r=>r.definition==='%ROUND-NEAREST-DOUBLE-FLOAT->FIXNUM').name,
         truncate=native.find(r=>r.definition==='%TRUNCATE-DOUBLE-FLOAT->FIXNUM').name;
   const dbl=v=>{const b=new ArrayBuffer(8),d=new DataView(b);d.setFloat64(0,v,true);return encode({double:[d.getUint32(4,true),d.getUint32(0,true)]});};
   for(const v of [536870911.5,2147483647.49,2147483647.5,2147483647.75,2147483648,-2147483648,-536870913.5,NaN,Infinity])refused(nearest,[dbl(v)],5);
   for(const v of [536870912,-536870913,2147483647.5,NaN,-Infinity])refused(truncate,[dbl(v)],5);
   assert.deepEqual(gen.invoke(nearest,[dbl(536870911.4)]).map(decode),[536870911]);
   assert.deepEqual(gen.invoke(nearest,[dbl(-536870912)]).map(decode),[-536870912]);
   assert.deepEqual(gen.invoke(nearest,[dbl(-536870912.5)]).map(decode),[-536870912]);}
  const v=encode({vector:[1,2]}),raw=encode({string:'bad'});
  for(const name of ['core_natural_left','core_natural_right']){
    refused(name,[-4],32);
    refused(name,[encode({string:'not a word'})],32);
    refused(name,[encode({integer:'4294967296'})],32);
    for(const words of [[0],[0x80000000],[1,0],[0xffffffff,1],[0x80000000,0xffffffff]])
      refused(name,[encode({raw:{tag:7,words}})],32);
  }
  // Generic logical operations now reach CCL's own definitions instead of refusing a bignum.
  assert.deepEqual(gen.invoke('core_logical',[encode({integer:'1152921504606846976'}),0]).map(decode),[0,{integer:'1152921504606846976'},0,{integer:'1152921504606846992'},-1,0]);
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

  const bad=get(tcr+48);put(bad+1,506);put(bad+5,NIL);
  refused('core_access',[bad+7,0],4);
  refused('core_ilognot',[75],5);
  refused('core_schar',[0,0],4);
  refused('core_schar',[raw,12],4);
  refused('core_code_char',[4456448],5);
  for(const [name,args,code] of [
    ['core_make_vector',[0xfffffffc,NIL],6], ['core_make_vector',[75,NIL],6],
    ['core_make_vector',[67108864,NIL],6], ['core_make_vector',[4000000,NIL],6],
    ['core_make_list',[0xfffffffc,NIL],6], ['core_make_list',[4000000,NIL],6],
    ['core_make_string',[4,0],5], ['core_make_octets',[4,1024],5],
    ['core_shifts',[0xfffffffc,4],5], ['core_shifts',[4,75],5],
    ['core_logbitp',[0xfffffffc,4],5], ['core_logbitp',[4,75],5],
    ['core_nth_value',[75,NIL],5], ['core_u16',[NIL,0],4],
    ['core_s32',[encode({string:'x'}),0],4]]) refused(name,args,code);
  const writable=encode({vector:[1,2]}),snapshot=Buffer.from(bytes(writable-6,16));
  refused('core_uvset_checked',[writable,8,T],4);
  assert.deepEqual(Buffer.from(bytes(writable-6,16)),snapshot,'store refused before publication');
  const allocation=[48,52,56].map(offset=>get(tcr+offset));
  for(const [offset,value] of [[48,allocation[2]-8],[48,allocation[0]+1],
                             [52,memory.buffer.byteLength+8],[52,allocation[0]+4]]){
    const before=Buffer.from(bytes(allocation[0],16));
    try{
      put(tcr+offset,value);
      refused('core_make_string',[4,97*256+75],6);
      assert.deepEqual(Buffer.from(bytes(allocation[0],16)),before,'allocation refused before writes');
      assert.equal(get(tcr+48),offset===48?value:allocation[0],'allocation pointer unchanged');
    }finally{[48,52,56].forEach((word,i)=>put(tcr+word,allocation[i]));}
  }
  const typed=encode({integers:{tag:215,width:2,signed:false,values:[1,2]}});
  for(const index of [75,0xfffffffc,8])refused('core_u16',[typed,index],4);
  refused('core_u16',[(end+6)>>>0,0],4);
  put(end-8,8*256+215);
  refused('core_u16',[(end-8+6)>>>0,0],4);
  const padded=gen.invoke('core_gvector',[NIL])[0];assert.equal(get(padded+6),0,'node-vector padding');
  const funcallable=checkFuncallables({gen,memory,tcr,root,config,collector,collect,encode,decode,get,put});
  const bignums=checkBignums({gen,memory,tcr,root,collect,encode,get,put});
  const keywordMetadata=checkKeywordMetadata({gen,memory,tcr,root,get,put,encode});
  const installation=checkInstaller({dir,gen,memory,tcr,get,put,owner:serviceOwner});
  parentPort.postMessage({processReady:get(1174208),classMode:true,scheduler:false,imageLoads,bignums,keywordMetadata,installation,funcallable,signedZero,libmRows,shiftRows,refusals,layout:{...layout,values:layoutValues},retryCollections,integerCalls,floatCalls,fastChecks,base,comparisons:rows.length,collections,internalCollections,growthChecks,rows,...gen.summary()});
}
