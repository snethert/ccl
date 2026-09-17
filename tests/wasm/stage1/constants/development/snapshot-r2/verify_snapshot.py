#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from pool import compile_pool
from test_pool import graph, vector, cons, ref, integer, NIL

HERE=Path(__file__).resolve().parent
objects=[('root',vector(ref('loop'),ref('loop'),ref('equal'),ref('a'),ref('b'),ref('cold'),{'symbol':'P::X'},NIL)),
         ('loop',cons(integer(7),ref('loop'))),('equal',cons(integer(7),ref('loop'))),
         ('a',{'kind':'string','value':[65,0x1f642]}),('b',{'kind':'string','value':[65,0x1f642]}),
         ('cold',vector(integer(123),ref('loop'))),('big',integer(2**63)),
         ('f32',{'kind':'single-float','value':'00001029'}),
         ('f64',{'kind':'double-float','value':'7ff8123456789abc'})]
for kind,values in [('u8',['255']),('s8',['-128']),('u16',['65535']),('s16',['-32768']),
                    ('u32',['4294967295']),('s32',['-2147483648']),('fixnum',['536870911']),
                    ('single-float',['7fc12345']),('double-float',['8000000000000000']),
                    ('complex-single-float',[['3f800000','80000000']]),
                    ('complex-double-float',[['3ff0000000000000','8000000000000000']]),('bit',[1,0,1])]:
    objects.append((kind,{'kind':'vector','type':kind,'elements':values}))
p=compile_pool(graph(objects,[ref('root'),ref('loop'),{'symbol':'P::X'},NIL]),{'P::X':0x4006})
m=p.at(0x1000)
fixture={'image':m.image.hex(),'mutationOffset':44,'manifest':{'base':m.base,'length':len(m.image),
         'objects':[{'id':i,'offset':o,'tag':t} for i,o,t in p.objects],
         'roots':m.roots,'symbols':{'P::X':0x4006}}}
wat='''(module (import "env" "memory" (memory 1))
(func (export "load") (param i32) (result i32) local.get 0 i32.load)
(func (export "store") (param i32 i32) local.get 0 local.get 1 i32.store))'''
with tempfile.TemporaryDirectory(prefix='ccl-pool-snapshot-') as temp:
    out=Path(temp);(out/'fixture.json').write_text(json.dumps(fixture));(out/'probe.wat').write_text(wat)
    subprocess.run(['/usr/local/bin/wat2wasm',str(out/'probe.wat'),'-o',str(out/'probe.wasm')],check=True,capture_output=True)
    result=subprocess.run(['/usr/local/bin/node',str(HERE/'test_snapshot.mjs'),str(out/'fixture.json'),str(out/'probe.wasm')],capture_output=True,text=True)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    report=json.loads(result.stdout)
    mutants=[
        ('lost-relocation', 'bytes.writeUInt32LE(translate(bytes.readUInt32LE(where)), where)',
         'translate(bytes.readUInt32LE(where))', 'deep-equal'),
        ('lost-root-relocation', 'return {bytes, roots, objects:', 'return {bytes, roots:record.roots, objects:', 'deep-equal'),
        ('raw-float-root', "check(count === 1, 'single-float count'); payload = 4;",
         "check(count === 1, 'single-float count'); payload = 4; offsets.push(cursor+4);", 'payload 120'),
        ('early-write', 'const linked = inspect(record, base, ownerSymbols);',
         "new Uint8Array(memory.buffer,base,record.image.length/2).set(Buffer.from(record.image,'hex')); const linked = inspect(record, base, ownerSymbols);", 'refusal changed memory: layout'),
        ('skip-digest', "check(digest(bytes) === expectedDigest, 'snapshot digest');", '', 'Missing expected exception'),
    ]
    implementation=(HERE/'snapshot.mjs').read_text()
    # Only relocate the schema URL for this disposable copy, not runtime logic.
    implementation=implementation.replace("new URL('../../../../doc/WASM/contracts/wasm32-layout.v1.json', import.meta.url)",
        'new URL('+json.dumps((HERE.parents[3]/'doc/WASM/contracts/wasm32-layout.v1.json').as_uri())+')')
    for f in ['test_snapshot.mjs','snapshot-worker.mjs']:
        (out/f).write_bytes((HERE/f).read_bytes())
    report['mutants']=[]
    for name,old,new,diagnostic in mutants:
        assert implementation.count(old)==1,(name,'mutation site not unique')
        (out/'snapshot.mjs').write_text(implementation.replace(old,new))
        run=subprocess.run(['/usr/local/bin/node',str(out/'test_snapshot.mjs'),str(out/'fixture.json'),str(out/'probe.wasm')],capture_output=True,text=True)
        log=run.stdout+run.stderr
        if run.returncode==0 or diagnostic not in log: raise RuntimeError(name+'\n'+log)
        report['mutants'].append({'case':name,'result':'REJECTED'})
    report['probe_wasm_sha256']=hashlib.sha256((out/'probe.wasm').read_bytes()).hexdigest()
report['scope']='Isolated constant snapshot transport with hand-built loads; not compiler-generated LL10 qualification.'
report['source_pins']={f:hashlib.sha256((HERE/f).read_bytes()).hexdigest() for f in ['encode.py','pool.py','test_pool.py','snapshot.mjs','snapshot-worker.mjs','test_snapshot.mjs','verify_snapshot.py']}
report['layout_sha256']=hashlib.sha256((HERE.parents[3]/'doc/WASM/contracts/wasm32-layout.v1.json').read_bytes()).hexdigest()
report['toolchain']={name:{'version':subprocess.check_output(['/usr/local/bin/'+name,'--version'],text=True).strip(),'sha256':hashlib.sha256(Path('/usr/local/bin/'+name).read_bytes()).hexdigest()} for name in ['node','wat2wasm']}
print(json.dumps(report,indent=2))
