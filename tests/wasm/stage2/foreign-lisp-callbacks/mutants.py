MUTANTS = [
 ('foreign-service.mjs','callback-root-reload',"const argument=boxVector(values.map((v,i)=>encoded(v,spec.params[i])));\n  const fn=readRoot(),entry=callable(fn);","const fn=readRoot(),argument=boxVector(values.map((v,i)=>encoded(v,spec.params[i])));\n  const entry=callable(fn);",'lisp-callback-boxing-move'),
 ('foreign-service.mjs','callback-restore',"offsets.forEach((o,i)=>put(tcr+o,saved[i]));",";",'lisp-callback-moving-0'),
 ('foreign-service.mjs','callback-retain-chain',"put(base,head);put(base+4,2);","put(base,0);put(base+4,2);",'lisp-callback-moving-0'),
 ('collector-owner.mjs','drain-live-heap','this.#validateLive();\n  this.#drainingFinalizers=true',';\n  this.#drainingFinalizers=true','finalizer-drain-live-heap'),
 ('foreign-service.mjs','callback-count',"result[1]===1&&result[0]!==NIL","result[0]!==NIL",'lisp-callback-result-count'),
 ('foreign-service.mjs','callback-scalar-input',"encoded(v,spec.params[i])","encoded(0,spec.params[i])",'lisp-callback-moving-0'),
 ('foreign-service.mjs','callback-deregister',"return t.library.deregisterCallback(t.handle)?4:0;","return 4;",'lisp-callback-moving-0'),
 ('foreign-service.mjs','callback-generation',"get(row+4)===generation","true",'lisp-callback-refuse-generation'),
 ('foreign-service.mjs','callback-row-kind',"get(row+8)===17","true",'lisp-callback-refuse-row-kind'),
 ('foreign-service.mjs','callback-row-flags',"get(row+12)===23","true",'lisp-callback-refuse-row-flags'),
 ('foreign-service.mjs','callback-output',"return scalars.length===0?undefined:scalars.length===1?scalars[0]:scalars;","return scalars.length===0?undefined:scalars.length===1?0:scalars;",'lisp-callback-moving-0'),
]
