#!/usr/bin/env python3
"""Run one correlated native build with the existing removable observation unit."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import time
import traceback

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'rich-observation'))
from unit import RichUnit
from install import write_install
sys.path.insert(0,str(HERE.parent/'closure'))
from support import save,digest,read

INTENTIONAL={'level-0/l0-def.dx64fsl','level-0/nfasload.dx64fsl','l1-fasls/l1-readloop.dx64fsl',
             'l1-fasls/nx.dx64fsl','bin/nx2.dx64fsl','bin/vinsn.dx64fsl','bin/nfcomp.dx64fsl','bin/dumplisp.dx64fsl'}


def run(a):
    work=a.work.resolve();out=a.output.resolve();store=a.evidence.resolve()
    for path in (work,out):
        if path==ROOT or ROOT in path.parents or path==store or store in path.parents:raise ValueError('disposable paths required')
        path.mkdir(parents=True,exist_ok=False)
    source=work/'ccl';source.mkdir();inputs=store/'macos-u1-inputs'
    save(work/'disposable.json',dict(purpose='rich-census-disposable-U1',source=str(source)))
    shutil.copytree(HERE,out/'executed-sources',ignore=shutil.ignore_patterns('__pycache__'))
    report=dict(status='RUNNING',scope='Native build observation; no gate or target implementation claim',commands=[],normalizations=[])
    unit=None;baseline=None
    env=dict(PATH='/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin',LANG='C',LC_ALL='C',CCL_DEFAULT_DIRECTORY=str(source))
    def command(name,argv,cwd=source,extra=None,marker=None,timeout=3600):
        row=dict(name=name,argv=argv,cwd=str(cwd),seconds=None,exit_code=None)
        report['commands'].append(row);save(out/'run.json',report)
        print('Running',name,flush=True);start=time.monotonic()
        try:
            with (out/(name+'.log')).open('wb') as log:
                child=subprocess.Popen(argv,cwd=cwd,env=dict(env,**(extra or {})),stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:row['exit_code']=child.wait(timeout=timeout)
                except BaseException:
                    try:os.killpg(child.pid,signal.SIGKILL)
                    except ProcessLookupError:pass
                    child.wait();raise
            if row['exit_code'] or marker and marker not in (out/(name+'.log')).read_text(errors='replace'):
                raise ValueError('child failed: '+name)
        finally:row['seconds']=round(time.monotonic()-start,3);save(out/'run.json',report)
    def bootstrap():
        with tarfile.open(inputs/'bootstrap.tar.gz') as archive:archive.extract('dx86cl64.image',source,filter='data')
    def helpers():
        return [HERE.parent/p for p in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp',
                                        'resident-bodies/export.lisp','dispatch-registry/inspect.lisp','registry-callees/build-observer.lisp')]
    def lisp(name,expr,loads=(),**kwargs):
        argv=[str(source/'dx86cl64'),'--no-init','--batch']
        for path in loads:argv+=['--load',str(path)]
        command(name,argv+['--eval',expr],**kwargs)
    def fasls():return {str(p.relative_to(source)):digest(p) for p in sorted(source.rglob('*.dx64fsl'))}
    def archive_fasls(name):
        with tarfile.open(out/(name+'.tar.gz'),'w:gz') as archive:
            for path in sorted(source.rglob('*.dx64fsl')):archive.add(path,arcname=str(path.relative_to(source)))
    def rebuild(name,observed=False):
        write_install(source,work/'install.lisp')
        build='(lambda () (let ((*gensym-counter* 100000)) (ccl:rebuild-ccl :clean t)))'
        if observed:
            body='(ccl-complete-census::with-build-observation '+json.dumps(str(out/'build.jsonl'))+' '+json.dumps(str(out/'registries.jsonl'))+' '+build+')'
        else:body='(funcall '+build+')'
        expr='(progn (let ((*gensym-counter* *gensym-counter*)) (load '+json.dumps(str(work/'install.lisp'))+')) '+body+' (format t "CORRELATED-REBUILD-PASS~%") (ccl:quit))'
        lisp(name,expr,helpers(),marker='CORRELATED-REBUILD-PASS',timeout=14400 if observed else 3600)
        result=fasls();save(out/(name+'-fasls.json'),result);return result
    def tests(name):
        target=out/name;target.mkdir()
        command(name+'-clean',['make','clean'],cwd=work/'ccl-tests')
        lisp(name,'(progn (cl-user::run-gate0-tests) (ccl:quit))',[HERE.parents[1]/'native-baseline/tests.lisp'],
             cwd=work/'ccl-tests',extra=dict(CCL_GATE0_TESTS=str(work/'ccl-tests')+'/',CCL_GATE0_OUTPUT=str(target)+'/'),
             marker='CCL-GATE0-TESTS-COMPLETE PASS')
        result=read(target/'test-summary.json')
        if not result['success'] or result['passed']!=21843 or result['upstream_disabled']!=75:raise ValueError('native test inventory changed')
        return result
    try:
        pins=read(inputs/'pins.json');report['inputs']=pins
        for name,want in pins['inputs'].items():
            if digest(inputs/name)!=want:raise ValueError('changed input '+name)
        for name,dest in (('source.tar',source),('tests.tar',work/'ccl-tests'),('bootstrap.tar.gz',source)):
            dest.mkdir(exist_ok=True)
            with tarfile.open(inputs/name) as archive:archive.extractall(dest,filter='data')
        kernel=store/'2026-09-12-native-census-r7/baseline/build/dx86cl64'
        shutil.copyfile(kernel,source/'dx86cl64');(source/'dx86cl64').chmod(0o755)
        report['kernel_sha256']=digest(kernel)
        if a.reuse_baseline:
            prior=a.reuse_baseline.resolve();record=read(prior/'run.json')
            if record['inputs']!=pins or record['kernel_sha256']!=report['kernel_sha256'] or not record['baseline_tests']['success']:
                raise ValueError('incompatible baseline reuse')
            baseline=read(prior/'baseline-fasls.json')
            with tarfile.open(prior/'baseline-fasls.tar.gz') as archive:archive.extractall(source,filter='data')
            if fasls()!=baseline:raise ValueError('baseline artifact reuse differs')
            report['baseline_tests']=record['baseline_tests']
            report['baseline_reused']=dict(path=str(prior),reason='Only the observation callback changed after the retained baseline build and test execution.')
            save(out/'baseline-fasls.json',baseline)
        else:
            baseline=rebuild('baseline');archive_fasls('baseline-fasls');report['baseline_tests']=tests('baseline-tests')
        bootstrap();unit=RichUnit(work)
        with unit:
            try:
                observed=rebuild('observed',True);archive_fasls('observed-fasls')
                if baseline.keys()!=observed.keys():raise ValueError('FASL inventory changed')
                changed={p for p in baseline if baseline[p]!=observed[p]}
                report['r6']=dict(fasls=len(baseline),identical=len(baseline)-len(changed),intentional=sorted(changed),unexplained=sorted(changed-INTENTIONAL))
                if changed!=INTENTIONAL:raise ValueError('unexplained R6 difference '+repr(changed))
                report['observed_tests']=tests('observed-tests')
            except BaseException:
                archive_fasls('failed-observed-fasls')
                for name in ('dx86cl64.image','x86-boot64.image'):
                    path=source/name
                    if path.exists():
                        with path.open('rb') as src,gzip.open(out/('failed-'+name+'.gz'),'wb') as dst:shutil.copyfileobj(src,dst)
                raise
        bootstrap();restored=rebuild('restored')
        if restored!=baseline:raise ValueError('restored FASLs differ')
        report.update(status='PASS',restored_fasls=len(restored),source_restored=True)
    except BaseException:
        report['status']='FAIL';(out/'failure.txt').write_text(traceback.format_exc());raise
    finally:
        if unit is not None:
            unit.check('original_sha256');report['source_restored']=True
        for name in ('build.jsonl','registries.jsonl'):
            path=out/name
            if path.exists():
                with path.open('rb') as src,gzip.open(str(path)+'.gz','wb',compresslevel=1) as dst:shutil.copyfileobj(src,dst)
                path.unlink()
        save(out/'run.json',report)
    print(json.dumps({k:report[k] for k in ('status','r6','restored_fasls','source_restored')},sort_keys=True),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--work',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence')
    p.add_argument('--reuse-baseline',type=Path)
    run(p.parse_args())
