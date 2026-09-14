"""Independently join the flat acode graph to the pre-existing census observer."""
from collections import Counter
from copy import deepcopy
import gzip
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LITERALS = {'CCL::IMMEDIATE', 'COMMON-LISP::FIXNUM', 'NIL', 'COMMON-LISP::T'}
CALLS = {'CCL::CALL', 'CCL::BUILTIN-CALL', 'CCL::LEXICAL-FUNCTION-CALL', 'CCL::SELF-CALL'}


def require(condition, reason):
    if not condition: raise ValueError(reason)


def read(path):
    return json.loads(gzip.decompress(path.read_bytes()) if path.suffix == '.gz' else path.read_bytes())


def functions(root):
    pending = [root]
    while pending:
        f = pending.pop(); yield f
        pending.extend(reversed(f['inner_functions']))


class Graph:
    def __init__(self, flow, function_root=True):
        self.nodes = {n['id']: n for n in flow['objects']}
        require(len(self.nodes) == len(flow['objects']), 'DUPLICATE_GRAPH_NODE')
        self.root = flow['root']
        require(self.root in self.nodes and (not function_root or self.nodes[self.root]['kind'] == 'function'), 'GRAPH_ROOT')
        shapes={'function':{'name','body','children'},'acode':{'operator','operator_id','operands'},
                'cons':{'car','cdr'},'variable':{'root','name','assigned'},
                'native-function':{'function_id','name'},'capture-guard':{'function_id','name'},
                'opaque-object':{'type'}}
        for n in self.nodes.values():
            require(n.get('kind') in shapes and set(n)==shapes[n['kind']]|{'id','kind'}, 'GRAPH_NODE_SHAPE')
            pending = list(n.values())
            while pending:
                x = pending.pop()
                if isinstance(x, dict):
                    if 'ref' in x: require(set(x) == {'ref'} and x['ref'] in self.nodes, 'DANGLING_REFERENCE')
                    else: require('symbol' in x and set(x) == {'symbol', 'identity'}, 'GRAPH_ATOM')
                elif isinstance(x, list): pending.extend(x)
        reached=set();pending=[{'ref':self.root}]
        while pending:
            x=pending.pop()
            if isinstance(x,dict):
                if 'ref' in x:
                    ident=x['ref']
                    if ident not in reached:
                        reached.add(ident);pending.extend(self.nodes[ident].values())
            elif isinstance(x,list):pending.extend(x)
        require(reached==set(self.nodes),'SURPLUS_GRAPH_NODE')

    def node(self, value):
        return self.nodes.get(value.get('ref')) if isinstance(value, dict) and 'ref' in value else None

    def items(self, value):
        seen = set(); result = []
        while value is not None:
            node = self.node(value)
            require(node and node['kind'] == 'cons' and node['id'] not in seen, 'OPERAND_LIST')
            seen.add(node['id']); result.append(node['car']); value = node['cdr']
        return result

    def body(self, function_id):
        pending = [self.nodes[function_id]['body']]; seen = set()
        while pending:
            node = self.node(pending.pop())
            if not node or node['id'] in seen: continue
            seen.add(node['id'])
            if node['kind'] == 'acode':
                yield node
                if node['operator'] not in LITERALS: pending.append(node['operands'])
            elif node['kind'] == 'cons': pending.extend((node['cdr'], node['car']))

    def check(self, observation):
        obs = list(functions(observation)); identifiers = [f['function_id'] for f in obs]
        observed_ids = {i for i,n in self.nodes.items() if n['kind'] == 'function'}
        require(len(set(identifiers)) == len(identifiers) and set(identifiers) == observed_ids, 'FUNCTION_SET')
        require(self.root == identifiers[0], 'FUNCTION_ROOT_JOIN')
        count = 0
        for f in obs:
            node = self.nodes[f['function_id']]
            require(node['name'] == f['name'], 'FUNCTION_NAME')
            require([v['ref'] for v in node['children']] == [x['function_id'] for x in f['inner_functions']], 'FUNCTION_CHILDREN')
            body = list(self.body(f['function_id']))
            histogram = Counter(n['operator_id'] for n in body)
            require([dict(id=k,count=v) for k,v in sorted(histogram.items())] == f['operators'], 'OPERATOR_COUNTS')
            calls = [n for n in body if n['operator'] in CALLS]
            require([(n['id'],n['operator']) for n in calls] == [(c['site_id'],c['operator']) for c in f['calls']], 'CALL_SITE_SET')
            for n,c in zip(calls,f['calls']):
                if n['operator'] != 'CCL::CALL': continue
                operands = self.items(n['operands'])
                # NX1-%FUNCTION emits two operands; NX1-CALL adds spread-p.
                # U1 X862-CALL declares that third operand optional.
                require(len(operands) in (2,3), 'CALL_OPERANDS')
                callee = self.node(operands[0]); seen = set()
                while callee and callee.get('operator') in ('CCL::TYPED-FORM', 'CCL::TYPE-ASSERTED-FORM'):
                    require(callee['id'] not in seen, 'CALLEE_WRAPPER_CYCLE'); seen.add(callee['id'])
                    callee = self.node(self.items(callee['operands'])[1])
                if callee and callee.get('operator') in ('CCL::LEXICAL-REFERENCE', 'CCL::INHERITED-ARG'):
                    var = self.node(self.items(callee['operands'])[0])
                    require(var and var['kind']=='variable' and c['dependency']['category']=='function-variable'
                            and c['dependency']['variable_id']==var['root'], 'CALLEE_VARIABLE')
                if callee and callee.get('operator') == 'CCL::IMMEDIATE':
                    value = self.items(callee['operands'])[0]
                    if isinstance(value,dict) and 'symbol' in value and c['dependency']['category']=='global-binding':
                        require(c['dependency']['targets']==[dict(kind='global-binding',name=value['symbol'])], 'GLOBAL_CALLEE')
            count += len(calls)
        return dict(functions=len(obs), calls=count, graph_objects=len(self.nodes))


def check(capture, corpus=False):
    require(capture['version']==1 and capture['observer_restored'] is True and capture['fasl_written'] is False,
            'SCOPE')
    require(capture['macro_environment_qualified'] is False, 'QUALIFICATION_PROMOTION')
    forms = capture['forms']; by_form = {r['sequence']:r for r in forms}
    require(list(by_form)==list(range(1,len(forms)+1)), 'FORM_SEQUENCE')
    for f in forms:
        require(f['parent'] is None or f['parent'] in by_form and f['parent']<f['sequence'], 'FORM_PARENT')
    require([r['ordinal'] for r in capture['captures']]==list(range(len(capture['captures']))), 'CAPTURE_SEQUENCE')
    guards = [r['guard_id'] for r in capture['captures']]
    require(len(set(guards))==len(guards), 'GUARD_IDENTITY')
    gaps=capture.get('gaps',[])
    require(len({g['form'] for g in gaps})==len(gaps) and all(g['form'] in by_form for g in gaps),'GAP_FORM_SET')
    for r in capture['captures']:
        require(all(i in by_form for i in r['form_stack']),'CAPTURE_FORM_JOIN')
        boundary=r['form_stack'][0] if r['form_stack'] else float('inf')
        require(r['prior_gaps']==[g['form'] for g in gaps if g['form']<boundary],'CAPTURE_PRIOR_GAPS')
    total=Counter()
    for r in capture['captures'] + capture.get('native_compilations',[]):
        total.update(Graph(r['flow']).check(r['function']))
        if 'emissions' in r:
            require([e['function_id'] for e in r['emissions']]==[f['function_id'] for f in functions(r['function'])],
                    'NATIVE_EMISSION_SET')
            require(r['emissions'][0]['native_function_id']==r['native_function_id'], 'NATIVE_EMISSION_ROOT')
            for e in r['emissions']:
                require((e['code'] is None)==(e['native_function_id'] is None),'NATIVE_EMISSION_PRESENCE')
                if e['code'] is not None:
                    require(e['code'] and len(e['code'])%16==0 and
                            all(x in '0123456789abcdef' for x in e['code']),'NATIVE_CODE_BYTES')
    if capture.get('output_graph'):
        outputs=Graph(capture['output_graph'],function_root=False)
        rows=[outputs.items(x) for x in outputs.items({'ref':outputs.root})]
        require([r[0] for r in rows]==capture['output_opcodes'],'FCOMP_OPCODE_JOIN')
        native_ids={e['native_function_id'] for r in capture.get('native_compilations',[])
                    for e in r.get('emissions',[]) if e['native_function_id'] is not None}
        guard_ids=set(guards)
        for r in rows:
            if r[0] in (4,35,37):  # U1 FASL lfuncall, defun, macro records.
                fn=outputs.node(r[1])
                require(fn and fn['kind'] in ('native-function','capture-guard'),'FCOMP_FUNCTION_KIND')
                if fn['id'] not in native_ids|guard_ids:
                    # Native LAP can supply function objects without invoking
                    # Lisp pass 2. Keep that population explicitly unjoined.
                    require(fn['kind']=='native-function','FCOMP_FUNCTION_JOIN')
                    total['unjoined_output_functions']+=1
        if corpus: require(not total['unjoined_output_functions'],'CORPUS_OUTPUT_JOIN')
    if corpus:
        require(capture['status']=='CAPTURED' and capture['problem'] is None and not capture.get('gaps'), 'CORPUS_COMPLETION')
        records=capture['captures'] or [r for r in capture.get('native_compilations',[]) if r['role']=='file-function']
        names=Counter(f['name'] for r in records for f in functions(r['function']))
        expected=('CENSUS-FIRST','CENSUS-SECOND','CENSUS-TWICE','CENSUS-SMALL','CENSUS-EXPANDED',
                  'CENSUS-DEFERRED','COPY-CENSUS-PAIR','CENSUS-PAIR-P','CENSUS-PAIR-LEFT','CENSUS-PAIR-RIGHT','MAKE-CENSUS-PAIR',
                  'CENSUS-INCLUDED','CENSUS-LOCAL-MACRO')
        for n in expected: require(names['COMMON-LISP-USER::'+n]==1, 'CORPUS_DEFINITION '+n)
        require(names['(COMMON-LISP-USER::CENSUS-METHOD (COMMON-LISP-USER::CENSUS-CELL))']==1,'CORPUS_METHOD')
        require(names['(COMMON-LISP:SETF COMMON-LISP-USER::CENSUS-PAIR-LEFT)']==1 and
                names['(COMMON-LISP:SETF COMMON-LISP-USER::CENSUS-PAIR-RIGHT)']==1,'CORPUS_ACCESSORS')
        deferred=next(r for r in records if r['function']['name']=='COMMON-LISP-USER::CENSUS-DEFERRED')
        require(sum(r['owner_id']==deferred['function']['function_id'] for r in records)==1,'DEFERRED_OWNER')
        require(all(f['completed'] for f in forms), 'CORPUS_FORM_COMPLETION')
        require(all(e['completed'] for e in capture['compile_time_effects']), 'CORPUS_EFFECT_COMPLETION')
        effect_ops={e['operator'] for e in capture['compile_time_effects']}
        require({'CCL::%DEFTYPE','CCL::DEFINE-COMPILE-TIME-MACRO','CCL::DEFINE-COMPILE-TIME-STRUCTURE',
                 'CCL::%COMPILE-TIME-DEFCLASS','COMMON-LISP::IF'}<=effect_ops, 'CORPUS_EFFECTS')
        require(len(capture['read_inputs'])==2 and all(r['completed'] for r in capture['read_inputs']) and
                capture['read_inputs'][1]['filename'].endswith('/included.lisp'), 'CORPUS_INCLUDE')
        wasm=bool(capture['captures'])
        require(names['COMMON-LISP-USER::CENSUS-WASM-FEATURE']==int(wasm) and
                names['COMMON-LISP-USER::CENSUS-NATIVE-FEATURE']==int(not wasm), 'CORPUS_READ_CONDITIONAL')
        if not wasm:
            require(capture['native_checks']==[
              dict(name='COMMON-LISP-USER::CENSUS-FIRST',input=41,result=42),
              dict(name='COMMON-LISP-USER::CENSUS-LOCAL-MACRO',input=41,result=42),
              dict(name='COMMON-LISP-USER::CENSUS-EXPANDED',input=20,result=40)],'CORPUS_NATIVE_RESULTS')
    return dict(total)


def controls(capture):
    rows=[]
    def trial(name, mutate, reason):
        changed=deepcopy(capture); mutate(changed)
        try: check(changed,corpus=True)
        except ValueError as e: require(str(e)==reason,'CONTROL_REASON '+name+': '+str(e))
        else: raise ValueError('CONTROL_ESCAPED '+name)
        rows.append(dict(name=name,status='REJECTED',reason=reason))
    def records(c):return c['captures'] or [r for r in c.get('native_compilations',[]) if r['role']=='file-function']
    def caller(c): return next(r for r in records(c) if r['function']['name']=='COMMON-LISP-USER::CENSUS-SECOND')
    trial('drop-observed-call',lambda c:caller(c)['function']['calls'].clear(),'CALL_SITE_SET')
    trial('invent-graph-function',lambda c:caller(c)['flow']['objects'].append(dict(id=-1,kind='function',name='invented',body=None,children=[])), 'SURPLUS_GRAPH_NODE')
    trial('change-call-target',lambda c:caller(c)['function']['calls'][0]['dependency']['targets'][0].__setitem__('name','WRONG'),'GLOBAL_CALLEE')
    trial('duplicate-graph-record',lambda c:caller(c)['flow']['objects'].append(deepcopy(caller(c)['flow']['objects'][0])),'DUPLICATE_GRAPH_NODE')
    trial('missing-graph-record',lambda c:caller(c)['flow']['objects'].pop(),'DANGLING_REFERENCE')
    if capture['captures']:
        trial('alias-guards',lambda c:c['captures'][1].__setitem__('guard_id',c['captures'][0]['guard_id']),'GUARD_IDENTITY')
    else:
        trial('drop-emission',lambda c:caller(c)['emissions'].clear(),'NATIVE_EMISSION_SET')
        trial('wrong-emitted-function',lambda c:caller(c)['emissions'][0].__setitem__('native_function_id',-1),'NATIVE_EMISSION_ROOT')
        trial('unexecuted-native-result',lambda c:c['native_checks'].pop(),'CORPUS_NATIVE_RESULTS')
    trial('false-source-completion',lambda c:c['forms'][0].__setitem__('completed',False),'CORPUS_FORM_COMPLETION')
    trial('false-effect-completion',lambda c:c['compile_time_effects'][0].__setitem__('completed',False),'CORPUS_EFFECT_COMPLETION')
    trial('omitted-compile-time-effects',lambda c:c['compile_time_effects'].clear(),'CORPUS_EFFECTS')
    trial('missing-owner',lambda c:next(r for r in records(c) if r['owner_id'] is not None).__setitem__('owner_id',-1),'DEFERRED_OWNER')
    trial('missing-include',lambda c:c['read_inputs'].pop(),'CORPUS_INCLUDE')
    trial('incomplete-include',lambda c:c['read_inputs'][1].__setitem__('completed',False),'CORPUS_INCLUDE')
    trial('qualification-promotion',lambda c:c.__setitem__('macro_environment_qualified',True),'QUALIFICATION_PROMOTION')
    return rows


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('capture',type=Path);p.add_argument('--corpus',action='store_true')
    a=p.parse_args();c=read(a.capture);print(check(c,a.corpus))
    if a.corpus: print('controls',len(controls(c)))
