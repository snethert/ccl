"""Independent, deliberately narrow data-FASL decoder and object identity oracle."""
from copy import deepcopy
import gzip
import importlib.util
import json
from pathlib import Path
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location('object_traversal_check', HERE.parent/'target-descriptions/analysis.py')
traversal = importlib.util.module_from_spec(spec); spec.loader.exec_module(traversal)
require = traversal.require
read = lambda p: json.loads(gzip.decompress(p.read_bytes()) if p.suffix == '.gz' else p.read_bytes())
s = lambda name: {'symbol': name}


def cons(a, b): return {'cons': [a, b]}


def l(*xs):
    answer = None
    for x in reversed(xs): answer = cons(x, answer)
    return answer


def elements(x):
    result = []
    while x is not None:
        require(isinstance(x, dict) and set(x) == {'cons'} and len(x['cons']) == 2, 'PROPER_LIST')
        a, x = x['cons']; result.append(a)
    return result


class Decoder:
    """Accept only the opcodes needed by this corpus; never evaluate Lisp/code.

    Counts use U1's high-bit *terminator*. Epush reserves ordinary object slots
    before their children, but EVAL publishes after reading its creation form.
    The small bound is a fixture bound, not a general CCL FASL implementation.
    """
    def __init__(self, data):
        self.data, self.pos, self.refs, self.ops = data, 0, [], []

    def take(self, n):
        require(n >= 0 and self.pos+n <= len(self.data), 'FASL_TRUNCATED')
        answer = self.data[self.pos:self.pos+n]; self.pos += n; return answer

    def byte(self): return self.take(1)[0]

    def count(self):
        answer = 0
        for shift in range(0, 35, 7):
            b = self.byte(); answer |= (b & 127) << shift
            if b & 128:
                require(answer <= 4096, 'FASL_COUNT_BOUND'); return answer
        raise ValueError('FASL_COUNT_BOUND')

    def string(self):
        value = self.take(self.count())
        require(all(32 <= c < 127 for c in value), 'FASL_ASCII')
        return value.decode('ascii')

    def expr(self, depth=0):
        require(depth < 64, 'FASL_DEPTH')
        offset, raw = self.pos, self.byte(); op, push = raw & 127, bool(raw & 128)
        require(op in (15, 18, 25, 28, 39, 44, 45, 63, 65, 66, 71) and raw != 255, 'FASL_OPCODE')
        require(not push or op in (15, 28, 44, 45, 65, 66), 'FASL_EPUSH')
        self.ops.append(dict(offset=offset, opcode=op, epush=push))
        placeholder = {}
        if push and op != 28: self.refs.append(placeholder)
        expr = lambda: self.expr(depth+1)
        if op == 18: value = None
        elif op == 25:
            idx = self.count(); require(idx < len(self.refs) and self.refs[idx], 'FASL_REFERENCE')
            value = self.refs[idx]
        elif op == 65: value = {'package': self.string()}
        elif op in (63, 66):
            pkg = expr(); require(set(pkg) == {'package'}, 'FASL_PACKAGE')
            value = s(pkg['package']+'::'+self.string())
        elif op == 15: value = cons(expr(), expr())
        elif op in (44, 45):
            items = [expr() for _ in range(self.count()+1)]
            value = None if op == 44 else expr()
            for x in reversed(items): value = cons(x, value)
        elif op == 28: value = {'eval': expr()}
        elif op == 71: value = {'istruct_cell': expr()}
        elif op == 39: value = {'defparameter': [expr(), expr(), expr()]}
        if push:
            placeholder.update(value); value = placeholder
            if op == 28: self.refs.append(value)
        return value

    def decode(self):
        require(len(self.data) <= 4096, 'FASL_SIZE_BOUND')
        magic, blocks, start, size = struct.unpack('>HHII', self.take(12))
        require((magic, blocks, start, size) == (0xff00, 1, 12, len(self.data)-12), 'FASL_HEADER')
        # Native x86-64 U1 data version, not a Wasm object file.
        require(self.take(6) == bytes.fromhex('ff6200000000'), 'FASL_NATIVE_VERSION')
        require(self.byte() == 24, 'FASL_TABLE')
        capacity = self.count(); value = self.expr()
        require(self.byte() == 255 and self.pos == len(self.data), 'FASL_END')
        require(len(self.refs) <= capacity, 'FASL_TABLE_CAPACITY')
        return value


CLASS_FORM = l(s('CCL::FIND-CLASS-CELL'), l(s('COMMON-LISP::QUOTE'), s('CCL::IOBLOCK')), s('COMMON-LISP::T'))
CONTROL_REASONS = {'wrong-class': 'CLASS_KEY', 'wrong-restart': 'RESTART_KEY',
                   'unregistered': 'RESTART_IDENTITY', 'unevaluated': 'CLASS_TYPE'}
FILES = ('objects', 'empty-payload', 'sentinel-payload', *CONTROL_REASONS)
POSITIVE = ('original', 'fresh', 'fresh-repeat', 'absent', 'created-repeat')


def object_oracle(row):
    require(row['length'] == 3, 'OBJECT_COUNT')
    require(row['class_cell'], 'CLASS_TYPE')
    require(row['class_name'] == s('CCL::IOBLOCK'), 'CLASS_KEY')
    require(row['class_registered'], 'CLASS_IDENTITY')
    require(row['shared_class'], 'CLASS_SHARING')
    require(row['restart_name'] == s('COMMON-LISP::RESTART'), 'RESTART_KEY')
    require(row['restart_registered'], 'RESTART_IDENTITY')


def refs(x):
    if isinstance(x, dict):
        if 'object_ref' in x: yield x['object_ref']
        for v in x.values(): yield from refs(v)
    elif isinstance(x, list):
        for v in x: yield from refs(v)


def compile_only(x, identity, inside=False):
    if isinstance(x, dict):
        if x.get('object_ref') == identity: require(inside, 'ENVIRONMENT_RUNTIME_REFERENCE')
        if set(x) == {'cons'} and x['cons'][0] == s('COMMON-LISP::EVAL-WHEN'):
            forms = elements(x)
            inside = elements(forms[1]) == [s('KEYWORD::COMPILE-TOPLEVEL')]
        for v in x.values(): compile_only(v, identity, inside)
    elif isinstance(x, list):
        for v in x: compile_only(v, identity, inside)


def decoded_objects(data):
    d = Decoder(data); tree = d.decode()
    require(set(tree) == {'defparameter'}, 'FASL_TOPLEVEL')
    name, values, doc = tree['defparameter']
    require(name == s('CCL-TARGET-OBJECTS::*LOADED*') and doc is None, 'FASL_BINDING')
    values = elements(values); require(len(values) == 3, 'FASL_OBJECT_COUNT')
    return values, d.ops


def check(c, t, binaries):
    require(set(binaries) == set(FILES), 'FILE_BOUND')
    traversal.check_capture(t, (ROOT/'lib/dumplisp.lisp').read_bytes(), read(HERE.parent/'target-descriptions/descriptions.json'))
    require(c['version'] == 1 and c['restored'] and c['native_data_only'] and
            c['wasm_materialization'] == 'NOT_RUN' and not c['macro_environment_qualified'] and
            c['graph_edges_replaced'] == 0, 'SCOPE')
    events, literals, w = c['events'], c['literals'], c['witness']
    require([e['sequence'] for e in events] == list(range(293)) and
            all(e['selected_id'] != e['original_id'] for e in events), 'SOURCE_ROUTING')
    require([(r['type'], r['name'], r['disposition']) for r in literals] == [
        ('CCL::LEXICAL-ENVIRONMENT', None, 'UNQUALIFIED_NATIVE_LITERAL'),
        ('CCL::CLASS-CELL', 'CCL::IOBLOCK', 'UNQUALIFIED_NATIVE_LITERAL'),
        ('CCL::CLASS-WRAPPER', 'COMMON-LISP::RESTART', 'UNQUALIFIED_NATIVE_LITERAL')], 'LITERAL_BOUND')
    env, cell, wrapper = [r['id'] for r in literals]
    require(len({env, cell, wrapper}) == 3 and w['class_literal_id'] == cell and
            w['wrapper_literal_id'] == wrapper and w['class_registry_join'] and
            w['wrapper_registry_join'] and w['registry_restored'], 'ACTUAL_OBJECT_JOIN')
    require(w['class_creation_form'] == CLASS_FORM and
            w['registered_restart'] == cons(s('COMMON-LISP::RESTART'), {'object_ref': wrapper}), 'CREATION_RECIPE')
    uses = {r['id']: [e['sequence'] for e in events if r['id'] in refs(e['output'])] for r in literals}
    require(uses == {env: [2, 3, 4], cell: [26, 27, 30, 31, 32, 33, 69, 70, 73, 74, 75, 76],
                     wrapper: [199, 212]}, 'OBJECT_EVENT_JOIN')
    for e in events: compile_only(e['output'], env)
    for n in uses[wrapper]:
        require(events[n]['operator'] == 'CCL::REGISTER-ISTRUCT-CELL' and
                events[n]['input'] == l(s('CCL::REGISTER-ISTRUCT-CELL'), l(s('COMMON-LISP::QUOTE'), s('COMMON-LISP::RESTART'))) and
                events[n]['output'] == l(s('COMMON-LISP::QUOTE'), w['registered_restart']), 'RESTART_EXPANSION')
    values, ops = decoded_objects(binaries['objects'])
    require(values[0] == {'eval': CLASS_FORM} and values[2] is values[0], 'SERIALIZED_CLASS_RECIPE')
    require(values[1] == {'istruct_cell': s('COMMON-LISP::RESTART')}, 'SERIALIZED_RESTART_KEY')
    require(binaries['objects'] == binaries['empty-payload'] == binaries['sentinel-payload'], 'PAYLOAD_ERASURE')
    rows = w['roundtrips']
    require([r['name'] for r in rows] == ['original', 'fresh', 'fresh-repeat', *CONTROL_REASONS, 'absent', 'created-repeat'], 'CASE_BOUND')
    for row in rows:
        name = row['name']
        require(row['file'] == (name if name in CONTROL_REASONS else 'objects')+'.dx64fsl', 'CASE_FILE')
        if name in POSITIVE:
            object_oracle(row)
            for key in ('class', 'restart'):
                require(row[key+'_original'] == (name == 'original') and
                        row[key+'_empty'] == (name != 'original') and
                        row[key+'_expected'] == (name != 'absent'), 'LOAD_REGISTRY_HANDOFF')
        else:
            try: object_oracle(row)
            except ValueError as e: require(str(e) == CONTROL_REASONS[name], 'NATIVE_CONTROL_REASON')
            else: raise ValueError('NATIVE_CONTROL_ESCAPED')
            changed, _ = decoded_objects(binaries[name]); expected = deepcopy(values)
            if name == 'wrong-class':
                form = l(s('CCL::FIND-CLASS-CELL'), l(s('COMMON-LISP::QUOTE'), s('CCL::NOT-IOBLOCK')), s('COMMON-LISP::T'))
                expected[0] = expected[2] = {'eval': form}
            elif name == 'wrong-restart': expected[1] = {'istruct_cell': s('CCL::NOT-RESTART')}
            elif name == 'unregistered': expected[1] = l(s('COMMON-LISP::RESTART'))
            elif name == 'unevaluated': expected[0] = expected[2] = CLASS_FORM
            require(changed == expected and changed[0] is changed[2], 'MUTANT_FASL_CONTENT')
    return dict(expansion_events=293, object_kinds=3, runtime_object_kinds=2,
                class_expansion_uses=12, restart_expansion_uses=2, compile_only_environment_uses=3,
                native_roundtrips=5, native_negative_cases=4, data_fasls=7,
                data_fasl_bytes=len(binaries['objects']), opcode_kinds=sorted({r['opcode'] for r in ops}))


def controls(c, t, binaries):
    rows = []
    def refusal(name, fn, reason):
        try: fn()
        except ValueError as e: require(str(e) == reason, 'WRONG_CONTROL '+name+': '+str(e))
        else: raise ValueError('CONTROL_ESCAPED '+name)
        rows.append(dict(name=name, status='REJECTED', reason=reason))
    mutations = [
        ('scope-promotion', lambda x: x.update(wasm_materialization='PASS'), 'SCOPE'),
        ('unjoined-object', lambda x: x['witness'].update(class_literal_id=-1), 'ACTUAL_OBJECT_JOIN'),
        ('omitted-event', lambda x: x['events'].pop(), 'SOURCE_ROUTING'),
        ('surplus-literal', lambda x: x['literals'].append(x['literals'][0]), 'LITERAL_BOUND'),
        ('wrong-recipe', lambda x: x['witness'].update(class_creation_form=None), 'CREATION_RECIPE'),
        ('lost-sharing', lambda x: x['witness']['roundtrips'][1].update(shared_class=False), 'CLASS_SHARING'),
        ('retained-host-object', lambda x: x['witness']['roundtrips'][1].update(class_original=True), 'LOAD_REGISTRY_HANDOFF'),
        ('retained-wrapper', lambda x: x['witness']['roundtrips'][1].update(restart_empty=False), 'LOAD_REGISTRY_HANDOFF'),
        ('wrong-fresh-registry', lambda x: x['witness']['roundtrips'][1].update(restart_expected=False), 'LOAD_REGISTRY_HANDOFF'),
        ('surplus-case', lambda x: x['witness']['roundtrips'].append(x['witness']['roundtrips'][0]), 'CASE_BOUND')]
    for name, mutate, reason in mutations:
        x = deepcopy(c); mutate(x); refusal(name, lambda: check(x, t, binaries), reason)
    x = dict(binaries); x['sentinel-payload'] = x['unregistered']
    refusal('payload-leak', lambda: check(c, t, x), 'PAYLOAD_ERASURE')
    data = binaries['objects']; d = Decoder(data); d.decode()
    for name, mutate, reason in [
        ('bad-header', lambda b: b.__setitem__(0, 0), 'FASL_HEADER'),
        ('trailing-byte', lambda b: b.extend(b'\0'), 'FASL_HEADER'),
        ('missing-end', lambda b: b.__setitem__(-1, 0), 'FASL_END'),
        ('native-code-opcode', lambda b: b.__setitem__(next(r['offset'] for r in d.ops if r['opcode'] == 71), 3), 'FASL_OPCODE'),
        ('invalid-reference', lambda b: b.__setitem__(next(r['offset'] for r in d.ops if r['opcode'] == 25)+1, 255), 'FASL_REFERENCE')]:
        x = bytearray(data); mutate(x); refusal(name, lambda: Decoder(bytes(x)).decode(), reason)
    return rows
