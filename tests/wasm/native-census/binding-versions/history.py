"""Separate observed versions, callable roles and incomplete coverage."""
from collections import Counter, defaultdict
from common import require, canonical, SCOPE


def identity(value):
    # Function names/source annotations may change without changing the object.
    if value['role']=='function': return ('function',value['object'],value['code'])
    if value['role']=='macro-wrapper': return ('macro-wrapper',value['object'],identity(value['payload']))
    if value['role']=='special-wrapper': return ('special-wrapper',value['object'],value['payload']['id'])
    return ('unclassified',canonical(value['raw']))


def assemble(facts, functions, calls):
    emitted={}
    for f in functions:
        for c in f['emitted']:
            require(c['code'] not in emitted,'MATERIALIZED_CODE_DUPLICATE')
            emitted[c['code']]=dict(afunc=f['function_id'],event=c['event'])
    reads=defaultdict(list); resident={}
    for r in facts['reads']:
        if r['reader_mode']=='native':
            require('function' in r and 'image_word' not in r,'NATIVE_READER_VALUE')
            reads[r['function']].append(r)
        else: require('image_word' in r and 'function' not in r,'IMAGE_READER_VALUE')
    for r in facts['residents']:
        if r['stage']=='before': resident[r['code']]=r['event']
    def origin(code,event):
        if code in emitted and emitted[code]['event']<event:
            return dict(kind='materialized',code=code,**emitted[code])
        candidates=[r for r in reads[code] if r['event']<event]
        if candidates:
            r=candidates[-1]; w=r['written']
            source=emitted.get(w['code']) if w else None
            if source and source['event']<w['event']:
                return dict(kind='exact-fasl-version',code=code,afunc=source['afunc'],
                            materialized=source,read=r)
            return dict(kind='native-read-unjoined',code=code,read=r)
        if code in resident and resident[code]<event:
            return dict(kind='resident-before',code=code,event=resident[code])
        return dict(kind='unjoined',code=code)
    def annotated(v,event):
        v=dict(v)
        if v['role']=='function':v['origin']=origin(v['code'],event)
        elif v['role']=='macro-wrapper':v['payload']=annotated(v['payload'],event)
        return v
    by_symbol=defaultdict(list); descriptors=defaultdict(dict); call_counts=Counter()
    for b in facts['bindings']:
        # The observer emits NIL as an atom, without allocating a symbol ID.
        # Preserve that distinct literal identity; never join it by a name.
        i=b['symbol'].get('id','literal-NIL'); by_symbol[i].append(b); descriptors[i][canonical(b['symbol'])]=b['symbol']
    for c in calls:
        if c['dependency']['category']!='global-binding': continue
        s=c['global_symbol']; require(s and s['kind']=='symbol','CALL_SYMBOL_IDENTITY')
        i=s['id'];call_counts[i]+=1;descriptors[i][canonical(s)]=s
    histories=[]
    for i in sorted(descriptors,key=lambda i:(isinstance(i,str),i)):
        observations=[]; gaps=[]; known=None; pending=None; checkpoints={}
        for b in by_symbol[i]:
            event=b['sequence']; kind=b['kind']; v=b['value']
            if kind=='resident-binding':
                stage=b['stage']; require(stage not in checkpoints,'DUPLICATE_CHECKPOINT_BINDING')
                checkpoints[stage]=event
            if (kind=='binding-removing' or b.get('stage')=='after') and known is not None and pending is None:
                if identity(known['value'])!=identity(v):
                    gaps.append(dict(kind='unobserved-change',previous=known['sequence'],witness=event))
            out=dict(b,value=annotated(v,event));observations.append(out)
            if kind=='binding-removing':
                # Store completion is not observed. A later old-value or
                # inventory read is an independent witness, not confirmation
                # manufactured by replaying the intended store.
                pending=event; known=None
            else:known=b;pending=None
        functions_seen=sorted({o['value']['code'] for o in observations if o['value']['role']=='function'})
        expanders=sorted({o['value']['payload']['code'] for o in observations if o['value']['role']=='macro-wrapper'})
        histories.append(dict(symbol_id=i,descriptors=[descriptors[i][k] for k in sorted(descriptors[i])],
            call_count=call_counts[i],observations=observations,checkpoints=checkpoints,
            ordinary_codes=functions_seen,macro_expander_codes=expanders,continuity_gaps=gaps,
            pending_removal_intent=pending,observed_only=True,
            obligation='Exhaustive callable versions, unobserved changes and target/profile disposition remain open.'))
    reached=[h for h in histories if h['call_count']]
    counts=Counter(b['kind']+(':'+b['stage'] if 'stage' in b else '') for b in facts['bindings'])
    roles=Counter(o['value']['role'] for h in reached for o in h['observations'])
    origins=Counter(o['value']['origin']['kind'] for h in reached for o in h['observations'] if o['value']['role']=='function')
    summary=dict(scope=SCOPE,census_gate_credit=False,events=facts['events'],binding_observations=dict(counts),
        binding_identities=len(histories),literal_nil_observations=len(by_symbol.get('literal-NIL',[])),
        global_call_sites=sum(call_counts.values()),
        called_binding_identities=len(reached),called_bindings_with_observations=sum(bool(h['observations']) for h in reached),
        called_bindings_without_observations=sum(not h['observations'] for h in reached),
        called_bindings_with_multiple_ordinary_codes=sum(len(h['ordinary_codes'])>1 for h in reached),
        called_binding_value_roles=dict(roles),called_ordinary_value_origins=dict(origins),
        called_binding_continuity_gaps=sum(len(h['continuity_gaps']) for h in reached),
        all_binding_continuity_gaps=sum(len(h['continuity_gaps']) for h in histories),
        closed_runtime_candidate_bounds=0,computed_calls_changed=False,native_execution=False)
    return histories,summary


def check(histories, summary, facts, functions, calls):
    expected,report=assemble(facts,functions,calls)
    require(histories==expected,'HISTORY_RECORDS')
    require(summary==report,'HISTORY_SUMMARY')
