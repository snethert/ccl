#!/usr/bin/env python3
"""Reproduce retained origin joins and omission controls without another boot."""
import argparse
import json
from pathlib import Path
import tarfile
from join import join, events, sha
from test_join import controls


def verify(packet, store, output):
    output.mkdir(parents=True,exist_ok=False); source=output/'source';source.mkdir()
    with tarfile.open(store/'macos-u1-inputs/source.tar') as a:a.extractall(source,filter='data')
    reference=store/'2026-09-13-boot-observation-r1'
    with tarfile.open(reference/'baseline-fasls.tar.gz') as a:a.extractall(source,filter='data')
    import shutil
    for p in (reference/'capture/changed-fasls').rglob('*.dx64fsl'):shutil.copyfile(p,source/p.relative_to(reference/'capture/changed-fasls'))
    origins=json.loads((packet/'origins.json').read_text())
    run=json.loads((packet/'run.json').read_text()); original_root=next(c['cwd'] for c in run['commands'] if c['name']=='observed-xload')
    # Only relocate the recorded absolute file names, preserving all identities,
    # positions, contexts and order in the source record.
    for p in origins['paths']:
        if not Path(p).is_relative_to(original_root):raise ValueError('escaping original input')
    origins['paths']=[str(source/Path(p).relative_to(original_root)) for p in origins['paths']]
    for row in origins['entries']:row['file']=str(source/Path(row['file']).relative_to(original_root))
    fasls=json.loads((packet/'fasls-before.json').read_text())
    overrides={str(p.relative_to(packet/'source-data')):p for p in (packet/'source-data').rglob('*.lisp')}
    boot=events(packet/'events.jsonl.gz'); result=join(origins,boot,source,fasls,overrides)
    if result!=json.loads((packet/'joins.json').read_text()):raise ValueError('join reproduction differs')
    tests=controls(origins,boot,source,fasls,overrides)
    if tests!=json.loads((packet/'controls.json').read_text()):raise ValueError('control reproduction differs')
    report={'status':'PASS','joins_identical':True,'controls_identical':True,'controls_rejected':tests['controls_rejected'],
            'inputs':{str(packet/n):sha((packet/n).read_bytes()) for n in ('origins.json','events.jsonl.gz','joins.json','controls.json','fasls-before.json')},
            'source_sha256':{str(Path(__file__).parent/n):sha((Path(__file__).parent/n).read_bytes()) for n in ('verify.py','join.py','test_join.py')}}
    (output/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: retained joins and '+str(tests['controls_rejected'])+' controls reproduce.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('packet','store','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();verify(a.packet.resolve(),a.store.resolve(),a.output.resolve())
