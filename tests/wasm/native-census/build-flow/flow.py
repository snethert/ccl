"""Read the *retained build's* complete IR using the reviewed flat-flow checker.

The older observer did not serialize assignment flags. The adapter supplies no
positive assignment hint; the bounder still scans writes and unknown variable
uses across the entire family. The reviewed cleared-flags control exercises
this mode. Symbols and literal payloads are data, not executable graph edges.
Names are diagnostic; AFUNC, variable, acode and code identities are unchanged.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'source-closure'))
from analysis import Graph, functions, require, CALLS
from bounds import analyze


def convert(payload, operators):
    observation = payload['function']; raw = payload['ir']
    nodes = {n['id']: n for n in raw['objects']}
    require(len(nodes) == len(raw['objects']), 'RICH_DUPLICATE_NODE')
    require(raw['root'] == {'ref': observation['function_id']}, 'RICH_ROOT')
    family = {f['function_id']: f for f in functions(observation)}
    # Check the full raw reference graph before projecting symbolic/literal data.
    pending = [raw['root']]; reached = set()
    while pending:
        x = pending.pop()
        if isinstance(x, dict):
            if 'ref' in x:
                require(set(x) == {'ref'} and x['ref'] in nodes, 'RICH_DANGLING')
                if x['ref'] not in reached:
                    reached.add(x['ref']); pending.extend(nodes[x['ref']].values())
            else: pending.extend(x.values())
        elif isinstance(x, list): pending.extend(x)
    require(reached == set(nodes), 'RICH_SURPLUS_NODE')
    require({n['id'] for n in nodes.values() if n['kind'] == 'afunc'} == set(family), 'RICH_FAMILY')

    def label(n):
        return (n['package'] or '#') + '::' + n['name']

    def ref(x):
        if x == {'atom': 'nil'}: return None
        for key in ('integer', 'string', 'character'):
            if isinstance(x, dict) and set(x) == {key}: return x[key]
        require(isinstance(x, dict) and set(x) == {'ref'} and x['ref'] in nodes, 'RICH_ATOM')
        n = nodes[x['ref']]
        if n['kind'] == 'symbol': return dict(symbol=label(n), identity=n['id'])
        return x

    converted = {}
    for ident, n in nodes.items():
        kind = n['kind']; out = dict(id=ident)
        if kind == 'symbol': continue
        if kind in ('acode', 'cons'):
            require(n['expanded'] is True, 'RICH_SHALLOW_EXECUTABLE')
        if kind == 'afunc':
            f = family[ident]
            require(n['parent'] == f['parent_id'], 'RICH_PARENT')
            out.update(kind='function', name=f['name'], body=ref(n['body']), children=n['children'])
        elif kind == 'acode':
            require(n['operator_id'] in operators and n['operator'] & 1023 == n['operator_id'], 'RICH_OPERATOR')
            out.update(kind=kind, operator=operators[n['operator_id']], operator_id=n['operator_id'], operands=ref(n['operands']))
        elif kind == 'cons':
            out.update(kind=kind, car=ref(n['car']), cdr=ref(n['cdr']))
        elif kind == 'variable':
            name = ref(n['name'])
            require(isinstance(name, dict) and 'symbol' in name, 'RICH_VARIABLE_NAME')
            out.update(kind=kind, root=n['root'], name=name['symbol'], assigned=False)
        elif kind == 'function':
            out.update(kind='native-function', function_id=n['code'], name=n['description']['name'])
        elif kind in ('simple-vector', 'pathname', 'opaque'):
            out.update(kind='opaque-object', type=kind)
        else: raise ValueError('RICH_NODE_KIND ' + kind)
        converted[ident] = out
    # Name graphs, native LFUN metadata and literal vectors may contain objects
    # that are not in executable IR. Preserve those in the original input only.
    pending = [raw['root']]; reached = set()
    while pending:
        x = pending.pop()
        if isinstance(x, dict) and 'ref' in x:
            if x['ref'] not in reached:
                reached.add(x['ref']); pending.extend(converted[x['ref']].values())
        elif isinstance(x, list): pending.extend(x)
    result = dict(function=observation,
                  flow=dict(root=observation['function_id'], objects=[converted[i] for i in sorted(reached)]))
    Graph(result['flow']).check(observation)
    return result


def extract(payload, operators, builtins):
    capture = convert(payload, operators)
    graph = Graph(capture['flow'])
    raw_nodes = {n['id']: n for n in payload['ir']['objects']}
    # Independently read direct/self/lexical/builtin targets from operands. The
    # inherited checker covers call-site order and variable/global callees.
    for f in functions(capture['function']):
        by_site = {c['site_id']: c for c in f['calls']}
        for n in graph.body(f['function_id']):
            if n['operator'] not in CALLS: continue
            c = by_site[n['id']]; d = c['dependency']; args = graph.items(n['operands'])
            expected = None
            if n['operator'] == 'CCL::SELF-CALL':
                require(d['category'] == 'self', 'SELF_CATEGORY'); expected = f['function_id']
            elif n['operator'] == 'CCL::LEXICAL-FUNCTION-CALL':
                target = graph.node(args[0])
                require(target and target['kind'] == 'function' and d['category'] == 'lexical', 'LEXICAL_CATEGORY')
                expected = target['id']
            elif n['operator'] == 'CCL::BUILTIN-CALL':
                index = graph.node(args[0])
                require(index and index['operator'] == 'COMMON-LISP::FIXNUM', 'BUILTIN_OPERAND')
                slot = graph.items(index['operands'])[0]
                require(d['category'] == 'builtin' and d['builtin_index'] == slot and slot in builtins,
                        'BUILTIN_INDEX')
                require(d['targets'] == [dict(kind='global-binding', name=builtins[slot])], 'BUILTIN_BINDING')
            elif d['category'] == 'lexical-function-value':
                callee = graph.node(args[0]); seen = set()
                while callee and callee.get('operator') in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
                    require(callee['id'] not in seen, 'CALLEE_WRAPPER_CYCLE'); seen.add(callee['id'])
                    callee = graph.node(graph.items(callee['operands'])[1])
                require(callee and callee.get('operator') in ('CCL::SIMPLE-FUNCTION','CCL::CLOSED-FUNCTION'),
                        'DIRECT_FUNCTION_VALUE')
                target = graph.node(graph.items(callee['operands'])[0])
                require(target and target['kind'] == 'function', 'DIRECT_FUNCTION_TARGET'); expected = target['id']
            if expected is not None:
                require(len(d['targets']) == 1 and d['targets'][0]['kind'] == 'function'
                        and d['targets'][0]['id'] == expected, 'DIRECT_FUNCTION_ID')
    bounds = {(r['function_id'], r['call_site']): r for r in analyze(capture)}
    rows = []
    for f in functions(capture['function']):
        for c in f['calls']:
            bound = bounds.get((f['function_id'], c['site_id']))
            row = dict(function_id=f['function_id'], site_id=c['site_id'], operator=c['operator'],
                       dependency=c['dependency'], name=f['name'])
            if c['dependency']['category']=='global-binding':
                callee=graph.node(graph.items(graph.nodes[c['site_id']]['operands'])[0]); seen=set()
                while callee and callee.get('operator') in ('CCL::TYPED-FORM','CCL::TYPE-ASSERTED-FORM'):
                    require(callee['id'] not in seen,'CALLEE_WRAPPER_CYCLE');seen.add(callee['id'])
                    callee=graph.node(graph.items(callee['operands'])[1])
                require(callee and callee.get('operator') in ('CCL::IMMEDIATE','CCL::%FUNCTION'),'GLOBAL_DESIGNATOR')
                value=graph.items(callee['operands'])[0]
                row['global_symbol']=raw_nodes[value['identity']] if isinstance(value,dict) and 'symbol' in value else None
            if bound is not None: row['lexical_bound'] = bound
            rows.append(row)
    return list(functions(capture['function'])), rows
