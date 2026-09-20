import shutil,subprocess

def run(out,command,read,save):
 rows=[]
 changes=[
 ('clock-clamp','config.mjs','Math.max(1000,x.clockTicks)','Math.max(999,x.clockTicks)','native source effects'),
 ('period-rounding','config.mjs','Math.floor(1000000000/ticks)','Math.ceil(1000000000/ticks)','native source effects'),
 ('stack-rounding','config.mjs','Math.floor(x.stackSize/2)','Math.ceil(x.stackSize/2)','native source effects'),
 ('zero-stack-overrides','config.mjs','active=x.stackSize>0','active=x.stackSize>=0','native source effects'),
 ('cpu-forced-single','config.mjs','cpuCount:x.cpuCount','cpuCount:1','native source effects'),
 ('native-page-constant','config.mjs','pageSize:x.pageSize','pageSize:4096','native source effects'),
 ('browser-cpu-constant','browser-config.mjs','cpuCount=host.navigator?.hardwareConcurrency','cpuCount=1','reported CPU'),
 ('browser-page-unchecked','browser-config.mjs','pageSize=new host.WebAssembly.Memory({initial:1,maximum:1}).buffer.byteLength','pageSize=65536','wrong page'),
 ('browser-clock-unchecked','browser-config.mjs',"need(Number.isFinite(first)&&first>=0&&Number.isFinite(second)&&second>=first,'BROWSER_CLOCK');",'','clock NaN'),
 ('spin-value','config_5566.wat','(i32.const 4096)','(i32.const 4)','POSTCONDITION'),
 ('completion-omitted','config_5566.wat','(i32.const 420)','(i32.const 0)','COMPLETION_MISSING'),
 ('foreign-binding-write','config_5566.wat','(i32.const 420)','(block (result i32) (i32.store (i32.const 139264) (i32.const 4)) (i32.const 420))','foreign owner region'),
 ]
 for name,file,old,new,why in changes:
  d=out/'faults'/name;d.mkdir(parents=True)
  for f in out.iterdir():
   if f.is_file() and (f.suffix in ['.mjs','.wasm'] or f.name in ['assets.json','expected.json','cases.json','tcr.json']):shutil.copy(f,d/f.name)
  c=d/'compiled';c.mkdir()
  for f in (out/'compiled').iterdir():
   if f.is_file() and f.suffix in ['.wasm','.json']:shutil.copy(f,c/f.name)
  p=(c if file.endswith('.wat') else d)/file
  source=(out/'compiled'/file if file.endswith('.wat') else out/file).read_text();assert source.count(old)==1,(name,source.count(old));p.write_text(source.replace(old,new))
  if file.endswith('.wat'):command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],d/'compile.log')
  else:command(['/usr/local/bin/node','--check',p],d/'syntax.log')
  args=['/usr/local/bin/node',d/('browser-check.mjs' if name.startswith('browser-') else 'node.mjs')]
  if not name.startswith('browser-'):args += [d,d/'execution.json']
  save(d/'command.json',list(map(str,args)))
  with (d/'fault.log').open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=120)
  assert r.returncode!=0,name+' escaped';log=(d/'fault.log').read_text();assert why in log,(name,log[-2000:])
  rows.append(dict(name=name,status='REJECTED',diagnostic=why))
 save(out/'controls.json',rows)
