"""Extend the arch proposal with the existing float service's hyperbolic entries."""
from pathlib import Path
import hashlib, importlib.util, json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('hyperbolic_arch',HERE.parent/'bootstrap-arch/backend.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
BACKEND,ARCH,PACKET=parent.BACKEND,parent.ARCH,parent.PACKET

def generate():
    text=parent.generate()
    old='%libm-tanh64 %libm-tanh32'
    assert text.count(old)==2
    text=text.replace(old,old+' %libm-asinh64 %libm-asinh32 %libm-acosh64 %libm-acosh32 %libm-atanh64 %libm-atanh32')
    assert text.count('(<= 12 op 37)')==1
    return text.replace('(<= 12 op 37)','(<= 12 op 43)')

def source_files(src):
    spec=importlib.util.spec_from_file_location('hyperbolic_sources',HERE/'sources.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return {**parent.source_files(src),**module.derive()}

def proposal(src,out):
    manifest=parent.proposal(src,out)
    changes={BACKEND:generate(),**source_files(src)}
    for row in manifest['added']+manifest['modified']:
        if row['path'] in changes:
            p=out/'files'/row['path'];p.write_text(changes[row['path']])
            row['sha256' if 'sha256' in row else 'after']=hashlib.sha256(p.read_bytes()).hexdigest()
    (out/'unit.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    return manifest

runtime_files=parent.runtime_files
