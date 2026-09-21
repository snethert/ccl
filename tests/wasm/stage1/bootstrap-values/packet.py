import argparse, hashlib, json, shutil, subprocess, sys, tarfile
from pathlib import Path
import run as r
from backend import generate
ID='STAGE1-BOOTSTRAP-VALUES-R1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
def files(root):
    return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
def pins():
    paths=set(p for p in r.HERE.iterdir() if p.is_file())
    for d in ['level-0','level-1']:
        paths.update((r.ROOT/d).glob('*.lisp'))
    for d in ['tests/wasm/stage1/constants','tests/wasm/stage1/registration']:
        paths.update(p for p in (r.ROOT/d).iterdir() if p.is_file())
    paths.update(r.ROOT/p for p in ['compiler/WASM32/wasm32-backend.lisp','compiler/WASM32/wasm32-arch.lisp',
        'runtime/wasm32/collector.c','doc/WASM/contracts/wasm32-layout.v1.json',
        'compiler/nx1.lisp','compiler/X86/x862.lisp',
        'tests/wasm/native-census/observer.lisp','tests/wasm/native-baseline/tests.lisp'])
    return {str(p.relative_to(r.ROOT)):sha(p) for p in sorted(paths)}
def tools():
    return {str(p):sha(p) for p in map(Path,['/usr/local/bin/node','/usr/local/bin/wat2wasm','/usr/local/opt/llvm/bin/clang'])}
def keep(path):
    return path.parts[0] not in ('driver','baseline-driver','measure-driver','fault-driver') and path.name!='command.json'
def deterministic(root):
    return {str(p.relative_to(root)):sha(p) for p in files(root) if keep(p.relative_to(root))
            and p.suffix in ('.json','.wasm','.wat','.lisp','.legacy','.mjs','.c','.dx64fsl')}
def assert_native(root):
    x=read(root/'run.json')
    assert x['status']=='PASS' and x['registered_tests']['passed']==21843
    assert x['r6']['identical']==162 and x['restored_fasls']==164 and x['source_restored']
    assert sha(root/'proposal/files/compiler/WASM32/wasm32-backend.lisp')==hashlib.sha256(generate().encode()).hexdigest()
def manifest(root):
    r.save(root/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',
        files=[dict(path=str(p.relative_to(root)),sha256=sha(p),bytes=p.stat().st_size)
               for p in files(root) if p.name!='packet.json']))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['retain','verify'])
    for n in ('packet','execution','native-run','output'):parser.add_argument('--'+n,type=Path)
    parser.add_argument('--native',action='store_true');a=parser.parse_args();p=a.packet.resolve()
    if a.mode=='retain':
        x=a.execution.resolve();n=a.native_run.resolve();assert_native(n)
        assert read(x/'summary.json')['status']=='PASS'
        p.mkdir();r.save(p/'source-pins.json',pins());r.save(p/'tools.json',tools())
        r.save(p/'deterministic.json',deterministic(x))
        for f in files(x):
            rel=f.relative_to(x)
            if keep(rel):
                dst=p/'execution'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dst)
        reused={}
        for f in files(n):
            rel=f.relative_to(n)
            if f.name in ('baseline.image','baseline-fasls.tar.gz'):
                reused[str(rel)]=sha(f);continue
            dst=p/'native'/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dst)
        r.save(p/'native-reused.json',reused)
        for name in ('README.md','development.json'):shutil.copy(r.HERE/name,p/name)
        with tarfile.open(p/'sources.tar.gz','w:gz') as tar:
            for name in pins():tar.add(r.ROOT/name,arcname=name,recursive=False)
        with tarfile.open(p/'development.tar.gz','w:gz') as tar:
            for name in read(r.HERE/'development.json')['retained']:
                tar.add(Path('/tmp')/name,arcname=name,recursive=False)
        manifest(p)
    else:
        assert pins()==read(p/'source-pins.json') and tools()==read(p/'tools.json')
        for row in read(p/'packet.json')['files']:assert sha(p/row['path'])==row['sha256'],row['path']
        assert_native(p/'native')
        out=a.output.resolve();r.run(out)
        actual=deterministic(out);expected=read(p/'deterministic.json')
        assert actual==expected, sorted(k for k in actual.keys()|expected.keys() if actual.get(k)!=expected.get(k))
        if a.native:
            n=out/'native-replay'
            subprocess.run([sys.executable,r.HERE/'native.py','--evidence',r.EVIDENCE,'--work',out/'native-work','--output',n],check=True)
            assert_native(n)
        result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(pins()),summary=read(out/'summary.json'),native_rebuilt=a.native)
        r.save(out/'verification.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
