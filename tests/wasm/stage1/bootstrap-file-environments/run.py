"""Recount definitions in fresh CCL file-compiler environments."""
import argparse, hashlib, importlib.util, json, os, shutil, subprocess, sys, tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
EVIDENCE=ROOT.parent/'ccl-evidence'
sys.path.insert(0,str(HERE.parent/'bootstrap-recipes'))
import backend
sys.path.insert(0,str(HERE.parent/'registration'))
from unit import Unit,sha,save

def run(out,selected=None):
    out=out.resolve();out.mkdir()
    work=out/'work';src=work/'ccl';src.mkdir(parents=True)
    save(work/'stage1-disposable.json',{'source':str(src)})
    inputs=EVIDENCE/'macos-u1-inputs';pins=json.loads((inputs/'pins.json').read_text())
    for name in ('source.tar','bootstrap.tar.gz'):
        assert sha(inputs/name)==pins['inputs'][name]
        with tarfile.open(inputs/name) as archive:archive.extractall(src,filter='data')
    kernel=EVIDENCE/'2026-09-12-native-census-r7/baseline/build/dx86cl64'
    image=EVIDENCE/'2026-09-16-stage1-1a-r2/native/baseline.image'
    shutil.copy(kernel,src/'dx86cl64');(src/'dx86cl64').chmod(0o755)
    shutil.copy(image,src/'dx86cl64.image')
    backend.proposal(src,out/'proposal')
    env=dict(PATH='/usr/local/bin:/usr/bin:/bin',LANG='C',LC_ALL='C',CCL_DEFAULT_DIRECTORY=str(src),RECOUNT_OUTPUT=str(out)+'/')
    with Unit(src,out/'proposal'):
        cmd=[str(src/'dx86cl64'),'--no-init','--batch','--eval','(ccl::in-development-mode (load "ccl:lib;systems.lisp") (load "ccl:lib;compile-ccl.lisp"))','--load',str(HERE.parent/'registration/load.lisp'),'--load',str(HERE/'setup.lisp')]
        with (out/'setup.log').open('w') as log:
            subprocess.run(cmd,cwd=src,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=120)
        paths=json.loads((out/'worklist.json').read_text())
        assert len(paths)==57
        if selected:paths=[p for p in paths if Path(p).stem in selected]
        rows=[]
        for index,path in enumerate(paths):
            dest=out/'files'/Path(path).stem;dest.mkdir(parents=True)
            cmd=[str(src/'dx86cl64'),'-I',str(out/'compiler.image'),'--no-init','--batch','--load',str(HERE/'entry.lisp')]
            with (dest/'compile.log').open('w') as log:
                result=subprocess.run(cmd,cwd=src,env={**env,'RECOUNT_FILE':path,'RECOUNT_FILE_OUTPUT':str(dest)+'/'},stdout=log,stderr=subprocess.STDOUT,timeout=60)
            if result.returncode or not (dest/'result.json').exists():raise RuntimeError(str(dest/'compile.log'))
            row=json.loads((dest/'result.json').read_text());rows.append(row)
            print(path,len(row['definitions']),sum(r['outcome']=='ADMITTED' for r in row['definitions']),row['complete'],row['failure'],flush=True)
        save(out/'results.json',rows)
        controls=[]
        for omitted in (False,True):
            dest=out/'controls'/('omitted' if omitted else 'file');dest.mkdir(parents=True)
            cmd=[str(src/'dx86cl64'),'-I',str(out/'compiler.image'),'--no-init','--batch']
            if omitted:cmd+=['--eval',"(push :omit-file-environment *features*)"]
            cmd+=['--load',str(HERE/'entry.lisp')]
            with (dest/'compile.log').open('w') as log:
                subprocess.run(cmd,cwd=src,env={**env,'RECOUNT_FILE':str(HERE/'environment-witness.lisp'),'RECOUNT_FILE_OUTPUT':str(dest)+'/'},stdout=log,stderr=subprocess.STDOUT,check=True,timeout=30)
            controls.append(json.loads((dest/'result.json').read_text()))
        real={r['name']:r for r in controls[0]['records']}
        missing={r['name']:r for r in controls[1]['records']}
        assert controls[0]['complete'] and controls[1]['complete']
        assert real['RECOUNT-MACRO']['outcome']=='ADMITTED' and not real['RECOUNT-MACRO']['dependencies']
        assert 'RECOUNT-LOCAL' in missing['RECOUNT-MACRO']['dependencies']
        assert 'RECOUNT-WORD-BYTES' not in real['RECOUNT-SYMBOL']['symbols']
        assert 'RECOUNT-WORD-BYTES' in missing['RECOUNT-SYMBOL']['symbols']
        assert 'NUMBER-CASE' in real['RECOUNT-NUMBER']['macros']
        assert 'NUMBER-CASE' in missing['RECOUNT-NUMBER']['dependencies']
        assert real['RECOUNT-EMPTY']['outcome']=='BOOTSTRAP-EMPTY-TARGET-BODY'
        assert real['RECOUNT-SELF']['outcome']=='BOOTSTRAP-SELF-ONLY-BODY'
        save(out/'controls.json',dict(status='PASS',omitted_environment_rejected=['function-macro','symbol-macro','required-macro'],body_refusals=['empty-target','self-call-only']))

    spec=importlib.util.spec_from_file_location("file_report",HERE/"report.py")
    report=importlib.util.module_from_spec(spec);spec.loader.exec_module(report)
    report.report(out)
    save(out/'inputs.json',dict(kernel=sha(kernel),image=sha(image),source=pins['inputs']['source.tar'],compiler=sha(out/'proposal/files'/backend.BACKEND)))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--files',nargs='+');a=p.parse_args();run(a.output,a.files)
