"""Join actual assembler parses/emissions to resident native body obligations.

The assembly instruction inventory is complete for each observed definition.
Register-indirect transfers, stores, traps and target replacements remain
explicit obligations; native assembly is never represented as empty Lisp IR.
"""
from collections import Counter,defaultdict
from copy import deepcopy
from pathlib import Path
import sys,json
from payloads import read,save,require,rows,capture,dependency_body_key,literal_regions,source_key
from bodies import node,edge,apply

HERE=Path(__file__).resolve().parent
KINDS={'assembly-enter','assembly-leave','assembly-instruction','assembly-emission','assembly-expansion','assembly-subprim'}


def decode(payload):
    nodes={n['id']:n for n in payload['objects']}
    require(len(nodes)==len(payload['objects']),'LAP_TREE_DUPLICATE')
    def visit(ref,seen=()):
        if ref=={'atom':'nil'}:return None
        if set(ref) in ({'integer'},{'string'},{'character'}):return ref
        require(set(ref)=={'ref'} and ref['ref'] in nodes,'LAP_TREE_REFERENCE')
        n=nodes[ref['ref']]
        if n['kind']=='symbol':return n
        if n['kind']!='cons':return dict(opaque=n)
        result=[]
        while ref!={'atom':'nil'}:
            require(set(ref)=={'ref'} and ref['ref'] in nodes,'LAP_TREE_TAIL')
            n=nodes[ref['ref']]
            require(n['kind']=='cons' and n['expanded'] and n['id'] not in seen,'LAP_TREE_LIST')
            seen=seen+(n['id'],);result.append(visit(n['car'],seen));ref=n['cdr']
        return result
    return visit(payload['root'])


def replay(events,functions):
    active=[];definitions={};parses={};completed=set();all_parses=set();all_emits=set()
    for r in events:
        kind=r['kind']
        if not kind.startswith('assembly-'):continue
        require(kind in KINDS,'LAP_UNKNOWN_EVENT')
        if kind=='assembly-enter':
            require(r['sequence'] not in definitions,'LAP_DUPLICATE_DEFINITION')
            name=decode(r['name']);require(name is None or isinstance(name,dict),'LAP_DEFINITION_NAME')
            definitions[r['sequence']]=dict(entry=r['sequence'],unit=source_key(r['unit']),name=name,
                forms=decode(r['forms']),instructions=[],expansions=[],subprims=[])
            active.append(r['sequence']);continue
        require(active,'LAP_OUTSIDE_DEFINITION');owner=active[-1];d=definitions[owner]
        if kind=='assembly-leave':
            require(r['entry']==owner and r['completed'] is True and not any(p['assembly']==owner for p in parses.values()),
                    'LAP_INCOMPLETE_DEFINITION')
            require(r['function'] in functions and functions[r['function']]['prototype']==r['function'],'LAP_OUTPUT_FUNCTION')
            d.update(function=r['function'],leave=r['sequence']);completed.add(owner);active.pop();continue
        require(r['assembly']==owner,'LAP_EXECUTION_CONTEXT')
        if kind=='assembly-instruction':
            require(r['sequence'] not in all_parses,'LAP_DUPLICATE_PARSE')
            form=decode(r['form']);require(isinstance(form,list) and form and form[0].get('kind')=='symbol','LAP_INSTRUCTION_FORM')
            parses[r['sequence']]=r;all_parses.add(r['sequence'])
        elif kind=='assembly-emission':
            require(r['parsed'] in parses and r['parsed'] not in all_emits,'LAP_EMISSION_WITHOUT_PARSE')
            p=parses.pop(r['parsed']);require(p['assembly']==owner and p['sequence']<r['sequence'],'LAP_EMISSION_CONTEXT')
            require(type(r['opcode']) is int and r['opcode']>=0 and isinstance(r['template'],str),'LAP_EMISSION_OPCODE')
            d['instructions'].append(dict(parsed=p['sequence'],emitted=r['sequence'],form=decode(p['form']),
                                          opcode=r['opcode'],template=r['template']))
            all_emits.add(p['sequence'])
        elif kind=='assembly-expansion':d['expansions'].append(dict(event=r['sequence'],input=decode(r['input']),output=decode(r['output'])))
        elif kind=='assembly-subprim':
            name=decode(r['name']);require(isinstance(name,dict) and name.get('kind')=='symbol'
                and type(r['offset']) is int and r['offset']>=0,'LAP_SUBPRIM_LOOKUP')
            d['subprims'].append(dict(event=r['sequence'],name=name,offset=r['offset']))
    require(not active and not parses and set(definitions)==completed and all_parses==all_emits,'LAP_INCOMPLETE_INVENTORY')
    require(all(d['instructions'] for d in definitions.values()),'LAP_EMPTY_ASSEMBLY')
    return [definitions[k] for k in sorted(definitions)]


def transfers(definition):
    result=[]
    for instruction in definition['instructions']:
        mnemonic=instruction['template'].lower()
        if not mnemonic.startswith(('call','jmp','ret','int','ud2')):continue
        row=dict(parsed=instruction['parsed'],mnemonic=mnemonic,form=instruction['form'])
        if mnemonic.startswith('ret'):row['kind']='RETURN'
        elif mnemonic.startswith(('int','ud2')):row['kind']='NATIVE_TRAP'
        else:
            operands=instruction['form'][1:];require(len(operands)==1,'LAP_TRANSFER_ARITY');arg=operands[0]
            # U1 parse-x86-operand treats a non-list argument as a local label.
            # The actual assembler returned successfully after relocation.
            if isinstance(arg,dict) and arg.get('kind')=='symbol':row['kind']='LOCAL_LABEL'
            elif isinstance(arg,list) and len(arg)==2 and arg[0].get('name')=='@' and set(arg[1])=={'integer'}:
                offset=arg[1]['integer'];lookups=[r for r in definition['subprims'] if r['offset']==offset and r['event']<instruction['parsed']]
                if lookups:
                    row.update(kind='SUBPRIMITIVE',offset=offset,lookups=lookups)
                else:row.update(kind='UNRESOLVED_ABSOLUTE_TRANSFER',offset=offset)
            else:row['kind']='UNRESOLVED_INDIRECT_TRANSFER'
        result.append(row)
    return result


def join(frontends,original,definitions,current,bindings,requested):
    before=defaultdict(list)
    for b in bindings:
        if b['kind']=='resident-binding' and b['stage']=='before' and b['value']['role']=='function' and b['symbol'].get('kind')=='symbol':
            if b['value']['code'] in requested:before[b['symbol']['id']].append(b)
    assembled=defaultdict(list)
    for d in definitions:
        if d['name'] and d['name'].get('kind')=='symbol':assembled[d['name']['id']].append(d)
    found=[]
    for event in frontends:
        if event['kind']!='frontend':continue
        payload=event['payload'];nodes={n['id']:n for n in payload['ir']['objects']};afunc=nodes[payload['ir']['root']['ref']]
        require(afunc['kind']=='afunc' and afunc['parent'] is None,'LAP_FRONTEND_ROOT')
        name=nodes.get(afunc['name'].get('ref'));code=afunc['function']['ref']
        if not name or name['kind']!='symbol':continue
        for old in before[name['id']]:
            resident=old['value']['code']
            require(old['symbol']==name,'LAP_ORIGINAL_CELL')
            if dependency_body_key(original[resident])!=dependency_body_key(original[code]):continue
            anchor=current[resident]
            require(anchor['payload_hex']==original[resident]['payload_hex'],'LAP_ANCHORED_PAYLOAD')
            # Observer numbers differ across sessions. Read the actual symbol
            # from the same name-slot word of the byte-anchored image function;
            # do not identify freshly allocated symbols by spelling or number.
            require(not (original[resident]['bits'] & (1<<29)) and
                    original[resident]['literals'][-1].get('symbol')==name['id'], 'LAP_ORIGINAL_NAME_SLOT')
            current_name=anchor['literals'][-1]
            require('symbol' in current_name and current_name['name']==dict(symbol=name['name'],package=name['package']),
                    'LAP_ANCHORED_NAME_SLOT')
            for d in assembled[current_name['symbol']]:
                if {k:v for k,v in d['name'].items() if k!='id'}!={k:v for k,v in name.items() if k!='id'} or d['unit']!=source_key(event['source']):continue
                rebuilt=current[d['function']]
                if dependency_body_key(anchor)!=dependency_body_key(rebuilt):continue
                # The cross-execution bridge is the original read-only body.
                # Every complete resident payload must also equal the fresh
                # image's payload; new dynamic instances are never aliased.
                found.append(dict(resident=resident,compiled=code,frontend=event['sequence'],afunc=afunc['id'],
                    symbol=name,anchored_name_symbol=current_name,assembly=d,transfers=transfers(d),materialization='UNRESOLVED',
                    constant_data='UNRESOLVED',target_replacement='UNRESOLVED'))
    require(len({r['resident'] for r in found})==len(found),'LAP_AMBIGUOUS_BODY')
    return found


def controls(events,functions):
    selected=[r for r in events if r['kind'].startswith('assembly-')]
    original=replay(selected,functions);result=[]
    parsed=next(r for r in selected if r['kind']=='assembly-instruction')
    emitted=next(r for r in selected if r['kind']=='assembly-emission')
    left=next(r for r in selected if r['kind']=='assembly-leave')
    def refuse(name,mutated,reason):
        try:replay(mutated,functions)
        except ValueError as e:require(str(e)==reason,'LAP_CONTROL_REASON '+name+' '+str(e))
        else:raise ValueError('LAP_CONTROL_ESCAPED '+name)
        result.append(dict(name=name,status='REJECTED'))
    refuse('omit-parse',[r for r in selected if r is not parsed],'LAP_EMISSION_WITHOUT_PARSE')
    refuse('omit-emission',[r for r in selected if r is not emitted],'LAP_INCOMPLETE_DEFINITION')
    refuse('substitute-parse-identity',[dict(r,parsed=-1) if r is emitted else r for r in selected],'LAP_EMISSION_WITHOUT_PARSE')
    refuse('emission-in-another-function',[dict(r,assembly=-1) if r is emitted else r for r in selected],'LAP_EXECUTION_CONTEXT')
    refuse('failed-assembler-as-success',[dict(r,completed=False) if r is left else r for r in selected],'LAP_INCOMPLETE_DEFINITION')
    refuse('substitute-assembled-function',[dict(r,function=-1) if r is left else r for r in selected],'LAP_OUTPUT_FUNCTION')
    duplicate=list(selected);duplicate.insert(duplicate.index(emitted)+1,dict(emitted))
    refuse('duplicate-emission',duplicate,'LAP_EMISSION_WITHOUT_PARSE')
    # The classification never promotes a register call or unwitnessed absolute
    # address to a known subprimitive merely because another call was known.
    known=next((d for d in original if any(t['kind']=='SUBPRIMITIVE' for t in transfers(d))),None)
    if known:
        damaged=dict(known,subprims=[])
        require(not any(t['kind']=='SUBPRIMITIVE' for t in transfers(damaged)),'LAP_MISSING_SUBPRIM_PROMOTED')
        result.append(dict(name='omit-subprimitive-lookup',status='REJECTED'))
    return result


def graph_delta(base,joined):
    nodes=[];edges=[];replacements=[]
    for r in joined:
        code=r['resident'];ident=f'resident-lap:{code}'
        nodes.append(node(ident,f'resident-lap/{code}',
            'Complete native assembler instruction witness. Target replacement, data, stores and traps remain obligations.',True))
        replacements.append(edge(f'identity:build:code:{code}',[ident],f'binding-versions/body/{code}','compile'))
        for t in r['transfers']:
            if t['kind'] in ('RETURN','LOCAL_LABEL'):continue
            target=ident+':transfer:'+str(t['parsed'])
            nodes.append(node(target,f'resident-lap/transfer/{code}/{t["parsed"]}',
                t['kind']+': '+t['mnemonic']+'; native transfer/condition requires target qualification.',True))
            edges.append(edge(ident,[target],f'resident-lap/transfer-use/{code}/{t["parsed"]}'))
            if t['kind'].startswith('UNRESOLVED'):
                edges.append(edge(target,[],f'resident-lap/transfer-values/{code}/{t["parsed"]}',complete=False))
    return dict(nodes=nodes,edges=edges,replacements=replacements)


def run(a):
    a.output.mkdir(parents=True,exist_ok=False)
    require(read(a.native/'summary.json')['status']=='PASS','LAP_NATIVE_RUN')
    old,_,_,_,_=capture(a.capture/'registries.jsonl.gz')
    bindings=read(a.bindings);frontends=read(a.frontends);requested=set(read(a.remaining));joined=[];checks=[];summaries=[]
    for unit in read(a.native/'summary.json')['units']:
        path=a.native/Path(unit['unit']).stem
        fs,_,_,_,_=capture(path/'registries.jsonl.gz',KINDS)
        events=list(rows(path/'registries.jsonl.gz'));definitions=replay(events,fs)
        found=join(frontends,old,definitions,fs,bindings,requested)
        joined.extend(found);checks.extend(dict(c,unit=unit['unit']) for c in controls(events,fs))
        # A wrong named definition can have the same machine code. It is still
        # refused unless the exact original cell and actual definition agree.
        if found:
            damaged=deepcopy(definitions)
            for d in damaged:
                if d['name']:d['name']['id']=-1
            require(not join(frontends,old,damaged,fs,bindings,requested),'LAP_WRONG_DEFINITION_ESCAPED')
            checks.append(dict(name='wrong-definition-cell',unit=unit['unit'],status='REJECTED'))
        summaries.append(dict(unit=unit['unit'],definitions=len(definitions),resident_joins=len(found),
            instructions=sum(len(d['instructions']) for d in definitions),
            transfers=dict(Counter(t['kind'] for d in definitions for t in transfers(d)))))
        save(a.output/(Path(unit['unit']).stem+'.json.gz'),definitions);print(summaries[-1],flush=True)
    ids={r['resident'] for r in joined};require(len(ids)==len(joined),'LAP_DUPLICATE_RESIDENT')
    expected={r['old'] for r in read(a.candidates)}&requested
    require(ids==expected,'LAP_RESIDENT_COVERAGE')
    base=read(a.base);delta=graph_delta(base,joined);graph=apply(base,delta)
    for name,value in [('joins.json.gz',joined),('controls.json',checks),('delta.json.gz',delta),('census.json.gz',graph),
                       ('remaining.json',sorted(requested-ids))]:save(a.output/name,value)
    from support import load_module
    errors=load_module('lap_contract',HERE.parents[3]/'doc/WASM/tools/check-census.py').validate(graph)
    require(all(e.startswith(('unresolved reachable edge from ','unimplemented reachable node ')) for e in errors),'LAP_GRAPH_STRUCTURE')
    summary=dict(status='PASS',census_status='BLOCKED',native_units=summaries,resident_assembly_bodies=len(joined),
                 remaining_readonly_bodies=len(requested-ids),controls=len(checks),target_assembly_implemented=False)
    save(a.output/'summary.json',summary);print(summary,flush=True)


if __name__=='__main__':
    import argparse,traceback
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('native','capture','bindings','frontends','candidates','remaining','base','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    try:run(a)
    except BaseException:
        if a.output.exists():(a.output/'failure.txt').write_text(traceback.format_exc())
        raise
