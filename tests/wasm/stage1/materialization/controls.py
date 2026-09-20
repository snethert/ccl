"""Faults run the unchanged materialization and native execution assertions."""
import json,shutil,subprocess
from backend import HERE,generate,replace
def run(out,compile,e):
 rows=[];dest=out/'mutants';dest.mkdir()
 faults=[
  ('shared-bit',"bytes[actual.offset]=shared?3:1;","bytes[actual.offset]=1;",'BINARY_IDENTITY'),
  ('callback-bit',"bytes[actual.offset]=shared?3:1;","bytes[actual.offset]=3;",'BINARY_IDENTITY'),
  ('trusted-offset',"need(same(actual,record),'TEMPLATE_RECORD');","/* omitted */",'CONTROL wrong-offset escaped'),
  ('abi-inventory',"need(same(s.imports,abi.imports)&&same(s.exports,abi.exports),'ABI_INVENTORY');","/* omitted */",'CONTROL abi-import escaped'),
  ('classification-digest',"need(c.binary_sha256===sha256(bytes),'CLASSIFICATION_DIGEST');","/* omitted */",'CONTROL classification-bytes escaped'),
  ('wait-and-legacy',"need(c.wait===false&&c.legacy===false,'FORBIDDEN_INSTRUCTIONS');","/* omitted */",'CONTROL wait escaped'),
  ('engine-features',"need(c.features.every(f=>policy.features.includes(f)),'FEATURE_NOT_ADMITTED');","/* omitted */",'CONTROL unknown-feature escaped'),
  ('engine-profile',"need(policy.admission[profile]===true,'PROFILE_NOT_ADMITTED');","/* omitted */",'CONTROL engine-profile escaped'),
  ('install-record',"need(same(record,expected.record),'INSTALL_RECORD');","/* omitted */",'CONTROL template-as-installed escaped'),
  ('installed-bytes',"need(sha256(bytes)===expected.record.binary_sha256,'INSTALLED_DIGEST');","/* omitted */",'CONTROL template-bytes-at-install escaped'),
 ]
 for name,old,new,diagnostic in faults:
  d=dest/name;d.mkdir()
  for folder in ['templates','baseline','malformed']:(d/folder).symlink_to(out/folder,target_is_directory=True)
  for n in ['policy.json','classifications.json','malformed.json','check.mjs','bytes.mjs','sha256.mjs','binary.mjs']:shutil.copy(out/n,d/n)
  (d/'materializer.mjs').write_text(replace((HERE/'materializer.mjs').read_text(),old,new))
  cmd=['/usr/local/bin/node',str(d/'check.mjs'),str(d)];(d/'command.json').write_text(json.dumps(cmd)+'\n')
  r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(d/'failure.log').write_text(r.stdout)
  assert r.returncode and diagnostic in r.stdout,(name,r.stdout[-2500:])
  rows.append(dict(name=name,status='REJECTED',diagnostic=diagnostic))
 # A compiler fault must recompile through U1; no binary edit stands in for it.
 d=dest/'compiler-shared-template';code=generate().replace('(if *wasm32-template-memory* "" " shared")','" shared"')
 compile(e,d,code,True)
 import sys
 sys.path.insert(0,str(HERE));from run import classify
 classes={p.stem:classify(p) for p in sorted(d.glob('*.wasm'))}
 check=dest/'compiler-check';check.mkdir()
 (check/'templates').symlink_to(d,target_is_directory=True);(check/'baseline').symlink_to(out/'baseline',target_is_directory=True)
 for n in ['policy.json','check.mjs','materializer.mjs','bytes.mjs','sha256.mjs','binary.mjs']:shutil.copy(out/n,check/n)
 (check/'classifications.json').write_text(json.dumps(classes,sort_keys=True)+'\n')
 cmd=['/usr/local/bin/node',str(check/'check.mjs'),str(check)]
 (check/'command.json').write_text(json.dumps(cmd)+'\n');r=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT);(check/'failure.log').write_text(r.stdout)
 assert r.returncode and 'CANONICAL_MEMORY' in r.stdout,r.stdout
 rows.append(dict(name='compiler-shared-template',status='REJECTED',diagnostic='CANONICAL_MEMORY'))
 (out/'controls.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n')
