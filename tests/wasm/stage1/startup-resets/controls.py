import shutil,subprocess

def run(out,command,read,save):
 rows=[]
 faults=[
  ('missing-global-store','wasm','POSTCONDITION'),
  ('wrong-global-value','wasm','POSTCONDITION'),
  ('wrong-global-destination','wasm','no foreign image writes'),
  ('missing-generated-completion','wasm','COMPLETION_MISSING'),
  ('unbound-install-identity','install','mutated installed bytes'),
  ('aliased-loader-bytes','install','PRIVATE_CATALOG'),
  ('wrong-binding-index-field','harness','non-global destination'),
  ('wrong-symbol-flags-field','harness','readonly destination'),
  ('forged-no-load','schedule','real native reset effects'),
 ]
 for name,kind,why in faults:
  d=out/'faults'/name;d.mkdir(parents=True)
  for f in out.iterdir():
   if f.is_file() and (f.suffix in ['.mjs','.wasm'] or f.name in ['expected.json','selection.json','tcr.json']):shutil.copy(f,d/f.name)
  c=d/'compiled';c.mkdir()
  for f in (out/'compiled').iterdir():
   if f.is_file() and f.suffix in ['.wasm','.json']:shutil.copy(f,c/f.name)
  if kind=='wasm':
   p=out/'compiled/reset_5568.wat';text=p.read_text()
   store='(i32.store (call $special_location (i32.load offset=8 (local.get $tmp1))) (i32.load offset=12 (local.get $tmp1)))'
   if name=='missing-generated-completion':old='(i32.const 404)';new='(i32.const 0)'
   else:
    old=store;new={'missing-global-store':'(drop (i32.load offset=12 (local.get $tmp1)))','wrong-global-value':'(i32.store (call $special_location (i32.load offset=8 (local.get $tmp1))) (i32.const 77838))','wrong-global-destination':'(i32.store (i32.add (call $special_location (i32.load offset=8 (local.get $tmp1))) (i32.const 32)) (i32.load offset=12 (local.get $tmp1)))'}[name]
   assert text.count(old)==1,(name,text.count(old));p=c/'reset_5568.wat';p.write_text(text.replace(old,new))
   command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',c/'reset_5568.wasm'],d/'compile.log')
  else:
   p=d/({'install':'install.mjs','harness':'check.mjs','schedule':'bootstrap-schedule.mjs'}[kind]);s=p.read_text()
   if name=='unbound-install-identity':
    start=s.index('      need(own&&');end=s.index("'INSTALL_PLAN_IDENTITY');",start)+len("'INSTALL_PLAN_IDENTITY');");s=s[:start]+s[end:]
   else:
    old,new={
     'aliased-loader-bytes':('bytes=snapshotBytes(m.bytes)','bytes=m.bytes'),
     'wrong-binding-index-field':("get(p+22),0,'RESET_GLOBAL_INDEX'","get(p+14),0,'RESET_GLOBAL_INDEX'"),
     'wrong-symbol-flags-field':("get(p+14)&8,0,'RESET_WRITABLE'","get(p+10)&8,0,'RESET_WRITABLE'"),
     'forged-no-load':('const result=invoke();',"for(const x of [...r.after,r.completion])new DataView(this.#memory.buffer).setUint32(x.address,x.value,true);const result=undefined;")
    }[name];assert s.count(old)==1;s=s.replace(old,new)
   p.write_text(s);command(['/usr/local/bin/node','--check',p],d/'syntax.log')
  args=['/usr/local/bin/node',d/'check.mjs',d,d/'execution.json'];save(d/'command.json',list(map(str,args)))
  with (d/'fault.log').open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=120)
  assert r.returncode!=0,name+' escaped'
  log=(d/'fault.log').read_text();assert why in log,(name,log[-3000:])
  rows.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(out/'controls.json',rows)
