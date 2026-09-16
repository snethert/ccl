#!/usr/bin/env python3
"""Build pristine U1, apply the Stage 1 registration proposal, compare, reverse."""
import argparse,json,os,platform,shutil,subprocess,sys,tarfile,time,traceback
from pathlib import Path
from unit import HERE,ROOT,U1,Unit,proposal,sha,save
from fasl import compare_compiler,compare_systems
OBSERVER=ROOT/'tests/wasm/native-census/observer.lisp'
TEST_DRIVER=ROOT/'tests/wasm/native-baseline/tests.lisp'

def run(inputs,kernel,work,out,baseline_from=None):
    if (platform.system(),platform.machine())!=('Darwin','x86_64'):raise ValueError('macOS x86-64 required')
    work.mkdir(parents=True,exist_ok=False);out.mkdir(parents=True,exist_ok=False)
    source=work/'ccl';source.mkdir();save(work/'stage1-disposable.json',{'source':str(source),'revision':U1})
    pins=json.loads((inputs/'pins.json').read_text())
    if pins['source_revision']!=U1:raise ValueError('U1 required')
    for name,h in pins['inputs'].items():
        if sha(inputs/name)!=h:raise ValueError('input changed: '+name)
    for filename,dest in [('source.tar',source),('tests.tar',work/'ccl-tests')]:
        dest.mkdir(exist_ok=True)
        with tarfile.open(inputs/filename) as t:t.extractall(dest,filter='data')
    originals={str(p.relative_to(source)):sha(p) for p in source.rglob('*') if p.is_file()}
    with tarfile.open(inputs/'bootstrap.tar.gz') as t:t.extractall(source,filter='data')
    shutil.copy(kernel,source/'dx86cl64');(source/'dx86cl64').chmod(0o755)
    unit=proposal(source,out/'proposal')
    commands=[];report={'version':1,'status':'FAIL','review_disposition':'NOT_REVIEWED','source_revision':U1,'inputs':pins,'kernel_sha256':sha(kernel),'normalizations':[]}
    env={'PATH':'/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin','LANG':'C','LC_ALL':'C','CCL_DEFAULT_DIRECTORY':str(source)}
    def command(name,argv,marker=None,extra=None,cwd=source):
        row={'name':name,'argv':list(map(str,argv)),'cwd':str(cwd),'environment':env| (extra or {})};commands.append(row);save(out/'commands.json',commands)
        print('Running '+name,flush=True)
        with (out/(name+'.log')).open('wb') as log:
            p=subprocess.run(row['argv'],cwd=cwd,env=row['environment'],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        row['exit_code']=p.returncode;save(out/'commands.json',commands)
        if p.returncode or marker and marker not in (out/(name+'.log')).read_text(errors='replace'):raise ValueError(name+' failed (retained log)')
    def lisp(name,expr=None,loads=(),marker=None,extra=None,cwd=source):
        argv=[source/'dx86cl64','--no-init','--batch']
        for p in loads:argv+=['--load',p]
        if expr:argv+=['--eval',expr]
        command(name,argv,marker,extra,cwd)
    def bootstrap():
        with tarfile.open(inputs/'bootstrap.tar.gz') as t:t.extract(t.getmember('dx86cl64.image'),source,filter='data')
    def fasls():return {str(p.relative_to(source)):sha(p) for p in sorted(source.rglob('*.dx64fsl')) if p.stem not in ('wasm32-arch','wasm32-backend','xwasm32fasload')}
    install='(let ((*gensym-counter* *gensym-counter*)) (load (compile-file "ccl:lib;systems.lisp")) (ccl::in-development-mode (load (compile-file "ccl:lib;compile-ccl.lisp"))))'
    def build(name,registered=False):
        # Start dependency preparation from source on every side, never leftover FASLs.
        for path in source.rglob('*.dx64fsl'):path.unlink()
        registration='(load '+json.dumps(str(HERE/'load.lisp'))+') (assert (ccl::find-backend :wasm32)) (format t "WASM32-LOADED-BEFORE-REBUILD~%")' if registered else ''
        bootstrap();lisp(name,'(progn '+install+' (ccl::in-development-mode (require "XFASLOAD" "ccl:xdump;xfasload")) '+registration+' (let ((*gensym-counter* 100000)) (rebuild-ccl :clean t)) (format t "S1-BUILD-PASS~%") (ccl:quit))',marker='S1-BUILD-PASS')
    def snapshot(name,registered):
        loads=([HERE/'load.lisp'] if registered else [])+[OBSERVER,HERE/'snapshot.lisp']
        lisp(name,loads=loads,marker='S1-SNAPSHOT-PASS',extra={'S1_SNAPSHOT':str(out/(name+'.json'))})
        return json.loads((out/(name+'.json')).read_text())
    def tests(name,registered):
        dest=out/name;dest.mkdir();command(name+'-clean',['make','clean'],cwd=work/'ccl-tests')
        lisp(name,'(cl-user::run-gate0-tests)',([HERE/'load.lisp'] if registered else [])+[TEST_DRIVER],
             'CCL-GATE0-TESTS-COMPLETE PASS',{'CCL_GATE0_TESTS':str(work/'ccl-tests')+'/','CCL_GATE0_OUTPUT':str(dest)+'/'},work/'ccl-tests')
        x=json.loads((dest/'test-summary.json').read_text())
        if not x['success'] or (x['passed'],x['upstream_disabled'])!=(21843,75):raise ValueError('native suite differs')
        return x
    try:
        command('host',['sw_vers']);command('compiler',['clang','--version'])
        if baseline_from is None:
            build('baseline-build');baseline=fasls();save(out/'baseline-fasls.json',baseline)
            if len(baseline)!=164:raise ValueError('native FASL inventory')
            with tarfile.open(out/'baseline-fasls.tar.gz','w:gz') as t:
                for n in baseline:t.add(source/n,arcname=n)
            shutil.copy(source/'dx86cl64.image',out/'baseline.image')
            before=snapshot('baseline-snapshot',False);report['baseline_tests']=tests('baseline-tests',False)
        else:
            prior=json.loads((baseline_from/'run.json').read_text())
            if prior['status']!='PASS' or prior['inputs']!=pins or prior['kernel_sha256']!=sha(kernel):raise ValueError('baseline reference changed')
            for path in baseline_from.glob('baseline*'):
                if path.is_dir():shutil.copytree(path,out/path.name)
                else:shutil.copy(path,out/path.name)
            baseline=json.loads((out/'baseline-fasls.json').read_text())
            before=json.loads((out/'baseline-snapshot.json').read_text());report['baseline_tests']=prior['baseline_tests']
            report['baseline_reuse']={'directory':str(baseline_from),'run_sha256':sha(baseline_from/'run.json'),'executed_here':False,
              'reason':'Same pristine U1 baseline recipe, inputs and kernel. Only the registered-build loading order changed.'}
            save(out/'baseline-reference.json',{'run':prior,'commands':json.loads((baseline_from/'commands.json').read_text())})
        with Unit(source,out/'proposal'):
            build('registered-build',registered=True);registered=fasls();save(out/'registered-fasls.json',registered)
            if registered.keys()!=baseline.keys():raise ValueError('native FASL set changed')
            changed=[n for n in baseline if baseline[n]!=registered[n]]
            if set(changed)!={'bin/systems.dx64fsl','bin/compile-ccl.dx64fsl'}:raise ValueError('unexpected FASL changes '+repr(changed))
            for n in changed:shutil.copy(source/n,out/('registered-'+Path(n).name))
            after=snapshot('registered-snapshot',True)
            for key in ('native','architectures','targets'):
                if before[key]!=after[key]:raise ValueError('R6a/native state differs: '+key)
            added={'CCL::WASM32-ARCH','CCL::WASM32-BACKEND','CCL::XWASM32FASLOAD'}
            if [r for r in after['modules'] if r['name'] not in added]!=before['modules']:raise ValueError('existing system entries differ')
            if {r['name'] for r in after['modules']}-{r['name'] for r in before['modules']}!=added:raise ValueError('added system entries differ')
            old={r['name']:r for r in before['shared_functions']};new={r['name']:r for r in after['shared_functions']}
            if old.keys()!=new.keys():raise ValueError('shared function set changed')
            code_changed=[n for n in old if old[n]!=new[n]]
            if set(code_changed)!={'CCL::TARGET-COMPILER-MODULES','CCL::TARGET-XLOAD-MODULES'}:raise ValueError('unexplained executable component '+repr(code_changed))
            report['r6']={'native_fasls':164,'identical':162,'intentional_artifacts':changed,'changed_code_functions':code_changed,'unchanged_code_functions':len(old)-2,'existing_architectures':len(after['architectures']),'existing_target_module_profiles':len(after['targets']),'native_state_equal':True}
            with tarfile.open(out/'baseline-fasls.tar.gz') as t:
                for name,fn in [('compile-ccl',compare_compiler),('systems',compare_systems)]:
                    original=t.extractfile('bin/'+name+'.dx64fsl').read()
                    with tarfile.open(inputs/'source.tar') as src:
                        before_text=src.extractfile('lib/'+name+'.lisp').read().decode()
                    comparison=fn(original,(out/('registered-'+name+'.dx64fsl')).read_bytes(),before_text,(source/('lib/'+name+'.lisp')).read_text())
                    save(out/(name+'-comparison.json'),comparison)
            shutil.copy(source/'dx86cl64.image',out/'registered.image')
            report['registered_tests']=tests('registered-tests',True)
            lisp('target',loads=[HERE/'load.lisp',HERE/'smoke.lisp'],marker='S1-TARGET-PASS',extra={'S1_OUTPUT':str(out)+'/'})
            command('wasm-execution',[sys.executable,HERE/'execute.py','--output',out],marker='S1-WASM-PASS')
        for n in ('wasm32-arch','wasm32-backend','xwasm32fasload'):(source/'bin'/(n+'.dx64fsl')).unlink(missing_ok=True)
        build('restored-build');restored=fasls();save(out/'restored-fasls.json',restored)
        if baseline!=restored:raise ValueError('restored FASLs differ')
        report['restored_fasls']=164;report['status']='PASS'
    except BaseException as e:report['failure']=str(e);(out/'failure.log').write_text(traceback.format_exc())
    finally:
        changed=[n for n,h in originals.items() if not (source/n).exists() or sha(source/n)!=h]
        report['source_restored']=not changed
        if changed:report.update(status='FAIL',source_changes=changed)
        save(out/'run.json',report)
    print(json.dumps(report.get('r6',report.get('failure'))),flush=True)
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('inputs','kernel','work','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--baseline-from',type=Path)
    a=p.parse_args();sys.exit(run(a.inputs.resolve(),a.kernel.resolve(),a.work.resolve(),a.output.resolve(),a.baseline_from.resolve() if a.baseline_from else None))
