"""R6 comparison for the reviewed U1 census-registration patch.

This profile accepts exactly the two module-data additions. It does not
normalize FASLs or exempt an intentionally changed file from decoding.
"""
import hashlib
import json
import re
import struct
import copy

U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'

def require(condition, reason):
    if not condition:
        raise ValueError(reason)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def symbol(name):
    return {'symbol': name}

class DataFasl:
    """Complete, bounded decoder for this registration FASL profile.

    Preserve every decoded form, location, identity reference and raw opcode
    offset. Preserve the original package thunk as raw code; never execute it.
    """
    def __init__(self, data):
        self.data = data
        self.pos = 0
        self.refs = []
        self.ops = []
        self.capacity = None
        self.package = 'COMMON-LISP-USER'
        self.spans = {}

    def take(self, n):
        require(0 <= n <= len(self.data)-self.pos, 'FASL_TRUNCATED')
        result = self.data[self.pos:self.pos+n]
        self.pos += n
        return result

    def byte(self):
        return self.take(1)[0]

    def count(self):
        result = 0
        for shift in range(0, 35, 7):
            b = self.byte()
            result |= (b & 127) << shift
            if b & 128:
                require(result <= 4096, 'FASL_COUNT_BOUND')
                return result
        raise ValueError('FASL_COUNT_BOUND')

    def string(self):
        data = self.take(self.count())
        require(all(32 <= b < 127 for b in data), 'FASL_STRING')
        return data.decode('ascii')

    def expr(self, depth=0):
        require(depth < 64, 'FASL_DEPTH')
        start, raw = self.pos, self.byte()
        op, push = raw & 127, bool(raw & 128)
        require(op not in (2, 20, 27, 35, 37), 'FASL_EXECUTABLE_OPCODE')
        require(raw != 255 and op in (0, 3, 4, 10, 15, 18, 23, 25, 28, 34, 39, 44, 45, 47, 57, 63, 65, 66, 67, 69, 70), 'FASL_UNKNOWN_OPCODE')
        require(not push or op in (3, 10, 15, 18, 28, 44, 45, 63, 65, 66, 67, 69), 'FASL_EPUSH')
        self.ops.append({'offset': start, 'opcode': op, 'epush': push})
        slot = None
        if push and op != 28:
            slot = len(self.refs)
            self.refs.append(None)
        expr = lambda: self.expr(depth+1)
        if op == 0:
            value = {'noop': True}
        elif op == 3:
            size, words = self.count(), self.count()
            require(0 < words <= size <= 4096, 'FASL_FUNCTION_SIZE')
            value = {'function': {'code': self.take(words*8).hex(),
                                  'constants': [expr() for _ in range(size-words)]}}
        elif op == 4:
            value = {'call': expr()}
            require(value['call'].get('function', {}).get('constants') ==
                    ['CCL', symbol('CCL::SET-PACKAGE'), -536870912], 'FASL_PACKAGE_CALL')
            self.package = 'CCL'
        elif op == 10:
            value = struct.unpack('>h', self.take(2))[0]
        elif op == 57:
            value = struct.unpack('>i', self.take(4))[0]
        elif op == 18:
            value = None
        elif op == 25:
            index = self.count()
            require(index < len(self.refs) and self.refs[index] is not None, 'FASL_REFERENCE')
            value = self.refs[index]
        elif op == 65:
            value = {'package': self.string()}
        elif op in (63, 66):
            package = expr()
            require(isinstance(package, dict) and set(package) == {'package'}, 'FASL_PACKAGE')
            value = symbol(package['package']+'::'+self.string())
        elif op == 67:
            value = symbol(self.package+'::'+self.string())
        elif op == 69:
            value = self.string()
        elif op == 15:
            value = {'cons': [expr(), expr()]}
        elif op in (44, 45):
            items = [expr() for _ in range(self.count()+1)]
            tail = None if op == 44 else expr()
            for item in reversed(items):
                tail = {'cons': [item, tail]}
            value = tail
        elif op == 34:
            subtag, count = self.byte(), self.count()
            require(subtag == 54 and count == 4, 'FASL_LOCATION_VECTOR')
            value = {'vector': {'subtag': subtag, 'values': [expr() for _ in range(count)]}}
        elif op == 39:
            value = {'defparameter': [expr(), expr(), expr()]}
        elif op in (23, 28, 47, 70):
            value = {{23: 'platform', 28: 'eval', 47: 'source', 70: 'location'}[op]: expr()}
            if op == 28:
                # Decode, never execute, the two original metadata forms.
                package = conslist(symbol('CCL::SET-PACKAGE'), 'CCL')
                source_note = conslist(symbol('CCL::FIND-CLASS-CELL'),
                    conslist(symbol('COMMON-LISP::QUOTE'), symbol('CCL::SOURCE-NOTE')),
                    symbol('COMMON-LISP::T'))
                require(value['eval'] in (package, source_note), 'FASL_EVAL_FORM')
                if value['eval'] == package:
                    self.package = 'CCL'
        if push:
            if op == 28:
                self.refs.append(value)
            else:
                self.refs[slot] = value
            require(len(self.refs) <= self.capacity, 'FASL_TABLE_CAPACITY')
        if isinstance(value, dict) and op != 25:
            self.spans[id(value)] = (start, self.pos)
        return value

    def decode(self):
        require(len(self.data) <= 65536, 'FASL_SIZE_BOUND')
        require(struct.unpack('>HHII', self.take(12)) == (0xff00, 1, 12, len(self.data)-12), 'FASL_HEADER')
        require(self.take(6) == bytes.fromhex('ff6200000000'), 'FASL_VERSION')
        require(self.byte() == 24, 'FASL_TABLE')
        self.capacity = self.count()
        result = []
        while self.pos < len(self.data) and self.data[self.pos] != 255:
            result.append(self.expr())
        require(self.byte() == 255 and self.pos == len(self.data), 'FASL_END')
        return result

def conslist(*items):
    result = None
    for item in reversed(items):
        result = {'cons': [item, result]}
    return result

def elements(value):
    result = []
    while value is not None:
        require(isinstance(value, dict) and set(value) == {'cons'} and len(value['cons']) == 2, 'DATA_LIST')
        result.append(value['cons'][0])
        value = value['cons'][1]
        require(len(result) <= 4096, 'DATA_LIST_BOUND')
    return result

class LiteralSource:
    """Reader for this file's lists, quotes, ASCII strings and symbol tokens.

    No reader evaluation, reader conditionals, macro execution or host packages.
    Its top-level spans independently supply the serialized source locations.
    """
    def __init__(self, text):
        self.text, self.pos, self.spans = text, 0, []

    def whitespace(self):
        while self.pos < len(self.text):
            if self.text[self.pos].isspace(): self.pos += 1
            elif self.text[self.pos] == ';':
                end = self.text.find('\n', self.pos)
                self.pos = len(self.text) if end == -1 else end+1
            else: break

    def expr(self, depth=0):
        require(depth < 64, 'SOURCE_DEPTH')
        self.whitespace(); require(self.pos < len(self.text), 'SOURCE_EOF')
        c = self.text[self.pos]; self.pos += 1
        if c == '(':
            items = []
            while True:
                self.whitespace(); require(self.pos < len(self.text), 'SOURCE_LIST')
                if self.text[self.pos] == ')': self.pos += 1; return conslist(*items)
                items.append(self.expr(depth+1)); require(len(items) <= 4096, 'SOURCE_LIST_BOUND')
        if c == "'": return conslist(symbol('COMMON-LISP::QUOTE'), self.expr(depth+1))
        if c == '"':
            start = self.pos
            while self.pos < len(self.text) and self.text[self.pos] != '"':
                require(32 <= ord(self.text[self.pos]) < 127 and self.text[self.pos] != '\\', 'SOURCE_STRING')
                self.pos += 1
            require(self.pos < len(self.text), 'SOURCE_STRING'); value = self.text[start:self.pos]; self.pos += 1
            return value
        require(c not in '#).`|\\,', 'SOURCE_READER_SYNTAX')
        start = self.pos-1
        while self.pos < len(self.text) and not self.text[self.pos].isspace() and self.text[self.pos] not in '();': self.pos += 1
        name = self.text[start:self.pos].upper()
        require(re.fullmatch(r'[A-Z0-9*+_-]+', name) is not None, 'SOURCE_SYMBOL')
        # These names in this file are inherited Common Lisp exports. All
        # other allowed tokens name private CCL module entries.
        inherited = ('IN-PACKAGE', 'DEFPARAMETER', 'DESCRIBE', 'APROPOS',
                     'DEFSTRUCT', 'METHOD-COMBINATION', 'READ', 'SORT', 'SETF',
                     'FORMAT', 'PPRINT', 'TIME', 'LOOP')
        return symbol(('COMMON-LISP::' if name in inherited else 'CCL::')+name)

    def decode(self):
        forms = []
        while True:
            self.whitespace()
            if self.pos == len(self.text): return forms
            start = self.pos; forms.append(self.expr()); self.spans.append([start, self.pos])


def modules(value):
    rows = []
    for item in elements(value):
        row = elements(item)
        require(len(row) == 3 and isinstance(row[0], dict) and set(row[0]) == {'symbol'} and isinstance(row[1], str), 'MODULE_SHAPE')
        rows.append(dict(name=row[0]['symbol'], binary=row[1], sources=elements(row[2])))
    return rows


def compare_systems(before, after, source_before, source_after):
    decoders = [DataFasl(b) for b in (before, after)]
    forms = [d.decode() for d in decoders]
    source = [LiteralSource(s.decode('ascii')) for s in (source_before, source_after)]
    literals = [r.decode() for r in source]
    for f, literal, reader in zip(forms, literals, source):
        require(len(literal) == 2 and literal[0] == conslist(symbol('COMMON-LISP::IN-PACKAGE'), 'CCL'), 'SOURCE_TOPLEVEL')
        definition = elements(literal[1]); require(len(definition) == 3 and definition[:2] == [symbol('COMMON-LISP::DEFPARAMETER'), symbol('CCL::*CCL-SYSTEM*')], 'SOURCE_DEFINITION')
        quoted = elements(definition[2]); require(len(quoted) == 2 and quoted[0] == symbol('COMMON-LISP::QUOTE'), 'SOURCE_QUOTE')
        require(len(f) == 6 and [list(x) for x in f] == [['platform'], ['source'], ['location'], ['call'], ['location'], ['defparameter']], 'FASL_TOPLEVEL')
        require(f[0] == {'platform': 83} and f[1] == {'source': 'ccl:lib;systems.lisp.newest'}, 'FASL_TARGET_SOURCE')
        require(f[5]['defparameter'] == [definition[1], quoted[1], None], 'FASL_SOURCE_DATA_JOIN')
        require(f[4]['location']['vector']['values'][-1] == {'cons': reader.spans[1]}, 'FASL_SOURCE_SPAN_JOIN')
    require(forms[0][:4] == forms[1][:4], 'FASL_EXECUTABLE_OR_METADATA_CHANGED')
    expected_location = copy.deepcopy(forms[0][4])
    expected_location['location']['vector']['values'][-1] = {'cons': source[1].spans[1]}
    require(forms[1][4] == expected_location, 'FASL_LOCATION_METADATA')
    rows = [elements(f[5]['defparameter'][1]) for f in forms]
    expected_additions = [conslist(symbol('CCL::WASM-CENSUS-'+suffix.upper()), 'ccl:bin;wasm-census-'+suffix,
                          conslist('ccl:compiler;WASM-CENSUS;census-'+suffix+'.lisp')) for suffix in ('arch', 'backend')]
    old = rows[0]
    at = next(i for i, row in enumerate(old) if elements(row)[0] == symbol('CCL::BACKEND'))+1
    require(rows[1] == old[:at]+expected_additions+old[at:], 'MODULE_ADDITION_BOUND')
    # Byte-level component accounting, not normalization: remove the two newly
    # decoded row spans and replace ONLY the list count, source-span record and
    # file-length field with their original bytes. Every remaining byte must
    # equal the baseline, including executable bytes, refs, opcodes and padding.
    spans = [d.spans for d in decoders]
    start = spans[1][id(rows[1][at])][0]; end = spans[1][id(rows[1][at+1])][1]
    locations = [spans[i][id(forms[i][4])] for i in range(2)]
    lists = [spans[i][id(forms[i][5]['defparameter'][1])][0] for i in range(2)]
    first = [spans[i][id(rows[i][0])][0] for i in range(2)]
    require(before[lists[0]] == after[lists[1]] == 44, 'FASL_MODULE_LIST_OPCODE')
    edits = [(8, 12, before[8:12], 'file length'),
             (*locations[1], before[slice(*locations[0])], 'source form span'),
             (lists[1], first[1], before[lists[0]:first[0]], 'module list count'),
             (start, end, b'', 'two literal module entries')]
    reconstructed = after
    for a, b, replacement, _ in sorted(edits, reverse=True): reconstructed = reconstructed[:a]+replacement+reconstructed[b:]
    require(reconstructed == before, 'FASL_UNEXPLAINED_BYTES')
    return dict(before_bytes=len(before), after_bytes=len(after), executable_bytes=64,
        executable_sha256=digest(bytes.fromhex(forms[0][3]['call']['function']['code'])),
        modules_before=len(old), modules_after=len(rows[1]), module_additions=modules(conslist(*expected_additions)),
        byte_components=[dict(start=a,end=b,component=label) for a,b,_,label in edits],
        source_spans=[r.spans for r in source], complete_decode=True, normalization_used=False), [modules(f[5]['defparameter'][1]) for f in forms]


def assess(case, profile):
    """Compare the actual patch and native run; raise the first precise refusal.

    Caller must bind inputs to profile['inputs'] before calling. Controls alter
    copies AFTER that binding to test the comparison, not just digest checking.
    """
    run = case['run']; source = case['source']; manifests = case['fasls']
    require(run['source_revision'] == U1 and run['test_revision'] == profile['test_revision'], 'INPUT_REVISIONS')
    require(run['inputs'] == profile['native_inputs'], 'INPUT_TOOLCHAIN_IMAGE')
    require(case['commands'] == profile['commands'], 'INPUT_OPTIONS_ENVIRONMENT')
    require(run['normalizations'] == [] and case['normalizations'] == [], 'UNAPPROVED_NORMALIZATION')
    expected_before = profile['source_manifest']
    require(source['before'] == expected_before, 'SOURCE_NOT_U1')
    changed = profile['modified']; added = profile['added']
    target = [n for n in expected_before if n.startswith(('compiler/X86/', 'compiler/PPC/', 'compiler/ARM/', 'level-0/X86/', 'level-0/PPC/', 'level-0/ARM/', 'lisp-kernel/'))]
    require(all(source['after'].get(n) == expected_before[n] for n in target), 'TARGET_SOURCE_EDIT')
    expected_after = dict(expected_before)
    expected_after.update({r['path']:r['after_sha256'] for r in changed})
    expected_after.update({r['path']:r['sha256'] for r in added})
    require(source['after'] == expected_after, 'SHARED_SOURCE_BOUND')
    require(source['restored'] == expected_before and case['restoration']['active'] is False, 'SOURCE_REVERSAL')
    for label in ('before', 'after'):
        require(digest(case['systems_source'][label]) == source[label]['lib/systems.lisp'], 'SOURCE_BYTE_JOIN')
    require(set(manifests) == {'baseline','registered','restored'} and len(manifests['baseline']) == 164 and
            manifests['registered'].keys() == manifests['baseline'].keys(), 'FASL_INVENTORY')
    require(manifests['restored'] == manifests['baseline'], 'FASL_REVERSAL')
    changed_fasls = [n for n in manifests['baseline'] if manifests['baseline'][n] != manifests['registered'][n]]
    require(changed_fasls == ['bin/systems.dx64fsl'], 'UNCHANGED_INPUT_FASL_CHANGED')
    require(case['intentional_artifacts'] == ['bin/systems.dx64fsl'], 'INTENTIONAL_ALLOWLIST')
    for label, key in [('baseline','before'), ('registered','after')]:
        require(digest(case['systems_fasl'][key]) == manifests[label]['bin/systems.dx64fsl'], 'FASL_BYTE_JOIN')
    comparison, decoded_modules = compare_systems(case['systems_fasl']['before'],case['systems_fasl']['after'],case['systems_source']['before'],case['systems_source']['after'])
    a,b = case['snapshots']['baseline'],case['snapshots']['registered']
    require(a['snapshot']['operators'] == b['snapshot']['operators'], 'R6A_OPERATOR_RECORDS')
    require(len(a['snapshot']['operators']) == 279 and sum(o['name'] is None for o in a['snapshot']['operators']) == 12, 'R6A_OPERATOR_BOUND')
    require(a['snapshot'] == b['snapshot'], 'R6A_ABI_FEATURE_SNAPSHOT')
    require([a['modules'],b['modules']] == decoded_modules, 'EVALUATED_MODULE_JOIN')
    require(case['probes']['baseline'] == case['probes']['registered'], 'NATIVE_PROBE_EXECUTABLE')
    require(run['execution_status'] == 'PASS' and run['all_archived_sources_restored'] and run['restored_fasls_equal'] == 164, 'NATIVE_EXECUTION')
    for label in ('baseline','registered'):
        t=case['tests'][label]
        require(t == run[label+'_tests'] and t == dict(registered=21918,eligible=21843,upstream_disabled=75,passed=21843,failed=0,missing=0,unexpected=0,success=True), 'NATIVE_TESTS')
    require(case['test_files']['baseline'] == case['test_files']['registered'], 'NATIVE_TEST_MEMBERSHIP')
    return dict(status='PASS', categories=dict(target_source=dict(files=len(target),unchanged=True),
        unchanged_inputs=dict(native_fasls=164,byte_identical=163),intentional_shared_artifact=comparison,
        existing_target=dict(native_tests_per_run=21843,disabled_upstream=75,operator_slots=279,reserved_slots=12,
          evaluated_records_equal=True,compiled_abi_probe_equal=True,unchanged_kernel=True)),
        source_files=len(expected_before),restored_fasls=164,restored_sources=True,
        native_execution='Reused accepted 2026-09-12 census-stub run; no new native build or tests',
        scope='U1 census registration patch only; no general FASL normalizer or Wasm implementation qualification')
