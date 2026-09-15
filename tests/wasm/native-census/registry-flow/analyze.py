"""Join compiler bodies and completed native registry operations by same-run EQ IDs."""
from collections import Counter
from copy import deepcopy


def require(ok, reason):
    if not ok: raise ValueError(reason)


def keyed(rows, field, reason):
    require(isinstance(rows,list) and all(isinstance(r,dict) and type(r.get(field)) is int for r in rows), reason)
    result={r[field]:r for r in rows}
    require(len(result)==len(rows),reason)
    return result


def assess(data):
    require(data['version']==1 and data['namespace']=='same-execution-native-registry-flow','NAMESPACE')
    require(data['mode']=='observed','OBSERVATION_MODE')
    require(data['observer_restored'] is True and data['exceptional_restoration'] is True,'RESTORATION')
    require(data['old_build_identity_join'] is False and data['exhaustive_callee_bound'] is False,'SCOPE')
    functions=keyed(data['functions'],'id','FUNCTION_IDS')
    for f in functions.values():
        require(f['prototype'] in functions,'PROTOTYPE')
    initial=keyed(data['initial'],'gf','INITIAL_IDS'); final=keyed(data['final'],'gf','FINAL_IDS')
    require(initial.keys()==final.keys(),'REGISTRY_SET')

    def state(s):
        require(s['gf'] in functions and s['dcode'] in functions,'STATE_FUNCTION')
        require(bool(functions[s['gf']]['bits'] & (1<<27)) and not functions[s['gf']]['bits'] & (1<<28),'GF_SUBTYPE')
        if s['status']=='UNINITIALIZED':
            require(s['methods'] is None and s['unbound_slots'], 'UNBOUND_STATE')
            return
        require(s['status']=='INITIALIZED' and s['native_standard_gf'] is True
                and s['slots_owner_matches'] is True,'STATE_SUBTYPE')
        methods=keyed(s['methods'],'id','METHOD_IDS')
        for m in methods.values():
            require(m['owner']==s['gf'],'METHOD_OWNER')
            require(m['function'] in functions and functions[m['function']]['bits'] & (1<<28),'METHOD_FUNCTION')
            require(isinstance(m['specializers'],list) and all(type(i) is int for i in m['specializers'])
                    and isinstance(m['qualifiers'],list),'METHOD_SHAPE')

    for s in list(initial.values())+list(final.values()): state(s)
    events=data['events']; stack=[]; entries={}; ended={}; mutations=[]; compiled=[]; calls=[]
    seen_gfs=set(); last={}; counts=Counter(); phase_counts=Counter()
    for seq,e in enumerate(events,1):
        require(e['sequence']==seq,'SEQUENCE')
        kind=e['kind']; counts[kind]+=1; phase_counts[e['phase']]+=1
        require(e['phase'] in ('describe','probe'),'PHASE')
        require(e['parent']==(stack[-1] if stack else None),'EVENT_PARENT')
        if kind.endswith('-enter'):
            require(kind in ('compile-enter','add-enter','remove-enter','dcode-enter'),'EVENT_KIND')
            entries[seq]=e; stack.append(seq)
            if kind!='compile-enter':
                state(e['state']); gf=e['state']['gf']
                require(gf in initial,'EVENT_GF')
                if gf not in seen_gfs:
                    require(e['state']==initial[gf],'INITIAL_STATE'); seen_gfs.add(gf)
        elif kind.endswith('-leave'):
            require(stack and e['entry']==stack[-1],'EVENT_PAIR')
            enter=entries[stack.pop()]
            require(kind==enter['kind'].replace('-enter','-leave') and e['phase']==enter['phase'],'EVENT_PAIR')
            require(e['completed'] is True,'INCOMPLETE_OPERATION')
            ended[e['entry']]=e
            if kind=='compile-leave':
                graph=enter['flow']; objects=keyed(graph['objects'],'id','IR_OBJECT_IDS')
                require(graph['root'] in objects and objects[graph['root']]['kind']=='function','IR_ROOT')
                # Graph links are explicit; opaque values are retained objects.
                todo=list(objects.values())
                while todo:
                    v=todo.pop()
                    if isinstance(v,dict):
                        if set(v)=={'ref'}: require(v['ref'] in objects,'IR_REFERENCE')
                        else: todo.extend(v.values())
                    elif isinstance(v,list): todo.extend(v)
                ir_functions={i:r for i,r in objects.items() if r['kind']=='function'}
                emissions=keyed(e['emissions'],'afunc','EMISSION_IDS')
                require(emissions.keys()==ir_functions.keys(),'EMISSION_COVERAGE')
                for a,r in emissions.items():
                    require(r['function'] in functions,'EMISSION_FUNCTION')
                    require(isinstance(r['code'],str) and r['code'] and len(r['code'])%16==0
                            and all(c in '0123456789abcdef' for c in r['code']),'EMISSION_CODE')
                    body=ir_functions[a]['body']
                    require(isinstance(body,dict) and body.get('ref') in objects,'IR_BODY')
                    compiled.append(dict(phase=e['phase'],entry=e['entry'],completed_at=seq,
                                         afunc=a,body=body['ref'],function=r['function'],code=r['code']))
            else:
                before=enter['state']; after=e['state']; state(after)
                require(before['gf']==after['gf'],'MUTATION_GF')
                gf=after['gf']; last[gf]=after
                if kind=='dcode-leave':
                    require(enter['method'] is None and e['method'] is None,'DCODE_METHOD')
                    require(before['methods']==after['methods'] and after['dcode']==enter['target'],'DCODE_TRANSITION')
                else:
                    m=enter['method']; n=e['method']
                    require(before['status']==after['status']=='INITIALIZED','MUTATION_INITIALIZATION')
                    require(m['id']==n['id'] and {k:v for k,v in m.items() if k!='owner'}==
                            {k:v for k,v in n.items() if k!='owner'},'METHOD_MUTATION')
                    if kind=='add-leave':
                        require(m['owner'] is None and n['owner']==gf,'ADD_OWNER')
                        replaced=[r for r in before['methods'] if r['qualifiers']==m['qualifiers'] and r['specializers']==m['specializers']]
                        require(len(replaced)<=1,'REPLACEMENT_AMBIGUITY')
                        expect=[n]+[r for r in before['methods'] if r not in replaced]
                        require(after['methods']==expect,'ADD_TRANSITION')
                        if replaced:
                            require(any(r['kind']=='remove-enter' and r['parent']==enter['sequence']
                                        and r['method']['id']==replaced[0]['id'] for r in events[enter['sequence']:seq-1]),'REPLACEMENT_REMOVAL')
                    else:
                        require(m['owner']==gf and n['owner'] is None,'REMOVE_OWNER')
                        require(m in before['methods'] and after['methods']==[r for r in before['methods'] if r['id']!=m['id']],'REMOVE_TRANSITION')
                    mutations.append(dict(kind=kind[:-6],entry=enter['sequence'],completed_at=seq,
                                          gf=gf,method=n['id'],function=n['function'],phase=e['phase']))
        else:
            require(kind=='call' and not stack,'EVENT_KIND')
            calls.append({k:e[k] for k in ('name','gf','values')})
    require(not stack and seen_gfs==initial.keys(),'EVENT_COVERAGE')
    for gf in final:
        require(last[gf]['methods']==final[gf]['methods'],'FINAL_METHODS')
    require([(c['name'],c['values']) for c in calls]==[
        ('replacement',[30,31]),('warm-replacement',[30,31]),('removed-specialization',[10,11])],'CALL_VALUES')
    require(len({c['gf'] for c in calls})==1,'CALL_GF')
    emitted=keyed(compiled,'function','COMPILED_FUNCTION_UNIQUENESS')
    joins=[]; missing=[]
    for m in sorted(mutations,key=lambda r:r['entry']):
        if m['kind']!='add': continue
        prototype=functions[m['function']]['prototype']
        if prototype in emitted:
            c=emitted[prototype]
            require(c['completed_at']<m['entry'],'BODY_BEFORE_INSTALL')
            require(c['code']==entries[m['entry']]['method_code'],'INSTALLED_CODE_BYTES')
            joins.append(dict(m,prototype=prototype,compile_entry=c['entry'],afunc=c['afunc'],body=c['body'],
                              relation='OBSERVED_INSTALLATION_TO_COMPILER_BODY'))
        else:
            missing.append(dict(m,prototype=prototype,reason='NO_COMPILER_BODY_IN_THIS_EXECUTION',
                                disposition='UNRESOLVED_CONSTRUCTION'))
    require(counts==Counter({'compile-enter':225,'compile-leave':225,'add-enter':240,'add-leave':240,
                             'remove-enter':239,'remove-leave':239,'dcode-enter':12,'dcode-leave':12,'call':3}),'CORPUS_EVENT_COUNTS')
    require(len(initial)==118 and len(compiled)==401 and len(joins)==163 and len(missing)==77,'CORPUS_JOIN_COUNTS')
    summary=dict(status='PASS',scope='native lib/describe.lisp reload and private replacement/removal probe',
                 events=len(events),event_counts=dict(sorted(counts.items())),phase_counts=dict(sorted(phase_counts.items())),
                 observed_gfs=len(initial),compiler_roots=225,compiler_functions=len(compiled),
                 installed_methods=len(joins)+len(missing),body_joins=len(joins),construction_gaps=len(missing),
                 old_build_identity_joins=0,exhaustive_callee_bounds=0,census_gate_credit=False)
    facts=dict(version=1,namespace=data['namespace'],body_joins=joins,construction_gaps=missing,
               completed_mutations=sorted(mutations,key=lambda r:r['entry']),
               compiler_bodies=[{k:v for k,v in c.items() if k!='code'} for c in compiled],
               initial=data['initial'],final=data['final'],scope=summary['scope'])
    return facts,summary


def check(facts,summary,data):
    expected=assess(data)
    require(facts==expected[0],'EXACT_JOIN_RECORDS')
    require(summary==expected[1],'EXACT_SUMMARY')


def controls(data,facts,summary,omission):
    rows=[]
    def reject(name,change,reason):
        a=deepcopy(data); f=deepcopy(facts); s=deepcopy(summary)
        change(a,f,s)
        try: check(f,s,a)
        except (ValueError,KeyError,TypeError) as e:
            require(str(e)==reason,'CONTROL_REASON '+name+' '+str(e)); rows.append(dict(name=name,status='REJECTED',reason=reason)); return
        raise ValueError('CONTROL_ESCAPED '+name)
    def first(a,kind): return next(e for e in a['events'] if e['kind']==kind)
    reject('foreign-namespace',lambda a,f,s:a.update(namespace='old-build'),'NAMESPACE')
    reject('old-build-promotion',lambda a,f,s:a.update(old_build_identity_join=True),'SCOPE')
    reject('callee-bound-promotion',lambda a,f,s:a.update(exhaustive_callee_bound=True),'SCOPE')
    reject('unrestored-exception',lambda a,f,s:a.update(exceptional_restoration=False),'RESTORATION')
    reject('duplicate-function',lambda a,f,s:a['functions'].append(a['functions'][0]),'FUNCTION_IDS')
    reject('missing-prototype',lambda a,f,s:a['functions'][0].update(prototype=-1),'PROTOTYPE')
    reject('wrong-owner',lambda a,f,s:a['initial'][0]['methods'][0].update(owner=-1),'METHOD_OWNER')
    reject('duplicate-method',lambda a,f,s:a['initial'][0]['methods'].append(a['initial'][0]['methods'][0]),'METHOD_IDS')
    reject('lost-event',lambda a,f,s:a['events'].pop(0),'SEQUENCE')
    reject('wrong-parent',lambda a,f,s:first(a,'add-enter').update(parent=-1),'EVENT_PARENT')
    reject('wrong-pair',lambda a,f,s:first(a,'add-leave').update(entry=-1),'EVENT_PAIR')
    reject('incomplete-install',lambda a,f,s:first(a,'add-leave').update(completed=False),'INCOMPLETE_OPERATION')
    reject('missing-emission',lambda a,f,s:first(a,'compile-leave')['emissions'].pop(),'EMISSION_COVERAGE')
    reject('unknown-emitted-function',lambda a,f,s:first(a,'compile-leave')['emissions'][0].update(function=-1),'EMISSION_FUNCTION')
    reject('absent-ir-root',lambda a,f,s:first(a,'compile-enter')['flow'].update(root=-1),'IR_ROOT')
    reject('wrong-dcode',lambda a,f,s:first(a,'dcode-enter').update(target=-1),'DCODE_TRANSITION')
    def wrong_code(a,f,s):
        entry=f['body_joins'][0]['entry']
        a['events'][entry-1]['method_code']='00'
    reject('wrong-installed-bytes',wrong_code,'INSTALLED_CODE_BYTES')
    reject('lost-result',lambda a,f,s:first(a,'call')['values'].pop(),'CALL_VALUES')
    reject('extra-body-join',lambda a,f,s:f['body_joins'].append(f['body_joins'][0]),'EXACT_JOIN_RECORDS')
    reject('retarget-body',lambda a,f,s:f['body_joins'][0].update(afunc=-1),'EXACT_JOIN_RECORDS')
    reject('hide-construction-gap',lambda a,f,s:f['construction_gaps'].pop(),'EXACT_JOIN_RECORDS')
    reject('unwitnessed-extra-method',lambda a,f,s:f['final'][0]['methods'].append(f['final'][0]['methods'][0]),'EXACT_JOIN_RECORDS')
    reject('changed-summary',lambda a,f,s:s.update(census_gate_credit=True),'EXACT_SUMMARY')
    omitted=deepcopy(omission); omitted['mode']='observed'
    try: assess(omitted)
    except ValueError as e:
        require(str(e) in ('FINAL_METHODS','CORPUS_EVENT_COUNTS','EVENT_COVERAGE'),'NATIVE_OMISSION_REASON '+str(e))
        rows.append(dict(name='native-add-hook-omission',status='REJECTED',reason=str(e)))
    else: raise ValueError('NATIVE_OMISSION_ESCAPED')
    return dict(status='PASS',controls_rejected=len(rows),controls=rows)
