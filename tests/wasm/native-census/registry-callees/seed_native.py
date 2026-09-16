"""Export the seed image's bodies alongside the actual inspector identities."""
import argparse,os,subprocess,traceback
from pathlib import Path
from payloads import read,save,require,rows
HERE=Path(__file__).resolve().parent


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    inspector=HERE.parent/'startup-closure/image-inventory.lisp';original=inspector.read_bytes()
    argv=[str(a.source/'dx86cl64'),'--image-name',str(a.image),'--no-init','--batch']
    for n in ('observer.lisp','dependencies.lisp','rich-observation/observer.lisp','resident-bodies/export.lisp',
              'dispatch-registry/inspect.lisp','registry-callees/build-observer.lisp',
              'startup-closure/image-inventory.lisp','registry-callees/seed-functions.lisp'):
        argv+=['--load',str(HERE.parent/n)]
    argv+=['--eval','(progn (ccl-seed-functions::run) (ccl:quit))']
    save(a.output/'command.json',dict(argv=argv,cwd=str(a.source)))
    with (a.output/'native.log').open('wb') as log:
        p=subprocess.run(argv,cwd=a.source,env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(a.source),
            SEED_INSPECTOR_SOURCE=str(inspector),SEED_FUNCTION_BYTES=str(a.output/'functions.jsonl'),
            SEED_IMAGE_INVENTORY=str(a.output/'image.json')),stdout=log,stderr=subprocess.STDOUT,timeout=120)
    require(p.returncode==0 and 'SEED-FUNCTION-EXPORT-PASS' in (a.output/'native.log').read_text(),'SEED_NATIVE_EXIT')
    require(inspector.read_bytes()==original,'SEED_INSPECTOR_SOURCE_CHANGED')
    records=list(rows(a.output/'functions.jsonl'));mapping=records[0]
    require(mapping['kind']=='inspection-map' and records[-1]['kind']=='complete','SEED_EXPORT_COMPLETE')
    fs={r['id']:r for r in records if r['kind']=='function'};image=read(a.output/'image.json')
    mp={r['inspection_id']:r['function'] for r in mapping['entries']}
    require(len(mp)==len(mapping['entries'])==len(image['functions'])==records[-1]['inspected_functions'],
            'SEED_MAP_POPULATION')
    require(set(mp.values())<=fs.keys(),'SEED_MAP_FUNCTIONS')
    for f in image['functions']:
        r=fs[mp[f['id']]]
        # The inspector maps literal closures to their prototypes. The byte
        # exporter records the actual closure objects first, then prototypes.
        expected={fs[v['function']]['prototype'] for v in r['literals'] if isinstance(v,dict) and 'function' in v}
        require({mp[i] for i in f['literal_functions']}==expected,'SEED_LITERAL_IDENTITY')
    summary=dict(status='PASS',inspected_functions=len(mp),payload_functions=len(fs),same_execution_literal_joins=len(mp),
                 historical_numeric_ids_reused=False,shared_source_changed=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','image','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():
            (a.output/'failure.txt').write_text(traceback.format_exc())
            for n in ('seed_native.py','seed-functions.lisp'):(a.output/n).write_bytes((HERE/n).read_bytes())
        raise
