"""Existing-target reader proof for target branches and definition-level FFI exclusions."""
import hashlib,importlib.util,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
import backend

def replay(evidence,proposal,out):
 out.mkdir();before=out/'before';after=out/'after';before.mkdir();after.mkdir()
 edits={
  'level-1/l1-aprims.lisp': ('(defun lfun-keyvect (lfun)\n  (let', '(defun lfun-keyvect (lfun)\n  #+wasm32-target (%wasm-function-keyvect lfun)\n  #-wasm32-target\n  (let'),
  'level-1/l1-clos-boot.lisp': ('(defun %non-standard-instance-slots (instance typecode)\n  (cond', '(defun %non-standard-instance-slots (instance typecode)\n  #+wasm32-target\n  (if (eql typecode target::subtag-function)\n    (gf.slots instance)\n    (error "Don\'t know how to find slots of ~s" instance))\n  #-wasm32-target\n  (cond')}
 exclusions=json.loads((HERE/'exclusions.json').read_text())
 paths=sorted(set(edits)|set(exclusions));proof=[]
 for name in paths:
  old=(ROOT/name).read_text();new=(proposal/name).read_text();restored=new
  before_forms=[];after_forms=[]
  for function in exclusions.get(name,[]):
   marker='(defun '+function+' ';guard='#-wasm32-target\n'+marker
   assert restored.count(guard)==1
   restored=restored.replace(guard,marker)
   form='(defun '+function+' () (retained-native-body))'
   before_forms.append(form);after_forms.append('#-wasm32-target\n'+form)
  if name in edits:
   a,b=edits[name];assert old.count(a)==1 and restored.count(b)==1
   restored=restored.replace(b,a)
   before_forms.append(a.rsplit('\n',1)[0]+'\n  (retained-native-body))')
   after_forms.append(b.rsplit('\n',1)[0]+'\n  (retained-native-body))')
  assert restored==old,name
  for directory,forms in ((before,before_forms),(after,after_forms)):
   p=directory/name;p.parent.mkdir(parents=True,exist_ok=True)
   p.write_text('(in-package :ccl)\n'+'\n'.join(forms)+'\n')
  proof.append(dict(file=name,original_sha256=hashlib.sha256(old.encode()).hexdigest(),proposal_sha256=hashlib.sha256(new.encode()).hexdigest(),sites=len(before_forms),inverse_bytes_equal=True))
 text=(HERE.parent/'bootstrap-core-acceptance/readers.lisp').read_text()
 old='(dolist (stem \'("l0-def" "l0-pred" "l0-utils"))\n            (let* ((relative (concatenate \'string "level-0/" stem ".lisp"))'
 new='(dolist (relative \'('+ ' '.join('"'+p+'"' for p in paths)+'))\n            (let* ((stem (pathname-name relative))'
 assert text.count(old)==1;text=text.replace(old,new).replace('(getenv "READER_U1"))))','(getenv "READER_ARCH_SOURCE"))))',1)
 script=out/'readers.lisp';script.write_text(text)
 with tempfile.TemporaryDirectory(prefix='ccl-math-reader-') as temp:
  source=Path(temp)
  for name in ('source.tar','bootstrap.tar.gz'):
   with tarfile.open(evidence/'macos-u1-inputs'/name) as archive:archive.extractall(source,filter='data')
  shutil.copy(evidence/'2026-09-12-native-census-r7/baseline/build/dx86cl64',source/'dx86cl64');(source/'dx86cl64').chmod(0o755)
  env=dict(os.environ,CCL_DEFAULT_DIRECTORY=str(source)+'/',READER_U1=str(before)+'/',READER_PROPOSAL=str(after)+'/',READER_OUTPUT=str(out)+'/',READER_ARCH_SOURCE=str(source)+'/')
  with (out/'run.log').open('w') as log:subprocess.run([source/'dx86cl64','--no-init','--batch','--load',ROOT/'tests/wasm/native-census/observer.lisp','--load',script],cwd=source,env=env,stdout=log,stderr=log,check=True,timeout=120)
 rows=json.loads((out/'readers.json').read_text())['rows'];assert len(rows)==17*len(paths) and all(x['equal'] for x in rows)
 for p in out.glob('*.forms'):p.unlink()
 (out/'summary.json').write_text(json.dumps(dict(status='PASS',comparisons=len(rows),inverse=proof,scope='New conditional forms read identically on all seventeen existing target profiles; inverse edits prove every original source byte is retained. Earlier integrated branches reuse their accepted reader proofs.'),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':
 import sys
 replay(*(Path(x).resolve() for x in sys.argv[1:]))
