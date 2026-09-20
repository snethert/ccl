// The factory in this test copy replaces its slow import with a throwing oracle.
// Thus these checks prove direct Wasm execution, not a counters-only claim.
for(const high of [false,true]){
 for(const pinned of [false,true]){
  setup(high);
  const normal={name:'fast-double-add',op:'add',a:{kind:'64',bits:'3ff0000000000000'},b:{kind:'64',bits:'4000000000000000'},mask:7,safe:1,expected:{width:64,value:'4008000000000000',flags:0,condition:0,stage:3,a_flags:0,b_flags:0}};
  const cases=[normal,
   {...normal,name:'fast-double-sub',op:'sub',expected:{...normal.expected,value:'bff0000000000000'}},
   {...normal,name:'fast-double-mul',op:'mul',expected:{...normal.expected,value:'4000000000000000'}},
   {...normal,name:'fast-double-div',op:'div',expected:{...normal.expected,value:'3fe0000000000000'}},
   {...normal,name:'fast-single-add',a:{kind:'32',bits:'3f800000'},b:{kind:'32',bits:'40000000'},expected:{...normal.expected,width:32,value:'40400000'}},
   {...normal,name:'fast-mixed',a:{kind:'integer',value:'7'},expected:{...normal.expected,value:'4022000000000000'}},
   {...normal,name:'fast-single-rounds-operands-first',a:{kind:'integer',value:'16777217'},b:{kind:'32',bits:'cb800000'},expected:{...normal.expected,width:32,value:'00000000'}},
   {...normal,name:'fast-single-coerce',op:'single',expected:{...normal.expected,width:32,value:'3f800000',stage:1}},
   {...normal,name:'fast-double-coerce',op:'double',a:{kind:'32',bits:'3f800000'},expected:{...normal.expected,value:'3ff0000000000000',stage:1}},
   {...normal,name:'fast-integer-coerce',op:'single',a:{kind:'integer',value:'7'},expected:{...normal.expected,width:32,value:'40e00000',stage:1}},
   {...normal,name:'fast-exact-comparison',op:'gt',a:{kind:'integer',value:'16777217'},b:{kind:'32',bits:'4b800000'},expected:{...normal.expected,width:0,value:'T'}},
   {...normal,name:'fast-negative-zero',op:'mul',a:{kind:'64',bits:'8000000000000000'},expected:{...normal.expected,value:'8000000000000000'}},
   {...normal,name:'fast-masked-underflow',op:'div',a:{kind:'64',bits:'0000000000000001'},expected:{...normal.expected,value:'0000000000000000'}}];
  for(const c of cases){current=c.name;reset(c,pinned);invoke(c);rows.push({name:current,high,pinned});}
  current='fast-identity';reset({...normal,op:'double'},pinned);const identity=get(ROOT+8);const status=calculate(11,ROOT,1);assert.equal(status,1024);assert.equal(get(ROOT+16),identity,current);rows.push({name:current,high,pinned});
  const mustMiss=(name,damage,action=()=>calculate(0,ROOT,1))=>{
   current=name;reset(normal,pinned);damage();const before=Buffer.from(new Uint8Array(memory.buffer,0,48*65536));
   assert.throws(action,/SCALAR_SLOW_POISON/,name);assert.deepEqual(Buffer.from(new Uint8Array(memory.buffer,0,48*65536)),before,name+' no writes');rows.push({name,high,pinned});
  };
  mustMiss('full-mask-fallback',()=>set(200,31));
  mustMiss('shortage-fallback',()=>set(48,t(52)));
  mustMiss('owner-boundary-fallback',()=>{},()=>owner.atSafepoint(()=>calculate(0,ROOT,1)));
  current='boundary-restored-fast';reset(normal,pinned);invoke(normal);rows.push({name:current,high,pinned});
  mustMiss('stack-operand-fallback',()=>{put(ROOT+64,791);put(ROOT+68,0);put(ROOT+72,0);put(ROOT+76,0x3ff00000);put(ROOT+8,ROOT+70);});
  mustMiss('retired-operand-fallback',()=>{const p=owner.spaces[1].start;put(p,791);put(p+4,0);put(p+8,0);put(p+12,0x3ff00000);put(ROOT+8,p+6);});
  mustMiss('wrong-result-root-fallback',()=>put(ROOT+16,0));
  mustMiss('invalid-live-bounds-fallback',()=>set(68,BASE));set(68,BASE+8);
  mustMiss('invalid-canonical-fallback',()=>put(T-6,1578));put(T-6,1850);
  mustMiss('partial-pinned-object-fallback',()=>{const p=IMAGE+16376;put(p,791);put(p+4,0);put(ROOT+8,p+6);});
  // Unchecked full masks may bypass detection, but invalid enable words may not.
  current='unchecked-full-mask';reset(normal,pinned);set(200,31);const unchecked={...normal,mask:31,safe:0};invoke(unchecked);rows.push({name:current,high,pinned});
  mustMiss('invalid-mode-fallback',()=>set(200,32));set(200,7);
 }
}
setup();
const admissionRow={name:'admission',op:'add',a:{kind:'64',bits:'3ff0000000000000'},b:{kind:'64',bits:'4000000000000000'},mask:7,safe:1,expected:{width:64,value:'4008000000000000',flags:0,condition:0,stage:3,a_flags:0,b_flags:0}};
current='scalar-digest';assert.throws(()=>floatService(options({scalarDigest:'0'.repeat(64)})),/SCALAR_DIGEST/);rows.push({name:current});
current='scalar-imports';assert.throws(()=>floatService(options({scalarBytes:bytes,scalarDigest:inputs.float_sha256})),/SCALAR_IMPORTS/);rows.push({name:current});
for(const [name,pinned] of [
 ['overlap-pinned-fallback',[{start:IMAGE,end:IMAGE+32},{start:IMAGE+8,end:IMAGE+40}]],
 ['overlap-active-fallback',[{start:t(56),end:t(56)+8}]],
 ]){current=name;calculate=floatService(options({pinned}));reset(admissionRow);assert.throws(()=>calculate(0,ROOT,1),/SCALAR_SLOW_POISON/,name);rows.push({name});}
current='pinned-manifest-copy';const pinnedCopy=[{start:IMAGE,end:IMAGE+16384}];calculate=floatService(options({pinned:pinnedCopy}));pinnedCopy[0].end=0;reset(admissionRow,true);invoke(admissionRow);rows.push({name:current});
