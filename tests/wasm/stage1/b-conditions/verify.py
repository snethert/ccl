#!/usr/bin/env python3
"""Replay native qualification and recompile every B call-core compiler mutant."""
import argparse,shutil,sys,tarfile,tempfile
from pathlib import Path
from support import HERE,ROOT,REG,read,sha,require
from mutants import mutations
sys.path.insert(0,str(REG));from qualify import qualify

def safe(root,name):
 p=Path(name);require(not p.is_absolute() and '..' not in p.parts,'SAFE_PATH');out=(root/p).resolve();require(out.is_relative_to(root.resolve()),'CONTAINED_PATH');return out

def hydrate(packet,evidence,dest):
 shutil.copytree(packet,dest)
 for ref in read(packet/'references.json'):
  source=safe(evidence,ref['evidence_path']);target=safe(dest,ref['path']);require(sha(source)==ref['sha256'] and not target.exists(),'REFERENCE '+ref['path']);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(source,target)
 with tarfile.open(packet/'mutants.tar.gz') as t:t.extractall(dest/'mutants',filter='data')
 with tarfile.open(packet/'condition-controls.tar.gz') as t:t.extractall(dest/'condition-controls',filter='data')


def verify(packet,evidence):
 for name in ('loader.mjs','binary.mjs','stub.wat'):
  expected=(HERE.parent/'b-block-exits'/name).read_text().replace('tail-block-v1','tail-mv-storage-v2')
  require((HERE/name).read_text()==expected,'PROFILE_ONLY_LOADER_CHANGE '+name)
 require((HERE/'wasm32-backend.lisp').read_text().split(';;; First B call unit:')[0]==(HERE.parent/'b-direct-context/wasm32-backend.lisp').read_text().split(';;; First B call unit:')[0],'REVIEWED_NON_B_ENTRIES_UNCHANGED')
 for name,h in read(packet/'source-pins.json').items():require(sha(ROOT/name)==h and sha(packet/'source'/name)==h,'SOURCE_PIN '+name)
 for row in read(packet/'packet.json')['files']:require(sha(safe(packet,row['path']))==row['sha256'],'PACKET_BYTES '+row['path'])
 temp=Path(tempfile.mkdtemp(prefix='ccl-multiple-verify-')).resolve()
 try:
  retained=temp/'retained';hydrate(packet,evidence,retained)
  qualifier=temp/'qualification';qualify(retained/'native',evidence/'macos-u1-inputs',evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64',qualifier)
  require(read(qualifier/'summary.json')==read(retained/'qualification/summary.json'),'NATIVE_QUALIFICATION')
  require(read(qualifier/'verification.json')==read(retained/'qualification/verification.json'),'NATIVE_CONTROLS')
  proposed=mutations((HERE/'wasm32-backend.lisp').read_text());require(set(proposed)=={x['name'] for x in read(retained/'controls.json')},'CONTROL_POPULATION')
  from replay import verify_case
  from concurrent.futures import ProcessPoolExecutor
  tasks=[]
  for name,backend in [('positive',None)]+list(proposed.items()):
   original=retained/'positive' if name=='positive' else retained/'mutants'/name
   if backend is not None:require(backend==(retained/'mutants'/(name+'.lisp')).read_text(),'MUTANT_SOURCE '+name)
   expected=retained/'execution.json' if name=='positive' else retained/'mutants'/(name+'.log')
   tasks.append((name,backend,str(evidence),str(temp),str(original),str(expected)))
  with ProcessPoolExecutor(max_workers=3) as pool:list(pool.map(verify_case,tasks))
  from conditions import run as conditions
  actual=conditions(evidence,temp/'conditions')
  require(actual==read(retained/'conditions/execution.json'),'CONDITION_REPLAY')
  for p in (retained/'conditions/compiled').iterdir():
   if p.suffix in ('.wat','.wasm') or p.name in ('native.json','cases.json','refusals.json','modules.json','compiler.dx64fsl','layout.json','entries.json','root-ir.json','root-contracts.json'):
    require(p.read_bytes()==(temp/'conditions/compiled'/p.name).read_bytes(),'CONDITION_RECOMPILED '+p.name)
  from condition_controls import run as condition_controls
  require(condition_controls(evidence,temp/'condition-controls')==read(retained/'condition-controls/controls.json'),'CONDITION_CONTROLS')
  for control in read(retained/'condition-controls/controls.json'):
   name=control['name']
   for p in (retained/'condition-controls'/name).glob('*.wasm'):
    require(p.read_bytes()==(temp/'condition-controls'/name/p.name).read_bytes(),'CONDITION_MUTANT_BYTES '+name+'/'+p.name)
  from condition_lazy import run as condition_lazy
  require(condition_lazy(temp/'conditions/compiled',temp/'conditions/execution.json',temp/'condition-lazy')==read(retained/'condition-lazy/summary.json'),'CONDITION_LAZY')
  from source_scope import run as source_scope
  require(source_scope(evidence,temp/'source-scope')==read(retained/'source-scope/controls.json'),'SOURCE_SCOPE_REPLAY')
  from result_demand import run as result_demand
  require(result_demand(evidence,temp/'result-demand')==read(retained/'result-demand/summary.json'),'RESULT_DEMAND_REPLAY')
  require(read(temp/'result-demand/observed.json')==read(retained/'result-demand/observed.json'),'RESULT_DEMAND_EVENTS')
  from copy_cost import run as copy_cost
  require(copy_cost(temp/'positive',temp/'copy-cost')==read(retained/'copy-cost/summary.json'),'COPY_COST')
  from lazy_composition import run as lazy_composition
  require(lazy_composition(temp/'positive',temp/'positive.json',temp/'lazy-composition')==read(retained/'lazy-composition/summary.json'),'LAZY_COMPOSITION')
  from loader_controls import run as loader_controls
  require(loader_controls(temp/'positive',temp/'loader-controls')==read(retained/'loader-controls/summary.json'),'LOADER_CONTROLS')
  from regressions import run as regressions
  require(regressions(evidence,temp/'positive',temp/'regressions')==read(retained/'regressions/controls.json'),'DEVELOPMENT_REGRESSIONS')
 except BaseException:
  print('Replay failure retained at',temp,flush=True)
  raise
 else:shutil.rmtree(temp)
 print('S1-B-CONDITIONS-VERIFIED: native R6/R6a, generated multiple-value calls and bindings, native comparisons, mutants, lazy composition and refusals')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();verify(a.packet.resolve(),a.evidence.resolve())
