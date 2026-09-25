"""Retain the focused integration evidence without duplicating reviewed packs."""
from pathlib import Path
import json,os,shutil,sys,tempfile
HERE=Path(__file__).resolve().parent
import check
import common as c
import storage

def retain(out,destination):
    assert not destination.exists()
    result=c.read(out/'integration.json');identity=check.check()
    assert result['status']=='PASS' and result['source_identity']==identity['source_identity']
    assert result['runtime_identity']==identity['runtime_identity']
    assert result['integration_record']==c.sha(c.ROOT/'doc/WASM/stage1/integration-loader.json')
    c.verify_files(c.ROOT,result['drivers'])
    execution=c.read(out/'execution/summary.json');c.verify_files(c.ROOT,execution['execution_inputs'])
    assert result['image_controls']==68 and result['fasl_version_refusals']==2
    assert all(r['status']=='KILLED' for r in result['occupied_slot_mutants'])
    packet=c.STORE/check.PACKET;manifest=c.read(packet/'packet.json')['files']
    temporary=Path(tempfile.mkdtemp(prefix='.loader-integration-',dir=destination.parent))
    generated={};reused={}
    def copy(p,name):
        target=temporary/name;target.parent.mkdir(parents=True,exist_ok=True)
        digest=c.sha(p);shutil.copyfile(p,target);assert c.sha(target)==digest
    try:
        for p in c.files(out):
            name=p.relative_to(out)
            if p.suffix in ('.image','.dx64fsl','.w32fsl','.wasm','.wat','.bin') or p.name=='dx86cl64':
                generated[str(name)]=dict(sha256=c.sha(p),bytes=p.stat().st_size);continue
            if str(name).startswith('execution/p2-0/artifacts/'):
                key=str(name)
                if key in manifest:
                    assert c.sha(p)==manifest[key],key
                    reused[key]=dict(packet=check.PACKET,sha256=manifest[key]);continue
            if any(part=='runtime' for part in name.parts):
                if p.name=='bundle.mjs' and name.parts[0] in ('mutant-public','mutant-tail'):
                    copy(p,name)
                elif p.suffix=='.log':copy(p,name)
                continue
            if len(name.parts)>1 and name.parts[:2]==('extra','compatibility'):continue
            if p.suffix in ('.json','.log') and not p.name.startswith('.'):copy(p,name)
        for p in HERE.iterdir():
            if p.is_file():copy(p,Path('source/loader-acceptance')/p.name)
        for name in ('proposal.py','run.py','build.py','load.lisp','controls.mjs'):
            copy(HERE.parent/'loader'/name,Path('source/loader')/name)
        for name in ('doc/WASM/stage1/integration-loader.json','doc/WASM/contracts/cross-image-owner.md'):
            copy(c.ROOT/name,Path('source')/name)
        c.save(temporary/'regenerable.json',generated);c.save(temporary/'reused-artifacts.json',reused)
        c.save(temporary/'packet.json',dict(id='STAGE1-LOADER-INTEGRATION',status='ACCEPTED_AND_INTEGRATED',
            product_review='AUDIT_179_NO_DEFECT',new_controls='AUTHOR_VERIFIED',slot_credit=False,
            reviewed_packet=dict(path=check.PACKET,sha256=check.PACKET_SHA),
            files=c.inventory(temporary)))
        c.verify_files(temporary,c.read(temporary/'packet.json')['files'])
        os.rename(temporary,destination)
    finally:
        if temporary.exists():shutil.rmtree(temporary)
    return dict(status='PASS',packet=str(destination),sha256=c.sha(destination/'packet.json'))

if __name__=='__main__':
    out,destination=map(lambda p:Path(p).resolve(),sys.argv[1:])
    with storage.lease([out]):print(json.dumps(retain(out,destination)))
