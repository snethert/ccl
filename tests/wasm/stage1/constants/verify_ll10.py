#!/usr/bin/env python3
"""Recompile and replay the final LL10 packet, including the inherited corpus."""
import argparse,shutil,tempfile
from pathlib import Path
from run import ROOT,source_pins,run,read,sha,require
from retain import hydrate

def verify(packet,evidence,out):
 require(read(packet/'source-pins.json')==source_pins(),'SOURCE_PINS')
 for name,h in read(packet/'source-pins.json').items():require(sha(packet/'source'/name)==h,'SNAPSHOTTED_SOURCE '+name)
 for row in read(packet/'packet.json')['files']:
  p=(packet/row['path']).resolve();require(p.is_relative_to(packet.resolve()) and sha(p)==row['sha256'],'PACKET '+row['path'])
 out.mkdir(parents=True,exist_ok=False);retained=out/'retained';hydrate(evidence,packet,retained)
 fresh=out/'fresh';run(evidence,retained/'native',fresh)
 require(read(fresh/'summary.json')==read(retained/'summary.json'),'SUMMARY_REPLAY')
 require(read(fresh/'coverage.json')==read(retained/'coverage.json'),'COVERAGE_REPLAY')
 require(read(fresh/'compiler-controls/controls.json')==read(retained/'compiler-controls/controls.json'),'COMPILER_CONTROLS')
 require(read(fresh/'image-controls/controls.json')==read(retained/'image-controls/controls.json'),'IMAGE_CONTROLS')
 folders=['positive','inherited/positive','inherited/conditions/compiled','inherited/call-errors/compiled']
 folders += ['compiler-controls/'+r['name'] for r in read(retained/'compiler-controls/controls.json')]
 count=0
 for folder in folders:
  for p in (retained/folder).iterdir():
   if p.suffix in ('.wat','.wasm','.dx64fsl') or p.name in ('native.json','pools.json','cases.json','modules.json','refusals.json','execution.json','snapshot.json','expected.json','root-contracts.json','root-ir.json'):
    require(p.read_bytes()==(fresh/folder/p.name).read_bytes(),'BYTE_REPLAY '+folder+'/'+p.name);count+=1
 for name in ('full-loader/full-controls.json','full-loader/mutants.json','loader-controls/summary.json','lazy/summary.json','condition-lazy/summary.json','error-lazy/summary.json'):
  require(read(fresh/'inherited'/name)==read(retained/'inherited'/name),'LOADER_REPLAY '+name)
 print('S1-LL10-VERIFIED',count,'deterministic files; native R6/R6a, generated pools, persistence, controls, inherited calls and lazy installation')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('packet','evidence','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();verify(a.packet.resolve(),a.evidence.resolve(),a.output.resolve())
