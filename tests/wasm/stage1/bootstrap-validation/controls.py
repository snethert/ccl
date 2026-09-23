"""Identity invalidation, deterministic sampling and cache corruption controls."""
from pathlib import Path
import argparse
import copy
import shutil
import tempfile
import common as c
import storage
from build import environment
from execute import row_key,sample,SEED,bound_report


def controls(base,cache,out):
    base,cache,out=map(Path,(base,cache,out));out.mkdir()
    env=environment();key=c.digest(env)
    assert c.cache_read(cache,'session',key)
    invalidations=[]
    for name in ('parent_sources','proposal_and_corpus','implementation','modes','kernel','image','environment_order'):
        altered=copy.deepcopy(env);altered[name]=['changed',altered[name]]
        changed=c.digest(altered);assert changed!=key and c.cache_read(cache,'session',changed) is None
        invalidations.append(name)
    runtime=c.read(base/'execution-environment.json');row=c.read(base/'compiled/native.json')[0]
    ident='control';before=row_key(c.digest(runtime),row,ident)
    for name in ('fp_control','movement','placements','engine','compiler_environment','tooling'):
        altered=copy.deepcopy(runtime);altered[name]=['changed',altered[name]]
        assert row_key(c.digest(altered),row,ident)!=before;invalidations.append(name)
    for name in ('float.wasm','hash.wasm','graph.mjs','compiled/pools.json','compiled/modules.json','compiled/symbols.json'):
        altered=copy.deepcopy(runtime);altered['files'][name]='0'*64
        assert row_key(c.digest(altered),row,ident)!=before;invalidations.append(name)
    altered=copy.deepcopy(row);altered['values']=['changed']
    assert row_key(c.digest(runtime),altered,ident)!=before;invalidations.append('oracle')
    ids=c.read(base/'case-ids.json');assert len(sample(ids))==32 and sample(ids)==sample(list(reversed(ids)))
    record=c.read(base/'assembly.json')['rows'][0];entry=c.cache_read(cache,'wabt',record['key'])
    temporary=out/'corrupt-cache';path=temporary/'wabt'/record['key'];shutil.copytree(entry,path)
    with (path/'module.wasm').open('ab') as stream:stream.write(b'corrupt')
    try:c.cache_read(temporary,'wabt',record['key'])
    except ValueError as error:corruption=str(error)
    else:raise AssertionError('corrupt cache admitted')
    shutil.rmtree(temporary)
    # Existing evidence corruption is an error, not permission to inherit it.
    report_path=out/'corrupt-report.json'
    shutil.copyfile(base/'execution-report.json',report_path)
    shutil.copyfile(base/'execution-report.identity.json',report_path.with_suffix('.identity.json'))
    with report_path.open('a') as stream:stream.write('\n')
    try:bound_report(report_path)
    except ValueError as error:report_corruption=str(error)
    else:raise AssertionError('corrupt execution report admitted')
    report_path.unlink();report_path.with_suffix('.identity.json').unlink()
    report=dict(status='PASS',invalidations=invalidations,corruption_rejected=corruption,
                report_corruption_rejected=report_corruption,
                sample_seed=SEED,sample_size=32,sample_order_independent=True)
    c.save(out/'controls.json',report)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('cache',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args()
    storage.gc(a.cache)
    try:
        with storage.lease([a.base,a.output],a.cache):print(controls(a.base,a.cache,a.output))
    finally:storage.gc(a.cache)
