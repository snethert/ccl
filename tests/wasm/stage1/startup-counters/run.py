import argparse,importlib.util,re,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('db_parent',HERE.parent/'startup-db/run.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
sha,read,save,command=old.sha,old.read,old.save,old.command
PARENT='2026-09-20-stage1-startup-db-r1';CONFIG=old.CONFIG
SOURCES=('counters.c','owner.mjs','compile.lisp','check.mjs','run.py','packet.py','README.md','scope.json')
def pins(e):
 old.pins(e) # Reassert the accepted native kernel/image and toolchain.
 p=read(e/PARENT/'source-pins.json')
 for n,h in p.items():assert sha(ROOT/n)==h,n
 for f in [*(HERE/n for n in SOURCES),ROOT/'level-1/l1-init.lisp',ROOT/'runtime/wasm32/sha256.mjs',ROOT/'runtime/wasm32/bytes.mjs']:p[str(f.relative_to(ROOT))]=sha(f)
 return dict(sorted(p.items()))
def controls(out):
 code=(out/'counters.c').read_text();rows=[]
 for name,a,b,diagnostic in [
  ('last-byte','i<bytes;','i+1<bytes;','counter exact zeroing and preservation'),
  ('published-count','S(result+8,1);','S(result+8,2);','counter publication'),
  ('address-check','||L(base+4)!=base+16','','counter refusal address'),
  ('alignment-check','(base&7)||','','counter refusal owner alignment'),
  ('kind-check','||(kind!=0&&kind!=4)','','counter refusal kind'),
 ]:
  assert code.count(a)==1;d=out/'faults'/name;d.mkdir(parents=True)
  for n in ['owner.mjs','sha256.mjs','bytes.mjs','adapter.wasm']:shutil.copy(out/n,d/n)
  shutil.copytree(out/'compiled',d/'compiled');(d/'counters.c').write_text(code.replace(a,b))
  command([old.CLANG,*old.FLAGS,'-Wl,--export=counter_run',d/'counters.c','-o',d/'counters.wasm'],d/'build.log');save(d/'service.json',dict(sha256=sha(d/'counters.wasm')))
  command([old.NODE,out/'check.mjs',d,d/'execution.json'],d/'rejected.log',diagnostic);rows.append(dict(name=name,status='REJECTED',diagnostic=diagnostic,binary=sha(d/'counters.wasm')))
 d=out/'faults'/'reuse-reservation';d.mkdir()
 for n in ['counters.wasm','service.json','sha256.mjs','bytes.mjs','adapter.wasm']:shutil.copy(out/n,d/n)
 shutil.copytree(out/'compiled',d/'compiled');owner=(out/'owner.mjs').read_text();assert owner.count('cursor=next;')==1;(d/'owner.mjs').write_text(owner.replace('cursor=next;','cursor=p;'))
 command([old.NODE,out/'check.mjs',d,d/'execution.json'],d/'rejected.log','fresh reservations');rows.append(dict(name='reuse-reservation',status='REJECTED',diagnostic='fresh reservations'))
 save(out/'controls.json',rows)
def run(e,out):
 source=pins(e);out.mkdir()
 arch=(ROOT/'compiler/X86/X8632/x8632-arch.lisp').read_text();assert '(define-imm-subtag macptr 3)' in arch and '(defconstant fulltag-immheader 7)' in arch and '(defconstant ntagbits 3)' in arch
 assert re.search(r'\(define-fixedsized-object macptr\s+address\s+domain\s+type\s*\)',arch)
 save(out/'layout.json',dict(subtag=(3<<3)|7,header=799,object_bytes=16,raw_words=['address','domain','type'],timeval_bytes=16,timevals=5,freed_bytes=8))
 reuse=read(e/CONFIG/'native-reuse.json');assert reuse['compiler_sha256']==sha(ROOT/'compiler/WASM32/wasm32-backend.lisp');save(out/'native-reuse.json',reuse)
 c=old.compile_source(e,out/'compile',(HERE/'compile.lisp').read_text(),None);shutil.copytree(c,out/'compiled',ignore=shutil.ignore_patterns('source','proposal'))
 for n in ['counters.c','owner.mjs','check.mjs']:shutil.copy(HERE/n,out/n)
 for n in ['sha256.mjs','bytes.mjs']:shutil.copy(ROOT/'runtime/wasm32'/n,out/n)
 command([old.CLANG,*old.FLAGS,'-Wl,--export=counter_run',out/'counters.c','-o',out/'counters.wasm'],out/'build.log');save(out/'service.json',dict(sha256=sha(out/'counters.wasm')))
 command([old.WABT,'--enable-threads','--enable-exceptions',ROOT/'runtime/wasm32/hash-adapter.wat','-o',out/'adapter.wasm'],out/'adapter.log')
 command([old.NODE,out/'check.mjs',out,out/'execution.json'],out/'execution.log')
 controls(out);assert pins(e)==source;save(out/'summary.json',dict(read(out/'execution.json')['summary'],source_pins=len(source),faults=len(read(out/'controls.json')),compiler_unchanged=True));print(read(out/'summary.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
