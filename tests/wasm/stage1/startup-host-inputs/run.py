import argparse,hashlib,importlib.util,json,os,re,shutil,subprocess,sys,tempfile
from pathlib import Path
from derive import HERE,ROOT,check
E=ROOT.parent/'ccl-evidence';NODE=Path('/usr/local/bin/node')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,**kw):
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300,**kw)
def cases():
 return [dict(name=n,input=dict(imageName=image,arguments=args)) for n,image,args in [
 ('empty','',[]),('one','/images/ccl.image',['ccl']),('spaces','/images/with spaces.image',['ccl','','a b','--load','ccl:boot.lisp']),
 ('unicode','/images/cafe\u0301-😀.image',['ccl','cafe\u0301','é','😀','中文']),('duplicates','image',['same','same','']),
 ('controls','line\nimage',['a\nb','a\tb','\\"']),('many','/ccl.image',[f'a{i}' for i in range(256)]),
 ('hangul','\u1100\u1161-가\u11a8.image',['D\U00010301','\u1100\u1161']),('astral-combiner','D\U00010301.image',[]),('composition','A\u030a\u0323.image',['A\u030a\u0323','Ạ̊',''])]]
def lispstr(s):return '"'+s.replace('\\','\\\\').replace('"','\\"')+'"'
def native(out):
 rows=cases();save(out/'host-cases.json',rows)
 (out/'native-cases.lisp').write_text('('+ '\n'.join('('+lispstr(r['name'])+' '+lispstr(r['input']['imageName'])+' ('+' '.join(map(lispstr,r['input']['arguments']))+'))' for r in rows)+')\n')
 shutil.copy(HERE/'native.lisp',out/'native.lisp');kernel=E/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=E/'2026-09-16-stage1-1a-r2/native/baseline.image'
 with tempfile.TemporaryDirectory(prefix='ccl-host-input-') as d:
  p=Path(d);shutil.copy(kernel,p/'dx86cl64');(p/'dx86cl64').chmod(0o755);shutil.copy(image,p/'dx86cl64.image')
  command([p/'dx86cl64','--no-init','--batch','--load',out/'native.lisp'],out/'native.log',cwd=ROOT,env={**os.environ,'HOST_CASES':str(out/'native-cases.lisp'),'HOST_ANSWERS':str(out/'native-answers.txt'),'HOST_FORMS':str(out/'native-forms.lisp'),'HOST_COMPOSITION':str(out/'native-composition.txt')})
 def parse(s):
  tokens=iter(re.findall(r'NIL|-?\d+|[()]',s))
  def item(t):
   if t=='NIL':return []
   if t!='(':return int(t)
   result=[]
   for t in tokens:
    if t==')':return result
    result.append(item(t))
   raise AssertionError('truncated native list')
  r=item(next(tokens));assert next(tokens,None) is None;return r
 answers=[]
 for i,line in enumerate((out/'native-answers.txt').read_text().splitlines()):
  index,name,image,args=line.split('|');assert int(index)==i and name==rows[i]['name'];answers.append(dict(name=name,image=parse(image),arguments=parse(args)))
 assert len(answers)==len(rows);save(out/'host-native.json',answers)
 pairs=[];witness=[]
 for line in (out/'native-composition.txt').read_text().splitlines():
  row=list(map(int,line.split()));assert len(row) in [3,4];witness.append(row)
  if len(row)==3:pairs.append(row)
 assert len(pairs)==len({tuple(r[:2]) for r in pairs})
 save(out/'composition-witness.json',witness)
 (out/'composition.mjs').write_text('// Derived from the pinned native precompose-simple-string pair domain.\nexport const pairs='+json.dumps(pairs,separators=(',',':'))+';\n')
def run(out):
 out.mkdir(parents=True,exist_ok=False);native(out)
 src=E/'2026-09-20-stage1-startup-joined-r1/execution'
 needed=set(read(src/'assets.json'))|{'assets.json'}
 for f in src.iterdir():
  if f.is_file() and (f.suffix in ['.mjs','.wasm','.html'] or f.name in needed):shutil.copy(f,out/f.name)
 shutil.copytree(src/'compiled',out/'compiled')
 # Freshly compile only the new functions, using the unchanged integrated compiler.
 spec=importlib.util.spec_from_file_location('host_compile',ROOT/'tests/wasm/stage1/startup-joined/compile.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
 compiled=c.compile_source(E,out/'build',(HERE/'compile.lisp').read_text(),None)
 backend=ROOT/'compiler/WASM32/wasm32-backend.lisp'
 assert sha(compiled/'proposal/files/compiler/WASM32/wasm32-backend.lisp')==sha(backend)==read(E/'2026-09-20-stage1-startup-config-r2/native-reuse.json')['compiler_sha256']
 (out/'new-compilation').mkdir()
 for n in ['modules.json','pools.json','materialized.json','compiler.dx64fsl','compile.log','command.json']:
  shutil.copy(compiled/n,out/'new-compilation'/n)
 save(out/'compiler-binding.json',dict(compiler_sha256=sha(backend),native_R6='REUSED_BY_EXACT_COMPILER_HASH',source_revision='c994217adc56b3f8a564526cee4695893ac84d86'))
 mods=read(out/'compiled/modules.json');mat=read(out/'compiled/materialized.json');new=read(compiled/'modules.json');newmat=read(compiled/'materialized.json');assert newmat['image']==''
 for row in new:
  for ext in ['wasm','wat']:shutil.copy(compiled/(row['name']+'.'+ext),out/'compiled'/(row['name']+'.'+ext))
 mods+=new;mat['roots']+=newmat['roots'];save(out/'compiled/modules.json',mods);save(out/'compiled/materialized.json',mat)
 selection=read(E/'2026-09-20-stage1-startup-config-r2/execution/config/selection.json')['callbacks'];selected=[r for r in selection if r.get('module') in {m['name'] for m in mods}]
 for ordinal,module in [(19,'host_image'),(20,'host_arguments')]:
  r=next(r for r in selection if r['group']=='system_pointers' and r['ordinal']==ordinal);selected.append(dict(r,module=module))
 selected.sort(key=lambda r:(r['group'],r['ordinal']));order=['preflight']+[r['module'] for r in selected]+['workload','host_readback'];assert len(order)==23
 save(out/'selected-host.json',dict(callbacks=selected,order=order,scope='20 of 35 registered callback snapshot entries, not definition/loading closure'))
 for f in (ROOT/'runtime/wasm32').glob('*.mjs'):
  if (out/f.name).exists():shutil.copy(f,out/f.name)
 shutil.copy(HERE/'owner-check.mjs',out/'owner-check.mjs');shutil.copy(HERE/'inputs.mjs',out/'inputs.mjs');(out/'check.mjs').write_text(check((src/'check.mjs').read_text(),order))
 shutil.copy(E/'2026-09-20-stage1-population-access-r1/execution/collector.wasm',out/'collector.wasm')
 assets=read(out/'assets.json')+['host-cases.json','host-native.json','composition-witness.json','collector.wasm']+['compiled/'+r['name']+'.wasm' for r in new];save(out/'assets.json',assets)
 command([NODE,out/'node.mjs',out,out/'execution.json'],out/'execution.log')
 tools=read(E/'2026-09-20-stage1-startup-config-r2/browser-tools.json')
 for n in ['node','browser','playwright']:assert sha(Path(tools[n]))==tools[n+'_sha256']
 command([tools['node'],out/'browser.mjs',out,tools['playwright'],tools['browser'],'execute'],out/'browser.log')
 from controls import controls
 faults=controls(out,NODE,Path('/usr/local/bin/wat2wasm'))
 rows=read(out/'execution.json')['rows'];assert {r['hostCase'] for w in rows for r in w['rows']}=={c['name'] for c in cases()}
 summary=dict(status='PASS',callbacks=20,modules=23,workers=4,scenarios=sum(len(r['rows']) for r in rows)*2,invocations=sum(r['invocations'] for r in rows)*2,collections=sum(len(r['rows']) for r in rows)*2,refusals=sum(len(r['refusals']) for r in rows)*2,owner_refusals=sum(r['admission']['refusals'] for r in rows)*2,composition_and_owner_comparisons=sum(r['admission']['comparisons'] for r in rows)*2,faults=len(faults),slot_credit=False);save(out/'summary.json',summary);print(summary)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();run(a.output.resolve())
