"""Focused executable controls; this is not a full compiler mutant sweep."""
import hashlib,json,re,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
WABT='/usr/local/bin/wat2wasm';NODE='/usr/local/bin/node'
def run(out):
    out=Path(out).resolve();dest=out/'faults';dest.mkdir()
    modules=json.loads((out/'compiled/modules.json').read_text())
    symbols={r['id']:r['name'] for r in json.loads((out/'compiled/symbols.json').read_text())}
    named={symbols.get(r['function']):r['name'] for r in modules}
    rows=[]
    def execute(name,target,mutant,diagnostic):
        original=target.read_bytes();before=hashlib.sha256(original).hexdigest()
        try:
            target.write_bytes(mutant.read_bytes())
            with (dest/(name+'.log')).open('w') as log:
                p=subprocess.run([NODE,out/'check.mjs',out,dest/(name+'.json')],stdout=log,stderr=log,timeout=120)
            text=(dest/(name+'.log')).read_text()
            assert p.returncode!=0 and re.search(diagnostic,text),name+' escaped or failed elsewhere'
            rows.append(dict(name=name,rejected=True,diagnostic=diagnostic,mutant_sha256=hashlib.sha256(mutant.read_bytes()).hexdigest()))
        finally:target.write_bytes(original)
        assert hashlib.sha256(target.read_bytes()).hexdigest()==before
    def wat_fault(name,module,change,diagnostic):
        text=(out/'compiled'/f'{module}.wat').read_text()
        prefix,body=text.split('(func $body ',1)
        changed=change(body);assert changed!=body
        p=dest/(name+'.wat');p.write_text(prefix+'(func $body '+changed)
        subprocess.run([WABT,'--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],check=True)
        execute(name,out/'compiled'/f'{module}.wasm',p.with_suffix('.wasm'),diagnostic)
    def root_count(text):
        pattern=r'(\(i32.store offset=4 \(local.get \$tmp\d+\) \(i32.const )2(\)\))'
        text,n=re.subn(pattern,r'\g<1>0\2',text,count=1);assert n==1
        return text
    wat_fault('gvector-unrooted-operands','core_gvector',root_count,'CORE-GVECTOR')
    def symbol_tag(text):
        assert '(i32.const 232)' in text
        return text.replace('(i32.const 232)','(i32.const 0)',1)
    wat_fault('wrong-symbol-tag',named['SYMBOLP'],symbol_tag,'SYMBOL')
    def force_slow(text):
        start=text.index('(if (result i32) (i32.eqz (i32.and (i32.or ')
        i=text.index('(i32.const 3)',start)
        return text[:i]+text[i:].replace('(i32.const 3)','(i32.const 4)',1)
    wat_fault('fixnum-comparison-js',named['MAX-2'],force_slow,'fixnum comparison left Wasm')
    old=dest/'collector-without-structures.wasm'
    subprocess.run(['/usr/local/opt/llvm/bin/clang','--target=wasm32','-O2','-nostdlib','-fno-builtin','-matomics','-mbulk-memory',
                    '-Wl,--no-entry','-Wl,--import-memory','-Wl,--shared-memory','-Wl,--max-memory=2147549184',
                    '-Wl,--global-base=1048576','-Wl,-z,stack-size=65536','-Wl,--export=collect','-Wl,--export=__stack_pointer',
                    ROOT/'runtime/wasm32/collector.c','-o',old],check=True)
    execute('missing-structure-scanner',out/'collector.wasm',old,'core_struct: AssertionError')
    (out/'faults.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':run(sys.argv[1])
