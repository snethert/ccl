 const scenarios=read('scenarios.json'),native=read('compiled/native.json');
 const functionObject=name=>object(compiled.find(m=>m.name===name).id);
 for(const [label,name,argNames] of scenarios)for(const collectBefore of [false,true]){
  setup(8192);
  // These test objects are in the movable heap, and published through host
  // roots before the optional collection. No stale pointer is reused after it.
  let cursor=t(48);const cell=(car,cdr)=>{const p=cursor;cursor+=8;put(p,cdr);put(p+4,car);return p+1;};
  const userObject=cell(17*4,N),callback=functionObject('termination_callback');
  const argsObject=cell(userObject,cell(callback,N));set(48,cursor);
  put(EXTERNAL,userObject);put(EXTERNAL+4,argsObject);put(DONE+3,0);put(DONE-1,0);
  if(collectBefore){owner.atSafepoint(o=>o.collect());collections++;}
  if(label==='automatic-enabled')put(symbolNames.get('automatic_termination_enabled')+2,T);
  const resolve=a=>a==='object'?get(EXTERNAL):a==='args'?get(EXTERNAL+4):a==='done'?DONE:a==='callback'?callback:functionObject(a);
  const row=native.find(r=>r.label===label),expected=row.values.map(n=>n===null?null:BigInt(n));
  assert.deepEqual(call(name,argNames.map(resolve)),expected,label+' Lisp result');
  assert.deepEqual([get(DONE+3)/4,get(DONE-1)/4],row.done,label+' cleanup');
  assert.equal(get(get(EXTERNAL)+3),row.object*4,label+' callback must not run');
  assert.equal(t(112),0,'binding chain');assert.equal(t(140),0,'handler chain');
  assert.equal(get(BINDINGS+4),243,'handler binding restored');
  comparisons++;rows.push({label,collectBefore,values:row.values,done:row.done,callbackInvoked:false});
 }
 // Without a handler the ordinary ERROR path reaches the accepted fatal
 // boundary. It must not look like successful registration or change user data.
 setup(8192);put(DONE+3,17*4);
 assert.throws(()=>call('termination_register',[DONE,functionObject('termination_callback')]),/checked /,'unhandled registration');
 assert.equal(get(DONE+3),17*4);assert.equal(t(128),ROOT);assert.equal(t(64),ROOT+8);assert.equal(t(112),0);assert.equal(t(140),0);
 parentPort.postMessage({base,comparisons,collections,rows,unhandled:'REFUSED'});
}
