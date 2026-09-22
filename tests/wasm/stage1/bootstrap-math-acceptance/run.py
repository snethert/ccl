"""Install and qualify the exact reviewed math R2 bytes."""
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[3]
FIXTURE=HERE.parent/'bootstrap-math'
PACKET=ROOT.parent/'ccl-evidence/2026-09-21-stage1-bootstrap-math-r2'
BACKEND='compiler/WASM32/wasm32-backend.lisp'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def files():
    proposal=PACKET/'execution/compiled/proposal'
    manifest=json.loads((proposal/'unit.json').read_text())
    result={}
    for row in manifest['added']+manifest['modified']:
        p=proposal/'files'/row['path'];assert sha(p)==row.get('sha256',row.get('after'))
        result[row['path']]=p
    for name in ('float.c','float-service.mjs'):
        result['runtime/wasm32/'+name]=PACKET/'execution/runtime'/name
    result['runtime/wasm32/transcend.c']=PACKET/'source/transcend.c'
    for p in (PACKET/'source/libm').rglob('*'):
        if p.is_file():result['runtime/wasm32/libm/'+str(p.relative_to(PACKET/'source/libm'))]=p
    return result

def proposal(src,dest):
    shutil.copytree(PACKET/'execution/compiled/proposal',dest)
    manifest=json.loads((dest/'unit.json').read_text())
    for row in manifest['added']+manifest['modified']:
        p=dest/'files'/row['path'];p.write_bytes((ROOT/row['path']).read_bytes())
        row['sha256' if 'sha256' in row else 'after']=sha(p)
    save(dest/'unit.json',manifest);return manifest

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('install','native','target'))
    p.add_argument('--output',type=Path,required=True);p.add_argument('--work',type=Path);p.add_argument('--resume-compiled',action='store_true')
    a=p.parse_args();out=a.output.resolve();expected=files()
    if a.mode=='install':
        out.mkdir();changes=[]
        for name,source in expected.items():
            target=ROOT/name;before=sha(target) if target.exists() else None
            target.parent.mkdir(parents=True,exist_ok=True)
            if before!=sha(source):
                shutil.copyfile(source,target);changes.append(dict(file=name,before=before,after=sha(target),reviewed=sha(source)))
        save(out/'changes.json',changes);return
    for name,source in expected.items():assert (ROOT/name).read_bytes()==source.read_bytes(),name
    sys.path.insert(0,str(FIXTURE));import backend
    backend.generate=lambda:(ROOT/BACKEND).read_text()
    backend.proposal=proposal
    backend.source_files=lambda src:{name:(ROOT/name).read_text() for name in expected if name.startswith(('level-0/','level-1/'))}
    if a.mode=='native':
        spec=importlib.util.spec_from_file_location('math_native',FIXTURE/'native.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        e=ROOT.parent/'ccl-evidence'
        assert m.m.driver.run(e/'macos-u1-inputs',e/'2026-09-12-native-census-r7/baseline/build/dx86cl64',a.work.resolve(),out,e/'2026-09-16-stage1-1a-r2/native')==0
        return
    import run
    if a.resume_compiled:
        for name in expected:
            if name.startswith(('compiler/','level-0/','level-1/')):
                assert (out/'compiled/proposal/files'/name).read_bytes()==(ROOT/name).read_bytes(),name
    else:
        run.compile_corpus(out);run.stable_reader_diagnostics(out)
    # Subprocesses import fresh modules. Give execution an explicit installed
    # build helper instead of relying on parent-only Python overrides.
    script=(FIXTURE/'execute.py').read_text()
    script=script.replace("h=Path(__file__).resolve().parent;r=h.parents[3];",f"h=Path({str(FIXTURE)!r});r=h.parents[3];")
    script=script.replace("h/'math-build.py'","r/'runtime/wasm32/build-float.py'")
    (out/'execute-installed.py').write_text(script)
    subprocess.run([sys.executable,out/'execute-installed.py',out],check=True)
    for name in ('checks.py','host-checks.py','faults.py','trap-control.py'):
        subprocess.run([sys.executable,FIXTURE/name,out],check=True)
    subprocess.run(['/usr/local/bin/node',FIXTURE/'math-check.mjs',out,out/'math-raw.json'],check=True)
    run.summarize(out)
    assert (out/'float.wasm').read_bytes()==(PACKET/'execution/float.wasm').read_bytes()
    matched=[]
    for path in sorted((out/'compiled').iterdir()):
        if path.suffix in ('.wat','.wasm','.legacy'):
            rel=path.relative_to(out);assert path.read_bytes()==(PACKET/'execution'/rel).read_bytes(),rel;matched.append(str(rel))
    for name in ('summary.json','execution.json','compiled/native.json','math-raw.json','trap-control.json','progress.json'):
        assert (out/name).read_bytes()==(PACKET/'execution'/name).read_bytes(),name;matched.append(name)
    owner=out/'owner-check';owner.mkdir()
    for path in (ROOT/'runtime/wasm32').glob('*.mjs'):shutil.copy(path,owner/path.name)
    shutil.copy(owner/'collector-owner.mjs',owner/'owner.mjs')
    shutil.copy(HERE.parent/'collector-owner/check.mjs',owner/'check.mjs')
    with (owner/'run.log').open('w') as log:subprocess.run(['/usr/local/bin/node',owner/'check.mjs',out/'collector.wasm',owner/'results.json'],stdout=log,stderr=log,check=True)
    checks=json.loads((owner/'results.json').read_text());assert checks['checks']==40 and checks['status']=='PASS'
    save(out/'integration.json',dict(status='PASS',identical_files=matched,owner_checks=40,float_binary=sha(out/'float.wasm'),files={name:sha(ROOT/name) for name in expected},scope='Exact reviewed bytes; production libm build reproduces reviewed binary; 40 collector-owner checks plus generated floating composition. No new execution credit.'))
if __name__=='__main__':main()
