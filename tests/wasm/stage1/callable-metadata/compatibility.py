"""Run the reviewed moving loop corpora with the metadata flag off; compare binaries."""
import sys,tarfile,hashlib
from pathlib import Path
from backend import generate
import importlib.util,json
HERE=Path(__file__).resolve().parent
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
PARENT='2026-09-19-stage1-closure-transfers-r1'
def run(e,out):
 driver=load('metadata_compatibility_driver',HERE.parent/'closure-transfers/run.py')
 driver.generate=generate
 driver.run(e,out)
 expected={}
 with tarfile.open(e/PARENT/'execution.tar.gz') as t:
  for m in t.getmembers():
   if m.name.startswith(('generated/compiled/','inherited/compiled/')) and m.name.endswith(('.wat','.wasm')):expected[m.name]=hashlib.sha256(t.extractfile(m).read()).hexdigest()
 assert expected
 actual={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for root in ['generated/compiled','inherited/compiled'] for p in (out/root).rglob('*') if p.suffix in ['.wat','.wasm']}
 assert actual==expected,'default-mode byte identity'
 result=dict(status='PASS',files=len(actual),corpora=['closed-GO/branches','temporaries'],comparisons=driver.json.loads((out/'summary.json').read_text()))
 save(out/'default-compatibility.json',result);return result
