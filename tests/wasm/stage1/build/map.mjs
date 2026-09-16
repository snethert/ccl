// Complete decoder for the initial nonallocating pass-2 module profile.
// Opcode/section coverage is deliberately narrow; new lowering must extend it.
export function decode(bytes, entry) {
  let p=0,end=bytes.length,last=0;
  const fail=x=>{throw Error('GENERATED_MAP_'+x);};
  const byte=()=>{if(p>=end)fail('TRUNCATED');return bytes[p++];};
  const leb=(signed=false)=>{let n=0n,s=0n,b;do{b=byte();n|=BigInt(b&127)<<s;s+=7n;if(s>35n)fail('LEB');}while(b&128);if(signed&&(b&64))n|=-1n<<s;return Number(n);};
  const str=()=>{const n=leb();if(n>64||p+n>end)fail('STRING');const s=new TextDecoder('utf-8',{fatal:true}).decode(bytes.subarray(p,p+n));p+=n;return s;};
  const vector=f=>{const n=leb();if(n>32)fail('VECTOR');return Array.from({length:n},f);};
  const type=()=>{if(byte()!==0x7f)fail('TYPE');return 'i32';};
  const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
  if(!equal(Array.from(bytes.subarray(0,8)),[0,97,115,109,1,0,0,0]))fail('HEADER');p=8;
  const sections=[],types=[],imports=[],functions=[];let functionTypes,exports;
  while(p<bytes.length){end=bytes.length;const id=byte(),length=leb(),stop=p+length;if(id<=last||stop>bytes.length)fail('SECTION');last=id;end=stop;sections.push(id);
    switch(id){
      case 1:types.push(...vector(()=>{if(byte()!==0x60)fail('FUNCTION_TYPE');return `(${vector(type).join(',')})->(${vector(type).join(',')})`;}));break;
      case 2:imports.push(...vector(()=>{const module=str(),name=str(),kind=byte();
        if(kind===2){if(byte()!==3)fail('SHARED_MEMORY');return {module,name,kind:'memory',minimum:leb(),maximum:leb()};}
        if(kind===3){const value=type(),mutable=byte();return {module,name,kind:'global',value,mutable};}fail('IMPORT_KIND');}));break;
      case 3:functionTypes=vector(()=>leb());break;
      case 7:exports=vector(()=>{const name=str(),kind=byte(),index=leb();return {name,kind,index};});break;
      case 10:{if(leb()!==1||functionTypes?.length!==1||types[functionTypes[0]]!==entry.signature)fail('BODY_SIGNATURE');
        const length=leb(),bodyEnd=p+length;if(bodyEnd>end||leb()!==1||leb()!==1||type()!=='i32')fail('LOCALS');
        const operations=[];let depth=1;
        while(p<bodyEnd){const offset=p,op=byte();let name,operands=[];
          switch(op){
            case 0:name='unreachable';break;
            case 4:name='if';{const block=byte();if(![0x40,0x7f].includes(block))fail('BLOCK');depth++;}break;
            case 5:name='else';if(depth<2)fail('ELSE');break;
            case 11:name='end';depth--;break;
            case 32:name='local.get';operands=[leb()];if(operands[0]>2)fail('LOCAL');break;
            case 33:name='local.set';operands=[leb()];if(operands[0]!==2)fail('LOCAL_SET');break;
            case 35:name='global.get';operands=[leb()];if(operands[0]!==0)fail('GLOBAL');break;
            case 40:name='i32.load';operands=[leb(),leb()];break;
            case 54:name='i32.store';operands=[leb(),leb()];break;
            case 65:name='i32.const';operands=[leb(true)];break;
            case 71:name='i32.ne';break;
            default:fail('OPCODE_'+op);
          }
          operations.push({offset,name,operands});if(depth<0||depth===0&&p!==bodyEnd)fail('END');
        }
        if(depth!==0||p!==bodyEnd)fail('BODY_END');functions.push({...entry,index:0,operations});break;}
      default:fail('SECTION_KIND');
    }if(p!==stop)fail('SECTION_END');
  }
  if(!equal(sections,[1,2,3,7,10])||!equal(exports,[{name:'entry',kind:0,index:0}])||!equal(imports,[
    {module:'env',name:'memory',kind:'memory',minimum:1,maximum:32769},
    {module:'env',name:'tcr',kind:'global',value:'i32',mutable:0}]))fail('MODULE_PROFILE');
  return {version:1,imports,exports,functions};
}
