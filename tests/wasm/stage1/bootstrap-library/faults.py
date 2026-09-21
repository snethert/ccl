"""Four focused regressions for the new behavior, without repeating the full suite."""
import json,os,re,subprocess,sys
from pathlib import Path
NODE='/usr/local/bin/node';WABT='/usr/local/bin/wat2wasm'

def run(out):
    out=Path(out).resolve();dest=out/'faults';dest.mkdir()
    rows=[]
    def execute(name,target,data,case,diagnostic):
        original=target.read_bytes()
        try:
            target.write_bytes(data)
            with (dest/(name+'.log')).open('w') as log:
                result=subprocess.run([NODE,out/'check.mjs',out,dest/(name+'.json')],env=dict(os.environ,CCL_LIBRARY_CASE=case),stdout=log,stderr=log,timeout=60)
            text=(dest/(name+'.log')).read_text()
            assert result.returncode!=0 and diagnostic in text,(name,text[-1800:])
            rows.append(dict(name=name,rejected=True,case=case,diagnostic=diagnostic))
        finally:target.write_bytes(original)
    def wat(name,module,change,case,diagnostic):
        source=(out/'compiled'/f'{module}.wat').read_text()
        prefix,body=source.split('(func $body ',1);changed=change(body);assert changed!=body
        p=dest/(name+'.wat');p.write_text(prefix+'(func $body '+changed)
        subprocess.run([WABT,'--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],check=True)
        execute(name,out/'compiled'/f'{module}.wasm',p.with_suffix('.wasm').read_bytes(),case,diagnostic)
    def lose_arguments(s):
        s,n=re.subn(r'(\(i32.store offset=12 \(call \$condition_slots \(local.get \$tmp\d+\)\) )\(i32.load offset=12 \(local.get \$tmp\d+\)\)',r'\1(i32.const 77825)',s)
        assert n==1;return s
    wat('lost-format-arguments','core_format_error',lose_arguments,'CORE-FORMAT-ERROR','CORE-FORMAT-ERROR')
    def old_char_code(s):
        old=r'\(i32.shl \(i32.shr_u (\(i32.load offset=8 \(local.get \$tmp\d+\)\)) \(i32.const 8\)\) \(i32.const 2\)\)'
        s,n=re.subn(old,r'(i32.shr_u \1 (i32.const 6))',s);assert n==1;return s
    wat('character-tag-leak','core_char_code',old_char_code,'CORE-CHAR-CODE','CORE-CHAR-CODE')
    def unsigned(s):
        assert s.count('(i32.lt_s')==1;return s.replace('(i32.lt_s','(i32.lt_u')
    wat('unsigned-fixnum-order','core_fixnum_less',unsigned,'CORE-FIXNUM-LESS','CORE-FIXNUM-LESS')
    p=out/'install.mjs';text=p.read_text();assert text.count('[4,8,12,16,24]')==1
    execute('unrooted-symbol-plist',p,text.replace('[4,8,12,16,24]','[4,8,12,16]').encode(),'PUT','type_error')
    (out/'faults.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':run(sys.argv[1])
