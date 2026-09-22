"""Retain the next execution proposal over the accepted math integration."""
import argparse, importlib.util, json, shutil, tarfile
from pathlib import Path
import backend, run as r
spec=importlib.util.spec_from_file_location('base_packet',r.HERE.parent/'bootstrap-library/packet.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
sha,read,files=base.sha,base.read,base.files
ID='STAGE1-BOOTSTRAP-RECIPES-R1'
def pins():
    x=base.pins()
    for directory in (r.HERE,r.ROOT/'runtime/wasm32/libm'):
        for p in files(directory):x[str(p.relative_to(r.ROOT))]=sha(p)
    for name in ('bootstrap-admission/native.py','bootstrap-admission/sources.py','bootstrap-admission/foreign.py','bootstrap-library/packet.py','float-core/execute.mjs'):
        p=r.HERE.parent/name;x[str(p.relative_to(r.ROOT))]=sha(p)
    for name in ('doc/WASM/tools/r6_registration.py','compiler/X86/X8632/x8632-arch.lisp'):
        x[name]=sha(r.ROOT/name)
    return x

def dependencies():
    x=base.dependencies()
    for p in files(backend.PACKET):x[str(p.relative_to(r.EVIDENCE))]=sha(p)
    for directory,names in [
        ('2026-09-21-stage1-bootstrap-math-r2',['packet.json','native/run.json']),
        ('2026-09-21-stage1-bootstrap-closure-r1',['packet.json','native/run.json','execution/execution-frontier.json']),
        ('2026-09-19-stage1-float-core-r2',['packet.json','execution/cases.json']),
        ('2026-09-21-stage1-bootstrap-carry-r1',['execution/compiled/native.json'])]:
        for name in names:x[directory+'/'+name]=sha(r.EVIDENCE/directory/name)
    return x

def native_check(n):
    x=read(n/'run.json');assert x['status']=='PASS' and x['registered_tests']['passed']==21843
    assert x['r6']['identical']==144 and x['restored_fasls']==164 and x['source_restored'] and x['r6']['native_state_equal']
    assert (n/'proposal/files'/backend.BACKEND).read_text()==backend.generate()
    for name,text in backend.source_files(r.ROOT).items():assert (n/'proposal/files'/name).read_text()==text,name

def source_check(out):
    for name in ('compile.lisp','cases.lisp','execute.lisp','probes.lisp','controls.lisp','whole-file.lisp','witnesses.lisp','inputs.lisp','foreign-scan.lisp','w32-os.lisp','os-probes.lisp','closure-controls.lisp','observers.lisp'):
        p=out/('compiled/source' if name=='compile.lisp' else 'driver')/name
        assert p.read_bytes()==r.fixture(name).read_bytes(),name
    for name in ('check.mjs','install.mjs'):assert (out/name).read_bytes()==(r.HERE/name).read_bytes(),name

def copy_native(src,dest):
    omitted={}
    for f in files(src):
        rel=f.relative_to(src)
        if f.name in ('baseline.image','baseline-fasls.tar.gz','registered.image'):
            omitted[str(rel)]=sha(f);continue
        p=dest/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,p)
    r.save(dest/'omitted-images.json',omitted)

def main():
    a=argparse.ArgumentParser();a.add_argument('mode',choices=('retain','verify'))
    for n in ('packet','execution','native-run','output'):a.add_argument('--'+n,type=Path)
    args=a.parse_args();p=args.packet.resolve()
    if args.mode=='retain':
        out=args.execution.resolve();n=r.EVIDENCE/'2026-09-21-stage1-bootstrap-closure-r1/native';native_check(n);source_check(out)
        assert read(out/'summary.json')['status']=='PASS';p.mkdir()
        for name,value in [('source-pins',pins()),('dependencies',dependencies()),('tools',base.tools()),('deterministic',base.deterministic(out))]:r.save(p/(name+'.json'),value)
        for f in files(out):
            rel=f.relative_to(out)
            if base.keep(rel):
                dest=p/'execution'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(f,dest)
        r.save(p/'native-reuse.json',dict(source=str(n.relative_to(r.EVIDENCE)),sha256=sha(n/'run.json'),reason='Compiler, runtime and CCL source unchanged from closure proposal. Only recipes and file-compilation environments change.'));shutil.copytree(r.HERE,p/'source',ignore=shutil.ignore_patterns('__pycache__'))
        with tarfile.open(p/'development.tar.gz','w:gz') as archive:
            for name in read(r.HERE/'development.json')['retained']:
                source=Path('/tmp')/name;assert source.is_file(),source
                archive.add(source,arcname=name,recursive=False)
        r.save(p/'packet.json',dict(id=ID,slot_credit=False,review_disposition='NOT_REVIEWED',files=[dict(path=str(f.relative_to(p)),sha256=sha(f),bytes=f.stat().st_size) for f in files(p)]))
    else:
        assert pins()==read(p/'source-pins.json'),'source pins'
        assert dependencies()==read(p/'dependencies.json'),'dependencies'
        assert base.tools()==read(p/'tools.json'),'tools'
        entries=read(p/'packet.json')['files'];assert {e['path'] for e in entries}=={str(f.relative_to(p)) for f in files(p) if f.name!='packet.json'}
        for e in entries:assert sha(p/e['path'])==e['sha256'],e['path']
        reuse=read(p/'native-reuse.json');n=r.EVIDENCE/reuse['source'];assert sha(n/'run.json')==reuse['sha256'];native_check(n);out=args.output.resolve();r.run(out);source_check(out)
        actual=base.deterministic(out);expected=read(p/'deterministic.json')
        assert actual==expected,sorted(k for k in actual.keys()|expected.keys() if actual.get(k)!=expected.get(k))
        r.save(out/'verification.json',dict(status='PASS',deterministic_files=len(actual),source_pins=len(pins()),summary=read(out/'summary.json'),native_reused_by_final_source_hash=True))
if __name__=='__main__':main()
