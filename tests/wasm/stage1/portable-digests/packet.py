import argparse,hashlib,json,shutil,subprocess,sys,tarfile
from pathlib import Path
from derive import ROOT,HERE,sha
from run import run,save
NAMES=['summary.json','sources.json','inputs.json','hashes.json','node.json','browser.json','binding-replay.json','controls.json','comparison.json']
def deterministic(out):
 return {n:sha(out/n) for n in NAMES}|{str(p.relative_to(out)):sha(p) for p in sorted((out/'proposal').iterdir())}
def comparison(out):
 rows={}
 for name,reference in [('eager.json','scalar/eager.json'),('cold.json','scalar/cold.json'),('binding-replay.json','binding/execution.json')]:
  actual=sha(out/name);assert actual==sha(out/reference);rows[name]=dict(sha256=actual,retained_reference=reference,equal=True)
 save(out/'comparison.json',rows)
def retain(out,pack):
 comparison(out);pack.mkdir(parents=True,exist_ok=False)
 for n in NAMES:shutil.copy(out/n,pack/n)
 shutil.copytree(out/'proposal',pack/'proposal')
 for n in ['tools.json','browser-environment.json']:shutil.copy(out/n,pack/n)
 for n in ['README.md','development.json']:shutil.copy(HERE/n,pack/n)
 save(pack/'deterministic.json',deterministic(out))
 sources=json.loads((out/'sources.json').read_text())
 for n,h in sources.items():assert sha(ROOT/n)==h,n
 with tarfile.open(pack/'sources.tar.gz','w:gz') as t:
  for n in sources:t.add(ROOT/n,arcname=n)
 with tarfile.open(pack/'execution-records.tar.gz','w:gz') as t:
  for p in sorted(out.rglob('*')):
   if p.is_file() and (p.parent==out and (p.suffix=='.log' or p.name.endswith('.command.json')) or 'mutants' in p.relative_to(out).parts):t.add(p,arcname=str(p.relative_to(out)))
 # Avoid duplicating the compiled corpora/archives. Their hashes and sources
 # above reproduce them; retain original failures and diagnostic artifacts.
 with tarfile.open(pack/'development.tar.gz','w:gz') as t:
  for name in ['r1','r2','r3','r4']:
   directory=Path('/tmp/ccl-portable-digests-'+name)
   if not directory.exists():continue
   for p in sorted(directory.iterdir()):
    if p.is_file() and (p.suffix=='.log' or p.name in ['checks-original.mjs','installer-original.mjs','binding-browser.mjs','worker.mjs','browser.mjs']):t.add(p,arcname=name+'/'+p.name)
   if name in ['r1','r2','r3'] and (directory/'proposal').exists():t.add(directory/'proposal',arcname=name+'/proposal')
  for p in sorted(Path('/tmp').glob('ccl-portable-r*.log')):t.add(p,arcname=p.name)
 save(pack/'packet.json',dict(id='STAGE1-PORTABLE-DIGESTS-R1',scope='Auxiliary runtime proposal; no compiler edits or slot credit. Chromium Worker construction and selected execution only.',files=[dict(path=str(p.relative_to(pack)),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(pack.rglob('*')) if p.is_file()]))
def verify(e,pack,out,playwright,browser):
 for r in json.loads((pack/'packet.json').read_text())['files']:assert sha(pack/r['path'])==r['sha256'],r['path']
 for n,h in json.loads((pack/'sources.json').read_text()).items():assert sha(ROOT/n)==h,n
 for n,h in json.loads((pack/'inputs.json').read_text()).items():assert sha(e/n)==h,n
 tools=json.loads((pack/'tools.json').read_text())
 for p,key in [(Path(shutil.which('node')),'node'),(Path(tools['clang']),'clang'),(browser,'browser'),(playwright,'playwright')]:assert sha(p)==tools[key+'_sha256'],key
 run(e,out,playwright,browser);comparison(out)
 expected=json.loads((pack/'deterministic.json').read_text());actual=deterministic(out);assert actual==expected,{k:(v,actual.get(k)) for k,v in expected.items() if actual.get(k)!=v}
 save(out/'verification.json',dict(status='PASS',deterministic_files=len(actual),packet_sha256=sha(pack/'packet.json')))
 print('PASS: retained portable digest proposal reproduced')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--playwright',type=Path);p.add_argument('--browser',type=Path);a=p.parse_args()
 if a.mode=='retain':retain(a.output.resolve(),a.packet.resolve())
 else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve(),a.playwright.resolve(),a.browser.resolve())
