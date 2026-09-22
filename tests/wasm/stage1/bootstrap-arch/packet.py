"""Retain and replay the arch-macro recount and whole-file execution."""
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys, tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3];EVIDENCE=ROOT.parent/'ccl-evidence'
sys.path.insert(0,str(HERE))
import backend
spec=importlib.util.spec_from_file_location('environment_packet',HERE.parent/'bootstrap-file-environments/packet.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
sha,read,files,save=parent.sha,parent.read,parent.files,parent.save
ID='STAGE1-BOOTSTRAP-ARCH-R1'

def pins():
    result=parent.pins()
    result.update({str(p.relative_to(ROOT)):sha(p) for p in files(HERE)})
    return result

def dependencies():
    result=parent.dependencies()
    for name in ('packet.json','artifacts.tar.gz','recount.json','execution.json'):
        path='2026-09-22-stage1-bootstrap-file-environments-r1/'+name
        result[path]=sha(EVIDENCE/path)
    return result

def source_check(numeric,native):
    for name in ('compile.lisp','cases.lisp','numeric-files.lisp','arch-probes.lisp','controls.lisp'):
        p=numeric/('compiled/source' if name=='compile.lisp' else 'driver')/name
        assert p.read_bytes()==(HERE/name).read_bytes(),name
    report=read(native/'run.json')
    assert report['status']=='PASS' and report['registered_tests']['passed']==21843
    assert report['restored_fasls']==164 and report['source_restored']
    assert report['r6']['native_state_equal'] and report['r6']['identical']==142
    expected={backend.BACKEND:backend.generate(),backend.ARCH:(ROOT/backend.ARCH).read_text()+'\n'+(HERE/'arch-macros.lisp').read_text(),**backend.source_files(ROOT)}
    for name,text in expected.items():
        assert (native/'proposal/files'/name).read_text()==text,name
        assert (numeric/'compiled/proposal/files'/name).read_text()==text,name

def deterministic(environment,numeric):
    result=parent.deterministic(environment,numeric)
    result['numeric/numeric-execution.json']=sha(numeric/'numeric-execution.json')
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=('retain','verify'))
    for name in ('packet','environment','numeric','native','output'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args();packet=args.packet.resolve()
    if args.mode=='retain':
        environment=args.environment.resolve();numeric=args.numeric.resolve();native=args.native.resolve()
        source_check(numeric,native)
        assert read(environment/'summary.json')['status']=='PASS'
        assert read(numeric/'numeric-execution.json')['status']=='PASS'
        packet.mkdir();records=deterministic(environment,numeric)
        for name,value in [('source-pins',pins()),('dependencies',dependencies()),('tools',parent.parent.base.tools()),('deterministic',records)]:save(packet/(name+'.json'),value)
        for source,name in [(environment/'summary.json','recount.json'),(numeric/'numeric-execution.json','execution.json'),(environment/'cohort-changes.json','cohort-changes.json')]:shutil.copyfile(source,packet/name)
        with tarfile.open(packet/'artifacts.tar.gz','w:gz') as archive:
            for name,digest in records.items():
                group,relative=name.split('/',1)
                p=(environment if group=='environment' else numeric)/relative
                assert sha(p)==digest;archive.add(p,arcname=name,recursive=False)
        parent.parent.copy_native(native,packet/'native')
        shutil.copytree(HERE,packet/'source',ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(packet/'development.tar.gz','w:gz') as archive:
            for name in read(HERE/'development.json')['retained']:
                p=Path('/tmp')/name;assert p.is_file(),p
                archive.add(p,arcname=name,recursive=False)
        save(packet/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(p.relative_to(packet)),sha256=sha(p),bytes=p.stat().st_size) for p in files(packet)]))
    else:
        assert pins()==read(packet/'source-pins.json'),'source pins'
        assert dependencies()==read(packet/'dependencies.json'),'dependencies'
        assert parent.parent.base.tools()==read(packet/'tools.json'),'tools'
        entries=read(packet/'packet.json')['files']
        assert {r['path'] for r in entries}=={str(p.relative_to(packet)) for p in files(packet) if p.name!='packet.json'}
        for row in entries:assert sha(packet/row['path'])==row['sha256'],row['path']
        expected=read(packet/'deterministic.json')
        with tarfile.open(packet/'artifacts.tar.gz') as archive:
            assert set(archive.getnames())==set(expected)
            for entry in archive:
                assert entry.isfile()
                assert hashlib.sha256(archive.extractfile(entry).read()).hexdigest()==expected[entry.name]
        out=args.output.resolve();out.mkdir()
        environment=out/'environment';numeric=out/'numeric'
        subprocess.run([sys.executable,HERE/'run.py',environment],check=True)
        subprocess.run([sys.executable,HERE/'numeric.py',numeric],check=True)
        source_check(numeric,packet/'native')
        actual=deterministic(environment,numeric)
        assert actual==expected,sorted(k for k in actual.keys()|expected.keys() if actual.get(k)!=expected.get(k))
        save(out/'verification.json',dict(status='PASS',deterministic_files=len(actual),source_pins=len(pins()),recount=read(environment/'summary.json'),execution=read(numeric/'numeric-execution.json'),native_reused_by_final_source_hash=True))

if __name__=='__main__':main()
