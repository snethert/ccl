"""Retain one review packet, then delete its managed disposable outputs."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
import proposal


def retain(destination,producer,native,corpus,development):
    assert not destination.exists()
    native_result=c.read(native/'results/run.json')
    regression=c.read(corpus/'regression.json')
    assert native_result['status']==regression['status']=='PASS'
    assert regression['fresh_comparisons']==26048 and regression['inherited_comparisons']==0
    assert c.read(producer/'checks.json')['status']=='PASS'
    assert len(c.read(producer/'checks.json')['controls'])==16
    assert len(c.read(producer/'guards.json'))==21
    assert len(c.read(producer/'fasl-controls/results.json'))==8
    identities=c.read(native/'qualification.json')['source_identity']
    assert identities==c.read(producer/'build.json')['source_identity']
    assert identities==c.read(corpus/'cold-compiler.json')['environment']['ready_compiler']['sources']
    spec=importlib.util.spec_from_file_location('cross_load_packet_qualification',HERE/'qualify.py')
    q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    assert identities=={n:hashlib.sha256(b.encode()).hexdigest() for n,b in q.sources().items()}
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.cross-load-retaining-',dir=destination.parent))
    copied={};rebuildable={};development_references={}
    def copy(source,name):
        target=temporary/name;target.parent.mkdir(parents=True,exist_ok=True)
        expected=c.sha(source);shutil.copyfile(source,target)
        assert c.sha(target)==expected
        copied[str(name)]=expected
    def retain_file(source,name):
        if source.suffix in ('.image','.dx64fsl','.wasm','.wat'):
            rebuildable[str(name)]=c.sha(source)
        else:copy(source,name)
    try:
        for p in HERE.iterdir():
            if p.is_file():copy(p,Path('source')/p.name)
        for name,body in {**proposal.sources(),**proposal.runtime_sources()}.items():
            path=temporary/'proposal'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(body)
        for p in c.files(producer):
            name=p.relative_to(producer)
            if name.parts[0]!='proposal':retain_file(p,Path('producer')/name)
        for p in native.iterdir():
            if p.is_file():retain_file(p,Path('native')/p.name)
        for p in c.files(native/'results'):
            name=p.relative_to(native/'results')
            if name.parts[0]=='proposal' or name.parts[0].startswith('baseline'):continue
            retain_file(p,Path('native/results')/name)
        for p in corpus.iterdir():
            if p.is_file():copy(p,Path('corpus')/p.name)
        for p in (corpus/'base').iterdir():
            if p.is_file() and p.suffix in ('.json','.log'):copy(p,Path('corpus/base')/p.name)
        # Native oracle rows are evidence, not a saved compiler session.
        copy(corpus/'base/compiled/native.json',Path('corpus/native.json'))
        copy(corpus/'base/compiled/modules.json',Path('corpus/modules.json'))
        known={c.sha(p):str(p.relative_to(temporary)) for p in c.files(temporary)
               if p.suffix in ('.lisp','.py')}
        for name,digest in identities.items():known.setdefault(digest,'qualified-source:'+name)
        for folder in development:
            assert storage.workspace(folder)!=folder
            for p in c.files(folder):
                name=p.relative_to(folder)
                if any(part in ('work','base','__pycache__') for part in name.parts):continue
                if any(part.startswith('baseline') for part in name.parts):continue
                if p.suffix not in ('.json','.log','.py','.lisp'):continue
                # Keep source deltas and failures; no repeated baseline trees.
                target=Path('development')/folder.parent.name/folder.name/name
                digest=c.sha(p)
                if p.suffix in ('.lisp','.py') and digest in known:
                    development_references[str(target)]=dict(sha256=digest,same_as=known[digest])
                else:
                    copy(p,target)
                    if p.suffix in ('.lisp','.py'):known[digest]=str(target)
        denominator=c.STORE/'2026-09-15-on-demand-census-r1'
        references={str((denominator/n).relative_to(c.STORE)):c.sha(denominator/n)
                    for n in ('packet.json','startup-compile-summary.json')}
        references.update({name:c.sha(c.STORE/name) for name in (
            '2026-09-16-stage1-1a-r2/native/run.json',
            '2026-09-24-namespace-consumers-r1/packet.json',
            '2026-09-24-namespace-consumer-integration/packet.json')})
        frontier=c.read(producer/'frontier/results.json')
        summary=dict(status='PASS',review='NOT_REVIEWED',slot_credit=False,
            ordered_production_files=[0,0,0],denominator=167,
            independent_level0_probes=dict(total=len(frontier['compile_order']),
                compiled=[r['path'] for r in frontier['compile_order'] if r['status']=='PASS']),
            fixture_files=[1,1,0],accepted_originals=[575,535],ledger=[21,12],
            native_tests=native_result['registered_tests']['passed'],regression=regression,
            compiler_sources=identities,boot=False,source_reconstruction='fresh process after source deletion',
            references=references,refusal_debt='source/admission-debt.json')
        c.save(temporary/'summary.json',summary)
        c.save(temporary/'development-references.json',development_references)
        c.save(temporary/'regenerable.json',rebuildable)
        c.save(temporary/'packet.json',dict(id='STAGE1-CROSS-LOAD-R1',status='PROPOSED',
            review='NOT_REVIEWED',slot_credit=False,files=c.inventory(temporary)))
        c.verify_files(temporary,c.read(temporary/'packet.json')['files'])
        os.rename(temporary,destination)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    for folder in [producer,native,corpus,*development]:
        assert storage.workspace(folder)!=folder
        if folder.exists():shutil.rmtree(folder)
    return dict(status='PASS',packet=str(destination),sha256=c.sha(destination/'packet.json'))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['retain'])
    for name in ('destination','producer','native','corpus'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--development',type=Path,action='append',default=[])
    args=parser.parse_args()
    paths=[args.producer,args.native,args.corpus,*args.development]
    with storage.lease(paths):
        print(json.dumps(retain(args.destination.resolve(),args.producer.resolve(),args.native.resolve(),
                                args.corpus.resolve(),[p.resolve() for p in args.development])))
