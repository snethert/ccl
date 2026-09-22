"""Existing-target reader proof for the two added Wasm source branches."""
import hashlib,importlib.util,json,os,shutil,subprocess,tarfile,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
import backend

def replay(evidence,proposal,out):
 out.mkdir();before=out/'before';after=out/'after';before.mkdir();after.mkdir()
 paths=['level-1/l1-numbers.lisp','level-0/l0-array.lisp'];proof=[]
 for name in paths:
  old=(ROOT/name).read_text();new=(proposal/name).read_text()
  if name.endswith('l1-numbers.lisp'):
   start=new.index('\n#+wasm32-target\n(defun %double-float-expt!')
   prefix=new[:start]
   # The original file has no Wasm exclusion tokens; the new tokens sit only
   # immediately before the selected native DEFUNs. All remaining bytes agree.
   assert '#-wasm32-target\n' not in old
   assert prefix.replace('#-wasm32-target\n','')==old
   count=prefix.count('#-wasm32-target\n');assert count>=26
   a='\n'.join('(retained-native-definition '+str(i)+')' for i in range(count))
   b='\n'.join('#-wasm32-target\n(retained-native-definition '+str(i)+')' for i in range(count))+new[start:]
  else:
   start=new.index('      #+wasm32-target\n      (svref')
   end=new.index('      #+arm-target\n      (svref arm::*immheader-array-types*',start)
   assert new[:start]+new[end:]==old
   count=1;a='';b=new[start:end]
  for directory,text in ((before,a),(after,b)):
   p=directory/name;p.parent.mkdir(exist_ok=True);p.write_text('(in-package :ccl)\n'+text+'\n')
  proof.append(dict(file=name,original_sha256=hashlib.sha256(old.encode()).hexdigest(),proposal_sha256=hashlib.sha256(new.encode()).hexdigest(),sites=count,inverse_bytes_equal=True))
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
 rows=json.loads((out/'readers.json').read_text())['rows'];assert len(rows)==34 and all(x['equal'] for x in rows)
 for p in out.glob('*.forms'):p.unlink()
 (out/'summary.json').write_text(json.dumps(dict(status='PASS',comparisons=len(rows),inverse=proof,scope='New conditional forms read identically on all seventeen existing target profiles; inverse edits prove every original source byte is retained. Earlier integrated branches reuse their accepted reader proofs.'),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':
 import sys
 replay(*(Path(x).resolve() for x in sys.argv[1:]))
