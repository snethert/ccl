"""Refusal controls for generated-symbol normalization and native code checks."""
from pathlib import Path
import json,sys,tarfile
import comparison
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'bootstrap-validation'))
import common as c

def run(out):
 out.mkdir(parents=True,exist_ok=True)
 with tarfile.open(c.STORE/'2026-09-16-stage1-1a-r2/native/baseline-fasls.tar.gz') as archive,tarfile.open(c.STORE/'macos-u1-inputs/source.tar') as src:
  data=archive.extractfile('bin/hashenv.dx64fsl').read();source=src.extractfile('xdump/hashenv.lisp').read().decode()
 decoder=comparison.base_comparator()['CompilerFasl'](data);forms=decoder.decode()
 f=next(row['defmacro'][0]['function'] for row in forms if 'defmacro' in row)
 code=bytes.fromhex(f['code']);code_at=data.index(code)
 _,spans,_=comparison.debug_bytes(data,True)
 generated=next(s for s in spans if not s.get('macro_arglist') and s['name'].startswith('G'))
 rows=[]
 for name,offset in [('executable-byte',code_at),('interned-identity',data.index(b'FUNCTION-SYMBOL-MAP')),('gensym-prefix',generated['end']-len(generated['name']))]:
  altered=bytearray(data);altered[offset]^=1
  try:comparison.compare(data,bytes(altered),source,source,'xdump/hashenv.lisp')
  except (AssertionError,ValueError,KeyError):rows.append(dict(name=name,status='REFUSED'))
  else:raise AssertionError('native comparison accepted '+name)
 with tarfile.open(c.STORE/'2026-09-16-stage1-1a-r2/native/baseline-fasls.tar.gz') as archive,tarfile.open(c.STORE/'macos-u1-inputs/source.tar') as src:
  data=archive.extractfile('xdump/xfasload.dx64fsl').read();source=src.extractfile('xdump/xfasload.lisp').read().decode()
 decoder=comparison.base_comparator()['CompilerFasl'](data);forms=decoder.decode()
 # Force the shared-source comparison path, with harmless trailing whitespace.
 comparison.compare(data,data,source,source+'\n','xdump/xfasload.lisp')
 for label,marker in [('old-accessor','CCL::BACKEND-XLOAD-INFO-NAME'),('old-setter','COMMON-LISP::SETF')]:
  candidates=[row['defun'][0] for row in forms if 'defun' in row and 'CCL::BACKEND-XLOAD-INFO-NAME' in json.dumps(row['defun'][0]['function']['constants'][-2])]
  wrapper=next(f for f in candidates if ('COMMON-LISP::SETF' in json.dumps(f['function']['constants'][-2]))==(label=='old-setter'))
  code=bytes.fromhex(wrapper['function']['code']);start,end=decoder.spans[id(wrapper)]
  altered=bytearray(data);altered[data.index(code,start,end)]^=1
  try:comparison.compare(data,bytes(altered),source,source+'\n','xdump/xfasload.lisp')
  except AssertionError as e:
   assert 'unexplained native difference' in str(e),str(e)
   rows.append(dict(name=label,status='REFUSED'))
  else:raise AssertionError('native comparison accepted '+label)
 result=dict(status='PASS',rows=rows)
 c.save(out/'controls.json',result);return result
if __name__=='__main__':print(run(Path(sys.argv[1]).resolve()))
