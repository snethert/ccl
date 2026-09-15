#!/usr/bin/env python3
"""Compile native U1 source with reversible registry/IR observers in one process."""
import argparse
from datetime import datetime, timezone
import gzip
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('registry_native', HERE.parent/'dispatch-registry/native.py')
native = importlib.util.module_from_spec(spec); spec.loader.exec_module(native)
read, save, digest, require = native.read, native.save, native.digest, native.require


def sources():
    return sorted(HERE.glob('*.py')) + sorted(HERE.glob('*.lisp')) + [
        HERE.parent/p for p in ('observer.lisp', 'dispatch-registry/inspect.lisp',
                              'dispatch-registry/native.py', 'dispatch-registry/inputs.json')
    ] + [ROOT/p for p in ('compiler/nx.lisp', 'compiler/nxenv.lisp', 'compiler/nx2.lisp',
                         'library/lispequ.lisp', 'level-1/l1-dcode.lisp', 'level-1/l1-clos.lisp',
                         'level-1/l1-clos-boot.lisp', 'lib/describe.lisp')]


def execute(source, out, name, mode):
    dest = out/(name+'.json')
    argv = [str(source/'dx86cl64'), '--no-init', '--batch']
    for p in (HERE.parent/'observer.lisp', HERE.parent/'dispatch-registry/inspect.lisp',
              HERE/'observe.lisp', HERE/'ir.lisp'):
        argv += ['--load', str(p)]
    argv += ['--eval', '(progn (ccl-registry-flow::export-state '+json.dumps(str(dest))+' "ccl:lib;describe.lisp" '+json.dumps(mode)+') (ccl:quit))']
    env = dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', LANG='C', LC_ALL='C',
               CCL_DEFAULT_DIRECTORY=str(source))
    command = dict(argv=argv, environment=env, cwd=str(source), timeout_seconds=180)
    save(out/(name+'-command.json'), command)
    try:
        with (out/(name+'.log')).open('wb') as log:
            child = subprocess.Popen(argv, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = child.wait(timeout=180)
            except BaseException:
                try: os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError: pass
                child.wait(); raise
        command['exit_code'] = rc
        require(rc==0 and 'REGISTRY-FLOW-PASS' in (out/(name+'.log')).read_text(), 'NATIVE_EXECUTION '+name)
        raw = dest.read_bytes()
        (out/(name+'.json.gz')).write_bytes(gzip.compress(raw,mtime=0))
        return json.loads(raw)
    finally:
        save(out/(name+'-command.json'),command)


def run(args):
    out, work, store = (x.resolve() for x in (args.output,args.work,args.evidence))
    require(all(a!=b and a not in b.parents and b not in a.parents for a,b in ((out,work),(out,store),(work,store))), 'SEPARATE_PATHS')
    require(ROOT not in out.parents and ROOT not in work.parents, 'DISPOSABLE_PATHS')
    out.mkdir(parents=True, exist_ok=False)
    report = dict(status='FAIL', timestamp=datetime.now(timezone.utc).isoformat(), command=sys.argv,
                  inputs=read(HERE.parent/'dispatch-registry/inputs.json'),
                  source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sources()})
    for p in sources():
        dest=out/'sources'/p.relative_to(ROOT); dest.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(p,dest)
    save(out/'run.json',report)
    try:
        source=native.prepare(store,work)
        first=execute(source,out,'first','observed')
        repeat=execute(source,out,'repeat','observed')
        require(first==repeat, 'NATIVE_REPRODUCTION')
        reference=execute(source,out,'reference','reference')
        require(first['initial_method_codes']==reference['initial_method_codes']
                and first['changed_methods']==reference['changed_methods'], 'OBSERVER_NATIVE_CODE_DELTA')
        omission=execute(source,out,'omit-add','omit-add')
        if not args.capture_only:
            from analyze import assess, controls
            facts, summary=assess(first)
            checked=controls(first,facts,summary,omission)
            for name,value in [('joins.json.gz',facts),('summary.json',summary),('controls.json',checked)]: save(out/name,value)
            report['controls_rejected']=checked['controls_rejected']
        pins=report['inputs']
        require(digest(source/'dx86cl64')==pins['inputs']['kernel']['sha256']
                and digest(source/pins['image_member'])==pins['image_sha256'], 'NATIVE_INPUT_CHANGED')
        for p in sources():
            rel=p.relative_to(ROOT)
            if not str(rel).startswith('tests/'):
                require(digest(source/rel)==report['source_sha256'][str(rel)], 'U1_SOURCE '+str(rel))
        outputs=['first.json.gz','repeat.json.gz','reference.json.gz','omit-add.json.gz','joins.json.gz','summary.json','controls.json']
        if args.packet:
            manifest=read(args.packet/'packet.json')
            require(manifest['id']=='NATIVE-REGISTRY-FLOW-R1','PACKET_ID')
            for r in manifest['files']:
                path=args.packet/r['path']
                require(path.parent==args.packet and path.stat().st_size==r['bytes'] and digest(path)==r['sha256'], 'PACKET_BYTES '+r['path'])
            require(report['source_sha256']==read(args.packet/'sources.json'),'PACKET_SOURCES')
            for name in outputs:
                require((out/name).read_bytes()==(args.packet/name).read_bytes(), 'REPRODUCTION '+name)
            report['replayed_outputs_byte_identical']=len(outputs)
        report.update(status='PASS', native_sessions=4, captured_events=len(first['events']),
                      observed_reference_method_bytes_equal=True, observer_restored=True,
                      shared_source_changes=False, census_gate_credit=False)
        print(json.dumps({k:v for k,v in report.items() if k not in ('inputs','source_sha256','command')},sort_keys=True),flush=True)
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc()); raise
    finally:
        save(out/'run.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('evidence','work','output'): p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--packet',type=Path)
    p.add_argument('--capture-only',action='store_true')
    run(p.parse_args())
