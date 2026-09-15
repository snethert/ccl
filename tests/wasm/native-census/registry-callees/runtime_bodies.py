"""Account for native assembly and generic-function entry code explicitly."""
from collections import defaultdict
from payloads import require,dependency_body_key,literal_regions
from registry import state_check
from lap_join import transfers


def join(functions,definitions,registries,runtime,requested):
    by_symbol=defaultdict(list)
    for d in definitions:
        if d['name'] and d['name'].get('kind')=='symbol':by_symbol[d['name']['id']].append(d)
    templates={}
    for r in runtime['dcode_prototypes']:
        require(r['dcode'] not in templates,'RUNTIME_DCODE_DUPLICATE');templates[r['dcode']]=r['prototype']
    result=[];open_=[]
    for ident in sorted(requested):
        fn=functions[ident];state=registries.get(ident);prototype=ident;kind='ASSEMBLED_BODY'
        if state:
            state_check(state,functions)
            if state['status']!='INITIALIZED':open_.append(dict(function=ident,reason='uninitialized-registry'));continue
            prototype=templates.get(state['dcode'],runtime['default_gf_prototype']);proto=functions[prototype]
            if fn['code_words']!=proto['code_words'] or fn['payload_hex'][:16*fn['code_words']]!=proto['payload_hex'][:16*proto['code_words']]:
                open_.append(dict(function=ident,reason='dispatch-template-not-witnessed'));continue
            values=literal_regions(fn)[0]
            if not (len(values)==4 and values[0].get('object')==state['wrapper'] and
                    values[2].get('object')==state['dispatch_table'] and values[3]==dict(function=state['dcode'])):
                open_.append(dict(function=ident,reason='dispatch-literal-layout'));continue
            kind='GENERIC_FUNCTION_ENTRY'
        proto=functions[prototype]
        # An actual named template definition is needed even when its code is
        # copied into a generic function with different data and runtime bits.
        if not proto['literals'] or not isinstance(proto['literals'][-1],dict) or 'symbol' not in proto['literals'][-1]:
            open_.append(dict(function=ident,reason='no-assembly-name-slot'));continue
        name=proto['literals'][-1]['symbol'];key=dependency_body_key(proto)
        found=[d for d in by_symbol[name] if key is not None and dependency_body_key(functions[d['function']])==key]
        if not found:open_.append(dict(function=ident,reason='no-matching-assembly-definition'));continue
        result.append(dict(function=ident,kind=kind,prototype=prototype,definitions=found,
            transfers=[dict(definition=d['entry'],transfers=transfers(d)) for d in found],
            registry=state,runtime_bound=False,target_replacement='UNRESOLVED',data_materialization='UNRESOLVED'))
    require({r['function'] for r in result}|{r['function'] for r in open_}==set(requested),'RUNTIME_BODY_POPULATION')
    return result,open_
