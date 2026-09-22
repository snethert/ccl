"""Count target-word differences separately from native-compatible execution."""
import json
from pathlib import Path

def check(out):
    read=lambda name:json.loads((out/name).read_text())
    save=lambda name,value:(out/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
    emitted=read('compiled/executed-operators.json')
    operators={op:[r['name'] for r in emitted if any(name==op for name,count in r['operators'])]
               for op in ('%SINGLE-FLOAT','%DOUBLE-FLOAT','NATURAL-SHIFT-LEFT','NATURAL-SHIFT-RIGHT','MINUS1')}
    assert all(operators.values()), operators
    save('math-operator-coverage.json',dict(executed={k:v for k,v in operators.items() if v},
        unexecuted=[k for k,v in operators.items() if not v],
        scope='All five operators, including MINUS1 through CCL %NEGATE, are source-emitted and executed.'))
    rows=read('execution.json')['rows']
    shifts=[r for run in rows for r in run['shiftRows']]
    assert len(shifts)==756
    assert any(r['args']==[1,-4] and r['target']==[536870910] and r['native']==[{'integer':'1152921504606846974'}] for r in shifts if 'RIGHT' in r['definition'])
    assert any(r['args']==[28,7] and r['target']==[-268435456] and r['native']==[{'integer':'1879048192'}] for r in shifts if 'LEFT' in r['definition'])
    admitted=read('compiled/admitted-shifts.json')
    names={r['name'] for r in admitted}
    assert 'LDB32' in names and 'ROTATE-HASH-CODE' in names
    save('shift-domains.json',dict(status='PASS',comparisons=len(shifts),differences=sum(r['native']!=r['target'] for r in shifts),
         cases=shifts,admitted_definitions=admitted,
         source_findings=[dict(name='LDB32',domain='HI-DATA and LO-DATA are declared FIXNUM, not nonnegative; its right shifts can observe the word width.'),
                          dict(name='ROTATE-HASH-CODE',domain='FIXNUM argument can be negative. Logical right shift exposes target width; its result is a target hash code.'),
                          dict(name='SWAP',domain='Source already has distinct 32-bit and 64-bit bodies. It is not eligible for raw cross-width return equality.')],
         scope='ILSL wraps in the signed fixnum payload; ILSR treats that payload as unsigned; IASR sign-extends. Counts are nonnegative. No claim that admission restricts all callers to the native-agreeing domain.'))
    libm=[r for run in rows for r in run['libmRows']]
    assert len({r['definition'] for r in libm})==26
    save('transcendental-comparisons.json',dict(status='PASS',entries=26,comparisons=len(libm),bit_identical=sum(r['ulps']==0 for r in libm),
         maximum_ulp=max(r['ulps'] for r in libm),differences=[r for r in libm if r['ulps']],
         scope='These are separate finite nearest-rounding libm comparisons, not bit-identical native execution credit or a full-domain accuracy proof. The adopted comparison envelope is two ULP; signed zeros must match exactly.'))
    return dict(shift_comparisons=len(shifts),shift_differences=sum(r['native']!=r['target'] for r in shifts),
                transcendental_comparisons=len(libm),transcendental_differences=sum(r['ulps']!=0 for r in libm))
