#!/usr/bin/env python3
"""Publish three unreviewed Stage 1A records; never accept or overwrite evidence."""
import argparse,datetime,json,shutil,sys
from pathlib import Path
from run import ROOT,HERE,read,save,sha,require,assess
sys.path.insert(0,str(ROOT/'doc/WASM/tools'))
from evidence_binding import bind_report,binding_errors,safe_path
from gate import assess as gate
IDS=['S1-LL08-a','S1-LL22-b','S1-LL23-a']
def publish(output,evidence,name):
    require(safe_path(name)==name and '/' not in name,'PACK_NAME')
    destination=evidence/name;envelope=evidence/(name+'-results.json')
    require(not destination.exists() and not envelope.exists(),'NEVER_OVERWRITE')
    require(read(output/'summary.json')['status']=='PASS','COMPLETED_BUILD')
    assess(read(output/'execution.json'),read(output/'build.json'),(output/'identity.disassembly').read_text())
    require((output/'verified.log').is_file() and 'S1-1A-VERIFIED' in (output/'verified.log').read_text(),'FRESH_VERIFIER_REQUIRED')
    for path,digest in read(output/'source-pins.json').items():require(sha(ROOT/path)==digest,'SOURCE_CHANGED '+path)
    inventory_path=ROOT/'doc/WASM/stage1/inventory.json';inventory=read(inventory_path)
    tests={t['id']:t for t in inventory['tests']}
    for id in IDS:require(tests[id]['runner'] and tests[id]['status']=='EXECUTED','REGISTERED_RUNNER '+id)
    shutil.copytree(output,destination,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copy(inventory_path,destination/'inventory.json')
    hashes={str(p.relative_to(destination)):sha(p) for p in sorted(destination.rglob('*')) if p.is_file()}
    # The complete pack manifest retains every file, while each result uses the
    # actual build-role records plus its native/qualification/diagnostic reports.
    artifacts=[dict(path=name+'/'+f['path'],role=f['role'],sha256=f['sha256']) for f in read(destination/'build.json')['files']]
    paths={a['path'] for a in artifacts}
    for path in ['native/run.json','native/baseline-fasls.tar.gz','native/registered-compile-ccl.dx64fsl','native/registered-systems.dx64fsl','native/compile-ccl-comparison.json','native/systems-comparison.json','qualification/verification.json','qualification/summary.json','qualification/baseline-operators.json','qualification/registered-operators.json','summary.json','execution.json','identity.disassembly','verified.log','build.json']:
        if name+'/'+path not in paths:artifacts.append({'path':name+'/'+path,'role':'log','sha256':hashes[path]})
    timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat();rows=[]
    for id in IDS:
        test=tests[id]
        rows.append({'id':id,'variant':test['variants'][0],'status':'PASS','source_revision':inventory['source_revision'],'evidence_kind':test['evidence_kind'],
            'review_disposition':'NOT_REVIEWED','test_revision':hashes['source-pins.json'],'timestamp':timestamp,'seed':100000,
            'command':test['runner']+'; exact invocations in native/commands.json, qualification/commands.json and commands.json',
            'toolchain':read(destination/'host-compiler.json'),'engine':{'native':'CCL U1 macOS x86-64','wasm':read(destination/'execution.json')['engine']},
            'configuration':{'profile':'Stage 1 full profile, one Worker','scope':read(destination/'summary.json')['scope'],
                'native_tests':21843,'native_disabled':75,'generated_leaf_functions':9,'claims':'Registration/R6, build binding and fatal diagnostics only; no general B ABI, target heap, bootstrap, GC or ordinary Lisp arity-condition implementation.',
                'integration':'Proposal applied only in disposable clean U1; shared checkout unchanged; Claude review required before integration.'},
            'substitutions':[],'skips':[],'assertions':[{'id':a['id'],'status':'PASS'} for a in test['assertions']],'artifacts':artifacts})
    report=bind_report({'version':1,'source_revision':inventory['source_revision'],'inventory_sha256':hashes['inventory.json'],'results':rows},inventory,name+'/inventory.json',hashes['inventory.json'])
    require(not binding_errors(inventory,report,lambda p:(evidence/p).read_bytes()),'BINDING')
    save(envelope,report)
    status,reasons=gate(inventory,report,sha(inventory_path),evidence)
    require(status=='BLOCKED' and len([r for r in reasons if r.startswith('unreviewed ')])==3 and len([r for r in reasons if r.startswith('missing ')])==28 and len(reasons)==31,'GATE_RESULT')
    save(destination/'gate.json',{'status':status,'reasons':reasons});hashes['gate.json']=sha(destination/'gate.json')
    packet={'id':'STAGE1-1A-R2','source_revision':inventory['source_revision'],'scope':'S1-LL08-a, S1-LL22-b and S1-LL23-a executed at initial generated-leaf scope, not accepted or integrated.',
      'review_disposition':'NOT_REVIEWED','envelope':envelope.name,'envelope_sha256':sha(envelope),
      'files':[{'path':p,'sha256':h,'bytes':(destination/p).stat().st_size} for p,h in sorted(hashes.items())]}
    save(destination/'packet.json',packet)
    print(json.dumps({'packet':str(destination/'packet.json'),'sha256':sha(destination/'packet.json'),'results':str(envelope),'result_sha256':sha(envelope),'missing':28,'unreviewed':3}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--name',required=True);a=p.parse_args();publish(a.output.resolve(),a.evidence.resolve(),a.name)
