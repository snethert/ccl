"""Focused regressions for the new behavior, without repeating the full suite."""
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
    def swap_bytes(s):
        # Restore audit 146's exact operand mistake after the three evaluations.
        head,tail=s.split('(local.set $tmp2 ',1)
        tail=tail.replace('offset=12 (local.get $tmp0)', 'offset=SWAP (local.get $tmp0)')
        tail=tail.replace('offset=16 (local.get $tmp0)', 'offset=12 (local.get $tmp0)')
        tail=tail.replace('offset=SWAP (local.get $tmp0)', 'offset=16 (local.get $tmp0)')
        return head+'(local.set $tmp2 '+tail
    wat('swapped-byte-index-value','core_byte_store',swap_bytes,'CORE-BYTE-STORE','CORE-BYTE-STORE')
    def nil_callable(s):
        pattern=r'(\(call \$resolve_lisp )\(i32.load offset=8 \(local.get \$tmp\d+\)\)'
        s,n=re.subn(pattern,r'\1(i32.const 77825)',s);assert n==1;return s
    wat('computed-call-is-nil','core_computed_call',nil_callable,'CORE-COMPUTED-CALL','checked')
    def integer_add_instead(s):
        old='(drop (call $integer (i32.const 5)'
        assert s.count(old)==1
        return s.replace(old,'(drop (call $integer (i32.const 0)')
    wat('integer-division-is-addition','core_integer_divide',integer_add_instead,'CORE-INTEGER-DIVIDE','CORE-INTEGER-DIVIDE')
    def ignore_remainder(s):
        pattern=r'\(if \(i32.ne \(i32.load offset=12 \(local.get \$tmp\d+\)\) \(i32.const 0\)\) \(then \(throw \$call_error \(i32.const 45\)\)\)\)'
        s,n=re.subn(pattern,'',s);assert n==1;return s
    wat('truncated-quotient-escapes','core_integer_divide',ignore_remainder,'CORE-INTEGER-DIVIDE','Missing expected exception')
    source=(out/'compiled/core_divide_zero.wat').read_text()
    pattern=r'\(block \(result i32\) \(local.set \$tmp\d+ (\(i32.load offset=4 \(call \$handler_cons \(i32.load offset=16 \(local.get \$tmp\d+\)\)\)\))\)'
    matches=list(re.finditer(pattern,source));assert len(matches)==1
    match=matches[0];depth=0;end=None
    for i in range(match.start(),len(source)):
        depth+=(source[i]=='(')-(source[i]==')')
        if depth==0:end=i+1;break
    assert end is not None
    changed=source[:match.start()]+'(i32.shr_u '+match.group(1)+' (i32.const 2))'+source[end:]
    p=dest/'handler-symbol-is-mask.wat';p.write_text(changed)
    subprocess.run([WABT,'--enable-threads','--enable-exceptions','--enable-tail-call',p,'-o',p.with_suffix('.wasm')],check=True)
    execute('handler-symbol-is-mask',out/'compiled/core_divide_zero.wasm',p.with_suffix('.wasm').read_bytes(),'CORE-DIVIDE-ZERO','CORE-DIVIDE-ZERO')
    def assq_sense(s):
        pattern='(if (i32.eq (i32.load offset=8 (local.get $tmp0))'
        assert s.count(pattern)==1
        return s.replace(pattern,pattern.replace('i32.eq','i32.ne'))
    wat('assq-match-sense','core_assq',assq_sense,'CORE-ASSQ','CORE-ASSQ')
    def logical_or(s):
        pattern='(i32.or (i32.const 0)'
        assert pattern in s
        return s.replace(pattern,'(i32.and (i32.const 0)',1)
    wat('logior-is-logand','core_logical',logical_or,'CORE-LOGICAL','CORE-LOGICAL')
    def subtraction(s):
        pattern='(call $integer (i32.const 1)'
        assert pattern in s
        return s.replace(pattern,'(call $integer (i32.const 0)',1)
    wat('subtraction-is-addition','core_subtract_call',subtraction,'CORE-SUBTRACT-CALL','CORE-SUBTRACT-CALL')
    def type_bound(s):
        assert '(i32.ge_s' in s
        return s.replace('(i32.ge_s','(i32.gt_s',1)
    wat('exclusive-type-lower-bound','core_type_tests',type_bound,'CORE-TYPE-TESTS','CORE-TYPE-TESTS')
    p=out/'install.mjs';text=p.read_text()
    needle="value=mat.roots[mods.length];"
    assert text.count(needle)==1
    execute('wrong-type-id-table',p,text.replace(needle,"{value=mat.roots[mods.length];put(value+14,77825);}").encode(),'CORE-BADARG','CORE-BADARG')
    (out/'faults.json').write_text(json.dumps(rows,indent=2,sort_keys=True)+'\n')
if __name__=='__main__':run(sys.argv[1])
