"""Rebuild and execute the integrated product; isolate audit 179's controls."""
from pathlib import Path
import importlib.util,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
import check
sys.path.insert(0,str(HERE.parent/'loader'))
import proposal
import common as c
import storage

def load(name):
    path=HERE.parent/'loader'/(name+'.py')
    spec=importlib.util.spec_from_file_location('integrated_loader_'+name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def run(out):
    out.mkdir(parents=True,exist_ok=True)
    before=check.check();c.save(out/'identity.json',before)
    execution=out/'execution';result=load('run').run(execution,stops=False)
    for name,digest in before['runtime_identity'].items():
        assert c.sha(execution/'runtime'/Path(name).name)==digest,name
    packet=c.STORE/check.PACKET
    previous=c.read(packet/'execution/summary.json')
    for name in ('artifacts','target','boots','native'):
        assert result[name]==previous[name],name
    old_controls=previous['controls'];new_controls=result['controls']
    added={'occupied table','occupied tail_table'}
    assert [r for r in new_controls if r['name'] not in added]==old_controls
    assert {r['name'] for r in new_controls if r['name'] in added}==added
    assert c.read(execution/'p2-0/fasl-controls.json')['status']=='PASS'
    # Bind every regenerated published artifact to the reviewed bytes.
    hashes=c.read(packet/'regenerable.json');rows={}
    for p in (execution/'p2-0').iterdir():
        if p.name not in ('p2-0.w32fsl','p2-0-second.w32fsl','heap.bin','static.bin'):continue
        key='execution/p2-0/'+p.name;assert c.sha(p)==hashes[key]['sha256'];rows[key]=c.sha(p)
    for p in (execution/'p2-0/artifacts').iterdir():
        key='execution/p2-0/artifacts/'+p.name
        if key in hashes:assert c.sha(p)==hashes[key]['sha256'];rows[key]=c.sha(p)
    mutants=[]
    public="table.get(m.slot)===null";tail="tailTable.get(m.slot)===null"
    for label,clause in [('public',public),('tail',tail)]:
        work=out/('mutant-'+label);proposal.prepare_runtime(work/'runtime')
        for name in ('controls.mjs','d2.mjs','policy.json','versions.json'):shutil.copyfile(execution/name,work/name)
        path=work/'runtime/bundle.mjs';source=path.read_text()
        assert source.count(clause)==1;path.write_text(source.replace(clause,'true'))
        with (work/'run.log').open('w') as log:
            process=subprocess.run([c.NODE,work/'controls.mjs',execution/'p2-0/artifacts'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
        text=(work/'run.log').read_text();case='occupied '+('table' if label=='public' else 'tail_table')
        assert process.returncode!=0 and 'Missing expected exception: '+case in text,text[-2000:]
        mutants.append(dict(clause=label,case=case,status='KILLED',source_sha256=c.sha(path)))
    extra=load('extra').run(out/'extra',execution)
    assert check.check()==before,'integrated files changed during qualification'
    record=dict(**before,new_product_execution=True,old_image_controls=len(old_controls),
        image_controls=len(new_controls),new_image_refusals=2,fasl_version_refusals=2,
        occupied_slot_mutants=mutants,keyword_mutant=extra['keyword_mutant'],
        d2_compatibility_checks=len(extra['compatibility']['controls']),
        reviewed_artifacts_reproduced=rows,boots=4,observations_per_boot=6,collections_per_collecting_boot=6)
    record.update(new_execution=True,mode='INTEGRATED_PRODUCT_REPLAY_WITH_REUSED_NATIVE_QUALIFICATION',
        integration_record=c.sha(c.ROOT/'doc/WASM/stage1/integration-loader.json'),
        drivers={str(p.relative_to(c.ROOT)):c.sha(p) for p in HERE.glob('*.py')})
    c.save(out/'integration.json',record)
    print(json.dumps({k:v for k,v in record.items() if k not in ('source_identity','runtime_identity','reviewed_artifacts_reproduced')}))
    return record

if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):run(Path(sys.argv[1]).resolve())
