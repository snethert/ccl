"""Small isolated edits over the accepted shared compiler; no patch chain."""
from pathlib import Path
import hashlib,json,shutil
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
PACKET=ROOT.parent/'ccl-evidence/2026-09-22-stage1-bootstrap-funcallable-r1'
BACKEND='compiler/WASM32/wasm32-backend.lisp';ARCH='compiler/WASM32/wasm32-arch.lisp'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def generate():
 text=(ROOT/BACKEND).read_text()
 marker='(defun bootstrap-function-immediate (forms storep)';assert text.count(marker)==1
 text=text.replace(marker,(HERE/'keywords.lisp').read_text()+'\n'+marker)
 marker="    (cond ((eq name 'ccl::%wasm-function-immediate)";assert text.count(marker)==1
 return text.replace(marker,"    (cond ((eq name 'ccl::%wasm-function-keyvect)\n           (b-multiple (make-b-raw-code :text (bootstrap-function-keyvect forms))))\n          ((eq name 'ccl::%wasm-function-immediate)")
def arch():return (ROOT/ARCH).read_text()
def source_files(root):
 manifest=json.loads((PACKET/'native/proposal/unit.json').read_text())
 result={r['path']:(root/r['path']).read_text() for r in manifest['added']+manifest['modified'] if r['path'].startswith(('level-0/','level-1/'))}
 name='level-1/l1-aprims.lisp';s=result[name];old='(defun lfun-keyvect (lfun)\n  (let';assert s.count(old)==1
 result[name]=s.replace(old,'(defun lfun-keyvect (lfun)\n  #+wasm32-target (%wasm-function-keyvect lfun)\n  #-wasm32-target\n  (let')
 name='level-1/l1-clos-boot.lisp';s=(root/name).read_text();old='(defun %non-standard-instance-slots (instance typecode)\n  (cond';assert s.count(old)==1
 result[name]=s.replace(old,'''(defun %non-standard-instance-slots (instance typecode)
  #+wasm32-target
  (if (eql typecode target::subtag-function)
    (gf.slots instance)
    (error "Don't know how to find slots of ~s" instance))
  #-wasm32-target
  (cond''')
 return result

def proposal(src,out):
 shutil.copytree(PACKET/'native/proposal',out)
 manifest=json.loads((out/'unit.json').read_text());edits={BACKEND:generate(),ARCH:arch(),**source_files(ROOT)}
 for row in manifest['added']+manifest['modified']:
  name=row['path'];path=out/'files'/name;path.write_text(edits.pop(name,(ROOT/name).read_text()))
  row['sha256' if 'sha256' in row else 'after']=sha(path)
 for name,text in edits.items():
  path=out/'files'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
  manifest['modified'].append(dict(path=name,before=sha(src/name),after=sha(path)))
 (out/'unit.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n');return manifest

def runtime_files():return {}
