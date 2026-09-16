#!/usr/bin/env python3
"""Qualify the reviewed on-demand census under LL15-b/c v0.2; no closure claim."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import traceback
from publication import Reference, ROOT, HERE, check_files, read, require, save, sha, write_publication, identity
import test_publication

QUERY=HERE.parent/'query'; TOOLS=ROOT/'doc/WASM/tools'
sys.path.insert(0,str(QUERY));sys.path.insert(0,str(TOOLS))
from capture import query
from evidence_binding import bind_report, contract_hash
from gate import assess, required_roles
IDS=('S0-LL15-b','S0-LL15-c')
SCOPE='Reviewed retained native instrument and 167-unit startup worklist with explicit unknowns; identity-bound queries and reversible source-specific call-site witnesses. Independent omissions and literal native semantic controls. No exhaustive callee bound, qualified closure, generated Wasm, or project acceptance.'

def sources():
    paths=list(HERE.glob('*.py'))+[HERE/'inputs.json',HERE/'README.md']+list(QUERY.glob('*.py'))+list(QUERY.glob('*.lisp'))
    paths += [HERE.parent/p for p in ('build-flow/flow.py','source-closure/analysis.py','source-closure/bounds.py','observer.lisp','dependencies.lisp','rich-observation/observer.lisp','resident-bodies/export.lisp','startup-closure/seeds.json')]
    paths += [TOOLS/p for p in ('evidence_binding.py','gate.py','check-census.py')]
    paths += [ROOT/'doc/WASM/contracts/census.md',ROOT/'doc/WASM/contracts/census.schema.json']
    return sorted(set(paths))

def command(argv, out, commands, name, expected=0):
    entry=dict(name=name,argv=list(map(str,argv)),cwd=str(ROOT),status='RUNNING');commands.append(entry);save(out/'commands.json',commands)
    with (out/(name+'.log')).open('w') as log:
        p=subprocess.run(entry['argv'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,timeout=900)
    entry.update(exit_code=p.returncode,status='PASS' if p.returncode==expected else 'FAIL');save(out/'commands.json',commands)
    require(p.returncode==expected,'CHILD_FAILED '+name)
    print(name+': PASS',flush=True)

def exercise(out, evidence, work, cache_path=None):
    require(platform.system()=='Darwin' and platform.machine()=='x86_64','MACOS_X86_64_REFERENCE')
    ref=Reference(evidence);save(out/'resolved-inputs.json',ref.inputs)
    commands=[];work=Path(work);require(not work.exists(),'FRESH_WORK');work.mkdir(parents=True)
    cache=Path(cache_path).resolve() if cache_path else work/'capture.sqlite'
    command([sys.executable,QUERY/'test_capture.py','--capture',ref.packets['capture'][0],'--cache',cache,'--output',out/'capture-controls'],out,commands,'capture-controls')
    # The damaged SQLite copy is a disposable test cache, not evidence.
    # Its mutation recipe, input identities and rejection are retained.
    for cache_file in (out/'capture-controls').glob('*.sqlite*'):cache_file.unlink()
    command([sys.executable,QUERY/'run.py','--evidence',evidence,'sites','--work',work/'native','--source','level-1/l1-utils.lisp','--function','CCL::GETF-TEST','--output',out/'sites'],out,commands,'sites')
    selection=read(out/'sites/answer.json')['selections'][0]
    require(selection==ref.witnesses['u1-witness']['selections'][0],'CLI_SITE_IDENTITY')
    save(out/'selection.json',selection)
    (out/'scenario.lisp').write_text('(lambda (fn) (funcall fn (list :a 10 :b 20) :b (function eq)))\n')
    command([sys.executable,QUERY/'run.py','--evidence',evidence,'probe','--work',work/'native','--source','level-1/l1-utils.lisp','--function','CCL::GETF-TEST','--selection',out/'selection.json','--scenario',out/'scenario.lisp','--output',out/'u1-witness'],out,commands,'probe')
    native=work/'native/ccl'
    command([sys.executable,QUERY/'test_native.py','--source',native,'--image',native/'dx86cl64.image','--kernel',native/'dx86cl64','--output',out/'native-controls'],out,commands,'native-controls')
    # The previous semantic checker already compares literals and actual source
    # mutants. Demand the complete reviewed test inventories, not just PASS.
    expected_capture=read(ref.member('tools','capture-controls.json'));expected_native=read(ref.member('tools','native-controls.json'))
    require(read(out/'capture-controls/summary.json')==expected_capture,'CAPTURE_CONTROL_INVENTORY')
    require(read(out/'native-controls/summary.json')==expected_native,'NATIVE_CONTROL_INVENTORY')
    queries={name:query(ref.packets['capture'][0],cache,question) for name,(question,_) in ref.queries.items()}
    witnesses={name:read(out/('u1-witness' if name=='u1-witness' else 'native-controls/'+name)/'answer.json') for name in ref.witnesses}
    pub=ref.make(queries,witnesses);write_publication(out/'publication',pub)
    summary=check_files(out/'publication',ref)
    # Keep the complete-closure check visibly BLOCKED, using the unchanged tool.
    spec=importlib.util.spec_from_file_location('qualification_census_checker',TOOLS/'check-census.py');checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    failures=checker.validate(pub['graph']);require(failures and all(x.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for x in failures),'CLOSURE_MUST_STAY_BLOCKED')
    save(out/'closure-assessment.json',dict(status='BLOCKED',reasons=sorted(failures),scope='Unchanged complete-closure checker; expected refusal is not an instrument failure.'))
    controls=test_publication.run(ref,pub,out/'publication-controls')
    summary.update(capture_checks=len(expected_capture['cases']),native_cases=len(expected_native['cases']),publication_controls=len(controls)-1)
    save(out/'summary.json',summary)
    pin=read(native.parent/'prepared.json');run=read(out/'u1-witness/run.json')
    # Manifests identify the actual image and compiler used; archived originals
    # are fixed inputs, not duplicated baseline payloads.
    save(out/'image.json',dict(role='executed-native-image-identity',sha256=run['image_sha256'],bootstrap_archive=pin['inputs']['bootstrap'],source='macos-u1-inputs/bootstrap.tar.gz!dx86cl64.image',scope='Actual fresh disposable image hash, bound to the retained pristine bootstrap archive.'))
    save(out/'host-compiler.json',dict(kernel_sha256=run['kernel_sha256'],helpers=run['helpers'],source_revision=pin['source_revision'],reference='macOS x86-64 native CCL; original pass 2 forwarded by reversible private observation'))
    save(out/'options.json',dict(complete_closure=False,native_event_limit=10000,timeout_seconds=120,negative_event_limit=2,source_unchanged=True,fasls_written=False,work='fresh disposable U1',retained_startup_units=167))
    return summary

def role(out,p):
    rel=p.relative_to(out).parts
    if p.name in ('host-compiler.json','image.json','options.json'):return p.stem
    if rel[0]=='sources':return 'source' if p.suffix=='.lisp' else 'implementation'
    if p.name=='inventory.json' or p.name=='inputs.json':return 'schema'
    if rel[0].endswith('controls'):return 'negative_control'
    if p.name=='test_publication.py':return 'test'
    return 'log'

def produce(out,evidence,work,cache=None):
    require(not out.exists() and ROOT not in out.parents,'FRESH_OUTPUT_OUTSIDE_CHECKOUT');out.mkdir(parents=True)
    snapshots={str(p.relative_to(ROOT)):p.read_bytes() for p in sources()}
    record=dict(version=1,status='FAIL',command=[sys.executable,*sys.argv],timestamp=datetime.now(timezone.utc).isoformat(),sources={n:__import__('hashlib').sha256(b).hexdigest() for n,b in snapshots.items()})
    try:
        summary=exercise(out,evidence,work,cache)
        for n,b in snapshots.items():
            dest=out/'sources'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
        invpath=ROOT/'doc/WASM/stage0/inventory.json';inv=read(invpath);(out/'inventory.json').write_bytes(invpath.read_bytes())
        artifacts=[dict(path=str(p.relative_to(out)),sha256=sha(p),role=role(out,p)) for p in sorted(out.rglob('*')) if p.is_file()]
        # Explicit roles for the independent checker/test and contract.
        for a in artifacts:
            if a['path'].endswith('/test_publication.py'):a['role']='test'
            if a['path'].endswith('/contracts/census.md'):a['role']='schema'
        results=[]
        for ident in IDS:
            test=next(t for t in inv['tests'] if t['id']==ident);require(test['runner']==str(HERE.relative_to(ROOT)/'run.py'),'RUNNER_REGISTRATION')
            results.append(dict(id=ident,variant='native',source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],status='PASS',assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],artifacts=artifacts,substitutions=[],skips=[],review_disposition='NOT_REVIEWED',command=record['command'],toolchain=read(out/'host-compiler.json'),engine='Native CCL macOS x86-64',timestamp=record['timestamp'],configuration=dict(scope=SCOPE,**summary),seed='Fixed reviewed captures, literal native scenarios and named publication mutations',test_revision=identity(record['sources'])))
        report=bind_report(dict(version=1,source_revision=inv['source_revision'],inventory_sha256=sha(out/'inventory.json'),scope=SCOPE,results=results),inv,'inventory.json',sha(out/'inventory.json'));save(out/'results.json',report)
        status,reasons=assess(inv,report,sha(invpath),out)
        expected=['missing '+t['id']+' ['+v+']' for t in inv['tests'] if t['id'] not in IDS for v in t['variants']]+['unreviewed '+i+' [native]' for i in IDS]
        require(status=='BLOCKED' and sorted(reasons)==sorted(expected),'RESULT_GATE')
        save(out/'result-gate.json',dict(status=status,reasons=reasons))
        # Production gate artifact-role omissions, without changing the inventory.
        from copy import deepcopy
        omissions=[]
        for i,r in enumerate(report['results']):
            test=next(t for t in inv['tests'] if t['id']==r['id'])
            for missing in sorted(required_roles(inv,test)):
                bad=deepcopy(report);bad['results'][i]['artifacts']=[a for a in r['artifacts'] if a['role']!=missing]
                s,rs=assess(inv,bad,sha(invpath),out);require(s=='FAIL' and 'missing artifact roles: '+r['id']+' [native]' in rs,'ROLE_OMISSION '+missing)
                omissions.append(dict(id=r['id'],role=missing,status=s,reason='missing artifact roles: '+r['id']+' [native]'))
        save(out/'role-omissions.json',omissions)
        require(record['sources']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_CHANGED')
        record.update(status='PASS',contracts={i:contract_hash(inv,i) for i in IDS})
        print('PASS: LL15-b/c instrument qualification; complete closure remains BLOCKED; review and acceptance pending.',flush=True)
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc());raise
    finally:
        save(out/'run.json',record)
        for n,b in snapshots.items():
            dest=out/'sources'/n;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)

def verify(packet,evidence):
    record=read(packet/'run.json');require(record['status']=='PASS','RETAINED_RUN')
    for n,h in record['sources'].items():require(sha(ROOT/n)==h,'SOURCE_PIN '+n)
    seen=set()
    for row in read(packet/'results.json')['results']:
        for a in row['artifacts']:
            if a['path'] not in seen:require(sha(packet/a['path'])==a['sha256'],'RETAINED_ARTIFACT '+a['path']);seen.add(a['path'])
    temp=Path(tempfile.mkdtemp(prefix='ccl-qualification-verify-'));fresh=temp/'fresh';fresh.mkdir()
    try:
        exercise(fresh,evidence,temp/'work')
        for name in ('summary.json','publication/publication.json.gz','publication/manifest.json','publication-controls/controls.json','closure-assessment.json','capture-controls/summary.json','native-controls/summary.json','image.json','host-compiler.json','options.json'):
            require((fresh/name).read_bytes()==(packet/name).read_bytes(),'REPLAY_DIFFERENCE '+name)
    except BaseException:
        (temp/'failure.txt').write_text(traceback.format_exc());print('Failed replay retained: '+str(temp));raise
    else:shutil.rmtree(temp)
    print('PASS: fresh native/query/control replay and publication byte identity.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path)
    p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--work',type=Path);p.add_argument('--cache',type=Path,help='Optional existing query cache; the query tool checks its complete input/tool fingerprint and bytes')
    a=p.parse_args()
    if a.verify:verify(a.verify.resolve(),a.evidence.resolve())
    else:
        require(a.work is not None,'EXPLICIT_FRESH_WORK_REQUIRED');produce(a.output.resolve(),a.evidence.resolve(),a.work.resolve(),a.cache)
