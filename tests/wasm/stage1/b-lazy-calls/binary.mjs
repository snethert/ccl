// Narrow reader for generated B modules. The engine validates instructions;
// this reader independently constrains the installation surface before instantiation.
export function inspect(bytes) {
  const fail = reason => { throw Error(reason); };
  if (Buffer.from(bytes.subarray(0,8)).toString('hex') !== '0061736d01000000') fail('HEADER');
  let p=8,end=bytes.length;const byte=()=>{if(p>=end)fail('TRUNCATED');return bytes[p++];};
  const leb=()=>{let n=0;for(let i=0;i<5;i++){const b=byte();if(i===4&&b>15)fail('LEB');n+=(b&127)*2**(7*i);if(!(b&128))return n;}fail('LEB');};
  const str=()=>{const n=leb();if(p+n>end)fail('NAME');const s=new TextDecoder('utf8',{fatal:true}).decode(bytes.subarray(p,p+n));p+=n;return s;};
  const vec=f=>{const n=leb();if(n>end-p)fail('VECTOR');return Array.from({length:n},f);};
  const type=()=>{const b=byte();const t={127:'i32',126:'i64',125:'f32',124:'f64',112:'funcref'}[b];if(!t)fail('TYPE');return t;};
  const limits=()=>{const flags=leb();if(flags>3)fail('LIMITS');return {flags,minimum:leb(),maximum:flags&1?leb():null};};
  const m={types:[],imports:[],functions:[],exports:[],sections:[]},seen=new Set();
  while(p<bytes.length){end=bytes.length;const id=byte(),n=leb();end=p+n;if(end>bytes.length)fail('SECTION');
    if(id!==0&&seen.has(id))fail('DUPLICATE_SECTION');seen.add(id);m.sections.push(id);
    // No start, data, element, defined memory/table/global or tag sections.
    if(![0,1,2,3,7,10].includes(id))fail('INITIALIZATION_OR_SECTION');
    if(id===1)m.types=vec(()=>{if(byte()!==96)fail('FUNCTION_TYPE');return {params:vec(type),results:vec(type)};});
    else if(id===2)m.imports=vec(()=>{const module=str(),name=str(),k=byte();
      if(k===0)fail('FUNCTION_IMPORT');
      if(k===1)return {module,name,kind:'table',element:type(),...limits()};
      if(k===2)return {module,name,kind:'memory',...limits()};
      if(k===3)return {module,name,kind:'global',type:type(),mutable:byte()};
      if(k===4){if(byte()!==0)fail('TAG_ATTRIBUTE');return {module,name,kind:'tag',signature:m.types[leb()]};}
      fail('IMPORT_KIND');});
    else if(id===3)m.functions=vec(leb);
    else if(id===7)m.exports=vec(()=>({name:str(),kind:byte(),index:leb()}));
    else p=end;
    if(p!==end)fail('SECTION_END');
  }
  return m;
}
