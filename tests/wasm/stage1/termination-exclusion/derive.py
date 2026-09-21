from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'startup-runtime'
def replace(s,a,b):
 assert s.count(a)==1,(a,s.count(a));return s.replace(a,b)
SCENARIOS=[
 ('named','termination_named',['object','callback','done']),
 ('default','termination_default',['object','done']),
 ('indirect','termination_indirect',['termination_register','object','callback','done']),
 ('apply','termination_apply',['termination_register','args','done']),
 ('dynamic','termination_dynamic',['termination_register','object','callback','done']),
 ('operands','termination_operands',['object','callback','done']),
 ('nested','termination_nested',['object','done']),
 ('handler','termination_rethrow',['object','done']),
 ('cancel','termination_indirect',['termination_cancel','object','callback','done']),
 ('lookup','termination_onearg',['termination_lookup','object']),
 ('drain','termination_noargs',['termination_drain']),
 ('automatic-disabled','termination_automatic',[]),
 ('automatic-enabled','termination_noargs',['termination_automatic']),
]
def compile_source(compiler_forms=None):
 forms=(HERE/'entries.lisp').read_text()
 scenarios='('+ ' '.join('("'+name+'" "'+fn+'" ('+' '.join('"'+a+'"' for a in args)+'))' for name,fn,args in SCENARIOS)+')'
 return '''(in-package :wasm32-compiler)
(load (merge-pathnames "export.lisp" *load-pathname*))
(let* ((out (ccl:getenv "POOL_OUTPUT")) (modules nil) (cases '%s) (native-cases '%s) (scenarios '%s))
 (dolist (row native-cases)
  (setf (fdefinition (intern (string-upcase (first row)))) (compile nil (second row))))
 (dolist (row cases)
  (let* ((m (compile-call-form (second row) (first row) (mapcar #'first cases))))
   (dolist (part (cons m (getf m :children)))
    (push part modules)
    (with-open-file(s(concatenate 'string out (getf part :name) ".wat") :direction :output :if-exists :error)
     (write-string(getf part :wat)s)))))
 (setq modules(nreverse modules))
 (with-open-file(s(concatenate 'string out "modules.json") :direction :output :if-exists :error)
  (write-char #\\[ s)(loop for m in modules for i from 0 do(unless(zerop i)(write-char #\\, s))
   (format s "{\\"name\\":~s}"(getf m :name)))(write-char #\\] s))
 (with-open-file(s(concatenate 'string out "pools.json") :direction :output :if-exists :error)
  (write-pool-graph s(mapcar(lambda(m)(getf m :pool))modules)))
 (set 'termination_unavailable (make-condition 'simple-error :format-control "Finalization is not supported in Stage 1."))
 (with-open-file(s(concatenate 'string out "native.json") :direction :output :if-exists :error)
  (write-char #\\[ s)
  (loop for (label name args) in scenarios for i from 0 do
   (unless(zerop i)(write-char #\\, s))
   (let* ((object(cons 17 nil)) (done(cons 0 0))
          (callback(fdefinition 'termination_callback)))
    (set 'automatic_termination_enabled (equal label "automatic-enabled"))
    (let* ((actual (mapcar (lambda(a) (cond ((equal a "object")object)((equal a "done")done)
                  ((equal a "callback")callback)((equal a "args")(list object callback))
                  (t(fdefinition(intern(string-upcase a)))))) args))
           (vals(multiple-value-list(apply(fdefinition(intern(string-upcase name)))actual))))
     (assert (= (car object) 17))
     (format s "{\\"label\\":~s,\\"values\\":[" label)
     (loop for val in vals for j from 0 do (unless(zerop j)(write-char #\\, s))
      (if(null val)(write-string "null" s)(format s "~d" val)))
     (format s "],\\"done\\":[~d,~d],\\"object\\":~d}"(car done)(cdr done)(car object)))))
  (write-char #\\] s)))
(format t "POOL-COMPILE-PASS~%%")
(ccl:quit)
''' % (compiler_forms or forms,forms,scenarios)

def check_source():
 s=(BASE/'check.mjs').read_text()
 s=s[:s.index(" for(const native of read('compiled/native.json'))")]
 for a in ["import {CollectionStatistics} from './statistics.mjs';\n","import {statisticsService} from './service.mjs';\n"]:s=replace(s,a,'')
 s=replace(s,"import {sha256} from './sha256.mjs';","import {sha256} from './sha256.mjs';\nimport {installConditions} from './conditions.mjs';")
 s=replace(s,",adapter=new WebAssembly.Module(fs.readFileSync(dir+'/adapter.wasm'))",'')
 s=s.replace('initial:16','initial:64').replace('32*16','32*64').replace('id<16','id<64').replace('i<16','i<64').replace('put(REG,16)','put(REG,64)').replace('size<=16','size<=64')
 s=replace(s,'  const layout={version:1,',"  const conditionData=installConditions(put,N);regions.push({name:'condition-image',role:'image',start:810000,end:conditionData.end});\n  const layout={version:1,")
 s=replace(s,'  put(N-1,N);','  installConditions(put,N);\n  put(N-1,N);')
 s=replace(s,'1180000,1184096','1180000,1196384')
 s=replace(s,'[104,BINDINGS],[108,0]','[104,BINDINGS],[108,4]')
 start=s.index('  clock=0n;step=0n;');end=s.index('  for(const m of compiled)',start)
 s=s[:start]+'''  for(let i=0;i<4;i++)put(BINDINGS+4*i,243);
  owner=CollectorOwner.create(memory,bytes,sha256(bytes),layout);
'''+s[end:]
 s=replace(s,'new WebAssembly.Instance(m.module,{env,symbols})','new WebAssembly.Instance(m.module,{env,symbols,codes:Object.fromEntries(compiled.map(c=>[c.name,4*c.id]))})')
 s=replace(s,"return [i.name,symbolNames.get(i.name)];","return [i.name,i.name==='condition_registry'?conditionData.registry:i.name==='error_message'?conditionData.message:symbolNames.get(i.name)];")
 start=s.index('  for(const [name,p] of symbolNames)');end=s.index(' function integer',start)
 s=s[:start]+'''  for(const [name,p] of symbolNames){
   if(name==='condition_handlers')put(p+22,4);
   if(name==='termination_unavailable')put(p+2,conditionData.condition);
   if(name==='automatic_termination_enabled')put(p+2,N);
   const m=compiled.find(m=>m.name===name);if(m)put(p+6,object(m.id));
  }
 }
'''+s[end:]
 s=replace(s,'function integer(p){','function integer(p){if(p===N)return null;')
 s=replace(s,'return n;}\n function call', 'if(get(p-2+4*((h>>>8)-1))&0x80000000)n-=1n<<BigInt(32*(h>>>8));return n;}\n function call')
 s=replace(s,"try{pair=m.entry(object(m.id),args.length);}catch(e){throw Error(name+': '+(e.is?.(call_error)?'checked '+e.getArg(call_error,0):String(e)));}","let failure;try{pair=m.entry(object(m.id),args.length);}catch(e){failure=Error(name+': '+(e.is?.(call_error)?'checked '+e.getArg(call_error,0):String(e)));}")
 s=replace(s,'  assert.equal(t(116),pair[1]);','  if(failure)throw failure;assert.equal(t(116),pair[1]);')
 s+=(HERE/'generated-check-tail.mjs').read_text()
 return s
