import argparse,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
from selection import ROOT,selection,native_source
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log,why=None):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:r=subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,timeout=240)
 if why:assert r.returncode and why in log.read_text(),(log,why)
 else:assert r.returncode==0,log

def run(e,out):
 out.mkdir(parents=True);sites=selection();save(out/'selection.json',sites)
 for n in ['policy.mjs','check.mjs']:shutil.copy(HERE/n,out/n)
 for n in ['hash.c','collector.c']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 clang='/usr/local/opt/llvm/bin/clang';node='/usr/local/bin/node'
 flags=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=__stack_pointer']
 for stem,names in [('hash',['ht_size','ht_init','ht_run']),('collector',['collect'])]:command([clang,*flags,*['-Wl,--export='+n for n in names],out/(stem+'.c'),'-o',out/(stem+'.wasm')],out/(stem+'-build.log'))
 source=native_source(sites);(out/'native.lisp').write_text(source)
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 save(out/'inputs.json',{str(p.relative_to(e)):sha(p) for p in [kernel,image]})
 with tempfile.TemporaryDirectory(prefix='ccl-strong-tables-') as tmp:
  work=Path(tmp);shutil.copy(kernel,work/'dx86cl64');(work/'dx86cl64').chmod(0o755);shutil.copy(image,work/'dx86cl64.image')
  command([work/'dx86cl64','--no-init','--batch','--load',out/'native.lisp'],out/'native.log')
  answers=[s for s in (out/'native.log').read_text().splitlines() if s.startswith('STRONG-ROW ')];assert len(answers)==21;save(out/'native.json',answers)
  # The unadapted constructors must fail the explicit non-weak claim.
  original=source
  for s in sites:original=original.replace('(new '+s['strong']+')','(new '+s['form']+')')
  (out/'native-weak-control.lisp').write_text(original)
  command([work/'dx86cl64','--no-init','--batch','--load',out/'native-weak-control.lisp'],out/'native-weak-control.log','(NULL (HASH-TABLE-WEAK-P NEW))')
 command([node,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 controls=[]
 for name,a,b,why in [
  ('consent',"policy!==STRONG_POLICY","false",'consent'),
  ('equality',"plan.test!=='eq'","false",'non-EQ admission'),
  ('weak-metadata','weak:null','weak:site.weak','strong plan'),
  ('size','capacity<plan.size','false','size refusal'),
  ('extent','end!==base+bytes','false','extent refusal')]:
  d=out/'faults'/name;d.mkdir(parents=True)
  for n in ['check.mjs','selection.json','hash.wasm','collector.wasm']:shutil.copy(out/n,d/n)
  s=(out/'policy.mjs').read_text();assert s.count(a)==1;(d/'policy.mjs').write_text(s.replace(a,b));command([node,d/'check.mjs',d,d/'execution.json'],d/'rejected.log',why);controls.append({'name':name,'status':'REJECTED','diagnostic':why})
 save(out/'controls.json',controls);save(out/'tools.json',{str(Path(p)):sha(Path(p)) for p in [clang,node]})
 result=json.loads((out/'execution.json').read_text());save(out/'summary.json',dict(result,native_constructor_rows=21,controls=6,shared_sources_changed=False,slot_credit=False));print({k:v for k,v in result.items() if k!='rows'})
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);a=a.parse_args();run(a.evidence.resolve(),a.output.resolve())
