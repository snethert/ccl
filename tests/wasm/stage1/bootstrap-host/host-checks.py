"""Check provider routing against explicit protocol answers, not native POSIX."""
import json
from pathlib import Path


def check(out):
    read=lambda n:json.loads((out/n).read_text())
    symbols={r['id']:(r['package'],r['name']) for r in read('compiled/symbols.json')}
    def decode(x):
        if isinstance(x,list):return tuple(map(decode,x))
        if isinstance(x,dict):
            if 'symbol' in x:return ('symbol',*symbols[x['symbol']])
            if 'function' in x:return ('function',*symbols[x['function']])
            if 'string' in x:return x['string']
            if 'integer' in x:return int(x['integer'])
        return x
    def lis(xs):
        result=None
        for x in reversed(xs):result=(x,result)
        return result
    def alist(x):
        result={}
        while x is not None:
            (key,value),x=x
            result[key]=value
        return result
    provider=('symbol','KEYWORD','PROVIDER')
    caught=('symbol','KEYWORD','CAUGHT-ERROR')
    event=('symbol','WASM32-COMPILER','*CORE-HOST-EVENTS*')
    rows=[r for r in read('compiled/native.json') if r.get('targetOnly')]
    expected_names={'GETENV','GET-UNIVERSAL-TIME','SIGNAL-SEMAPHORE','WAIT-ON-SEMAPHORE',
                    'TIMED-WAIT-ON-SEMAPHORE','YIELD','WASM-HOST-SERVICE'}
    assert {r['definition'] for r in rows}==expected_names
    for r in rows:
        name=r['definition'];args=list(map(decode,r['args']));values=list(map(decode,r['values']))
        events=alist(decode(r['globalsAfter']))[event]
        assert alist(decode(r['globals']))[event] is None
        expected_events=None;error=False
        if name=='GETENV':
            if args==['PRESENT']:expected=['value']
            elif args==['MISSING']:expected=[None]
            else:assert args==[7];expected=[caught];error=True
        elif name=='GET-UNIVERSAL-TIME':expected=[4000000000]
        elif name=='WASM-HOST-SERVICE':expected=[caught];error=True
        else:
            delivered=args
            if name=='WAIT-ON-SEMAPHORE':
                delivered=(args+[None,'semaphore wait']) if len(args)==1 else args
                expected=[True]
            elif name=='TIMED-WAIT-ON-SEMAPHORE':
                delivered=args+[None] if len(args)==2 else args
                expected=[provider,lis(delivered)]
            else:expected=[provider,lis(delivered)]
            expected_events=lis([lis(delivered)])
        assert values==expected,(name,args,values,expected)
        assert events==expected_events,(name,events,expected_events)
        assert r['caught']==error
    whole=[r for r in read('compiled/whole-file.json') if r['file'].endswith('w32-os.lisp')]
    assert [(r['name'],r['status']) for r in whole if r['status']!='ADMITTED']==[('CPU-COUNT','GLOBAL-SETQ')]
    result=dict(status='PASS',compiled_and_executed=sorted(expected_names),protocol_rows=len(rows),
        checked_errors=sum(r['caught'] for r in rows),provider_effect_rows=sum(r['definition'] in ('SIGNAL-SEMAPHORE','WAIT-ON-SEMAPHORE','TIMED-WAIT-ON-SEMAPHORE','YIELD') for r in rows),
        refused={'CPU-COUNT':'GLOBAL-SETQ; keep the native cache algorithm and record missing lowering'},
        scope='Explicit provider protocol expectations plus execution of the same target Lisp on native CCL. Not equivalence to native POSIX, not live host providers, and not a replacement module-list admission.')
    (out/'host-protocol.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    import sys
    check(Path(sys.argv[1]))
