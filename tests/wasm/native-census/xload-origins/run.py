#!/usr/bin/env python3
"""Collect cold-thunk origins with reversible process-local xload wrappers."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import tarfile
from join import join, events, sha
from test_join import controls

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('reviewed_boot_analyzer', HERE.parent / 'boot-observation/analyze.py')
_boot = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_boot)
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'

def save(p,x): p.write_text(json.dumps(x,indent=2)+'\n')
def digest(p): return sha(p.read_bytes())
def compress(src,dest):
    with src.open('rb') as s,gzip.open(dest,'wb') as d:shutil.copyfileobj(s,d)


def run(store, work, out):
    if platform.system() != 'Darwin' or platform.machine() != 'x86_64': raise ValueError('requires reference macOS x86-64')
    if any(a==b or a in b.parents or b in a.parents for a,b in ((store,work),(store,out),(work,out))):raise ValueError('separate evidence, work and output required')
    out.mkdir(parents=True,exist_ok=False); work.mkdir(parents=True,exist_ok=False); source=work/'ccl';source.mkdir()
    save(work/'disposable.json',{'purpose':'xload-origin-witness','source':str(source)})
    report={'version':1,'status':'FAIL','review_disposition':'NOT_REVIEWED','commands':[],
            'source_revision':U1,'scope':'No shared-source edits or compilation; xload dispatch/function wrappers restored in the disposable process.'}
    env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin','LANG':'C','LC_ALL':'C','CCL_DEFAULT_DIRECTORY':str(source)}
    kernel=source/'dx86cl64'; reference=store/'2026-09-13-boot-observation-r1'; inputs=store/'macos-u1-inputs'
    def command(name,argv,*,cwd=source,extra=None,stdin=None,marker=None,timeout=60):
        row={'name':name,'argv':argv,'cwd':str(cwd),'environment':{**env,**(extra or {})},'stdin':stdin,
             'started':datetime.now(timezone.utc).isoformat(),'timeout_seconds':timeout}
        try:
            with (out/(name+'.log')).open('wb') as log:
                p=subprocess.Popen(argv,cwd=cwd,env=row['environment'],stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:p.communicate(None if stdin is None else stdin.encode(),timeout=timeout)
                except BaseException:
                    try:os.killpg(p.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    p.wait();raise
            row['exit_code']=p.returncode
            if p.returncode or marker and marker not in (out/(name+'.log')).read_text(errors='replace'):raise ValueError(name+' failed: retained log')
        finally:
            report['commands'].append(row);save(out/'commands.json',report['commands'])
    def lisp(name,expr,loads=(),**kw):
        argv=[str(kernel),'--no-init','--batch']
        for p in loads:argv+=['--load',str(p)]
        command(name,argv+['--eval',expr],**kw)
    def fasls():return {str(p.relative_to(source)):digest(p) for p in sorted(source.rglob('*.dx64fsl'))}
    try:
        pins=json.loads((inputs/'pins.json').read_text());assert pins['source_revision']==U1
        packet=json.loads((reference/'packet.json').read_text());expected={r['path']:r['sha256'] for r in packet['files']}
        paths=[inputs/n for n in ('source.tar','bootstrap.tar.gz')]+[reference/n for n in ('baseline-fasls.tar.gz','capture/observed-fasls.json','capture/events.jsonl.gz','capture/run.json')]
        report['inputs']={str(p):digest(p) for p in paths}
        for name in ('source.tar','bootstrap.tar.gz'):
            if report['inputs'][str(inputs/name)]!=pins['inputs'][name]:raise ValueError('archive input changed')
        for p in paths[2:]:
            if report['inputs'][str(p)]!=expected[str(p.relative_to(reference))]:raise ValueError('reference input changed')
        for path in (inputs/'source.tar',inputs/'bootstrap.tar.gz',reference/'baseline-fasls.tar.gz'):
            with tarfile.open(path) as a:a.extractall(source,filter='data')
        for p in (reference/'capture/changed-fasls').rglob('*.dx64fsl'):shutil.copyfile(p,source/p.relative_to(reference/'capture/changed-fasls'))
        oldrun=json.loads((reference/'capture/run.json').read_text()); retained_kernel=Path(oldrun['kernel']['path'])
        if digest(retained_kernel)!=oldrun['kernel']['sha256']:raise ValueError('kernel identity')
        shutil.copyfile(retained_kernel,kernel);kernel.chmod(0o755);report['kernel']=oldrun['kernel']
        before=fasls();recorded=json.loads((reference/'capture/observed-fasls.json').read_text())
        if before!=recorded:raise ValueError('not the reviewed 164 FASLs')
        save(out/'fasls-before.json',before)
        dependencies=[HERE/n for n in ('run.py','observe.lisp','join.py','test_join.py')]+[HERE.parent/'boot-observation'/n for n in ('export.lisp','analyze.py','patch.json','observation.patch')]+[HERE.parent/'observer.lisp']
        report['source_sha256']={str(p):digest(p) for p in dependencies}
        source_pins=['xdump/xfasload.lisp','xdump/faslenv.lisp','lib/nfcomp.lisp','level-1/l1-reader.lisp','compiler/X86/X8664/x8664-arch.lisp']
        report['u1_sources']={p:digest(source/p) for p in source_pins}
        lisp('plain-xload','(progn (ccl::xload-level-0 nil) (format t "PLAIN-XLOAD-COMPLETE~%") (ccl:quit))',[HERE/'observe.lisp'],marker='PLAIN-XLOAD-COMPLETE')
        boot_image=source/'x86-boot64.image';plain=digest(boot_image);compress(boot_image,out/'plain-boot.image.gz')
        lisp('observed-xload','(progn (ccl-xload-origins::run) (ccl:quit))',[HERE/'observe.lisp'],extra={'CCL_XLOAD_OUTPUT':str(out/'origins.json')},marker='XLOAD-WRAPPERS-RESTORED')
        report['boot_images']={'plain':plain,'observed':digest(boot_image),'identical':plain==digest(boot_image)}
        compress(boot_image,out/'observed-boot.image.gz')
        command('boot',[str(kernel),'--image-name',str(boot_image),'--no-init','--batch'],stdin='(ccl:save-application '+json.dumps(str(out/'booted.image'))+')\n')
        command('export',[str(kernel),'--image-name',str(out/'booted.image'),'--no-init','--batch','--load',str(HERE.parent/'observer.lisp'),'--load',str(HERE.parent/'boot-observation/export.lisp'),'--eval','(progn (cl-user::export-boot-census) (ccl:quit))'],extra={'CCL_BOOT_CENSUS_OUTPUT':str(out/'events.jsonl')},marker='BOOT-CENSUS-EXPORTED')
        boot=events(out/'events.jsonl'); _boot.analyze(boot)
        original_root=next(c['cwd'] for c in oldrun['commands'] if c['name']=='observed')
        original=gzip.decompress((reference/'capture/events.jsonl.gz').read_bytes()).decode()
        normalized=(out/'events.jsonl').read_text().replace(str(source),original_root)
        if normalized!=original:raise ValueError('fresh boot stream differs beyond declared archive root relocation')
        report['fresh_boot_stream_identical_after_root_relocation']=True
        # Materialize reviewed observed source bytes as data for their source
        # ranges. These copies are never loaded or compiled by the native run.
        data=out/'source-data';data.mkdir();manifest=json.loads((HERE.parent/'boot-observation/patch.json').read_text())
        for row in manifest['files']:
            p=data/row['path'];p.parent.mkdir(parents=True,exist_ok=True)
            if digest(source/row['path'])!=row['original_sha256']:raise ValueError('U1 source input changed')
            shutil.copyfile(source/row['path'],p)
        command('materialize-source-data',['/usr/bin/patch','-p1','--batch','--input',str(HERE.parent/'boot-observation/observation.patch')],cwd=data)
        overrides={r['path']:data/r['path'] for r in manifest['files']}
        for row in manifest['files']:
            if digest(overrides[row['path']])!=row['observed_sha256']:raise ValueError('observed source materialization differs')
        origins=json.loads((out/'origins.json').read_text());joined=join(origins,boot,source,before,overrides)
        save(out/'joins.json',joined);save(out/'summary.json',joined['summary'])
        save(out/'controls.json',controls(origins,boot,source,before,overrides))
        lisp('abort-control','(progn (handler-case (ccl-xload-origins::run) (error (c) (unless (search "XLOAD-CONTROL-ABORT" (princ-to-string c)) (error c)) (format t "ABORT-CONTROL-CAUGHT~%"))) (ccl:quit))',[HERE/'observe.lisp'],extra={'CCL_XLOAD_CONTROL':'abort-before-dump','CCL_XLOAD_OUTPUT':str(out/'forbidden.json')},marker='ABORT-CONTROL-CAUGHT')
        if 'XLOAD-WRAPPERS-RESTORED' not in (out/'abort-control.log').read_text() or (out/'forbidden.json').exists() or digest(boot_image)!=report['boot_images']['observed']:raise ValueError('abort restoration failed')
        lisp('omission-control','(progn (ccl-xload-origins::run) (ccl:quit))',[HERE/'observe.lisp'],extra={'CCL_XLOAD_CONTROL':'omit-entry','CCL_XLOAD_OUTPUT':str(out/'omitted-origins.json')},marker='XLOAD-WRAPPERS-RESTORED')
        try:join(json.loads((out/'omitted-origins.json').read_text()),boot,source,before,overrides)
        except ValueError as e:
            if str(e)!='QUEUE_COUNT':raise
        else:raise ValueError('native omission escaped')
        if fasls()!=before:raise ValueError('FASLs changed without compilation')
        if any(digest(source/r['path'])!=r['original_sha256'] for r in manifest['files']):raise ValueError('source changed')
        report.update(status='PASS',summary=joined['summary'],native_controls_rejected=2,fasls_unchanged=164,source_unchanged=True)
        compress(out/'events.jsonl',out/'events.jsonl.gz');(out/'events.jsonl').unlink()
        compress(out/'booted.image',out/'booted.image.gz');(out/'booted.image').unlink()
        if report['boot_images']['identical']:(out/'plain-boot.image.gz').unlink()
    except BaseException as e:report['error']=type(e).__name__+': '+str(e)
    finally:
        report['completed']=datetime.now(timezone.utc).isoformat();save(out/'run.json',report)
    print(json.dumps({k:report[k] for k in ('status','error','summary','boot_images','fasls_unchanged') if k in report}))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('store','work','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();sys.exit(run(a.store.resolve(),a.work.resolve(),a.output.resolve()))
