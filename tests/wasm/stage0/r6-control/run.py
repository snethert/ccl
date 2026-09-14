#!/usr/bin/env python3
"""S0-LL22-b: compare the actual reversible census registration patch under R6."""
import argparse
import copy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
TOOLS=ROOT/'doc/WASM/tools'
STUB=ROOT/'tests/wasm/native-census/stub-backend'
sys.path.insert(0,str(TOOLS))
sys.path.insert(0,str(STUB))
from r6_registration import assess, DataFasl, digest, require
from evidence_binding import bind_report, contract_hash
from registration import Registration
ID='S0-LL22-b'
PACK='2026-09-12-census-stub-r1/'

def read(p): return json.loads(p.read_text())
def save(p,x): p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def sha(p): return digest(p.read_bytes())
def sources():
    return [HERE/'run.py',HERE/'cases.json',HERE/'inputs.json',TOOLS/'r6_registration.py',TOOLS/'gate.py',TOOLS/'evidence_binding.py',STUB/'registration.py',STUB/'patch.json',STUB/'registration.patch',STUB/'payload/census-arch.lisp',STUB/'payload/census-backend.lisp',STUB.parent/'reversible.py',ROOT/'xdump/faslenv.lisp',ROOT/'level-0/nfasload.lisp',ROOT/'lib/nfcomp.lisp']

def input_data(evidence):
    profile=read(HERE/'inputs.json'); blobs={}
    for item in profile['inputs']:
        path=evidence/item['path']
        require(path.resolve().is_relative_to(evidence) and sha(path)==item['sha256'],'INPUT_PIN '+item['path'])
        blobs[item['path']]=path.read_bytes()
    profile['commands']=json.loads(blobs[PACK+'commands.json'])
    with tarfile.open(evidence/'macos-u1-inputs/source.tar') as archive:
        members=[m for m in archive.getmembers() if m.isfile()]
        require(len({m.name for m in members})==len(members),'SOURCE_ARCHIVE_DUPLICATE')
        profile['source_manifest']={m.name:digest(archive.extractfile(m).read()) for m in members}
    patch=read(STUB/'patch.json');profile['modified']=patch['modified'];profile['added']=patch['added']
    return profile,blobs

def manifest(root):
    return {str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file()}

def prepare(evidence,profile,blobs):
    # Reapply and remove only the accepted observation unit, in our own pristine
    # archive. Native binaries are read as evidence, never loaded or rebuilt.
    with tempfile.TemporaryDirectory(prefix='ccl-r6-registration-') as tmp:
        work=Path(tmp).resolve(); source=work/'ccl'; source.mkdir()
        with tarfile.open(evidence/'macos-u1-inputs/source.tar') as t:t.extractall(source,filter='data')
        save(work/'disposable.json',dict(purpose='census-stub-disposable-U1',source=str(source)))
        before=manifest(source); source_before=(source/'lib/systems.lisp').read_bytes()
        with Registration(work,STUB):
            after=manifest(source); source_after=(source/'lib/systems.lisp').read_bytes()
        restored=manifest(source); restoration=read(work/'registration-state.json')
    get=lambda n: json.loads(blobs[PACK+n])
    with tarfile.open(evidence/(PACK+'baseline-fasls.tar.gz')) as t:
        expected=get('baseline-fasls.json');members=t.getmembers()
        require(len(members)==164 and {m.name for m in members}==set(expected),'BASELINE_CORPUS_BOUND')
        for m in members:require(m.isfile() and digest(t.extractfile(m).read())==expected[m.name],'BASELINE_CORPUS_BYTES')
        fasl_before=t.extractfile('bin/systems.dx64fsl').read()
    case=dict(source=dict(before=before,after=after,restored=restored),
        systems_source=dict(before=source_before,after=source_after),restoration=restoration,
        fasls={n:get(n+'-fasls.json') for n in ('baseline','registered','restored')},
        systems_fasl=dict(before=fasl_before,after=blobs[PACK+'registered-systems.dx64fsl']),
        snapshots={n:get(n+'-snapshot.json') for n in ('baseline','registered')},
        probes={n:blobs[PACK+n+'-probe.dx64fsl'] for n in ('baseline','registered')},
        tests={n:get(n+'-tests/test-summary.json') for n in ('baseline','registered')},
        test_files={n:{f:digest(blobs[PACK+n+'-tests/'+f]) for f in ('test-results.sexp','test-inventory.sexp')} for n in ('baseline','registered')},
        run=get('results.json'),commands=get('commands.json'),normalizations=[],intentional_artifacts=['bin/systems.dx64fsl'])
    return case

def damage(base,name):
    c=copy.deepcopy(base)
    if name=='complete': return c
    if name=='target-source-edit':
        key=next(n for n in c['source']['before'] if n.startswith('compiler/X86/'));c['source']['after'][key]='0'*64
    elif name=='shared-source-edit': c['source']['after']['lib/nfcomp.lisp']='0'*64
    elif name=='additional-source': c['source']['after']['lib/hidden.lisp']='0'*64
    elif name=='source-not-restored': c['source']['restored']=c['source']['after']
    elif name=='registration-still-active': c['restoration']['active']=True
    elif name=='source-byte-mismatch': c['systems_source']['after']+=b'\n'
    elif name=='source-revision': c['run']['source_revision']='OTHER'
    elif name=='bootstrap-image': c['run']['inputs']['pins']['inputs']['bootstrap.tar.gz']='0'*64
    elif name=='compiler-kernel': c['run']['inputs']['kernel_sha256']='0'*64
    elif name=='compiler-options': next(x for x in c['commands'] if x['name']=='registered-rebuild')['argv'][-1]+=' ; changed'
    elif name=='compiler-environment': next(x for x in c['commands'] if x['name']=='registered-rebuild')['environment']['LANG']='en_US.UTF-8'
    elif name=='normalization-request': c['normalizations']=['erase code differences']
    elif name=='extra-fasl-change': c['fasls']['registered']['bin/nfcomp.dx64fsl']='0'*64
    elif name=='missing-fasl': del c['fasls']['registered']['bin/systems.dx64fsl']
    elif name=='fasl-not-restored': c['fasls']['restored']['bin/systems.dx64fsl']='0'*64
    elif name=='whole-file-exemption': c['intentional_artifacts'].append('bin/nfcomp.dx64fsl')
    elif name=='wrong-fasl-hash': c['fasls']['registered']['bin/systems.dx64fsl']='0'*64
    elif name in ('code-byte','code-constant','module-data','location','opcode','trailing-data','equivalent-extra-noop','eval-function','location-metadata','table-capacity'):
        data=bytearray(c['systems_fasl']['after']);d=DataFasl(bytes(data));forms=d.decode()
        if name=='code-byte':data[143]^=1
        elif name=='code-constant':data[225]^=1  # original function flags, not module data
        elif name=='module-data':
            at=data.index(b'ccl:bin;backend');data[at]=ord('z')
        elif name=='location':data[243]^=1
        elif name=='location-metadata':data[234]=0
        elif name=='table-capacity':data[19]=134
        elif name=='opcode':data[244]=35  # defparameter -> executable defun
        elif name=='trailing-data':data+=b'\x00'
        elif name=='equivalent-extra-noop':data.insert(len(data)-1,0)
        elif name=='eval-function':
            at=data.index(b'FIND-CLASS-CELL');data[at]=ord('X')
        data[8:12]=(len(data)-12).to_bytes(4,'big')
        c['systems_fasl']['after']=bytes(data)
        # Rebind the mutated payload to reach the semantic comparator.
        c['fasls']['registered']['bin/systems.dx64fsl']=digest(bytes(data))
    elif name.startswith('operator-'):
        operators=c['snapshots']['registered']['snapshot']['operators']
        if name=='operator-omission':operators.pop()
        elif name=='operator-order':operators[10],operators[11]=operators[11],operators[10]
        elif name=='operator-reserved':next(o for o in operators if o['name'] is None)['name']='INVENTED'
        else:
            row=next(o for o in operators if o['name'] is not None)
            key=name.removeprefix('operator-');row[key]=row[key]+1 if isinstance(row[key],int) else 'INVENTED'
    elif name=='abi-word-size':c['snapshots']['registered']['snapshot']['word_bits']=32
    elif name=='target-features':c['snapshots']['registered']['snapshot']['target_features'].append(':INVENTED')
    elif name=='vinsn-template':c['snapshots']['registered']['snapshot']['vinsn_templates'].pop()
    elif name=='evaluated-registration':c['snapshots']['registered']['modules'][-1]['binary']='wrong'
    elif name=='abi-probe':c['probes']['registered']+=b'\x00'
    elif name=='native-run-failed':c['run']['execution_status']='FAIL'
    elif name=='native-test-failed':c['tests']['registered']['failed']=1
    elif name=='native-test-missing':c['tests']['registered']['passed']-=1
    elif name=='native-test-inventory':c['test_files']['registered']['test-inventory.sexp']='0'*64
    else:raise ValueError('UNKNOWN_CASE '+name)
    return c

def exercise(base,profile):
    cases=read(HERE/'cases.json');observations=[]
    for case in cases['cases']:
        mutated=damage(base,case['name'])
        try:
            result=assess(mutated,profile);actual='PASS'
        except ValueError as e:actual=str(e)
        require(actual==case['expected'],'CONTROL_ORACLE '+case['name']+': '+actual)
        observations.append(dict(name=case['name'],status='PASS' if actual=='PASS' else 'REJECTED',reason=actual,
            scope='Complete actual input' if actual=='PASS' else 'Quarantined alteration after real input identity validation'))
    require(len(observations)==len({o['name'] for o in observations})==45,'CASE_BOUND')
    return observations

def gate(inventory,results):
    argv=[sys.executable,str(TOOLS/'gate.py'),'--inventory',str(inventory),'--results',str(results)]
    p=subprocess.run(argv,capture_output=True,text=True,timeout=30)
    require(p.stderr=='','GATE_STDERR');return dict(exit_code=p.returncode,result=json.loads(p.stdout))

def slot(out):
    inventory=read(out/'inventory.json');inventory['tests']=[t for t in inventory['tests'] if t['id'] in (ID,'G0-U1-a')]
    save(out/'slot-inventory.json',inventory);result=gate(out/'slot-inventory.json',out/'results.json')
    save(out/'slot-gate.json',result)
    require(result['exit_code']==2 and result['result']==dict(status='BLOCKED',reasons=['missing G0-U1-a [macos-x86-64]','unreviewed S0-LL22-b [control]']),'SLOT_GATE')

def write_outputs(out,base,profile):
    summary=assess(base,profile);observations=exercise(base,profile)
    summary.update(id=ID,positive_cases=1,rejected_cases=len(observations)-1,review_disposition='NOT_REVIEWED')
    save(out/'summary.json',summary);save(out/'observations.json',observations)
    (out/'source-witness.json.gz').write_bytes(gzip.compress((json.dumps(dict(manifests=base['source'],restoration=base['restoration']),sort_keys=True,separators=(',',':'))+'\n').encode(),mtime=0))
    (out/'systems-before.lisp').write_bytes(base['systems_source']['before']);(out/'systems-after.lisp').write_bytes(base['systems_source']['after'])
    save(out/'cases.json',read(HERE/'cases.json'))

def run(out,evidence):
    require(not out.exists() and not out.is_relative_to(ROOT),'FRESH_EXTERNAL_OUTPUT');out.mkdir(parents=True)
    record=dict(version=1,status='FAIL',timestamp=datetime.now(timezone.utc).isoformat(),command=[sys.executable,*sys.argv],
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources()})
    try:
        profile,blobs=input_data(evidence);base=prepare(evidence,profile,blobs);write_outputs(out,base,profile)
        (out/'source').mkdir()
        for p in sources():
            dest=out/'source'/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
        (out/'inventory.json').write_bytes((ROOT/'doc/WASM/stage0/inventory.json').read_bytes())
        # Temporary hardlinks let the ordinary gate inspect real input bytes.
        # Publishing rebases these paths to existing evidence, without copies.
        (out/'references').mkdir()
        for i,item in enumerate(profile['inputs']):
            dest=out/'references'/str(i)
            try:os.link(evidence/item['path'],dest)
            except OSError:shutil.copyfile(evidence/item['path'],dest)
        save(out/'references.json',[dict(temporary_path='references/'+str(i),**item) for i,item in enumerate(profile['inputs'])])
        environment=dict(python=sys.version,executable=sys.executable,executable_sha256=sha(Path(sys.executable).resolve()),platform=platform.platform())
        save(out/'environment.json',environment)
        inventory=read(out/'inventory.json');test=next(t for t in inventory['tests'] if t['id']==ID)
        require(test['runner']==str(HERE.relative_to(ROOT)/'run.py'),'REGISTERED_RUNNER')
        artifacts=[]
        for p in sorted(out.rglob('*')):
            if not p.is_file() or p.is_relative_to(out/'references'):continue
            role='implementation' if p.name in ('r6_registration.py','registration.py') else 'test' if p.name=='run.py' else 'schema' if p.name in ('inputs.json','cases.json','inventory.json','patch.json') else 'log'
            artifacts.append(dict(path=str(p.relative_to(out)),role=role,sha256=sha(p)))
        artifacts.extend(dict(path='references/'+str(i),role=item['role'],sha256=item['sha256']) for i,item in enumerate(profile['inputs']))
        result=dict(id=ID,variant='control',source_revision=test['source_revision'],evidence_kind=test['evidence_kind'],status='PASS',
            assertions=[dict(id=a['id'],status='PASS') for a in test['assertions']],artifacts=artifacts,substitutions=[],skips=[],
            review_disposition='NOT_REVIEWED',command=record['command'],timestamp=record['timestamp'],test_revision=sha(HERE/'run.py'),
            toolchain=environment,engine='Python R6 comparator; actual native evidence reused, never executed here',seed='45 named cases',
            configuration=read(out/'summary.json'))
        save(out/'results.json',bind_report(dict(version=1,source_revision=inventory['source_revision'],inventory_sha256=sha(out/'inventory.json'),results=[result]),inventory,'inventory.json',sha(out/'inventory.json')))
        slot(out);record.update(status='PASS',contract_sha256=contract_hash(inventory,ID))
        require(record['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_CHANGED')
        print('PASS S0-LL22-b: actual patch applied/restored; 1 complete input, 44 rejected controls; native execution reused.')
    except BaseException as e:record['error']=type(e).__name__+': '+str(e);raise
    finally:save(out/'run.json',record)

def verify(packet,evidence):
    record=read(packet/'run.json');require(record['status']=='PASS','RUN_STATUS')
    require(record['source_sha256']=={str(p.relative_to(ROOT)):sha(p) for p in sources()},'SOURCE_PINS')
    profile,blobs=input_data(evidence);base=prepare(evidence,profile,blobs)
    with tempfile.TemporaryDirectory(prefix='ccl-r6-replay-') as tmp:
        fresh=Path(tmp);write_outputs(fresh,base,profile)
        for p in fresh.iterdir():require(p.read_bytes()==(packet/p.name).read_bytes(),'REPLAY '+p.name)
    print('PASS retained R6 comparison, source reversal and all 45 cases reproduce.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);p.add_argument('--evidence',type=Path,required=True)
    a=p.parse_args();run(a.output.resolve(),a.evidence.resolve()) if a.output else verify(a.verify.resolve(),a.evidence.resolve())
