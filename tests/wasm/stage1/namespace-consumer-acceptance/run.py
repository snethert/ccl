"""Verify exact reviewed product integration and exercise its runtime anew."""
from pathlib import Path
import argparse, hashlib, importlib.util, json, shutil, subprocess, sys, tarfile
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c
import storage
import refusals

PACKET='2026-09-24-namespace-consumers-r1'
PACKET_SHA='e851adaecfa7b5e441f975fe8157e6018f94799a5d33469e840a17596b720f31'

def standing(out):
 out.mkdir(parents=True,exist_ok=True)
 for name in ('ready-acceptance','ready-runtime-acceptance','stream-constructor-acceptance'):
  spec=importlib.util.spec_from_file_location(name,HERE.parent/name/'check.py')
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  result=module.check() if name=='stream-constructor-acceptance' else module.check(c.STORE)
  assert result['status']=='PASS'
  c.save(out/(name+'.json'),result)
  if name=='stream-constructor-acceptance':
   try:module.check(None)
   except AssertionError as error:
    assert str(error)=='compiler/WASM32/wasm32-backend.lisp'
    c.save(out/'r13-rejects-successor.json',dict(status='PASS',successor_rejected=True,reason=str(error)))
   else:raise AssertionError('namespace successor must not pass R13 historical identity')

def identity():
 packet=c.STORE/PACKET
 assert c.sha(packet/'packet.json')==PACKET_SHA
 manifest=c.read(packet/'packet.json')['files']
 def bound(name):
  assert c.sha(packet/name)==manifest[name],name
  return c.read(packet/name)
 summary=bound('summary.json');native=bound('native/qualification.json')
 c.verify_files(c.ROOT,summary['implementation_inputs'])
 primitive=bound('primitive-r2/pins.json')
 for name in ('host.mjs','protocol.mjs'):
  path='tests/wasm/stage1/namespace-primitives/'+name
  assert c.sha(c.ROOT/path)==primitive[path],path
 readers=bound('readers/summary.json');integration=c.read(c.ROOT/'doc/WASM/stage1/integration-namespace-consumers.json')
 assert integration['packet']['sha256']==PACKET_SHA
 for name,digest in integration['qualification']['records'].items():
  assert c.sha(packet/name)==manifest[name]==digest,name
 review=integration['review']
 blob=subprocess.check_output(['git','show',review['commit']+':'+review['path']],cwd=c.ROOT)
 assert hashlib.sha256(blob).hexdigest()==review['sha256']
 for name,digest in native['source_identity'].items():
  assert c.sha(c.ROOT/name)==digest,name
 sources={**summary['source_identity'],**summary['runtime_identity']}
 assert len(sources)==15
 assert {row['file']:row['after'] for row in integration['files']}==sources
 assert all(row['after']==row['reviewed'] for row in integration['files'])
 for name,digest in sources.items():
  assert c.sha(c.ROOT/name)==digest==manifest['proposal/'+name],name
  assert c.sha(packet/'proposal'/name)==digest,name
  if name in summary['source_identity']:
   assert native['source_identity'][name]==digest,name
   if '/WASM32/' not in name:assert readers['full_sources'][name]['after']==digest,name
 return packet,manifest,dict(status='PASS',source_identity=sources,
  native_tests_reused=21843,corpus_comparisons_reused=26048,
  existing_target_reader_rows_reused=153,source_packet=PACKET,source_packet_sha256=PACKET_SHA,
  slot_credit=False,accepted_originals=575,accepted_non_nil=535,
  files_cross_compiled=0,files_cross_loaded=0,files_target_loaded=0)

def run(out):
 out.mkdir(parents=True,exist_ok=True)
 packet,manifest,result=identity()
 standing(out/'standing')
 for name in ('execution.tar.gz','execution-inputs.json'):
  assert c.sha(packet/name)==manifest[name]
 with tarfile.open(packet/'execution.tar.gz') as archive:archive.extractall(out,filter='data')
 target=out/'target';c.verify_files(target,c.read(packet/'execution-inputs.json'))
 # Match integrated source to the archived source and rebuild each C service.
 for name in result['source_identity']:
  if not name.startswith('runtime/'):continue
  dst=target/'runtime'/Path(name).name
  assert c.sha(dst)==c.sha(c.ROOT/name),name
  shutil.copyfile(c.ROOT/name,dst)
 for service in ('collector','symbols'):
  binary=out/(service+'.wasm')
  flags=refusals.FLAGS if service=='symbols' else [
   f for f in refusals.FLAGS if f!='-Wl,--export-all']+['-Wl,--export=collect','-Wl,--export=__stack_pointer']
  c.command(['/usr/local/opt/llvm/bin/clang',*flags,target/'runtime'/(service+'.c'),'-o',binary],out/(service+'.build.log'))
  assert c.sha(binary)==c.sha(target/(service+'.wasm')),service
  shutil.copyfile(binary,target/(service+'.wasm'))
 profiles=[]
 for base in (8388608,2146500608):
  for move in (False,True):
   suffix=f'{base}-{str(move).lower()}'
   args=[c.NODE,HERE.parent/'namespace-consumers/check.mjs',target,'--namespace','--foreign']
   if base>8388608:args.append('--high')
   if move:args.append('--move')
   c.command(args,out/('replay-'+suffix+'.log'),timeout=180)
   name='consumer-result-'+suffix+'.json'
   assert c.sha(packet/'consumers'/name)==manifest['consumers/'+name]
   assert c.read(out/name)==c.read(packet/'consumers'/name),name
   profiles.append(dict(base=base,move=move,record=c.sha(out/name)))
 controls=refusals.run(out/'admission',c.ROOT/'runtime/wasm32/symbols.c')
 result.update(new_runtime_execution=True,profiles=profiles,
  independent_refusals=len(controls['controls']),isolated_mutants=len(controls['isolated_mutants']),
  equivalent_clauses=1,admission=c.sha(out/'admission/refusals.json'))
 c.save(out/'integration.json',result)
 return result

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('out',type=Path)
 a=parser.parse_args()
 with storage.lease([a.out]):result=run(a.out)
 print(json.dumps({k:v for k,v in result.items() if k not in ('source_identity','profiles')}))
