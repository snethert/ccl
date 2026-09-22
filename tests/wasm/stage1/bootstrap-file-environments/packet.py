"""Retain compact, replayable file-environment and numeric execution evidence."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3];EVIDENCE=ROOT.parent/'ccl-evidence'
sys.path.insert(0,str(HERE.parent/'bootstrap-recipes'))
spec=importlib.util.spec_from_file_location('recipe_packet',HERE.parent/'bootstrap-recipes/packet.py')
parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
sha,read=parent.sha,parent.read
ID='STAGE1-BOOTSTRAP-FILE-ENVIRONMENTS-R1'
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def files(p):return sorted(f for f in p.rglob('*') if f.is_file() and '__pycache__' not in f.parts)
def pins():
    result=parent.pins()
    result.update({str(p.relative_to(ROOT)):sha(p) for p in files(HERE)})
    return result

def dependencies():
    result=parent.dependencies()
    base='2026-09-21-stage1-bootstrap-recipes-r1/'
    for name in ['packet.json','execution/execution-frontier.json','execution/compiled/throughput.json','execution/compiled/worklist-throughput.json']:
        result[base+name]=sha(EVIDENCE/(base+name))
    return result

def environment_files(out):
    names=['worklist.json','results.json','summary.json','cohort-changes.json','additional-definitions.json','audit156-cohort.json','controls.json','inputs.json']
    result={n:sha(out/n) for n in names}
    # Keep a digest for every emitted module; retain the requested numeric
    # modules themselves. Do not duplicate 700 MB of repetitive WAT helpers.
    modules={str(p.relative_to(out)):sha(p) for p in sorted((out/'files').rglob('*.wat'))}
    save(out/'module-digests.json',modules);result['module-digests.json']=sha(out/'module-digests.json')
    for directory in ('controls','files/l0-numbers','files/l0-float','files/l0-bignum32'):
        for p in files(out/directory):
            if p.suffix in ('.json','.wat','.wasm'):result[str(p.relative_to(out))]=sha(p)
    return result

def deterministic(environment,numeric):
    return {**{'environment/'+k:v for k,v in environment_files(environment).items()},
            **{'numeric/'+k:v for k,v in parent.base.deterministic(numeric).items()}}

def source_check(numeric):
    for name in ['compile.lisp','cases.lisp','numeric-files.lisp']:
        p=numeric/('compiled/source' if name=='compile.lisp' else 'driver')/name
        assert p.read_bytes()==(HERE/name).read_bytes(),name
    parent.native_check(EVIDENCE/'2026-09-21-stage1-bootstrap-closure-r1/native')

def main():
    a=argparse.ArgumentParser();a.add_argument('mode',choices=('retain','verify'));a.add_argument('--packet',type=Path,required=True)
    a.add_argument('--environment',type=Path);a.add_argument('--numeric',type=Path);a.add_argument('--output',type=Path)
    args=a.parse_args();p=args.packet.resolve()
    if args.mode=='retain':
        env=args.environment.resolve();numeric=args.numeric.resolve();source_check(numeric)
        assert read(env/'summary.json')['status']=='PASS' and read(numeric/'numeric-execution.json')['status']=='PASS'
        p.mkdir();records=deterministic(env,numeric)
        for name,x in [('source-pins',pins()),('dependencies',dependencies()),('tools',parent.base.tools()),('deterministic',records)]:save(p/(name+'.json'),x)
        for source,name in [(env/'summary.json','recount.json'),(numeric/'numeric-execution.json','execution.json'),(env/'audit156-cohort.json','audit156-cohort.json'),(env/'cohort-changes.json','cohort-changes.json')]:shutil.copyfile(source,p/name)
        with tarfile.open(p/'artifacts.tar.gz','w:gz') as archive:
            for name,digest in records.items():
                group,relative=name.split('/',1);f=(env if group=='environment' else numeric)/relative
                assert sha(f)==digest;archive.add(f,arcname=name,recursive=False)
        shutil.copytree(HERE,p/'source',ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(p/'development.tar.gz','w:gz') as archive:
            for name in read(HERE/'development.json')['retained']:
                f=Path('/tmp')/name;assert f.is_file(),f;archive.add(f,arcname=name,recursive=False)
        save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p)]))
    else:
        assert pins()==read(p/'source-pins.json'),'source pins'
        assert dependencies()==read(p/'dependencies.json'),'dependencies'
        assert parent.base.tools()==read(p/'tools.json'),'tools'
        entries=read(p/'packet.json')['files'];assert {e['path'] for e in entries}=={str(f.relative_to(p)) for f in files(p) if f.name!='packet.json'}
        for e in entries:assert sha(p/e['path'])==e['sha256'],e['path']
        expected=read(p/'deterministic.json')
        with tarfile.open(p/'artifacts.tar.gz') as archive:
            assert set(archive.getnames())==set(expected)
            for entry in archive:
                assert entry.isfile()
                assert hashlib.sha256(archive.extractfile(entry).read()).hexdigest()==expected[entry.name],entry.name
        out=args.output.resolve();out.mkdir();env=out/'environment';numeric=out/'numeric'
        subprocess.run([sys.executable,HERE/'run.py',env],check=True)
        subprocess.run([sys.executable,HERE/'numeric.py',numeric],check=True)
        source_check(numeric)
        actual=deterministic(env,numeric)
        assert actual==expected,sorted(k for k in actual.keys()|expected.keys() if actual.get(k)!=expected.get(k))
        save(out/'verification.json',dict(status='PASS',deterministic_files=len(actual),source_pins=len(pins()),recount=read(env/'summary.json'),execution=read(numeric/'numeric-execution.json'),native_reused_by_final_source_hash=True))
if __name__=='__main__':main()
