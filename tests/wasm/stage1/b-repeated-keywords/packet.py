#!/usr/bin/env python3
"""Retain and replay one auxiliary proposal without duplicating native baselines."""
import argparse,hashlib,importlib.util,json,shutil,subprocess,sys,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE.parent/'constants';REG=HERE.parent/'registration'
sys.path.insert(0,str(BASE))
from backend import generate

def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(argv,log):
    with log.open('w') as f:subprocess.run(list(map(str,argv)),check=True,stdout=f,stderr=subprocess.STDOUT)
def qualify(evidence,native,out):
    if (native/'proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()!=generate():raise ValueError('native compiler identity')
    command([sys.executable,REG/'qualify.py','--output',native,'--inputs',evidence/'macos-u1-inputs','--kernel',evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64','--destination',out],out.with_suffix('.log'))
def pins():
    spec=importlib.util.spec_from_file_location('constants_run_pins',BASE/'run.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    result=m.source_pins()
    for p in list(HERE.glob('*'))+[BASE/'review-followup/run.py']:
        if p.is_file():result[str(p.relative_to(ROOT))]=sha(p)
    return result

def archive(out,rows):
    with tarfile.open(out,'w:gz') as t:
        for path,name in rows:t.add(path,arcname=name)

def inherited_identity(evidence,inherited):
    count=0;names=set()
    parent='2026-09-17-stage1-ll10-r1/inherited.tar.gz'
    with tarfile.open(evidence/parent) as t:
        for m in t.getmembers():
            p=Path(m.name)
            if p.parts[0]=='positive' and len(p.parts)==2 and p.suffix in ('.wat','.wasm'):
                if t.extractfile(m).read()!=(inherited/p).read_bytes():raise ValueError('inherited changed '+str(p))
                count+=1;names.add(p.name)
    actual={p.name for p in (inherited/'positive').iterdir() if p.suffix in ('.wat','.wasm')}
    if count!=1178 or names!=actual:raise ValueError('inherited binary population')
    return {'status':'PASS','parent':parent,'files':count,'scope':'Inherited positive WAT and Wasm byte-identical to accepted LL10.'}

def retain(evidence,run,native,inherited,out):
    if out.exists():raise ValueError('never overwrite packet')
    for p in (run/'summary.json',native/'run.json',inherited/'summary.json'):
        if read(p)['status']!='PASS':raise ValueError('incomplete run '+str(p))
    backend=generate()
    for p in (run/'wasm32-backend.lisp',native/'proposal/files/compiler/WASM32/wasm32-backend.lisp',inherited/'harness/wasm32-backend.lisp'):
        if p.read_text()!=backend:raise ValueError('compiler join '+str(p))
    out.mkdir(parents=True);qualify(evidence,native,out/'qualification')
    save(out/'inherited-identity.json',inherited_identity(evidence,inherited))
    save(out/'source-pins.json',pins());shutil.copy(run/'summary.json',out/'summary.json')
    shutil.copy(run/'native-keyword-answers.json',out/'native-keyword-answers.json')
    shutil.copy(run/'controls.json',out/'controls.json')
    (out/'wasm32-backend.lisp').write_text(backend)
    for name,directory in (('execution',run),('inherited',inherited)):
        archive(out/(name+'.tar.gz'),[(p,str(p.relative_to(directory))) for p in sorted(directory.rglob('*')) if p.is_file() and '__pycache__' not in p.parts])
    # The accepted baseline is immutable and is referenced, not copied again.
    prior=evidence/'2026-09-16-stage1-1a-r2'
    known={r['sha256']:str((prior/r['path']).relative_to(evidence)) for r in read(prior/'packet.json')['files']}
    refs=[];rows=[]
    for p in sorted(native.rglob('*')):
        if not p.is_file():continue
        h=sha(p);rel=str(p.relative_to(native))
        if h in known:refs.append({'path':rel,'sha256':h,'evidence_path':known[h]})
        else:rows.append((p,rel))
    archive(out/'native.tar.gz',rows);save(out/'native-references.json',refs)
    save(out/'validation.json',{'native':read(native/'run.json'),'qualification':read(out/'qualification/summary.json'),'inherited':read(inherited/'summary.json'),'loader':read(inherited/'full-loader/summary.json'),'scope':'Executed proposal; NOT_REVIEWED. No acceptance, integration or inventory changes.'})
    save(out/'development.json',{'status':'No implementation failure in this unit. First target run and all controls passed.','prior_survey':'Scratch ARM survey established the previous validator refusal; not claimed as qualification evidence here.'})
    save(out/'packet.json',{'id':'STAGE1-B-REPEATED-KEYWORDS-R1','review_disposition':'NOT_REVIEWED','files':[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.rglob('*')) if p.is_file()]})

def verify(evidence,packet,out):
    out.mkdir(parents=True,exist_ok=False)
    for r in read(packet/'packet.json')['files']:
        p=(packet/r['path']).resolve()
        if not p.is_relative_to(packet.resolve()) or sha(p)!=r['sha256']:raise ValueError('packet '+r['path'])
    for name,h in read(packet/'source-pins.json').items():
        if sha(ROOT/name)!=h:raise ValueError('source changed '+name)
    if (packet/'wasm32-backend.lisp').read_text()!=generate():raise ValueError('proposal derivation')
    native=out/'native';native.mkdir()
    with tarfile.open(packet/'native.tar.gz') as t:t.extractall(native,filter='data')
    for r in read(packet/'native-references.json'):
        src=(evidence/r['evidence_path']).resolve();dst=(native/r['path']).resolve()
        if not src.is_relative_to(evidence.resolve()) or not dst.is_relative_to(native) or dst.exists() or sha(src)!=r['sha256']:raise ValueError('reference')
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy(src,dst)
    qualify(evidence,native,out/'qualification')
    target=out/'execution';command([sys.executable,HERE/'run.py','--evidence',evidence,'--output',target],out/'execution.log')
    inherited=out/'inherited';command([sys.executable,HERE/'inherited.py','--evidence',evidence,'--output',inherited],out/'inherited.log')
    if inherited_identity(evidence,inherited)!=read(packet/'inherited-identity.json'):raise ValueError('inherited identity replay')
    compared=0
    for name,dest in (('execution',target),('inherited',inherited)):
        with tarfile.open(packet/(name+'.tar.gz')) as t:
            for member in t.getmembers():
                p=Path(member.name)
                if p.suffix in ('.wasm','.wat','.dx64fsl') or p.name in ('summary.json','native-keyword-answers.json','controls.json','execution.json','expected.json','expected-restored.json','native.json','identity.json'):
                    if t.extractfile(member).read()!=(dest/member.name).read_bytes():raise ValueError('replay '+name+'/'+member.name)
                    compared+=1
    save(out/'verification.json',{'status':'PASS','deterministic_files':compared,'source_pins':len(read(packet/'source-pins.json')),'native_qualification':read(out/'qualification/summary.json')})
    print(json.dumps(read(out/'verification.json')))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['retain','verify']);p.add_argument('--evidence',type=Path,default=ROOT.parent/'ccl-evidence');p.add_argument('--output',type=Path,required=True)
    for n in ('run','native','inherited','packet'):p.add_argument('--'+n,type=Path)
    a=p.parse_args()
    if a.mode=='retain':retain(a.evidence.resolve(),a.run.resolve(),a.native.resolve(),a.inherited.resolve(),a.output.resolve())
    else:verify(a.evidence.resolve(),a.packet.resolve(),a.output.resolve())
