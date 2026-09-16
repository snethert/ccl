#!/usr/bin/env python3
"""Replay a 1A packet: native qualification, generated binary checks and mutants.
The three native build logs/results are checked; full rebuild uses registration/run.py.
"""
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'registration'))
from unit import sha
from qualify import qualify
from check import require,read
# Load this directory's driver explicitly: the registration runner has the same basename.
import importlib.util
spec=importlib.util.spec_from_file_location('stage1_build',HERE/'run.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
def verify(packet,evidence):
    for name,digest in read(packet/'source-pins.json').items():
        require(sha(ROOT/name)==digest and sha(packet/'source'/name)==digest,'EXECUTED_SOURCE '+name)
    for f in read(packet/'build.json')['files']:require(sha(packet/f['path'])==f['sha256'],'BUILD_BYTES '+f['path'])
    with tempfile.TemporaryDirectory(prefix='ccl-stage1-verify-') as tmp:
        tmp=Path(tmp).resolve();q=tmp/'qualification'
        qualify(packet/'native',evidence/'macos-u1-inputs',evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64',q)
        require(read(q/'summary.json')==read(packet/'qualification/summary.json'),'QUALIFICATION_SUMMARY')
        require(read(q/'verification.json')==read(packet/'qualification/verification.json'),'NEGATIVE_CONTROLS')
        for name in ('baseline-operators.json','registered-operators.json','wasm32-arch.dx64fsl','wasm32-backend.dx64fsl','xwasm32fasload.dx64fsl'):
            require((q/name).read_bytes()==(packet/'qualification'/name).read_bytes(),'QUALIFICATION_BYTES '+name)
        # Replay against the original bound manifest, which includes the original
        # retained native logs and image. A fresh build manifest would name new logs.
        reporter=ROOT/'tests/wasm/stage0/diagnostics/reporter.mjs'
        wanted={'wrong-code','wrong-slot','wrong-signature','wrong-operation','wrong-offset','overwrite-first','unbounded-output','skip-unreadable-top'}
        require({p.stem for p in (packet/'controls').glob('*.mjs')}==wanted,'MUTANT_INVENTORY')
        require({r['name'] for r in read(packet/'summary.json')['diagnostic_mutants']}==wanted and all(r['status']=='REJECTED' for r in read(packet/'summary.json')['diagnostic_mutants']),'MUTANT_DISPOSITIONS')
        commands=[('execution',reporter)]+[(p.stem,p) for p in sorted((packet/'controls').glob('*.mjs'))]
        disasm=(packet/'identity.disassembly').read_text();manifest=read(packet/'build.json')
        for name,source in commands:
            out=tmp/(name+'.json');log=tmp/(name+'.log')
            with log.open('w') as stream:child=subprocess.run(['/usr/local/bin/node',str(HERE/'execute.mjs'),str(packet),str(source),str(out)],stdout=stream,stderr=subprocess.STDOUT,timeout=180)
            if name=='execution':
                require(child.returncode==0,'POSITIVE_REPLAY');build.assess(read(out),manifest,disasm)
                require(read(out)==read(packet/'execution.json'),'OBSERVATION_REPLAY')
            elif child.returncode==0:
                try:build.assess(read(out),manifest,disasm)
                except ValueError:pass
                else:raise ValueError('MUTANT_REPLAY '+name)
            else:require('AssertionError' in log.read_text(),'MUTANT_EXECUTION '+name)
    print('S1-1A-VERIFIED: native qualification, nine generated modules, 37 binding controls, eight diagnostic mutants')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args();verify(a.packet.resolve(),a.evidence.resolve())
