"""Retain one compact review packet; binaries remain regenerable by hash."""
from pathlib import Path
import argparse,gzip,hashlib,json,os,shutil,sys,tempfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import proposal
import storage

def retain(destination,execution,native,corpus,replay,readers,extra,comparison,misplaced,development):
    assert not destination.exists()
    source_identity={n:hashlib.sha256(b.encode()).hexdigest() for n,b in proposal.sources().items()}
    assert source_identity==c.read(native/'qualification.json')['source_identity']
    assert source_identity==c.read(execution/'p2-0/build-completion.json')['sources']
    assert source_identity==c.read(corpus/'cold-compiler.json')['environment']['ready_compiler']['sources']
    assert source_identity==c.read(replay/'summary.json')['source_identity']
    result=c.read(execution/'summary.json');regression=c.read(corpus/'regression.json')
    assert regression['fresh_comparisons']==26048 and regression['inherited_comparisons']==0
    for p in (execution/'summary.json',native/'results/run.json',corpus/'regression.json',replay/'summary.json',readers/'summary.json',extra/'summary.json',comparison/'controls.json'):
        assert c.read(p)['status']=='PASS',p
    assert '(= 1 (COUNT' in (misplaced/'run.log').read_text(),'misplaced-hook control did not reach the reader assertion'
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=Path(tempfile.mkdtemp(prefix='.loader-retaining-',dir=destination.parent))
    regenerable={};compressed={}
    def copy(p,name):
        target=temporary/name;target.parent.mkdir(parents=True,exist_ok=True)
        digest=c.sha(p)
        if p.suffix in ('.image','.dx64fsl','.w32fsl','.wasm','.wat','.bin') or p.name=='dx86cl64':
            regenerable[str(name)]=dict(sha256=digest,bytes=p.stat().st_size);return
        if p.stat().st_size>131072:
            target=target.with_name(target.name+'.gz')
            with p.open('rb') as source,target.open('wb') as output,gzip.GzipFile(filename='',mode='wb',fileobj=output,mtime=0) as stream:
                shutil.copyfileobj(source,stream)
            with gzip.open(target,'rb') as stream:assert hashlib.file_digest(stream,'sha256').hexdigest()==digest
            compressed[str(name)]=dict(file=str(target.relative_to(temporary)),sha256=digest,bytes=p.stat().st_size)
        else:
            shutil.copyfile(p,target);assert c.sha(target)==digest
    try:
        for p in c.files(HERE):
            if '__pycache__' not in p.parts:copy(p,Path('source')/p.relative_to(HERE))
        copy(HERE.parent/'ready/compiler.py',Path('source/ready-compiler.py'))
        for name,body in {**proposal.sources(),**proposal.runtime_sources()}.items():
            p=temporary/'proposal'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(body)
        for p in c.files(execution):
            n=p.relative_to(execution)
            if n.parts[0]=='runtime' and p.suffix not in ('.wasm','.log'):continue
            if len(n.parts)==1 and p.suffix=='.mjs':continue
            copy(p,Path('execution')/n)
        for p in native.iterdir():
            if p.is_file() and not p.name.startswith('.'):copy(p,Path('native')/p.name)
        for p in (native/'results').iterdir():
            if p.is_file() and not p.name.startswith('baseline'):copy(p,Path('native/results')/p.name)
        for p in corpus.iterdir():
            if p.is_file() and not p.name.startswith('.'):copy(p,Path('corpus')/p.name)
        for p in (corpus/'base').iterdir():
            if p.is_file() and p.suffix in ('.json','.log'):copy(p,Path('corpus/base')/p.name)
        for name in ('native.json','modules.json'):copy(corpus/'base/compiled'/name,Path('corpus')/name)
        for label,folder in [('readers',readers),('comparison-controls',comparison),('misplaced-hook',misplaced)]:
            for p in folder.iterdir():
                if p.is_file() and not p.name.startswith('.'):copy(p,Path(label)/p.name)
        for label,folder,names in [('replay',replay,('summary.json','replay.log','prepare.log','prepare.py')),
                                   ('extra',extra,('summary.json','keyword-mutant.log','compatibility.log'))]:
            for name in names:copy(folder/name,Path(label)/name)
        for p in development.iterdir():
            if p.is_file() and p.suffix in ('.json','.log','.md','.patch'):copy(p,Path('development')/p.name)
        references={name:c.sha(c.STORE/name) for name in (
            '2026-09-16-stage1-1a-r2/native/run.json',
            '2026-09-24-namespace-consumers-r1/packet.json',
            '2026-09-25-cross-load-r1/packet.json',
            '2026-09-25-stage1-cross-load-r1/packet.json',
            '2026-09-20-stage1-materialization-r1/execution/policy.json')}
        summary=dict(status='PASS',review='NOT_REVIEWED',product_integration=False,
            source_identity=source_identity,artifacts=result['artifacts'],target=result['target'],
            controls=len(result['controls']),replay='byte-identical, Git-free checkout at another absolute path',
            regression=regression,native_tests=c.read(native/'results/run.json')['registered_tests']['passed'],
            level0=result['level0'],files=[0,0,0],native_units=167,fixture_files=[2,2,0],
            accepted_originals=[575,535],ledger=[21,12],slot_credit=False,boot=False,
            references=references)
        c.save(temporary/'summary.json',summary)
        c.save(temporary/'regenerable.json',regenerable);c.save(temporary/'compressed.json',compressed)
        c.save(temporary/'packet.json',dict(id='STAGE1-LOADER-DESIGN-R1',status='PROPOSED',review='NOT_REVIEWED',slot_credit=False,files=c.inventory(temporary)))
        c.verify_files(temporary,c.read(temporary/'packet.json')['files'])
        os.rename(temporary,destination)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return dict(status='PASS',packet=str(destination),sha256=c.sha(destination/'packet.json'))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('destination','execution','native','corpus','replay','readers','extra','comparison','misplaced','development'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=vars(parser.parse_args())
    with storage.lease([p for name,p in args.items() if name!='destination']):print(json.dumps(retain(**args)))
