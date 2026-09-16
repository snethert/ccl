#!/usr/bin/env python3
"""Lazy installation over pinned, reviewed compiler-generated B modules."""
import argparse,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
from prepare import HERE,ROOT,harness
BASE='2026-09-16-stage1-b-tail-calls-r1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def command(argv,out,name,timeout=180):
    save(out/(name+'-command.json'),argv)
    with (out/(name+'.log')).open('w') as log:
        child=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
    return child.returncode

def malformed(base,out):
    text=(base/'positive/v1.wat').read_text().rstrip()+'\n';assert text.endswith(')\n')
    changes={
      'active-data':(text[:-2]+'(data (i32.const 16) "\\aa"))\n','INITIALIZATION_OR_SECTION'),
      'active-element':(text[:-2]+'(elem (i32.const 0) func $body))\n','INITIALIZATION_OR_SECTION'),
      'start-writer':(text[:-2]+'(func $boot (i32.store (i32.const 16) (i32.const 99))) (start $boot))\n','INITIALIZATION_OR_SECTION'),
      'defined-table':(text[:-2]+'(table 1 funcref))\n','INITIALIZATION_OR_SECTION'),
      'extra-export':(text[:-2]+'(export "extra" (func $body)))\n','EXPORT_SET'),
      'wrong-export-signature':(text.replace('(export "entry")','(export "renamed")')[:-2]+'(func (export "entry") (param i64) (result i64) (local.get 0)))\n','EXPORT_SET'),
      'unshared-memory':(text.replace('(memory 1 32769 shared)','(memory 1 32769)'),'ENV_IMPORTS'),
      'mutable-tcr':(text.replace('(global $tcr i32)','(global $tcr (mut i32))'),'ENV_IMPORTS'),
      'extra-global':(text.replace('(func $span','(import "foreign" "alien" (global i32)) (func $span',1),'IMPORT_AUTHORITY'),
      'function-import':(text.replace('(func $span','(import "env" "evil" (func $evil)) (func $span',1),'FUNCTION_IMPORT'),
    }
    # Replace the export's index rather than adding a third export: both symbols
    # remain present, but public entry has the internal three-argument signature.
    changes['wrong-export-signature']=(text.replace('(export "entry")','').replace('(export "tail_entry")','(export "tail_entry") (export "entry")'),'EXPORT_SIGNATURE')
    (out/'malformed').mkdir()
    for name,(wat,_)in changes.items():
        p=out/'malformed'/(name+'.wat');p.write_text(wat)
        assert command(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',str(p),'-o',str(p.with_suffix('.wasm'))],out,'assemble-'+name)==0,name
    save(out/'malformed.json',{n:v[1]for n,v in changes.items()})

def prepare(evidence,out):
    assert not out.exists(),'NO_OVERWRITE';out.mkdir(parents=True)
    (out/'executed-sources').mkdir()
    for p in HERE.iterdir():
        if p.is_file():shutil.copy(p,out/'executed-sources'/p.name)
    base=evidence/BASE;pin=read(HERE/'inputs.json');assert pin['base_packet']==BASE and sha(base/'packet.json')==pin['manifest_sha256'],'REVIEWED_BASE'
    assert sha(ROOT/'compiler/WASM32/wasm32-backend.lisp')==pin['compiler_sha256'],'INTEGRATED_COMPILER_UNCHANGED'
    pins=read(base/'packet.json');expected={r['path']:r['sha256']for r in pins['files']}
    dependencies=[]
    def copy(rel,dest):
        p=base/rel;assert sha(p)==expected[rel],rel
        dependencies.append({'path':str(p.relative_to(evidence)),'sha256':expected[rel]})
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy(p,dest)
    for name in ['modules.json','cases.json','root-contracts.json']:copy('positive/'+name,out/name)
    for p in sorted((base/'positive/installed').glob('*.wasm')):copy('positive/installed/'+p.name,out/'installed'/p.name)
    for rel in ['execution.json','positive/v1.wat']:
        p=base/rel;assert sha(p)==expected[rel];dependencies.append({'path':str(p.relative_to(evidence)),'sha256':expected[rel]})
    original=ROOT/'tests/wasm/stage1/b-tail-calls/execute.mjs';assert sha(original)==read(base/'source-pins.json')[str(original.relative_to(ROOT))]
    dependencies.append({'path':str((base/'source/tests/wasm/stage1/b-tail-calls/execute.mjs').relative_to(evidence)),'sha256':sha(original)})
    save(out/'dependencies.json',dependencies)
    for p in HERE.glob('*.mjs'):shutil.copy(p,out/p.name)
    (out/'harness.mjs').write_text(harness());shutil.copy(HERE/'stub.wat',out/'stub.wat')
    assert command(['/usr/local/bin/wat2wasm','--enable-tail-call',str(out/'stub.wat'),'-o',str(out/'lazy-stub.wasm')],out,'stub-build')==0
    assert command(['/usr/local/bin/node',str(out/'catalog.mjs'),str(out),str(out/'catalog.json')],out,'catalog')==0
    alias=out/'path alias';alias.symlink_to(out,target_is_directory=True)
    assert command(['/usr/local/bin/node',str(alias/'catalog.mjs'),str(out),str(out/'alias-catalog.json')],out,'catalog-path-alias')==0
    assert (out/'alias-catalog.json').read_bytes()==(out/'catalog.json').read_bytes(),'CATALOG_PATH_ALIAS'
    malformed(base,out)

def run(evidence,out,mutants=True):
    prepare(evidence,out)
    assert command(['/usr/local/bin/node',str(out/'harness.mjs'),str(out),str(out/'execution.json')],out,'execution')==0,'POSITIVE '+str(out/'execution.log')
    result=read(out/'execution.json');lazy=result.pop('lazy_runs');assert result==read(evidence/BASE/'execution.json'),'UNCHANGED_ORACLE'
    assert all(any(e['event']=='INSTALLED'for e in r['events'])for r in lazy)
    assert command(['/usr/local/bin/node',str(out/'controls.mjs'),str(out),str(out/'controls.json')],out,'controls')==0,'CONTROLS '+str(out/'controls.log')
    mutations=[]
    if mutants:
        from mutants import run as test_mutants
        mutations=test_mutants(out,command)
    summary={'status':'PASS','modules':result['modules'],'comparisons':result['comparisons'],'tail_chains':len(result['tail_runs']),'tail_steps':100000,'stack_bytes':2048,
      'controls':len(read(out/'controls.json')['cases']),'mutants':len(mutations),
      'cold_installations':[sum(e['event']=='INSTALLED'for e in r['events'])for r in lazy],
      'distinct_installed_modules':[len({e['slot']for e in r['events']if e['event']=='INSTALLED'})for r in lazy],
      'scope':'Authenticating single-Worker lazy B/tail installation over unchanged reviewed generated modules. Native/compiler R6 evidence reused; full Lisp conditions, cleanup/binding extent, collection and complete LL05 qualification remain open.'}
    save(out/'summary.json',summary);print('S1-B-LAZY-CALLS-PASS',json.dumps(summary))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True,type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--no-mutants',action='store_true');a=p.parse_args();run(a.evidence.resolve(),a.output.resolve(),not a.no_mutants)
