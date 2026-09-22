"""Retain the condition/FFI delta and replay from an arbitrary checkout."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];EVIDENCE=ROOT.parent/'ccl-evidence'
sys.path.insert(0,str(HERE));import backend
spec=importlib.util.spec_from_file_location('introspection_packet',HERE.parent/'bootstrap-introspection/packet.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
sha,read,save,files=base.sha,base.read,base.save,base.files
PARENT=EVIDENCE/'2026-09-22-stage1-bootstrap-introspection-r1'
ID='STAGE1-BOOTSTRAP-CONDITION-FRONTIER-R1'
def pins():
    return {**base.pins(),**{str(p.relative_to(ROOT)):sha(p) for p in files(HERE)}}
def dependencies():
    return {**base.dependencies(),**{str((PARENT/n).relative_to(EVIDENCE)):sha(PARENT/n) for n in ('packet.json','artifacts.tar.gz','deterministic.json')}}
def source_check(numeric,native):
    for p in files(HERE):
        name=p.name
        if p.suffix=='.lisp' and name not in ('constructor.lisp','readers.lisp','keywords.lisp','immediates.lisp','environment-witness.lisp','entry.lisp','setup.lisp','measure.lisp'):
            copy=numeric/('compiled/source' if name=='compile.lisp' else 'driver')/name
            if copy.exists():assert copy.read_bytes()==p.read_bytes(),name
    for name in ('check.mjs','install.mjs','gf-check.mjs','installer-check.mjs','metadata-check.mjs'):
        assert (numeric/name).read_bytes()==(HERE/name).read_bytes(),name
    report=read(native/'run.json')
    assert report['status']=='PASS' and report['registered_tests']['passed']==21843
    assert report['restored_fasls']==164 and report['source_restored'] and report['r6']['identical']==140
    for name,text in {backend.BACKEND:backend.generate(),backend.ARCH:backend.arch(),**backend.source_files(ROOT)}.items():
        assert (native/'proposal/files'/name).read_text()==text,name
        assert (numeric/'compiled/proposal/files'/name).read_text()==text,name
    for p in (ROOT/'runtime/wasm32').glob('*.mjs'):
        assert (numeric/'runtime'/p.name).read_bytes()==p.read_bytes(),p.name

def reports(environment,numeric):
    import frontier,exclusions
    frontier.report(environment,numeric);exclusions.report(environment,numeric)

def deterministic(environment,numeric):
    result=base.deterministic(environment,numeric)
    for name in ('condition-class-proof.json','condition-controls.json','ffi-exclusions.json'):
        result['numeric/'+name]=sha(numeric/name)
    result['environment/target-exclusions.json']=sha(environment/'target-exclusions.json')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=('retain','verify'))
    for name in ('packet','environment','numeric','native','output'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();packet=a.packet.resolve()
    if a.mode=='retain':
        environment=a.environment.resolve();numeric=a.numeric.resolve();native=a.native.resolve()
        reports(environment,numeric);source_check(numeric,native)
        assert read(environment/'summary.json')['status']=='PASS' and read(numeric/'numeric-execution.json')['status']=='PASS'
        expected=deterministic(environment,numeric);previous=read(PARENT/'deterministic.json')
        retained={k:v for k,v in expected.items() if previous.get(k)!=v}
        reused={k:v for k,v in expected.items() if previous.get(k)==v}
        packet.mkdir()
        for name,value in [('source-pins',pins()),('dependencies',dependencies()),('tools',base.parent.parent.base.tools()),('deterministic',expected),('reused',reused)]:save(packet/(name+'.json'),value)
        for source,name in [(environment/'summary.json','recount.json'),(numeric/'numeric-execution.json','execution.json'),(environment/'cohort-changes.json','cohort-changes.json')]:shutil.copyfile(source,packet/name)
        with tarfile.open(packet/'artifacts.tar.gz','w:gz',dereference=True) as archive:
            for name,digest in retained.items():
                group,relative=name.split('/',1);path=(environment if group=='environment' else numeric)/relative
                assert sha(path)==digest;archive.add(path,arcname=name,recursive=False)
        base.parent.parent.copy_native(native,packet/'native')
        shutil.copytree(HERE,packet/'source',ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(packet/'development.tar.gz','w:gz') as archive:
            for relative in read(HERE/'development.json')['retained']:
                path=Path('/tmp')/relative;assert path.is_file(),path
                archive.add(path,arcname=relative,recursive=False)
        save(packet/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',reused_files=len(reused),retained_files=len(retained),files=[dict(path=str(p.relative_to(packet)),sha256=sha(p),bytes=p.stat().st_size) for p in files(packet)]))
    else:
        assert pins()==read(packet/'source-pins.json'),'source pins'
        assert dependencies()==read(packet/'dependencies.json'),'dependencies'
        assert base.parent.parent.base.tools()==read(packet/'tools.json'),'tools'
        entries=read(packet/'packet.json')['files']
        assert {r['path'] for r in entries}=={str(p.relative_to(packet)) for p in files(packet) if p.name!='packet.json'}
        for row in entries:assert sha(packet/row['path'])==row['sha256'],row['path']
        expected=read(packet/'deterministic.json');reused=read(packet/'reused.json');previous=read(PARENT/'deterministic.json')
        assert all(previous.get(k)==v==expected[k] for k,v in reused.items())
        with tarfile.open(packet/'artifacts.tar.gz') as archive:
            assert set(archive.getnames())==expected.keys()-reused.keys()
            for entry in archive:
                assert entry.isfile() and hashlib.sha256(archive.extractfile(entry).read()).hexdigest()==expected[entry.name]
        out=a.output.resolve();out.mkdir();environment=out/'environment';numeric=out/'numeric'
        subprocess.run([sys.executable,HERE/'run.py',environment],check=True)
        subprocess.run([sys.executable,HERE/'numeric.py',numeric],check=True)
        subprocess.run([sys.executable,HERE/'faults.py',numeric],check=True)
        reports(environment,numeric);source_check(numeric,packet/'native')
        actual=deterministic(environment,numeric)
        assert actual==expected,sorted(k for k in actual.keys()|expected.keys() if actual.get(k)!=expected.get(k))
        save(out/'verification.json',dict(status='PASS',deterministic_files=len(actual),reused_files=len(reused),source_pins=len(pins()),recount=read(environment/'summary.json'),execution=read(numeric/'numeric-execution.json'),native_reused_by_final_source_hash=True))
if __name__=='__main__':main()
