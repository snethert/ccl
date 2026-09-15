"""Behavioral expectations from native-compiled probes and damaged claims."""
from copy import deepcopy
from finite import Resolver,require


def native_checks(raw,convert):
    require(raw['restored'] is True and raw['effects']==2,'NATIVE_RESTORATION')
    ops={r['id']:r['name'] for r in raw['snapshot']['operators']}
    expected={r['name']:r for r in raw['checks']}
    require(len(raw['captures'])==len(expected)==15,'NATIVE_PROBE_COVERAGE')
    captures={};claims={}
    for c in raw['captures']:
        capture=convert(c,ops);rs=Resolver(capture).calls();name=c['case'];e=expected[name]
        require(len(rs)==1,'NATIVE_PROBE_CALLS');r=rs[0]
        require((r['status']=='FINITE_EXPRESSION')==(e['status']!='UNRESOLVED'),'NATIVE_EXPECTED_STATUS '+name)
        if e['status']=='FINITE':
            syms={n['id']:str(n['package'])+'::'+n['name'] for n in c['ir']['objects'] if n['kind']=='symbol'}
            require(all(t['kind']=='symbol' for t in r['targets']) and
                    {syms[t['id']] for t in r['targets']}==set(e['targets']),'NATIVE_EXPECTED_CANDIDATES '+name)
            mode='symbol-designator' if name=='if-symbols' else 'captured-function-cell-value'
            require(all(t['mode']==mode for t in r['targets']),'NATIVE_LOOKUP_TIME')
        if e['status']=='LEXICAL':
            require(len(r['targets'])==e['targets'] and all(t['kind']=='afunc' for t in r['targets']),'NATIVE_CLOSURE_UNION')
        captures[name]=capture;claims[name]=rs
    controls=[]
    def refuses(name,capture,claim):
        require(Resolver(capture).calls()!=claim,'CLAIM_MUTANT_ESCAPED '+name)
        controls.append(dict(name=name,status='REJECTED'))
    for case in ('if-functions','if-symbols','if-closures'):
        value=deepcopy(claims[case]);value[0]['targets'].pop()
        refuses('drop-branch-'+case,captures[case],value)
    value=deepcopy(claims['if-symbols']);value[0]['targets'][0]['mode']='captured-function-cell-value'
    refuses('confuse-symbol-and-captured-function',captures['if-symbols'],value)
    value=deepcopy(claims['function-cell']);value[0]['targets'][0]['id']=-1
    refuses('substitute-function-cell-id',captures['function-cell'],value)
    for case in ('parameter','unknown-if-branch','assigned','captured-write','shadowed-parameter','unknown-or'):
        value=deepcopy(claims[case]);value[0].update(status='FINITE_EXPRESSION',targets=claims['function-cell'][0]['targets'])
        refuses('hide-unknown-'+case,captures[case],value)
    # Clearing serialized flags does not erase an actual SETQ in any child.
    for case in ('assigned','captured-write'):
        c=deepcopy(captures[case])
        for n in c['flow']['objects']:
            if n['kind']=='variable':n['assigned']=False
        require(Resolver(c).calls()[0]['status']=='UNRESOLVED','STRUCTURAL_WRITE_SCAN')
        controls.append(dict(name='cleared-flags-'+case,status='REJECTED'))
    return dict(native_probes=len(captures),finite_expected=9,unknown_expected=6,
                controls_rejected=len(controls),controls=controls)
