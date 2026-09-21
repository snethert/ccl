import argparse,importlib.util,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('db_parent',HERE.parent/'startup-db/run.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
sha,read,save,command=old.sha,old.read,old.save,old.command
PARENT='2026-09-20-stage1-startup-db-r1'
SOURCES=('run.py','packet.py','directed.mjs','README.md','scope.json')
def pins(e):
 p=read(e/PARENT/'source-pins.json')
 for n,h in p.items():assert sha(ROOT/n)==h,n
 for n in SOURCES:p[str((HERE/n).relative_to(ROOT))]=sha(HERE/n)
 return dict(sorted(p.items()))
def copy(src,d):
 d.mkdir(parents=True);shutil.copytree(src/'compiled',d/'compiled');shutil.copy(src/'adapter.wasm',d/'adapter.wasm')
def run(e,out):
 source=pins(e);p=e/PARENT
 for r in read(p/'packet.json')['files']:assert sha(p/r['path'])==r['sha256'],r['path']
 for n,h in read(p/'tools.json').items():assert sha(Path(n))==h,n
 out.mkdir();src=p/'execution';previous=(src/'check.mjs').read_text();anchor=' parentPort.postMessage({base,rows,refusals});'
 assert previous.count(anchor)==1
 fixed=previous.replace(anchor,(HERE/'directed.mjs').read_text()+anchor)
 target=out/'positive';copy(src,target);(target/'check.mjs').write_text(fixed);shutil.copy(src/'db.wasm',target/'db.wasm')
 command([old.NODE,target/'check.mjs',target,target/'execution.json'],target/'execution.log')
 assert (target/'execution.json').read_bytes()==(src/'execution.json').read_bytes()
 code=(src/'db.c').read_text();controls=[]
 for name,a,b,diagnostic in [
  ('no-membership','||!member(current,base,count)','','isolated admission foreign-directory'),
  ('no-count','seen!=count||','','isolated admission omitted-directory'),
  ('same-descriptor','||header_type==dir_type','','isolated admission shared-descriptor'),
 ]:
  assert code.count(a)==1;d=out/'faults'/name;copy(src,d);(d/'db.c').write_text(code.replace(a,b));(d/'previous.mjs').write_text(previous);(d/'fixed.mjs').write_text(fixed)
  command([old.CLANG,*old.FLAGS,'-Wl,--export=db_run',d/'db.c','-o',d/'db.wasm'],d/'build.log')
  command([old.NODE,d/'previous.mjs',d,d/'previous.json'],d/'previous.log');assert (d/'previous.json').read_bytes()==(src/'execution.json').read_bytes()
  command([old.NODE,d/'fixed.mjs',d,d/'execution.json'],d/'rejected.log',diagnostic)
  controls.append(dict(name=name,previous='ESCAPED',corrected='REJECTED',diagnostic=diagnostic,binary=sha(d/'db.wasm')))
 inherited=[]
 for row in read(src/'controls.json'):
  d=out/'inherited'/row['name'];copy(src,d);shutil.copy(src/'faults'/row['name']/'db.wasm',d/'db.wasm');(d/'check.mjs').write_text(fixed)
  command([old.NODE,d/'check.mjs',d,d/'execution.json'],d/'rejected.log',row['diagnostic']);inherited.append(row)
 save(out/'controls.json',dict(new=controls,inherited=inherited));assert pins(e)==source
 save(out/'summary.json',dict(status='PASS',source_pins=len(source),directed_refusals=6,new_faults=3,previous_escapes=3,inherited_faults=len(inherited),positive_identical=True,compiler_service_adapter_unchanged=True,slot_credit=False))
 print(read(out/'summary.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
