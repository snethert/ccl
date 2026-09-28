// Foreign modules have their own memory and initialization surface. Keep this
// reader separate from binary.mjs, whose generated-Lisp restrictions still hold.
import {hex} from './bytes.mjs';

export function inspectForeign(bytes) {
  const need=(ok,reason)=>{if(!ok)throw Error('foreign-binary: '+reason);};
  need(hex(bytes.subarray(0,8))==='0061736d01000000','HEADER');
  let p=8,end=bytes.length;
  const byte=()=>{need(p<end,'TRUNCATED');return bytes[p++];};
  const leb=()=>{let n=0;for(let i=0;i<5;i++){
    const b=byte();need(i!==4||b<=15,'LEB');n+=(b&127)*2**(7*i);
    if(!(b&128))return n;
  }throw Error('foreign-binary: LEB');};
  const str=()=>{const n=leb();need(p+n<=end,'NAME');
    const s=new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(p,p+n));p+=n;return s;};
  const vec=f=>{const n=leb();need(n<=end-p,'VECTOR');return Array.from({length:n},f);};
  const scalar=()=>{const t={127:'i32',126:'i64',125:'f32',124:'f64'}[byte()];need(t,'SCALAR_TYPE');return t;};
  const limits=()=>{const flags=leb();need(flags===1,'BOUNDED_UNSHARED_LIMITS');
    const minimum=leb(),maximum=leb();need(minimum<=maximum,'LIMITS_ORDER');return {minimum,maximum};};
  const m={types:[],imports:[],functions:[],exports:[],memories:[],tables:[],start:null};
  const seen=new Set();
  while(p<bytes.length){
    end=bytes.length;const id=byte(),size=leb();end=p+size;need(end<=bytes.length,'SECTION');
    need(id<=13,'SECTION_KIND');need(id===0||!seen.has(id),'DUPLICATE_SECTION');seen.add(id);
    if(id===1)m.types=vec(()=>{need(byte()===96,'FUNCTION_TYPE');return {params:vec(scalar),results:vec(scalar)};});
    else if(id===2)m.imports=vec(()=>{
      const module=str(),name=str();need(byte()===0,'FUNCTION_IMPORT_ONLY');
      const index=leb();m.functions.push(index);need(m.types[index],'IMPORT_TYPE');
      return {module,name,...m.types[index]};
    });
    else if(id===3)m.functions.push(...vec(leb));
    else if(id===4)m.tables=vec(()=>{need(byte()===112,'FUNCREF_TABLE');return limits();});
    else if(id===5)m.memories=vec(limits);
    else if(id===7)m.exports=vec(()=>({name:str(),kind:byte(),index:leb()}));
    else if(id===8)m.start=leb();
    // Globals, elements, code, data, data-count and exception tags are checked
    // by the engine. With no resource imports they can initialize only this instance.
    else p=end;
    need(p===end,'SECTION_END');
  }
  for(const e of m.exports)if(e.kind===0){
    e.signature=m.types[m.functions[e.index]];need(e.signature,'EXPORT_TYPE');
  }
  return m;
}
