"""Focused mutation and compatibility checks for the consolidated loader."""
from pathlib import Path
import json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import proposal
import storage

def run(out,execution):
    out.mkdir(parents=True,exist_ok=True)
    proposal.prepare_runtime(out/'runtime')
    for name in ('controls.mjs','d2.mjs'):shutil.copyfile(HERE/name,out/name)
    for name in ('policy.json','versions.json'):shutil.copyfile(execution/name,out/name)
    path=out/'runtime/cross-image.mjs';original=path.read_text()
    clause="   need(i.module!=='keywords','KEYWORD_IMPORT');"
    assert original.count(clause)==1
    path.write_text(original.replace(clause,''))
    with (out/'keyword-mutant.log').open('w') as log:
        result=subprocess.run([c.NODE,out/'controls.mjs',execution/'p2-0/artifacts'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
    path.write_text(original)
    text=(out/'keyword-mutant.log').read_text()
    assert result.returncode!=0 and 'Missing expected exception: keyword import' in text,text[-2000:]
    # The accepted D2 fixture retains serialized slots. Its original checks
    # must still pass when no owner mapping is supplied.
    prior=c.STORE/'2026-09-20-stage1-granularity-r1/execution'
    compatible=out/'compatibility';proposal.prepare_runtime(compatible)
    refs={}
    for name in ('modules.json','versions.json','materialization.json'):
        shutil.copyfile(prior/name,compatible/name);refs[name]=c.sha(prior/name)
    for m in c.read(prior/'modules.json'):
        for folder in ('full','templates'):
            name=folder+'/'+m['name']+'.wasm';p=compatible/name;p.parent.mkdir(exist_ok=True)
            shutil.copyfile(prior/name,p);refs[name]=c.sha(prior/name)
    shutil.copyfile(HERE.parent/'granularity/check.mjs',compatible/'check.mjs')
    c.command([c.NODE,compatible/'check.mjs',compatible],out/'compatibility.log')
    result=dict(status='PASS',keyword_mutant='KILLED',compatibility=c.read(compatible/'checks.json'),
                compatibility_reference=str(prior.relative_to(c.STORE)),reference_files=refs)
    c.save(out/'summary.json',result);return result

if __name__=='__main__':
    with storage.lease([Path(sys.argv[1])]):print(json.dumps(run(Path(sys.argv[1]),Path(sys.argv[2]))))
