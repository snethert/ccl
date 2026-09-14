// Decode the complete small fixture binary; fail on any unrecognized shape.
export function decode(bytes, abi) {
  const fail = why => { throw Error(`MAP_${why}`); };
  const eq = (a,b) => JSON.stringify(a)===JSON.stringify(b);
  const r={p:8,end:bytes.length};
  const byte=()=>{if(r.p>=r.end)fail('TRUNCATED');return bytes[r.p++];};
  const leb=(signed=false)=>{let n=0n,shift=0n,b;do{b=byte();n|=BigInt(b&127)<<shift;shift+=7n;if(shift>35n)fail('LEB_BOUND');}while(b&128);
    if(signed&&(b&64))n|=(-1n)<<shift;const v=Number(n);if(!Number.isSafeInteger(v))fail('INTEGER');return v;};
  const vec=fn=>{const n=leb();if(n>64)fail('VECTOR_BOUND');return Array.from({length:n},fn);};
  const str=()=>{const n=leb();if(n>64||r.p+n>r.end)fail('STRING');const b=bytes.subarray(r.p,r.p+n);r.p+=n;return new TextDecoder('utf-8',{fatal:true}).decode(b);};
  const type=()=>{const b=byte();if(b!==0x7f&&b!==0x7e)fail('VALUE_TYPE');return b===0x7f?'i32':'i64';};
  const signature=()=>{if(byte()!==0x60)fail('TYPE');return `(${vec(type).join(',')})->(${vec(type).join(',')})`;};
  const limits=()=>{if(byte()!==1)fail('LIMIT_KIND');return [leb(),leb()];};
  if(!eq(Array.from(bytes.subarray(0,8)),[0,97,115,109,1,0,0,0]))fail('HEADER');
  const sections=[],types=[],imports=[],indices=[],exports={},slots=[],functions=[];
  let last=0;
  while(r.p<bytes.length){r.end=bytes.length;const section=byte(),size=leb(),end=r.p+size;
    if(section<=last||end>bytes.length)fail('SECTION_ORDER');last=section;r.end=end;sections.push(section);
    switch(section){
      case 1:types.push(...vec(signature));break;
      case 2:imports.push(...vec(()=>{const module=str(),name=str();if(byte()!==0)fail('IMPORT_KIND');return {module,name,signature:types[leb()]};}));break;
      case 3:indices.push(...vec(()=>leb()));break;
      case 4:if(leb()!==1||byte()!==0x70||!eq(limits(),[5,5]))fail('TABLE');break;
      case 5:if(leb()!==1||!eq(limits(),[1,1]))fail('MEMORY');break;
      case 7:vec(()=>{const name=str();if(byte()!==0||name in exports)fail('EXPORT');exports[name]=leb();});break;
      case 9:if(leb()!==1||leb()!==0||byte()!==0x41||leb(true)!==0||byte()!==0x0b)fail('ELEMENT');slots.push(...vec(()=>leb()));break;
      case 10:{const count=leb();if(count!==indices.length)fail('BODY_COUNT');
        for(let i=0;i<count;i++){const length=leb(),stop=r.p+length;if(stop>r.end||leb()!==0)fail('BODY_LOCALS');
          const index=imports.length+i,entry=abi.functions.find(f=>f.index===index),operations=[];let depth=1;
          if(!entry||types[indices[i]]!==entry.signature||slots[entry.slot]!==index)fail('ENTRY_IDENTITY');
          while(r.p<stop){const offset=r.p,op=byte();let name,operands=[];
            switch(op){
              case 0x00:name='unreachable';break;
              case 0x04:name='if';if(byte()!==0x40)fail('BLOCK_TYPE');depth++;break;
              case 0x0b:name='end';depth--;break;
              case 0x10:name='call';operands=[leb()];break;
              case 0x11:name='call_indirect';operands=[leb(),leb()];if(operands[1]!==0||!types[operands[0]])fail('CALL_TYPE');break;
              case 0x1a:name='drop';break;
              case 0x20:name='local.get';operands=[leb()];if(operands[0]!==0)fail('LOCAL');break;
              case 0x28:name='i32.load';operands=[leb(),leb()];break;
              case 0x41:name='i32.const';operands=[leb(true)];break;
              case 0x42:name='i64.const';operands=[leb(true)];break;
              case 0x46:name='i32.eq';break;
              case 0x6a:name='i32.add';break;
              case 0x6d:name='i32.div_s';break;
              default:fail('OPCODE');
            }
            operations.push({offset,name,operands});if(depth<0||(depth===0&&r.p!==stop))fail('END');
          }
          if(r.p!==stop||depth!==0)fail('BODY_END');functions.push({...entry,operations});
        }break;}
      default:fail('SECTION');
    }
    if(r.p!==end)fail('SECTION_END');
  }
  if(!eq(sections,[1,2,3,4,5,7,9,10])||!eq(imports,abi.imports)||!eq(exports,abi.exports)||
     !eq(slots,[1,2,3,4,5])||functions.length!==abi.functions.length)fail('MODULE_SHAPE');
  return {version:1,imports,exports,functions};
}
