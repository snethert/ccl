"""Check the changed Lisp dependency, admission cases and signed-zero boundary."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def check(out):
    read = lambda name: json.loads((out / name).read_text())
    whole = read('compiled/whole-file.json')
    assq, = [r for r in whole if r['name'] == 'ASSQ']
    assert assq['status'] == 'ADMITTED' and not assq['dependencies']
    source = (out / 'compiled/proposal/files/level-0/WASM32/w32-prims.lisp').read_text()
    assert source == (ROOT / 'level-0/WASM32/w32-prims.lisp').read_text()
    backend = (out / 'compiled/proposal/files/compiler/WASM32/wasm32-backend.lisp').read_text()
    assert 'bootstrap-assq' not in backend
    native = read('compiled/native.json')
    assert len([r for r in native if r['definition'] == 'ASSQ']) >= 5
    assert len([r for r in native if r['definition'] == 'CORE-ASSQ-IDENTITY']) == 5
    added = ['CHEAP-CONS','CHEAP-COPY-LIST','CHEAP-FREE-LIST','CHEAP-LIST','FREE-CONS',
             'CLEAR-LOCK-ACQUISITION-STATUS','CLEAR-SEMAPHORE-NOTIFICATION-STATUS',
             'LOCK-ACQUISITION-STATUS','SEMAPHORE-NOTIFICATION-STATUS',
             'COERCE-TO-VALUES','MAKE-INTERSECTION-CTYPE','NUMERIC-TYPES-ADJACENT',
             'EVENT-TICKS','FIND-NAMED-PERIODIC-TASK','SET-EVENT-TICKS',
             'INSTALL-IOBLOCK-INPUT-LINE-TERMINATION','INSTALL-IOBLOCK-OUTPUT-LINE-TERMINATION',
             'IOBLOCK-ELEMENTS-TO-OCTETS','IOBLOCK-OCTETS-TO-ELEMENTS',
             'OBJECT-IN-APPLICATION-HEAP-P','UCS-4-STREAM-DECODE','USING-LINEAR-SCAN',
             'RECURSIVE-LOCK-PTR','READ-WRITE-LOCK-PTR','%IOBLOCK-UNTYI','IOBLOCK-INPOS','IOBLOCK-OUTPOS',
             'STRING-INPUT-STREAM-IOBLOCK-READ-CHAR','STRING-INPUT-STREAM-IOBLOCK-PEEK-CHAR',
             'STRING-INPUT-STREAM-IOBLOCK-UNREAD-CHAR','%EPUSHVAL']
    assert all(any(r['definition'] == name for r in native) for name in added)
    assert len(added) == 31
    assert (out / 'compiled/io-constants.sexp').read_text().strip() == '(0 1 4 17 23 24)'
    prior = ROOT.parent/'ccl-evidence/2026-09-21-stage1-bootstrap-carry-r1/execution/compiled/native.json'
    from collections import Counter
    counts = Counter(r['definition'] for r in native)
    old_counts = Counter(r['definition'] for r in json.loads(prior.read_text()))
    assert all(counts[name] >= count for name, count in old_counts.items())
    (out/'inputs.json').write_text(json.dumps(dict(status='PASS',new_definitions=added,
        original_native_rows_retained=sum(old_counts.values()),
        input_scope='Lock pointer slots use tagged sentinels, never OS pointers. I/O structures are in-memory data, not live descriptors. Pinned structure/pool fields are registered roots; conses and generated allocations move.',
        constants=[0,1,4,17,23,24],
        constants_scope='Declared Wasm file-provider protocol, not native errno acquisition. Providers must translate host errors. No provider implemented here.'),indent=2,sort_keys=True)+'\n')
    # Callers must link to the real definition rather than silently inline a
    # second implementation. The target source is not an unchanged native DEFUN.
    deps = (out / 'compiled/dependencies.sexp').read_text()
    assert '(CCL::REGISTER-ISTRUCT-CELL (CCL:ASSQ))' in deps
    controls = (out / 'compiled/measure-controls.sexp').read_text()
    for name in ('UNKNOWN-HANDLER-BIND', 'UNKNOWN-HANDLER-CASE',
                 'MACRO-INTRODUCED-HANDLER', 'COMPOUND-HANDLER-TYPE'):
        assert f'(:{name} :B-CONDITION-TYPE)' in controls
    for name in ('SIGNAL-SPREAD', 'ERROR-SPREAD'):
        assert f'(:{name} :BOOTSTRAP-SIGNAL-SPREAD)' in controls
    assert '(:HANDLER-GUARD-OMISSION :ADMITTED)' in controls
    execution = read('execution.json')['rows']
    signed = [dict(base=r['base'], **s) for r in execution for s in r['signedZero']]
    assert len(signed) == 32
    different = [s for s in signed if s['native'] != s['target']]
    assert len(different) == 4
    assert all(s['definition'] == 'CORE-SIGNED-ZERO-LITERAL' and
               s['args'] == [{'double': [0x80000000, 0]}] and
               s['native'] == [{'double': [0, 0]}] and
               s['target'] == [{'double': [0x80000000, 0]}] for s in different)

    # Mutate only the generated Lisp ASSQ's EQ, then run its ordinary caller
    # against the same native cases. No changes to the caller or runtime.
    module = out / 'compiled' / assq['module']
    wat = module.with_suffix('.wat').read_text()
    prefix, body = wat.split('(func $body ', 1)
    pattern = r'\(i32.eq (\(i32.load offset=8 \(local.get (\$tmp\d+)\)\)) (\(i32.load offset=12 \(local.get \2\)\))\)'
    body, n = re.subn(pattern, r'(i32.ne \1 \3)', body)
    assert n == 1, n
    faults = out / 'carry-faults'
    faults.mkdir()
    mutant = faults / 'assq-match-sense.wat'
    mutant.write_text(prefix + '(func $body ' + body)
    subprocess.run(['/usr/local/bin/wat2wasm', '--enable-threads', '--enable-exceptions',
                    '--enable-tail-call', mutant, '-o', mutant.with_suffix('.wasm')], check=True)
    binary = module.with_suffix('.wasm')
    original = binary.read_bytes()
    try:
        binary.write_bytes(mutant.with_suffix('.wasm').read_bytes())
        with (faults / 'assq-match-sense.log').open('w') as log:
            p = subprocess.run(['/usr/local/bin/node', out / 'check.mjs', out, faults / 'unused.json'],
                               env=dict(os.environ, CCL_LIBRARY_CASE='CORE-ASSQ'),
                               stdout=log, stderr=log, timeout=60)
        text = (faults / 'assq-match-sense.log').read_text()
        assert p.returncode != 0 and 'CORE-ASSQ' in text and 'AssertionError' in text
    finally:
        binary.write_bytes(original)
    accepted = ROOT.parent / 'ccl-evidence/2026-09-21-stage1-bootstrap-witnesses-accepted'
    inherited = json.loads((accepted / 'execution/owner-check/results.json').read_text())
    assert inherited['status'] == 'PASS' and inherited['checks'] == 40
    for name in ('collector.c', 'collector-owner.mjs'):
        assert (out / 'runtime' / name).read_bytes() == (accepted / 'integrated/runtime/wasm32' / name).read_bytes()
    integrated = json.loads((accepted / 'execution/integration.json').read_text())
    assert hashlib.sha256((out / 'collector.wasm').read_bytes()).hexdigest() == integrated['collector_sha256']
    result = dict(status='PASS', lisp_assq=assq, handler_refusals=4, spread_refusals=2,
                  handler_guard_omission_admitted=True, assq_wrong_sense_rejected=True,
                  signed_zero=signed, signed_zero_differences=len(different),
                  signed_zero_scope='Native literal-zero optimization differs; variable zero agrees. Preserve target IEEE subtraction. No claim of bitwise native equality for the four disclosed rows.',
                  collector_checks=dict(reused=40, integration='b9de543d',
                                        record='2026-09-21-stage1-bootstrap-witnesses-accepted/execution/owner-check/results.json'))
    (out / 'carry.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve())
