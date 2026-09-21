"""Replay the new execution work; reuse the unchanged source-reader qualification."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
import run as r
from backend import generate,source_files
PARENT=r.HERE.parent/'bootstrap-library'
spec=importlib.util.spec_from_file_location('library_packet',PARENT/'packet.py')
prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
sha=prior.sha;read=prior.read;files=prior.files;deterministic=prior.deterministic
ID='STAGE1-BOOTSTRAP-DIVISION-R1'
LIBRARY='2026-09-21-stage1-bootstrap-library-r1'

def pins():
    result=prior.pins()
    result.update({str(p.relative_to(r.ROOT)):sha(p) for p in PARENT.iterdir() if p.is_file()})
    result.update({str(p.relative_to(r.ROOT)):sha(p) for p in (r.HERE.parent/'bootstrap-execution').iterdir() if p.is_file()})
    return result

def dependencies():
    result=prior.dependencies()
    previous='2026-09-21-stage1-bootstrap-execution-r2/packet.json'
    result[previous]=sha(r.EVIDENCE/previous)
    for name in ['packet.json','native/run.json','native/registered-fasls.json','native/registered-snapshot.json','readers/readers.json','readers/summary.json']:
        path=LIBRARY+'/'+name;result[path]=sha(r.EVIDENCE/path)
    return result

def native_check(n):
    prior.assert_native(n)
    reference=r.EVIDENCE/LIBRARY/'native'
    x=read(n/'run.json')
    assert not x['registered_tests_reuse']['executed_here']
    assert x['registered_tests_reuse']['run_sha256']==sha(reference/'run.json')
    assert read(n/'registered-fasls.json')==read(reference/'registered-fasls.json')
    assert read(n/'registered-snapshot.json')==read(reference/'registered-snapshot.json')
    for name,text in source_files(r.ROOT).items():
        assert text==(reference/'proposal/files'/name).read_text(),name
    assert sha(n/'proposal/files/compiler/WASM32/wasm32-backend.lisp')==hashlib.sha256(generate().encode()).hexdigest()

def assert_source_copies(out):
    # Compare the exact copies the compiler consumed, not just today's pins.
    for name in ['compile.lisp','cases.lisp','execute.lisp','probes.lisp','controls.lisp','whole-file.lisp']:
        source=r.fixture(name)
        copied=out/('compiled/source' if name=='compile.lisp' else 'driver')/name
        assert copied.read_bytes()==source.read_bytes(), 'stale compiled source: '+name

def main():
    a=argparse.ArgumentParser();a.add_argument('mode',choices=['retain','verify'])
    for n in ['packet','execution','native-run','output']:a.add_argument('--'+n,type=Path)
    args=a.parse_args();p=args.packet.resolve()
    if args.mode=='retain':
        out=args.execution.resolve();n=args.native_run.resolve();native_check(n)
        assert read(out/'summary.json')['status']=='PASS'
        assert_source_copies(out)
        p.mkdir()
        for name,data in [('source-pins',pins()),('dependencies',dependencies()),('tools',prior.tools()),('deterministic',deterministic(out))]:r.save(p/(name+'.json'),data)
        for f in files(out):
            rel=f.relative_to(out)
            if prior.keep(rel):
                d=p/'execution'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,d)
        omitted={}
        for f in files(n):
            rel=f.relative_to(n)
            if f.name in ['baseline.image','baseline-fasls.tar.gz','registered.image']:
                omitted[str(rel)]=sha(f);continue
            d=p/'native'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,d)
        r.save(p/'omitted-images.json',omitted)
        r.save(p/'native-reuse.json',dict(reference=LIBRARY,readers_reexecuted=False,tests_reexecuted=False,
            reason='Source forms unchanged from audit 146; all freshly rebuilt native FASLs and snapshot equal the passing library qualification. Compiler is new and all target cases execute.'))
        shutil.copytree(r.HERE,p/'source',ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copy(r.HERE/'README.md',p/'README.md')
        with tarfile.open(p/'development.tar.gz','w:gz') as tar:
            for f in read(r.HERE/'development.json')['retained']:tar.add('/tmp/'+f,arcname=f,recursive=False)
        r.save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p)]))
    else:
        assert pins()==read(p/'source-pins.json'),'source pins'
        assert dependencies()==read(p/'dependencies.json'),'dependencies'
        assert prior.tools()==read(p/'tools.json'),'tools'
        listed=read(p/'packet.json')['files']
        assert {x['path'] for x in listed}=={str(f.relative_to(p)) for f in files(p) if f.name!='packet.json'}
        for row in listed:assert sha(p/row['path'])==row['sha256'],row['path']
        native_check(p/'native')
        out=args.output.resolve();r.run(out)
        actual=deterministic(out);expected=read(p/'deterministic.json')
        assert actual==expected,sorted(k for k in actual.keys()|expected.keys() if actual.get(k)!=expected.get(k))
        result=dict(status='PASS',deterministic_files=len(actual),source_pins=len(pins()),summary=read(out/'summary.json'))
        r.save(out/'verification.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
