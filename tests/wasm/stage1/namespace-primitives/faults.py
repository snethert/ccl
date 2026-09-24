"""Directed bridge faults against generated callers and their native answers."""
from pathlib import Path
import subprocess
import sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'bootstrap-validation'))
import common as c

def run(out):
    directory=out/'faults';directory.mkdir(exist_ok=True)
    source=(HERE/'client.mjs').read_text()
    cases={
      'stale-buffer-after-collection':('object(get(args+8),[199,207,215,223,167,175,183])','object(bv,[199,207,215,223,167,175,183])','FD-READ: checked 4'),
      'omit-buffer-copy':('new Uint8Array(memory.buffer,buffer.base+4,length).set(bytes);',';','native values and buffer post-state'),
      'wrong-eof-count':('return (result*4)|0;','return ((op===1 && result===0?1:result)*4)|0;','native values and buffer post-state'),
      'omit-foreign-state':('Atomics.store(new Int32Array(memory.buffer), (tcr+32)/4,3);',';','request in FOREIGN'),
    }
    rows=[]
    for name,(old,new,reason) in cases.items():
        assert source.count(old)==1,name
        changed=source.replace(old,new).replace("'./protocol.mjs'",repr((HERE/'protocol.mjs').as_uri()))
        path=directory/(name+'.mjs');path.write_text(changed)
        log=directory/(name+'.log')
        with log.open('w') as stream:
            result=subprocess.run([c.NODE,HERE/'check.mjs',out,path],stdout=stream,stderr=subprocess.STDOUT,timeout=30)
        assert result.returncode and reason in log.read_text(),(name,log.read_text())
        rows.append(dict(name=name,status='REJECTED',reason=reason))
    source=(HERE/'host.mjs').read_text()
    old='session.read(a,Math.min(c,CAPACITY))'
    assert source.count(old)==1
    path=directory/'omit-read-cap.mjs'
    path.write_text(source.replace(old,'session.read(a,c)').replace("'./protocol.mjs'",repr((HERE/'protocol.mjs').as_uri())))
    log=directory/'omit-read-cap.log'
    with log.open('w') as stream:
        result=subprocess.run([c.NODE,HERE/'check.mjs',out,HERE/'client.mjs',path],stdout=stream,stderr=subprocess.STDOUT,timeout=30)
    assert result.returncode and 'request result range' in log.read_text(),log.read_text()
    rows.append(dict(name='omit-read-cap',status='REJECTED',reason='request result range'))
    c.save(out/'faults.json',dict(status='PASS',rows=rows))
    return rows
