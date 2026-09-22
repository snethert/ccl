"""Focused caller controls; only changed modules and small logs are retained."""
from pathlib import Path
import json,re,subprocess,sys

def controls(out):
 native=json.loads((out/'compiled/native.json').read_text());root=out/'lexpr-faults';root.mkdir()
 cases=[]
 for name,definition in [('tail-order','CORE-LEXPR-LIST'),('internal-order','CORE-LEXPR-VALUES')]:
  rows=[r for r in native if r['definition']==definition];assert rows
  module=rows[0]['name'];wat=(out/'compiled'/(module+'.wat')).read_text()
  pattern=r'\(i32.sub \(i32.add \(local.get (\$\w+)\) \(i32.const (\d+)\)\) \(local.get (\$\w+)\)\)'
  start=wat.index('(block $lexpr_done',wat.index('(block $lexpr_found'));end=wat.index('(br $lexpr_copy)))',start)
  matches=list(re.finditer(pattern,wat[start:end]));assert len(matches)==1
  m=matches[0];a=start+m.start();b=start+m.end()
  bad=wat[:a]+f'(i32.add (i32.sub (local.get {m[3]}) (i32.const {m[2]})) (i32.const 1))'+wat[b:]
  cases.append((name,definition,module,bad))
 definition='CORE-LEXPR-PREFIX';rows=[r for r in native if r['definition']==definition];module=rows[0]['name']
 wat=(out/'compiled'/(module+'.wat')).read_text()
 pattern=r'\(memory.copy \(i32.add \(local.get \$\w+\) \(i32.const (?:16|48)\)\) \(i32.add \(local.get \$\w+\) \(i32.const 16\)\) \(i32.const 4\)\)'
 matches=list(re.finditer(pattern,wat));assert len(matches)==1
 m=matches[0];cases.append(('prefix-omitted',definition,module,wat[:m.start()]+'(nop)'+wat[m.end():]))
 results=[]
 for name,definition,module,wat in cases:
  d=root/name;d.mkdir();compiled=d/'compiled';compiled.mkdir()
  for f in out.iterdir():
   if f.name not in ('compiled','lexpr-faults'):(d/f.name).symlink_to(f,target_is_directory=f.is_dir())
  for f in (out/'compiled').iterdir():(compiled/f.name).symlink_to(f,target_is_directory=f.is_dir())
  for filename in ('native.json',module+'.wat',module+'.wasm'):(compiled/filename).unlink()
  rows=[r for r in native if r['definition']==definition];(compiled/'native.json').write_text(json.dumps(rows))
  (d/'fault.wat').write_text(wat)
  subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',d/'fault.wat','-o',d/'fault.wasm'],check=True)
  (compiled/(module+'.wat')).symlink_to(d/'fault.wat');(compiled/(module+'.wasm')).symlink_to(d/'fault.wasm')
  with (d/'refusal.log').open('w') as log:
   run=subprocess.run(['/usr/local/bin/node',out/'check.mjs',d,d/'result.json'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
  text=(d/'refusal.log').read_text()
  assert run.returncode and definition in text and 'AssertionError' in text,(name,text[-2000:])
  assert 'RuntimeError:' not in text,(name,text[-2000:])
  (d/'refusal.log').write_text(text.replace(str(out),'<RUN>'))
  results.append(dict(name=name,definition=definition,rejected=True))
 (out/'lexpr-controls.json').write_text(json.dumps(dict(status='PASS',faults=results),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':controls(Path(sys.argv[1]).resolve())
