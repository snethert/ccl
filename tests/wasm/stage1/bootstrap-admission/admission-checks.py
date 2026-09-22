"""Separate actual execution, named refusals and excluded native subsystems."""
import collections
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EVIDENCE = ROOT.parent / 'ccl-evidence'


def check(out):
    read = lambda p: json.loads(p.read_text())
    save = lambda name, data: (out / name).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')
    before = read(EVIDENCE / '2026-09-21-stage1-bootstrap-host-r1/execution/compiled/worklist-throughput.json')
    after = read(out / 'compiled/worklist-throughput.json')
    current = {(r['file'], r['name']): r for r in after['functions']}
    crashes = [r for r in before['functions'] if r['outcome'] == 'TYPE-ERROR']
    assert len(crashes) == 17
    fixed = []
    for old in crashes:
        new = current[(old['file'], old['name'])]
        assert new['outcome'] == 'NATIVE-FFI-EXCLUDED', new
        fixed.append(dict(file=old['file'], name=old['name'], before=old['message'], after=new['outcome']))
    assert not any(r['outcome'] == 'TYPE-ERROR' for r in after['functions'])
    controls = (out / 'compiled/measure-controls.sexp').read_text()
    for name, reason in [('NATIVE-FFI', 'NATIVE-FFI-EXCLUDED'),
                         ('FUNCTION-IMMEDIATE-READ', 'FUNCTION-IMMEDIATE-LAYOUT'),
                         ('FUNCTION-IMMEDIATE-WRITE', 'FUNCTION-IMMEDIATE-LAYOUT')]:
        assert f'(:{name} :{reason})' in controls, (name, reason)
    visits = read(out / 'compiled/executed-operators.json')
    operators = ['GLOBAL-SETQ', 'LIST*', 'VECTOR', '%MAKE-UVECTOR', 'MAKE-LIST',
                 'NTH-VALUE', 'LOGBITP', '%ILSL', '%ILSR', '%IASR', 'UVREF', 'UVSET', '%TYPED-UVREF', '%TYPED-UVSET']
    witnesses = {op: sorted(r['name'] for r in visits if any(k == op for k, n in r['operators'])) for op in operators}
    assert all(witnesses.values()), witnesses
    native = read(out / 'compiled/native.json')
    names = {r['definition'] for r in native}
    for name in ('CORE-AUX', 'CORE-LEXPR', 'CORE-LEXPR-ZERO', 'CORE-GLOBAL-CELL',
                 'CORE-RETRY-VECTOR', 'CORE-RETRY-LIST'):
        assert name in names, name
    rows = read(out / 'execution.json')['rows']
    assert all(r['retryCollections'] > 0 for r in rows)
    save('admission.json', dict(status='PASS', previous_compiler_crashes=fixed,
        current_host_errors=dict(collections.Counter(r['outcome'] for r in after['functions'] if r['message'])),
        emitted_and_executed=witnesses, allocation_retry_collections=sum(r['retryCollections'] for r in rows),
        source_argument_conventions=['sequential AUX', 'rooted reversed LEXPR frame; native primary-value convention'],
        named_layout_refusal='NTH-IMMEDIATE/SET-NTH-IMMEDIATE: native code/immediates are not D1 callable metadata.',
        unexecuted_new_dispatch=['%AREF1/ASET1', 'REALPART/IMAGPART/COMPLEX', '%SLOT-UNBOUND-MARKER'],
        scope='Operator witnesses are source-emitted and executed, not branch coverage. Unexecuted dispatch only creates ordinary Lisp dependencies. Native FFI is excluded, never emulated by an empty stub.'))
    from sources import files, plan, EXCLUDED_CONSTANTS, CONSTANTS
    excluded = [dict(file=file, **row) for file in files() for row in plan(ROOT, file)[1]]
    arch = (out / 'compiled/proposal/files/compiler/WASM32/wasm32-arch.lisp').read_text()
    from foreign import target_name
    assert all('(defconstant ' + target_name(n) + ' ' not in arch for n in EXCLUDED_CONSTANTS)
    assert len(CONSTANTS) == 31
    decisions = {
        'native processes, credentials, signals, terminals, sockets, mappings and dynamic libraries':
            'Exclude their native calling definitions. No provider obligation or target constant is created.',
        'F_GETFL/F_SETFL, POLLIN/POLLOUT':
            'Exclude fd flag and poll consumers. A future file provider must define its own nonblocking readiness contract.',
        '_PC_MAX_INPUT/_PC_PIPE_BUF':
            'Exclude native pipe-size acquisition. Browser streams do not expose these POSIX limits.',
        '_SC_CLK_TCK/_SC_PAGESIZE':
            'Exclude native sysconf callers. Memory owners and clocks supply their own units, not libc constants.',
        'CPU-COUNT':
            'Exclude native host_info/sysctl/sysconf definition; target prototype retains OR/SETQ cache semantics and tests compiled cold/warm callers.',
        'scheduler and capability authority':
            'Only protocol routing is executed. Production must use owner-sealed capabilities; the fixture special alist is not authority. Browser main-thread blocking waits are not admitted.',
    }
    save('foreign-boundaries.json', dict(status='PASS', constants_removed=sorted(EXCLUDED_CONSTANTS),
        retained_constant_identifiers=len(CONSTANTS), excluded_definitions=excluded, decisions=decisions,
        module_list='Both original lists retained, including linux-files.',
        scope='Missing references to excluded entries remain open dependencies. This proposal does not claim a complete target OS replacement or a READY image.'))


if __name__ == '__main__':
    check(Path(sys.argv[1]).resolve())
