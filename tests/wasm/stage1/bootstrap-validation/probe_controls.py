"""Refuse omitted execution entries, leaked macros and installation overflow."""
from pathlib import Path
import argparse
import shutil
import subprocess
import common as c
import storage
from probe import probe
from prepare import prepare


def controls(base,cache,out):
    out=Path(out);out.mkdir();rows=[]
    inputs=out/'missing-inputs.lisp'
    inputs.write_text("(in-package :wasm32-compiler)\n(defun validation-probe-cases () '((validation-helper ((1)))))\n")
    missing=out/'missing-macro.lisp'
    missing.write_text('(in-package :wasm32-compiler)\n(defun validation-helper (x) (validation-increment x))\n')
    for name,source,expected in [('execution-entry',c.HERE/'examples/probes.lisp','no explicit execution entry'),
                                 ('file-macro',missing,'Missing probe dependency')]:
        target=out/name
        try:probe(base,source,inputs,target,cache)
        except subprocess.CalledProcessError:
            if expected not in (target/'probe.log').read_text():raise
        else:raise AssertionError('probe refusal did not fire: '+name)
        rows.append(dict(name=name,status='REFUSED',log=c.sha(target/'probe.log')))
        # Keep the failure and its submitted inputs, not another corpus copy.
        saved=out/(name+'-evidence');saved.mkdir()
        shutil.copyfile(target/'probe.log',saved/'probe.log')
        shutil.copytree(target/'submitted',saved/'submitted')
        c.save(saved/'reproduction.json',dict(base=c.sha(Path(base)/'build-invocation.json'),
               source=c.sha(source),inputs=c.sha(inputs),expected=expected))
        shutil.rmtree(target)
    capacity=out/'capacity'
    shutil.copytree(base,capacity,ignore=shutil.ignore_patterns('compiler.image'))
    modules=c.read(capacity/'compiled/modules.json')
    modules.extend([modules[0]]*(4089-len(modules)))
    c.save(capacity/'compiled/modules.json',modules)
    try:prepare(capacity)
    except ValueError as error:assert 'installation capacity' in str(error)
    else:raise AssertionError('capacity admitted')
    shutil.copyfile(capacity/'compiled/modules.json',out/'capacity-modules.json')
    shutil.rmtree(capacity)
    rows.append(dict(name='capacity',status='REFUSED',installation_started=False))
    result=dict(status='PASS',rows=rows)
    c.save(out/'probe-controls.json',result);return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('cache',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    storage.gc(a.cache)
    try:
        with storage.lease([a.base,a.output],a.cache):print(controls(a.base,a.cache,a.output))
    finally:storage.gc(a.cache)
