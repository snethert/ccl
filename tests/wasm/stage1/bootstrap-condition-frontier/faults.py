"""Focused executable controls for the new constructor and class dispatch."""
import json,re,shutil,subprocess,sys
from pathlib import Path

def controls(out):
    native=json.loads((out/'compiled/native.json').read_text());root=out/'condition-faults';root.mkdir()
    cases=[]
    bad=(out/'compiled/core_condition_bad_slot.wat').read_text()
    pattern=r'\(i32.store offset=24 \(call \$condition_slots \(local.get (\$\w+)\)\) \(i32.load offset=24 \(local.get \$\w+\)\)\)'
    found=list(re.finditer(pattern,bad));assert len(found)==1,len(found)
    m=found[0]
    cases.append(('last-slot-omitted','CORE-CONDITION-BAD-SLOT',bad[:m.start()]+'(nop)'+bad[m.end():]))
    cases.append(('default-overwritten','CORE-CONDITION-BAD-SLOT',bad[:m.start()]+f'(i32.store offset=16 (call $condition_slots (local.get {m[1]})) (i32.const 77825))'+bad[m.start():]))
    package=(out/'compiled/core_condition_simple_package.wat').read_text()
    pattern=r'\(if \(result i32\) \(i32.and \(call \$condition_mask .*?\) \(i32.const 16777216\)\) \(then \(i32.const 16\)\) \(else \(i32.const 8\)\)\)'
    matches=list(re.finditer(pattern,package));assert len(matches)==1,len(matches)
    m=matches[0];cases.append(('inherited-package-offset','CORE-CONDITION-SIMPLE-PACKAGE',package[:m.start()]+'(i32.const 8)'+package[m.end():]))
    closed=(out/'compiled/core_condition_stream.wat').read_text()
    anchor='(then (br 1 (i32.const 1048576)))'
    assert closed.count(anchor)==2
    cases.append(('stream-parent-mask','CORE-CONDITION-STREAM',closed.replace(anchor,'(then (br 1 (i32.const 4194304)))')))
    result=[]
    for name,definition,wat in cases:
        d=root/name;d.mkdir();compiled=d/'compiled';compiled.mkdir()
        for f in out.iterdir():
            if f.name not in ('compiled','condition-faults'): (d/f.name).symlink_to(f,target_is_directory=f.is_dir())
        for f in (out/'compiled').iterdir():(compiled/f.name).symlink_to(f,target_is_directory=f.is_dir())
        selected=[r for r in native if r['definition']==definition];assert selected
        p=compiled/'native.json';p.unlink();p.write_text(json.dumps(selected))
        module=selected[0]['name'];p=compiled/(module+'.wat');p.unlink();p.write_text(wat)
        p=compiled/(module+'.wasm');p.unlink()
        subprocess.run(['/usr/local/bin/wat2wasm','--enable-threads','--enable-exceptions','--enable-tail-call',compiled/(module+'.wat'),'-o',p],check=True)
        with (d/'refusal.log').open('w') as log:
            run=subprocess.run(['/usr/local/bin/node',out/'check.mjs',d,d/'result.json'],stdout=log,stderr=subprocess.STDOUT,timeout=120)
        text=(d/'refusal.log').read_text()
        assert run.returncode and definition in text and ('AssertionError' in text or module+': checked ' in text),(name,text[-2000:])
        assert 'RuntimeError: memory access out of bounds' not in text,text[-2000:]
        result.append(dict(name=name,definition=definition,rejected=True))
    (out/'condition-controls.json').write_text(json.dumps(dict(status='PASS',faults=result),indent=2,sort_keys=True)+'\n')
if __name__=='__main__':controls(Path(sys.argv[1]).resolve())
