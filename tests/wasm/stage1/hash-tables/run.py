#!/usr/bin/env python3
import argparse,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
from collector import generate,replace,ROOT
from corpus import trace,native_source
HERE=Path(__file__).resolve().parent
CLANG=Path('/usr/local/opt/llvm/bin/clang');NODE=Path('/usr/local/bin/node')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=__stack_pointer']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def read(p):return json.loads(p.read_text())
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
def build(source,out,collector=False):
 exports=['collect'] if collector else ['ht_size','ht_init','ht_run']
 command([CLANG,*FLAGS,*['-Wl,--export='+x for x in exports],source,'-o',out],out.with_suffix('.build.log'))
def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 shutil.copy(HERE/'hash.c',out/'hash.c');(out/'collector.c').write_text(generate());shutil.copy(HERE/'check.mjs',out/'check.mjs')
 build(out/'hash.c',out/'hash.wasm');build(out/'collector.c',out/'collector.wasm',True)
 rows=trace();save(out/'trace.json',rows);(out/'native.lisp').write_text(native_source(rows))
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 save(out/'inputs.json',{str(p.relative_to(e)):sha(p) for p in [kernel,image]})
 with tempfile.TemporaryDirectory(prefix='ccl-hash-native-') as tmp:
  work=Path(tmp);shutil.copy(kernel,work/'dx86cl64');(work/'dx86cl64').chmod(0o755);shutil.copy(image,work/'dx86cl64.image')
  command([work/'dx86cl64','--no-init','--batch','--load',out/'native.lisp'],out/'native.log')
 answers=[list(map(int,line.split()[1:])) for line in (out/'native.log').read_text().splitlines() if line.startswith('HASH-ROW ')]
 assert len(answers)==len(rows),(len(answers),len(rows));save(out/'native.json',answers)
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 # Reuse the independent accepted core oracle against the extended scanner.
 checks=(ROOT/'tests/wasm/stage1/collector-core/check.mjs').read_text()
 checks=replace(checks,'// Deterministic graph independent of collector enumeration',(ROOT/'tests/wasm/stage1/collector-live/check-extra.mjs').read_text()+'\n// Deterministic graph independent of collector enumeration')
 (out/'core-check.mjs').write_text(checks);command([NODE,out/'core-check.mjs',out/'collector.wasm',out/'core-checks.json'],out/'core.log')
 import generated
 generated.run(e,out,command)
 shutil.copy(HERE/'generated.mjs',out/'generated.mjs')
 command([NODE,out/'check.mjs',out,out/'generated.json','generated'],out/'generated.log')
 faults=[
  ('moved-key-notification','collector','|(1u<<29));','|0u);','moved-key notification'),
  ('value-parity','collector','index>=14&&!(index&1)','index>=14&&(index&1)','moved-key notification'),
  ('rehash-notification','hash','if(L(b+8)&MOVED){','if(0){','native trace'),
  ('cache-on-rehash','hash',' invalidate(b);\n __builtin_memcpy',' /* omitted */\n __builtin_memcpy','native trace'),
  ('cached-value-replacement','hash','S(b+48,v);','S(b+48,NIL);','native trace'),
  ('cache-on-deletion','hash','S(b+36,L(b+36)-4);invalidate(b);','S(b+36,L(b+36)-4);','native trace'),
  ('duplicate-count','hash','if(!found){if(L(p)==DELETED)','if(1){if(L(p)==DELETED)','native trace'),
  ('cached-key-scanner','collector','U old=LOAD(p+4*index),v=forward(s,old);','U old=LOAD(p+4*index),v=((LOAD(o->moved)&255)==74&&index==10)?old:forward(s,old);','cached key relocated'),
  ('cached-value-scanner','collector','U old=LOAD(p+4*index),v=forward(s,old);','U old=LOAD(p+4*index),v=((LOAD(o->moved)&255)==74&&index==11)?old:forward(s,old);','cached value relocated'),
 ]
 controls=[]
 for name,kind,old,new,diagnostic in faults:
  m=out/'mutants'/name;m.mkdir(parents=True)
  for n in ['trace.json','native.json','hash.wasm','collector.wasm']:shutil.copy(out/n,m/n)
  source=m/(kind+'.c');source.write_text(replace((out/(kind+'.c')).read_text(),old,new));build(source,m/(kind+'.wasm'),kind=='collector')
  try:command([NODE,out/'check.mjs',m,m/'execution.json'],m/'execution.log')
  except subprocess.CalledProcessError:
   log=(m/'execution.log').read_text();assert diagnostic in log,(name,log[-2500:]);controls.append(dict(name=name,status='REJECTED',diagnostic=diagnostic))
  else:raise AssertionError('mutant escaped: '+name)
 # Adapter faults run the same generated program against unchanged primitives.
 for name,old,new,diagnostic in [
  ('adapter-presence','(i32.load offset=4 (global.get $result))','(i32.const 77825)','native trace'),
  ('adapter-dynamic-displacement','(local.set $dst (i32.load offset=8 (local.get $d)))','(local.set $dst (i32.add (i32.load offset=8 (local.get $d)) (i32.const 4)))','native trace'),
  ('adapter-value-count','(local.get $v) (local.get $n)))','(local.get $v) (i32.const 1)))','generated result count'),
 ]:
  m=out/'mutants'/name;m.mkdir()
  for n in ['trace.json','native.json','hash.wasm','collector.wasm','generated.mjs']:shutil.copy(out/n,m/n)
  shutil.copytree(out/'compiled',m/'compiled')
  source=m/'adapter.wat';source.write_text(replace((HERE/'adapter.wat').read_text(),old,new))
  command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions',source,'-o',m/'adapter.wasm'],m/'adapter-build.log')
  try:command([NODE,out/'check.mjs',m,m/'execution.json','generated'],m/'execution.log')
  except subprocess.CalledProcessError:
   log=(m/'execution.log').read_text();assert diagnostic in log,(name,log[-2500:]);controls.append(dict(name=name,status='REJECTED',diagnostic=diagnostic))
  else:raise AssertionError('adapter mutant escaped: '+name)
 save(out/'controls.json',controls)
 save(out/'toolchain.json',{'tools':[dict(path=str(p),sha256=sha(p)) for p in [CLANG,NODE,Path('/usr/local/bin/wat2wasm')]]})
 execution=read(out/'execution.json');generated=read(out/'generated.json')
 summary=dict(status='PASS',scope='S1-LL18-b strong EQ moved-key protocol through generated B callers and owner-installed runtime leaves',native_cases=len(rows),core_comparisons=sum(r['nativeComparisons'] for r in execution['rows']),generated_comparisons=sum(r['nativeComparisons']+2 for r in generated['rows']),generated_modules=9,generated_calls=sum(r['generated']['calls']+2 for r in generated['rows']),collections=sum(len(r['moves']) for r in execution['rows']+generated['rows'])+4,scenario_checks=sum(len(r['checks']) for r in execution['rows']+generated['rows']),refusals=sum(len(r['refusals']) for r in execution['rows']+generated['rows']),core_checks=len(read(out/'core-checks.json')['tests']),mutants=len(controls))
 import assess
 save(out/'assessment.json',assess.check(out));save(out/'publication-controls.json',assess.controls(out))
 save(out/'summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
