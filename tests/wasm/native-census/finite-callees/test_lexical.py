"""Native entry/capture behavior and adversarial edits to argument-flow proofs."""
from copy import deepcopy
from lexical import Resolver,require
from test_finite import native_checks


def selected(capture,resolver=Resolver):
    r=resolver(capture);names={n['root']:n['name'] for n in r.graph.nodes.values() if n['kind']=='variable'}
    return [c for c in r.calls() if names.get(c['variable_id'],'').endswith('::CALLEE')]


def check(raw,convert):
    require(len(raw['checks'])==len(raw['captures'])==41,'LEXICAL_CORPUS_COVERAGE')
    old=dict(raw,checks=raw['checks'][:15],captures=raw['captures'][:15]);earlier=native_checks(old,convert)
    ops={r['id']:r['name'] for r in raw['snapshot']['operators']};by_name={r['name']:r for r in raw['checks']}
    claims={};captures={}
    for raw_capture in raw['captures']:
        name=raw_capture['case'];capture=convert(raw_capture,ops);rs=selected(capture);want=by_name[name]
        require(bool(rs),'LEXICAL_MISSING_CALL '+name)
        for r in rs:
            require((r['status']=='FINITE_EXPRESSION')==(want['status']!='UNRESOLVED'),'LEXICAL_EXPECTED_STATUS '+name+' '+str(r))
            if want['status']=='FINITE':
                syms={n['id']:str(n['package'])+'::'+n['name'] for n in raw_capture['ir']['objects'] if n['kind']=='symbol'}
                require(all(t['kind']=='symbol' for t in r['targets']) and
                        {syms[t['id']] for t in r['targets']}==set(want['targets']),'LEXICAL_TARGET_UNION '+name)
            elif want['status']=='LEXICAL':
                require(len(r['targets'])==want['targets'] and all(t['kind']=='afunc' for t in r['targets']),
                        'LEXICAL_PROTOTYPE '+name)
        claims[name]=rs;captures[name]=capture
    controls=[]
    def refusal(name,case,mutate):
        claim=deepcopy(claims[case]);mutate(claim)
        require(selected(captures[case])!=claim,'LEXICAL_MUTANT_ESCAPED '+name)
        controls.append(dict(name=name,status='REJECTED'))
    for case in ('two-local-callers','recursive-parameter','mutual-parameters'):
        refusal('drop-incoming-value-'+case,case,lambda r:r[0]['targets'].pop())
    refusal('wrong-register-argument','register-argument-position',
            lambda r:r[0].update(targets=claims['stack-argument-position'][0]['targets']))
    for case in ('local-value-escapes','unknown-local-caller','assigned-parameter','captured-write-new',
                 'captured-external-parameter','optional-parameter-signature','spread-local-call','inline-unknown-value'):
        refusal('hide-refusal-'+case,case,lambda r:r[0].update(status='FINITE_EXPRESSION',targets=claims['local-parameter'][0]['targets']))
    for case in ('assigned-parameter','captured-write-new'):
        c=deepcopy(captures[case])
        for n in c['flow']['objects']:
            if n['kind']=='variable':n['assigned']=False
        require(all(r['status']=='UNRESOLVED' for r in selected(c)),'LEXICAL_STRUCTURAL_WRITES')
        controls.append(dict(name='cleared-flags-'+case,status='REJECTED'))
    class IgnoreEscape(Resolver):
        def __init__(self,capture):
            super().__init__(capture);self.escapes.clear()
    bad=selected(captures['local-value-escapes'],IgnoreEscape)
    require(all(r['status']=='FINITE_EXPRESSION' for r in bad) and
            bad!=claims['local-value-escapes'],'LEXICAL_ESCAPE_MUTANT_NOT_WITNESSED')
    controls.append(dict(name='ignore-function-binding-escape',status='REJECTED'))
    class IgnoreCaller(Resolver):
        def __init__(self,capture):
            super().__init__(capture)
            for fn,calls in self.incoming.items():self.incoming[fn]=calls[:1]
    bad=selected(captures['two-local-callers'],IgnoreCaller)
    require(all(r['status']=='FINITE_EXPRESSION' and len(r['targets'])==1 for r in bad) and
            bad!=claims['two-local-callers'],'LEXICAL_CALLER_MUTANT_NOT_WITNESSED')
    controls.append(dict(name='ignore-additional-direct-caller',status='REJECTED'))
    return dict(native_probes=41,earlier_controls=earlier['controls_rejected'],
                controls_rejected=len(controls)+earlier['controls_rejected'],controls=controls)
