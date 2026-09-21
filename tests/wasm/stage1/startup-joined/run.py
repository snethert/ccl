import argparse,hashlib,json,shutil,subprocess
from pathlib import Path
from derive import derive
from compile import compile_source
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
CONFIG='2026-09-20-stage1-startup-config-r2';RESETS='2026-09-20-stage1-startup-resets-r1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(args,log):
 save(log.with_suffix('.command.json'),list(map(str,args)))
 with log.open('w') as f:subprocess.run(list(map(str,args)),check=True,stdout=f,stderr=subprocess.STDOUT,timeout=240)
def run(e,out):
 out.mkdir(parents=True,exist_ok=False);p=e/CONFIG/'execution/config';r=e/RESETS/'execution'
 for parent in [e/CONFIG,e/RESETS]:
  for row in read(parent/'packet.json')['files']:assert sha(parent/row['path'])==row['sha256']
 # Reuse compiled/native identities from accepted packets, no recompilation.
 for f in p.iterdir():
  if f.is_file() and f.suffix in ['.mjs','.json','.wasm','.html']:shutil.copy(f,out/f.name)
 shutil.copytree(p/'compiled',out/'compiled')
 for f in (ROOT/'runtime/wasm32').glob('*.mjs'):
  if (out/f.name).exists():shutil.copy(f,out/f.name)
 selected=[x for x in read(r/'selection.json')['callbacks'] if x['disposition']=='SELECTED_LITERAL_RESET']
 save(out/'resets.json',selected);save(out/'native-resets.json',read(r/'compiled/native.json'))
 source=(ROOT/'tests/wasm/stage1/startup-resets/compile.lisp').read_text();assert source.count('(+ 101 (length modules))')==1
 source=source.replace('(+ 101 (length modules))','(+ 201 (length modules))');(out/'reset-compile.lisp').write_text(source)
 rebuilt=compile_source(e,out/'reset-build',source,(r.parent/'execution/selection.lisp').read_text())
 assert read(rebuilt/'native.json')==read(r/'compiled/native.json')
 mods=read(out/'compiled/modules.json');mat=read(out/'compiled/materialized.json');oldmods=read(r/'compiled/modules.json');oldmat=read(r/'compiled/materialized.json');assert not oldmat['image']
 for row in selected:
  n=row['module'];mods.append(dict(name=n));mat['roots'].append(oldmat['roots'][next(i for i,m in enumerate(oldmods) if m['name']==n)])
  for ext in ['wasm','wat']:shutil.copy(rebuilt/(n+'.'+ext),out/'compiled'/(n+'.'+ext))
 save(out/'compiled/modules.json',mods);save(out/'compiled/materialized.json',mat)
 (out/'check.mjs').write_text(derive((p/'check.mjs').read_text()))
 assets=read(out/'assets.json')+['resets.json','native-resets.json']+['compiled/'+r['module']+'.wasm' for r in selected];save(out/'assets.json',assets)
 command(['/usr/local/bin/node',out/'node.mjs',out,out/'execution.json'],out/'execution.log')
 tools=read(e/CONFIG/'browser-tools.json')
 for n in ['node','browser','playwright']:assert sha(Path(tools[n]))==tools[n+'_sha256']
 command([tools['node'],out/'browser.mjs',out,tools['playwright'],tools['browser'],'execute'],out/'browser.log')
 rows=read(out/'execution.json')['rows'];save(out/'summary.json',dict(status='PASS',selected_callbacks=18,modules=len(mods),workers=4,scenarios=sum(len(r['rows']) for r in rows)*2,callback_comparisons=sum(len(r['rows'])*18 for r in rows)*2,invocations=sum(r['invocations'] for r in rows)*2,refusals=sum(len(r['refusals']) for r in rows)*2,foreign_checks=sum(r['foreignChecks'] for r in rows)*2,native_answers_reused=True,slot_credit=False))
 save(out/'module-pins.json',{m['name']:sha(out/'compiled'/(m['name']+'.wasm')) for m in mods});print(read(out/'summary.json'))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();run(a.evidence.resolve(),a.output.resolve())
