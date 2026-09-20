#!/usr/bin/env python3
import argparse,hashlib,json,shutil,subprocess,tempfile
from pathlib import Path
from corpus import trace,native_source
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
CLANG=Path('/usr/local/opt/llvm/bin/clang');NODE=Path('/usr/local/bin/node')
FLAGS=['--target=wasm32','-O2','-nostdlib','-matomics','-mbulk-memory','-fno-builtin','-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184','-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=__stack_pointer']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def read(p):return json.loads(p.read_text())
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=300)
def build(source,out):command([CLANG,*FLAGS,*['-Wl,--export='+x for x in ['symbols_admit','symbols_run','symbol_hash']],source,'-o',out],out.with_suffix('.build.log'))
def run(e,out):
 out.mkdir(parents=True,exist_ok=False)
 for n in ['symbols.c','image.mjs','check.mjs','generated.mjs']:shutil.copy(HERE/n,out/n)
 build(out/'symbols.c',out/'symbols.wasm')
 rows=trace();save(out/'trace.json',rows);(out/'native.lisp').write_text(native_source(rows))
 kernel=e/'2026-09-12-native-census-r7/baseline/build/dx86cl64';image=e/'2026-09-16-stage1-1a-r2/native/baseline.image'
 save(out/'inputs.json',{str(p.relative_to(e)):sha(p) for p in [kernel,image]})
 with tempfile.TemporaryDirectory(prefix='ccl-symbol-native-') as tmp:
  w=Path(tmp);shutil.copy(kernel,w/'dx86cl64');(w/'dx86cl64').chmod(0o755);shutil.copy(image,w/'dx86cl64.image')
  command([w/'dx86cl64','--no-init','--batch','--load',out/'native.lisp'],out/'native.log')
 log=(out/'native.log').read_text();answers=[list(map(int,l.split()[1:])) for l in log.splitlines() if l.startswith('SYMBOL-ROW ')];assert len(answers)==len(rows),(len(answers),len(rows));save(out/'native.json',answers)
 names=list(dict.fromkeys(r[1] for r in rows if r[2]=='KEYWORD'));initial=[int(l.split()[1]) for l in log.splitlines() if l.startswith('INITIAL-KW ')];assert len(initial)==len(names);save(out/'initial-keywords.json',[n for n,b in zip(names,initial) if b])
 save(out/'bindings.json',[list(map(int,l.split()[1:])) for l in log.splitlines() if l.startswith('BIND-ROW ')][0])
 import generated;generated.run(e,out,command)
 command([NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 controls=[]
 faults=[
 ('unqualified-package','symbols.c','U error=lookup(c,b,a,&w,&v);','b=L(L(c+16)+6);U error=lookup(c,b,a,&w,&v);','distinct package symbol identities'),
 ('nil-symbol-pointer','symbols.c','return raw==NILSYM+6?NIL:raw;','return raw;','legacy hash rebuild'),
 ('inherited-external','symbols.c','tables[2]=L(L(used+3)+2);','tables[2]=0;','native trace'),
 ('keyword-self','symbols.c','S(p+8,op==1&&b==L(c+36)?sym:UNBOUND);','S(p+8,UNBOUND);','restored image admission'),
 ('prelookup-hash','symbols.c','if(L(c+24)!=1||L(c+20)!=1)return HASH;','if(0)return HASH;','pre-admission lookup refused'),
 ('rebuild-copy','symbols.c','S(bucket(vecs[i],j),L(sc+offsets[i]+4*j));','S(bucket(vecs[i],j),L(bucket(vecs[i],j)));','target hash admission'),
 ('exact-name','symbols.c','if(L(a-2+4*i)!=L(b-2+4*i))return 0;','if(0)return 0;','native trace'),
 ('combined-allocation','symbols.c','if((W)base+bytes>end)return SPACE;','if((W)base>end)return SPACE;','allocation exhaustion'),
 ('loaded-value-tag','image.mjs','[1,6].includes(v&7)&&v>=s.base','v>=s.base','tag-looking fixnum value preserved'),
 ('adapter-status','adapter.wat','(i32.load offset=4 (global.get $result))','(i32.const 77825)','native trace'),
 ('adapter-descriptor','adapter.wat','(local.set $dst (i32.load offset=8 (local.get $d)))','(local.set $dst (i32.add (i32.load offset=8 (local.get $d)) (i32.const 4)))','native trace'),
 ('adapter-count','adapter.wat','(local.get $v) (local.get $n)))','(local.get $v) (i32.const 1)))','generated result count'),
 ]
 for name,file,old,new,diagnostic in faults:
  m=out/'mutants'/name;m.mkdir(parents=True)
  for n in ['symbols.wasm','adapter.wasm','check.mjs','image.mjs','generated.mjs','trace.json','native.json','bindings.json','initial-keywords.json']:shutil.copy(out/n,m/n)
  (m/'compiled').mkdir()
  for f in (out/'compiled').iterdir():
   if f.suffix=='.wasm' or f.name in ['modules.json','materialized.json']:shutil.copy(f,m/'compiled'/f.name)
  text=(HERE/file).read_text();assert text.count(old)==1,(name,text.count(old));(m/file).write_text(text.replace(old,new))
  if file.endswith('.c'):build(m/file,m/'symbols.wasm')
  if file.endswith('.wat'):command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions',m/file,'-o',m/'adapter.wasm'],m/'adapter-build.log')
  try:command([NODE,m/'check.mjs',m,m/'execution.json'],m/'execution.log')
  except subprocess.CalledProcessError:
   text=(m/'execution.log').read_text();assert diagnostic in text,(name,text[-2500:]);controls.append(dict(name=name,status='REJECTED',diagnostic=diagnostic))
  else:raise AssertionError('fault escaped '+name)
 save(out/'controls.json',controls)
 import assess
 save(out/'assessment.json',assess.check(out));save(out/'publication-controls.json',assess.controls(out))
 execution=read(out/'execution.json');save(out/'summary.json',dict(status='PASS',trace_rows=len(rows),modules=len(read(out/'compiled/modules.json')),native_comparisons=sum(r['nativeComparisons'] for r in execution['rows']),generated_comparisons=sum(r['nativeComparisons']+r['bindingComparisons'] for r in execution['rows'] if r['generated']),binding_comparisons=sum(r['bindingComparisons'] for r in execution['rows']),placements=3,loads=sum(len(r['loads']) for r in execution['rows']),refusals=sum(len(r['refusals']) for r in execution['rows']),faults=len(controls)))
 print(json.dumps(read(out/'summary.json'),indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--evidence',type=Path,required=True);a.add_argument('--output',type=Path,required=True);v=a.parse_args();run(v.evidence.resolve(),v.output.resolve())
