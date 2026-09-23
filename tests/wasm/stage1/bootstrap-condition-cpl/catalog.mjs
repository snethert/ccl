import assert from 'node:assert/strict';
import fs from 'node:fs';
const dir=process.argv[2], reports=[];
for(const base of [262144,2147483648]){
  const memory=new WebAssembly.Memory({initial:base/65536+1,maximum:32769,shared:true});
  const view=new DataView(memory.buffer),end=memory.buffer.byteLength;
  const put=(p,x)=>view.setUint32(p,x,true),get=p=>view.getUint32(p,true);
  const error=new WebAssembly.Tag({parameters:['i32']}),name=600006,cls=base+134,cell=base+65;
  const modules=Object.fromEntries(await Promise.all(['reader','header','pointer','last','class'].map(async key=>
    [key,await WebAssembly.compile(fs.readFileSync(`${dir}/${key}.wasm`))])));
  function reset(){
    new Uint8Array(memory.buffer,base,256).fill(0);
    new Uint8Array(memory.buffer,end-32,32).fill(0);
    put(base,506);put(base+4,cell);put(cell-1,cls);put(cell+3,name);put(cls-6,882);
    return base+6;
  }
  const cases=[
    ['first',()=>reset(),name,cls],
    ['last',()=>{const p=reset();put(base,762);put(base+4,base+81);put(base+8,cell);put(base+80,cls);put(base+84,name+32);return p;},name,cls],
    ['missing',()=>reset(),name+32,null,12],
    ['empty',()=>{const p=reset();put(base,250);return p;},name,null,12],
    ['pointer',()=>{reset();put(base+1,506);put(base+5,cell);return base+7;},name,null,12],
    ['header',()=>{const p=reset();put(base,504);return p;},name,null,12],
    ['header-span',()=>{reset();return end+6;},name,null,4],
    ['body-span',()=>{reset();put(end-8,762);put(end-4,cell);return end-2;},name,null,4],
    ['body-exact',()=>{reset();put(end-8,506);put(end-4,cell);return end-2;},name,cls],
    ['nil-cell',()=>{const p=reset();put(base+4,77825);return p;},name,null,12],
    ['cell-tag',()=>{const p=reset();put(base+4,cell+1);return p;},name,null,12],
    ['cell-span',()=>{const p=reset();put(base+4,end+1);return p;},name,null,4],
    ['class-nil',()=>{const p=reset();put(cell-1,77825);return p;},name,null,4],
    ['class-header',()=>{const p=reset();put(cls-6,626);return p;},name,null,4],
    ['class-span',()=>{const p=reset();put(cell-1,end-2);put(end-8,882);return p;},name,null,4],
    ['class-exact',()=>{const p=reset();put(cell-1,end-10);put(end-16,882);return p;},name,end-10],
  ];
  function run(module,row){
    const [label,prepare,key,expected,code]=row,catalog=prepare();
    const snapshot=[...new Uint8Array(memory.buffer,base,256),...new Uint8Array(memory.buffer,end-32,32)];
    const lookup=new WebAssembly.Instance(modules[module],{env:{memory,call_error:error,catalog}}).exports.lookup;
    let actual,refusal;
    try {actual=lookup(key)>>>0;} catch(e){
      assert(e.is?.(error),`${label}: trap is not a checked refusal`);
      refusal=e.getArg(error,0);
    }
    assert.deepEqual([...new Uint8Array(memory.buffer,base,256),...new Uint8Array(memory.buffer,end-32,32)],snapshot,label+' read-only');
    if(expected===null)assert.equal(refusal,code,label);
    else{assert.equal(refusal,undefined,label);assert.equal(actual,expected,label);}
  }
  for(const row of cases)run('reader',row);
  const rejected=[];
  for(const [mutant,label] of [['header','header'],['pointer','pointer'],['last','last'],['class','class-nil']]){
    assert.throws(()=>run(mutant,cases.find(row=>row[0]===label)),undefined,mutant+' must fail');rejected.push(mutant);
  }
  reports.push({base,checks:cases.length,rejected});
}
fs.writeFileSync(dir+'/results.json',JSON.stringify({status:'PASS',reports},null,2)+'\n');
console.log('PASS: catalog admission, both placements');
