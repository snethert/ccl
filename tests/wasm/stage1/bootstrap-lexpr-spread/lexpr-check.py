"""Exercise the exact emitted lexpr frame validator independently of callers."""
from pathlib import Path
import json,re,subprocess,sys,hashlib
HERE=Path(__file__).resolve().parent
out=Path(sys.argv[1]).resolve();text=(out/'compiled/core_lexpr_list.wat').read_text()
pattern=r'\(local.set (\$\w+) \(i32.load offset=128 \(global.get \$tcr\)\)\) \(local.set (\$\w+) \(local.get \$top\)\)\(block \$lexpr_found.*?\(local.set (\$\w+) \(i32.shr_u \(local.get \3\) \(i32.const 2\)\)\)'
m=re.search(pattern,text);assert m,'emitted validator'
body=m[0];frame,limit,length=m[1],m[2],m[3]
pointer=re.search(r'\(br_if \$lexpr_found \(i32.eq \(local.get (\$\w+)\)',body)[1]
names=set(re.findall(r'local\.(?:get|set) (\$\w+)',body))-{pointer,'$top'}
prefix='(module (import "env" "memory" (memory 80 32769 shared)) (import "env" "error" (tag $call_error (param i32))) (global $tcr i32 (i32.const 1024)) (func (export "validate") (param '+pointer+' i32) (param $top i32) (result i32) '+''.join('(local '+n+' i32)' for n in sorted(names))
suffix=' (local.get '+length+')))'
directory=out/'lexpr-validation';directory.mkdir(exist_ok=True)
wat=directory/'validator.wat';wat.write_text(prefix+body+suffix)
subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions',wat,'-o',directory/'validator.wasm'],check=True)
subprocess.run(['/usr/local/bin/node',HERE/'lexpr-check.mjs',directory],check=True)

parent=HERE.parents[3].parent/'ccl-evidence/2026-09-22-stage1-bootstrap-condition-frontier-r1'
expected=json.loads((parent/'deterministic.json').read_text())
legacy=[]
for file in sorted((out/'compiled').glob('*.legacy')):
    key='numeric/compiled/'+file.name
    digest=hashlib.sha256(file.read_bytes()).hexdigest()
    assert expected[key]==digest,file.name
    legacy.append(dict(file=file.name,sha256=digest))
assert len(legacy)==10
(directory/'legacy.json').write_text(json.dumps(dict(status='PASS',files=legacy),indent=2,sort_keys=True)+'\n')
