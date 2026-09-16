#!/usr/bin/env python3
"""Replay native qualification and recompile every B call-core compiler mutant."""
import argparse,re,shutil,sys,tarfile,tempfile
from pathlib import Path
from support import HERE,ROOT,REG,compile_cases,read,sha,require
from mutants import mutations
import importlib.util
spec=importlib.util.spec_from_file_location("b_call_run",HERE/"run.py");runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner);execute=runner.execute
sys.path.insert(0,str(REG));from qualify import qualify

def safe(root,name):
 p=Path(name);require(not p.is_absolute() and '..' not in p.parts,'SAFE_PATH');out=(root/p).resolve();require(out.is_relative_to(root.resolve()),'CONTAINED_PATH');return out

def hydrate(packet,evidence,dest):
 shutil.copytree(packet,dest)
 for ref in read(packet/'references.json'):
  source=safe(evidence,ref['evidence_path']);target=safe(dest,ref['path']);require(sha(source)==ref['sha256'] and not target.exists(),'REFERENCE '+ref['path']);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(source,target)
 with tarfile.open(packet/'mutants.tar.gz') as t:t.extractall(dest/'mutants',filter='data')

def first_failure(log):
 match=re.search(r'AssertionError[^\n]*: (.+)',log);require(match is not None,'SEMANTIC_FAILURE');return match[1]

def verify(packet,evidence):
 require((HERE/'wasm32-backend.lisp').read_text().split(';;; First B call unit:')[0]==(HERE.parent/'b-callables/wasm32-backend.lisp').read_text().split(';;; First B call unit:')[0],'REVIEWED_NON_B_ENTRIES_UNCHANGED')
 for name,h in read(packet/'source-pins.json').items():require(sha(ROOT/name)==h and sha(packet/'source'/name)==h,'SOURCE_PIN '+name)
 for row in read(packet/'packet.json')['files']:require(sha(safe(packet,row['path']))==row['sha256'],'PACKET_BYTES '+row['path'])
 with tempfile.TemporaryDirectory(prefix='ccl-b-call-verify-') as tmp:
  temp=Path(tmp).resolve();retained=temp/'retained';hydrate(packet,evidence,retained)
  qualifier=temp/'qualification';qualify(retained/'native',evidence/'macos-u1-inputs',evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64',qualifier)
  require(read(qualifier/'summary.json')==read(retained/'qualification/summary.json'),'NATIVE_QUALIFICATION')
  require(read(qualifier/'verification.json')==read(retained/'qualification/verification.json'),'NATIVE_CONTROLS')
  proposed=mutations((HERE/'wasm32-backend.lisp').read_text());require(set(proposed)=={x['name'] for x in read(retained/'controls.json')},'CONTROL_POPULATION')
  for name,backend in [('positive',None)]+list(proposed.items()):
   original=retained/'positive' if name=='positive' else retained/'mutants'/name
   if backend is not None:
    require(backend==(retained/'mutants'/(name+'.lisp')).read_text(),'MUTANT_SOURCE '+name)
    path=temp/(name+'.lisp');path.write_text(backend)
   else:path=None
   fresh=temp/name;compile_cases(evidence,fresh,path)
   for p in original.iterdir():
    if p.suffix in ('.wat','.wasm') or p.name in ('native.json','cases.json','refusals.json','modules.json','compiler.dx64fsl','layout.json','entries.json'):
     require(p.read_bytes()==(fresh/p.name).read_bytes(),'RECOMPILED_BYTES '+name+'/'+p.name)
   for p in (original/'installed').glob('*.wasm'):require(p.read_bytes()==(fresh/'installed'/p.name).read_bytes(),'INSTALLED_BYTES')
   code,_=execute(fresh,temp/(name+'.log'),temp/(name+'.json'))
   if name=='positive':require(code==0 and read(temp/(name+'.json'))==read(retained/'execution.json'),'TARGET_REPLAY')
   else:require(code!=0 and first_failure((temp/(name+'.log')).read_text())==first_failure((retained/'mutants'/(name+'.log')).read_text()),'CONTROL_REPLAY '+name)
 print('S1-B-CLOSURES-VERIFIED: native R6/R6a, escaping closures, shared mutable captures and refusals')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();verify(a.packet.resolve(),a.evidence.resolve())
