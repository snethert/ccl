// Exercise the actual emitted token expression independently of Lisp's frame
// prologue: an invalid TCR is outside the installed module's calling contract.
import fs from 'node:fs';
import assert from 'node:assert/strict';
const [dir,output]=process.argv.slice(2),rows=[];
for(const [variant,accepted] of [['real',[]],['zero',[0]],['alignment',[1025]],['positive',[2147483648]]]){
  const bytes=fs.readFileSync(dir+'/'+variant+'.wasm');
  for(const tcr of [0,1025,2147483648,1024,2147483632]){
    const module=(await WebAssembly.instantiate(bytes,{env:{tcr}})).instance.exports;
    const invalid=[0,1025,2147483648].includes(tcr);
    if(invalid&&!accepted.includes(tcr)){
      assert.throws(()=>module.token(),e=>e.is?.(module.call_error)&&e.getArg(module.call_error,0)===4);
      rows.push({variant,tcr,refused:4});
    }else{
      assert.equal(module.token()>>>0,tcr);rows.push({variant,tcr,returned:tcr});
    }
  }
}
fs.writeFileSync(output,JSON.stringify({status:'PASS',scope:'emitted expression; invalid TCRs cannot enter the ordinary Lisp frame safely',rows},null,2)+'\n');
