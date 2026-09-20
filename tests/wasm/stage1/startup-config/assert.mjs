const fail=m=>{throw Error(m||'assertion');};
function assert(ok,m){if(!ok)fail(m);}
assert.equal=(a,b,m)=>{if(a!==b)fail(m||('equal '+a+' '+b));};
assert.deepEqual=(a,b,m)=>{
 const norm=x=>ArrayBuffer.isView(x)?Array.from(new Uint8Array(x.buffer,x.byteOffset,x.byteLength)):Array.isArray(x)?x.map(norm):x&&typeof x==='object'?Object.fromEntries(Object.keys(x).sort().map(k=>[k,norm(x[k])])):x;
 if(JSON.stringify(norm(a))!==JSON.stringify(norm(b)))fail(m||'deepEqual');
};
assert.throws=(fn,re,m)=>{let threw=false;try{fn();}catch(e){threw=true;if(!re.test(String(e)))fail((m||'throws')+': '+String(e));}if(!threw)fail(m||'missing refusal');};
export default assert;
