#!/usr/bin/env python3
"""Read native bootstrap bodies in disposable processes, with no build or patch."""
import argparse
from datetime import datetime,timezone
import gzip
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
import traceback
from common import HERE,ROOT,read,save,digest,require
from analyze import analyze,missing_codes


def initial_rows(path):
    out=[]
    with gzip.open(path,'rb') as stream:
        for line in stream:
            out.append(line)
            if b'"kind":"inventory-return"' in line[:120]:break
    require(json.loads(out[-1])['kind']=='inventory-return','INITIAL_INVENTORY_END')
    return out


def execute_native(source,out,paths,requests,mode):
    # Same original observer bytes, with their original source-note context;
    # LOAD-FROM-STREAM is U1's ordinary source loader. No file is overwritten.
    recorded=str(ROOT/'tests/wasm/native-census/rich-observation/observer.lisp')
    load_expr='(with-open-file (s '+json.dumps(str(paths['observer']))+' :external-format :utf-8) (let ((ccl::*loading-file-source-file* '+json.dumps(recorded)+') (*package* *package*) (*readtable* *readtable*)) (ccl::load-from-stream s nil)))'
    prefix=out/(mode+'-prefix.jsonl');export=out/(mode+'-bodies.json')
    expr='(progn (let ((*gensym-counter* *gensym-counter*)) (load '+json.dumps(str(paths['installer']))+')) (ccl-rich-census::start '+json.dumps(str(prefix))+') (setq ccl::*startup-census-hook* nil) (close ccl-rich-census::*stream*) (setq ccl-rich-census::*stream* nil) (load '+json.dumps(str(HERE/'export.lisp'))+'))'
    argv=[str(source/'dx86cl64'),'--no-init','--batch']
    for name in ('observer.lisp','dependencies.lisp'):argv+=['--load',str(HERE.parent/name)]
    argv+=['--eval',load_expr,'--eval',expr,'--eval',
        '(progn (ccl-resident-bodies::export-image '+json.dumps(str(requests))+' '+json.dumps(str(export))+') (ccl:quit))']
    env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin',LANG='C',LC_ALL='C',CCL_DEFAULT_DIRECTORY=str(source))
    record=dict(argv=argv,environment=env,cwd=str(source),timeout_seconds=60)
    save(out/(mode+'-command.json'),record)
    try:
        with (out/(mode+'.log')).open('wb') as log:
            child=subprocess.Popen(argv,cwd=source,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:rc=child.wait(timeout=60)
            except BaseException:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                child.wait();raise
        record['exit_code']=rc
        require(rc==0 and 'RESIDENT-BODIES-PASS' in (out/(mode+'.log')).read_text(),'NATIVE_EXPORT '+mode)
    finally:save(out/(mode+'-command.json'),record)
    return prefix.read_bytes().splitlines(keepends=True),read(export)


def run(args):
    work=args.work.resolve();out=args.output.resolve();store=args.evidence.resolve()
    require(platform.system()=='Darwin' and platform.machine()=='x86_64','MACOS_X8664_REQUIRED')
    require(all(a!=b and a not in b.parents and b not in a.parents for a,b in ((work,out),(work,store),(out,store))), 'SEPARATE_DIRECTORIES')
    require(ROOT not in work.parents and ROOT not in out.parents,'DISPOSABLE_REQUIRED')
    work.mkdir(parents=True,exist_ok=False);out.mkdir(parents=True,exist_ok=False)
    files=list(HERE.glob('*.py'))+list(HERE.glob('*.lisp'))+[HERE/'inputs.json',HERE.parent/'observer.lisp',HERE.parent/'dependencies.lisp']
    files += [ROOT/p for p in ('level-0/l0-utils.lisp','level-0/X86/x86-utils.lisp','level-0/X86/x86-def.lisp',
        'level-1/l1-files.lisp','level-1/l1-reader.lisp','lib/edit-callers.lisp','compiler/X86/X8664/x8664-arch.lisp',
        'lisp-kernel/image.h','lisp-kernel/image.c','lisp-kernel/area.h','lisp-kernel/pmcl-kernel.c','lisp-kernel/platform-darwinx8664.h')]
    pins=read(HERE/'inputs.json');report=dict(status='FAIL',command=sys.argv,timestamp=datetime.now(timezone.utc).isoformat(),
        input_pins=pins,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in files})
    for p in files:
        dest=out/'sources'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
    save(out/'run.json',report)
    try:
        paths={k:store/r['path'] for k,r in pins['inputs'].items()}
        for k,p in paths.items():require(digest(p)==pins['inputs'][k]['sha256'],'INPUT '+k)
        source=work/'ccl';source.mkdir()
        with tarfile.open(paths['source']) as archive:archive.extractall(source,filter='data')
        with tarfile.open(paths['bootstrap']) as archive:
            # Source and the image are sufficient; no retained tree or FASLs are modified.
            archive.extract(archive.getmember(pins['image_member']),source,filter='data')
        kernel=source/'dx86cl64';shutil.copyfile(paths['kernel'],kernel);kernel.chmod(0o755)
        image=source/pins['image_member'];require(digest(image)==pins['image_sha256'],'BOOTSTRAP_IMAGE')
        requested=missing_codes(read(paths['bindings']));request_file=out/'requests.lisp'
        request_file.write_text('('+' '.join(map(str,requested))+')\n')
        old=initial_rows(paths['events'])
        print('Exporting the bootstrap read-only region in two disposable native sessions.',flush=True)
        first,export=execute_native(source,out,paths,request_file,'first')
        facts,summary=analyze(image.read_bytes(),old,first,export,requested)
        save(out/'bodies.json.gz',facts);save(out/'summary.json',summary)
        second,repeated=execute_native(source,out,paths,request_file,'repeat')
        facts2,summary2=analyze(image.read_bytes(),old,second,repeated,requested)
        require(facts==facts2 and summary==summary2 and export==repeated,'NATIVE_REPRODUCTION')
        require(digest(image)==pins['image_sha256'] and digest(kernel)==pins['inputs']['kernel']['sha256'],'NATIVE_INPUT_CHANGED')
        from controls import run as controls
        checks=controls(image.read_bytes(),old,first,export,requested,facts,summary)
        save(out/'controls.json',checks)
        for mode in ('first','repeat'):
            for suffix in ('prefix.jsonl','bodies.json'):
                p=out/(mode+'-'+suffix)
                (out/(p.name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0));p.unlink()
        report.update(status='PASS',summary=summary,controls=checks['controls_rejected'],
                      native_sessions=2,native_inputs_unchanged=True,shared_source_changes=False)
        print(json.dumps(dict(summary,controls_rejected=checks['controls_rejected']),sort_keys=True),flush=True)
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());raise
    finally:save(out/'run.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','work','output'):p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
