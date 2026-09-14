"""Omissions, insertions, wrong roles and false closure claims must be refused."""
from copy import deepcopy
from common import require
from collect import binding
from history import check as check_history, assemble
from links import check as check_patch


def run(facts,functions,calls,histories,summary,delta,base,samples):
    results=[]
    def reject(name,fn,reason):
        try: fn()
        except ValueError as e: require(str(e)==reason,'CONTROL_REASON '+name);results.append(dict(name=name,reason=reason))
        else: raise ValueError('CONTROL_ESCAPED '+name)
    def history_mutant(name,index,mutate):
        hs=list(histories); hs[index]=deepcopy(hs[index]);mutate(hs[index])
        reject(name,lambda:check_history(hs,summary,facts,functions,calls),'HISTORY_RECORDS')
    called=next(i for i,h in enumerate(histories) if h['call_count'] and len(h['ordinary_codes'])>1)
    removed=next(i for i,h in enumerate(histories) if any(o['kind']=='binding-removing' for o in h['observations']))
    macro=next(i for i,h in enumerate(histories) if h['macro_expander_codes'])
    history_mutant('omit-earlier-version',called,lambda h:h['observations'].pop(0))
    history_mutant('drop-observed-candidate',called,lambda h:h['ordinary_codes'].pop(0))
    history_mutant('duplicate-observation',called,lambda h:h['observations'].append(deepcopy(h['observations'][0])))
    history_mutant('invent-closed-bound',called,lambda h:h.update(observed_only=False))
    history_mutant('change-symbol-identity',called,lambda h:h.update(symbol_id=h['symbol_id']+1))
    history_mutant('omit-removal-intent',removed,lambda h:h.update(observations=[o for o in h['observations'] if o['kind']!='binding-removing']))
    history_mutant('macro-expander-as-runtime-target',macro,lambda h:h['ordinary_codes'].append(h['macro_expander_codes'][0]))
    origin_index=next(i for i,h in enumerate(histories) if any(o['value'].get('origin',{}).get('kind')=='exact-fasl-version' for o in h['observations']))
    def stale(h):
        o=next(o for o in h['observations'] if o['value'].get('origin',{}).get('kind')=='exact-fasl-version')
        o['value']['origin']['read']['written']['event']+=1
    history_mutant('wrong-fasl-write-generation',origin_index,stale)
    gap=next((i for i,h in enumerate(histories) if h['continuity_gaps']),None)
    if gap is not None:history_mutant('erase-unobserved-change',gap,lambda h:h.update(continuity_gaps=[]))
    def patch_mutant(name,field,index,mutate):
        d=dict(delta);d[field]=list(d[field]);d[field][index]=deepcopy(d[field][index]);mutate(d[field][index])
        reject(name,lambda:check_patch(d,base,histories,calls),'PATCH_'+field.upper())
    patch_mutant('wrong-call-symbol','replacements',0,lambda r:r.update(target='identity:build:binding-cell:999999999'))
    patch_mutant('cross-process-call','replacements',0,lambda r:r.update(target='boot:object:1'))
    patch_mutant('promote-incomplete-candidates','edges',0,lambda r:r.update(resolution='complete'))
    patch_mutant('invent-candidate','edges',0,lambda r:r['targets'].append('identity:build:code:999999999'))
    patch_mutant('change-node-description','nodes',0,lambda r:r.update(reason='qualified'))
    patch_mutant('waive-cell-obligation','nodes',0,lambda r:r.update(required=False))
    for name,field,insert in [('omit-call','replacements',False),('duplicate-call','replacements',True),
                              ('omit-obligation','edges',False),('surplus-edge','edges',True),
                              ('omit-cell','nodes',False),('surplus-node','nodes',True)]:
        d=dict(delta);d[field]=list(d[field])
        if insert:d[field].append(deepcopy(d[field][0]))
        else:d[field].pop(0)
        reject(name,lambda:check_patch(d,base,histories,calls),'PATCH_'+field.upper())
    d=dict(delta,census_gate_credit=True)
    reject('false-gate-credit',lambda:check_patch(d,base,histories,calls),'PATCH_SCOPE')
    d=dict(delta,removed_name_nodes=delta['removed_name_nodes']+[base['seeds'][0]])
    reject('erase-unrelated-required-node',lambda:check_patch(d,base,histories,calls),'PATCH_REMOVED_NAME_NODES')
    # Positive decoder probes: unknown wrappers stay unknown, never expander
    # targets. Equal display names with different IDs stay distinct symbols.
    raw=deepcopy(next(v for k,v in samples.items() if k.endswith(':macro-wrapper')))
    p=raw['payload'].get('binding',raw['payload'])
    wrapper=next(n for n in p['objects'] if n['kind']=='simple-vector' and n['length']==2)
    wrapper['elements'][0]={'integer':0}
    require(binding(raw)['value']['role']=='unclassified','UNKNOWN_WRAPPER_PROMOTED')
    raw=deepcopy(next(iter(samples.values())));original=deepcopy(binding(raw))
    p=raw['payload'].get('binding',raw['payload'])
    old=original['symbol']['id'];new=999999999
    for n in p['objects']:
        if n['id']==old:n['id']=new
        if n.get('car')=={'ref':old}:n['car']={'ref':new}
    changed=binding(raw)
    require(changed['symbol']['id']!=original['symbol']['id'] and
            changed['symbol']['name']==original['symbol']['name'],'SAME_NAME_IDENTITY')
    original['stage']='before';changed['stage']='before'
    pair=dict(facts,bindings=[original,changed])
    hs,_=assemble(pair,[],[])
    require(len(hs)==2 and {h['symbol_id'] for h in hs}=={old,new},'SAME_NAME_HISTORY_MERGE')
    # A deliberately missing change between two confirmed observations must
    # appear as a discontinuity. The real stream currently has none under this
    # comparison; that is not a completeness proof for unobserved intervals.
    later=deepcopy(original);later['sequence']+=1;later['stage']='after'
    require(later['value']['role']=='function','CONTINUITY_PROBE_KIND')
    later['value']['object']+=100000000;later['value']['code']+=100000000
    hs,_=assemble(dict(facts,bindings=[original,later]),[],[])
    require(len(hs)==1 and hs[0]['continuity_gaps']==[dict(kind='unobserved-change',
            previous=original['sequence'],witness=later['sequence'])],'MISSING_CONTINUITY_GAP')
    return dict(status='PASS',controls_rejected=len(results),controls=results,
                positive_probes=['unknown-wrapper-remains-unclassified','same-name-distinct-symbols',
                                 'missing-change-remains-a-gap'])
