"""Native lookup values, shadowing and preservation of captured cell values."""
from copy import deepcopy
from run import read,convert
from lookups import Resolver
from finite import require
from test_lexical import check as lexical_check, selected


def check(raw,convert):
    require(len(raw['checks'])==len(raw['captures'])==47,'LOOKUP_CORPUS')
    earlier=lexical_check(dict(raw,checks=raw['checks'][:41],captures=raw['captures'][:41]),convert)
    operators={r['id']:r['name'] for r in raw['snapshot']['operators']}
    by_name={r['name']:r for r in raw['checks']};captures={};claims={}
    for original in raw['captures']:
        name=original['case'];capture=convert(original,operators);claims[name]=selected(capture,Resolver)
        require(bool(claims[name]),'LOOKUP_CALL_MISSING '+name)
        if name in {r['case'] for r in raw['captures'][:41]}:
            require(claims[name]==selected(capture),'LOOKUP_CHANGED_EARLIER_CASE '+name)
            continue
        captures[name]=capture;expected=by_name[name]
        symbols={n['id']:str(n['package'])+'::'+n['name'] for n in original['ir']['objects'] if n['kind']=='symbol'}
        for result in claims[name]:
            require((result['status']=='FINITE_EXPRESSION')==(expected['status']=='FINITE'),'LOOKUP_STATUS '+name)
            if expected['status']=='FINITE':
                require(all(t['kind']=='symbol' and t['mode']=='captured-function-cell-value' for t in result['targets']),
                        'LOOKUP_VALUE_SEMANTICS '+name)
                require({symbols[t['id']] for t in result['targets']}==set(expected['targets']),'LOOKUP_TARGETS '+name)
    controls=[]
    for name,operator in [('foreign-package','USER::FDEFINITION'),('different-operation','COMMON-LISP::IDENTITY')]:
        c=deepcopy(captures['fdefinition-symbol']);changed=0
        def walk(v):
            nonlocal changed
            if isinstance(v,dict):
                if v.get('symbol')=='COMMON-LISP::FDEFINITION':v['symbol']=operator;changed+=1
                if v.get('kind')=='global-binding' and v.get('name')=='COMMON-LISP::FDEFINITION':v['name']=operator
                for item in v.values():walk(item)
            elif isinstance(v,list):
                for item in v:walk(item)
        walk(c);require(changed>0,'LOOKUP_CONTROL_NOT_APPLIED')
        require(all(r['status']=='UNRESOLVED' for r in selected(c,Resolver)),'LOOKUP_CONTROL_ESCAPED '+name)
        controls.append(dict(name=name,status='REJECTED'))
    for name in ('fdefinition-dynamic-name','fdefinition-local-shadow'):
        require(all(r['status']=='UNRESOLVED' for r in claims[name]),'LOOKUP_UNSUPPORTED_PROMOTION')
        controls.append(dict(name='promote-'+name,status='REJECTED'))
    for result in claims['lookup-captures-value']:
        require(all(t['mode']=='captured-function-cell-value' for t in result['targets']), 'LOOKUP_CURRENT_VALUE_SUBSTITUTED')
    return dict(native_probes=47,earlier_controls=earlier['controls_rejected'],
                controls_rejected=earlier['controls_rejected']+len(controls),controls=controls)


if __name__=='__main__':
    import sys
    from pathlib import Path
    print(check(read(Path(sys.argv[1])),convert))
