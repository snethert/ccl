#!/usr/bin/env python3
"""Omission, substitution and insertion controls over a genuine boot capture."""
import argparse
import copy
import json
from pathlib import Path
from analyze import analyze, bind_files, read


def controls(rows):
    analyze(rows); outcomes = []
    def event(rs, kind): return next(r for r in rs if r['kind'] == kind)
    def repair_counts(rs):
        es = [r for r in rs if 'sequence' in r]
        for i, r in enumerate(es, 1): r['sequence'] = i
        rs[0]['events'] = rs[-1]['events'] = len(es)
    def check(name, mutation, reason, repair=False):
        rs = copy.deepcopy(rows); mutation(rs)
        if repair: repair_counts(rs)
        try: analyze(rs)
        except ValueError as exc:
            if str(exc) != reason: raise ValueError(name + ': wrong oracle: ' + str(exc))
            outcomes.append({'name': name, 'status': 'REJECTED', 'reason': reason})
        else: raise ValueError('control escaped: ' + name)
    check('truncated-stream', lambda rs: rs.pop(), 'STREAM_COMPLETION')
    check('foreign-thread', lambda rs: rs[0].update(foreign_thread_observed=True), 'OWNER_THREAD_SCOPE')
    check('missing-event', lambda rs: rs.remove(event(rs, 'cold-return')), 'EVENT_COUNTS')
    check('missing-cold-return-with-recount', lambda rs: rs.remove(event(rs, 'cold-return')), 'COLD_QUEUE_ORDER', True)
    def cold_pair(rs):
        i = event(rs, 'cold-enter')['payload']['function']
        rs[:] = [r for r in rs if not (r['kind'] in ('cold-enter', 'cold-return') and r['payload']['function'] == i)]
        event(rs, 'boot-start')['payload']['queued'].remove(i)
    check('missing-cold-pair-and-edited-event-queue', cold_pair, 'ORIGINAL_COLD_QUEUE', True)
    check('changed-cold-identity', lambda rs: event(rs, 'cold-enter')['payload'].update(function=rs[0]['original_cold_queue'][1]), 'COLD_QUEUE_ORDER')
    check('missing-call-return-with-recount', lambda rs: rs.remove(event(rs, 'call-return')), 'RETURN_NESTING', True)
    check('wrong-return-identity', lambda rs: event(rs, 'call-return')['payload'].update(function=rs[0]['original_cold_queue'][0]), 'RETURN_IDENTITY')
    check('empty-return-payload', lambda rs: event(rs, 'call-return').update(payload={}), 'EVENT_FIELDS')
    check('reader-wrong-load', lambda rs: event(rs, 'reader-enter')['payload'].update(file='invented.dx64fsl'), 'READER_LOAD_CONTEXT')
    check('reader-wrong-table', lambda rs: event(rs, 'reader-enter')['payload'].update(table=rs[-1]['identities']), 'READER_LOAD_CONTEXT')
    check('invalid-reader-offset', lambda rs: event(rs, 'reader-enter')['payload'].update(offset=-1), 'READER_OPERAND')
    check('missing-installation-with-recount', lambda rs: rs.remove(event(rs, 'binding-installed')), 'BINDING_CHAIN', True)
    check('removal-to-function', lambda rs: event(rs, 'binding-removing')['payload'].update(new=rs[0]['original_cold_queue'][0]), 'REMOVAL_TARGET')
    check('missing-final-binding', lambda rs: event(rs, 'final-bindings')['bindings'].pop(), 'FINAL_BINDING_STATE')
    check('changed-final-binding', lambda rs: event(rs, 'final-bindings')['bindings'][0].update(value=rs[0]['original_cold_queue'][0]), 'FINAL_BINDING_STATE')
    check('duplicate-final-binding', lambda rs: event(rs, 'final-bindings')['bindings'].append(copy.deepcopy(event(rs, 'final-bindings')['bindings'][0])), 'FINAL_BINDING_STATE')
    def add_node(rs): rs.insert(-1, copy.deepcopy(event(rs, 'object')))
    check('duplicate-object', add_node, 'OBJECT_IDENTITIES')
    check('surplus-section', lambda rs: rs.insert(-1, {'version': 1, 'kind': 'invented'}), 'SURPLUS_STREAM_RECORD')
    def extra_event(rs): rs.insert(2, copy.deepcopy(event(rs, 'boot-start')))
    check('inserted-boot-start', extra_event, 'DUPLICATE_BOOT_START', True)
    check('unknown-event', lambda rs: event(rs, 'cold-enter').update(kind='invented'), 'EVENT_FIELDS')
    check('surplus-event-field', lambda rs: event(rs, 'cold-enter').update(implemented=True), 'EVENT_FIELDS')
    return outcomes


def file_controls(rows, source, overrides, recorded_root=None):
    result = analyze(rows); genuine = bind_files(result, source, overrides, recorded_root); outcomes = []
    for name, offset, expected in [('different-byte', 1, 'FASL_OPCODE_IDENTITY'), ('past-file-end', 10**9, 'FASL_OPCODE_IDENTITY')]:
        mutant = copy.deepcopy(result); mutant['readers'][0]['offset'] = offset
        try: bind_files(mutant, source, overrides, recorded_root)
        except ValueError as exc:
            if str(exc) != expected: raise
            outcomes.append({'name': name, 'status': 'REJECTED', 'reason': str(exc)})
        else: raise ValueError('file control escaped: ' + name)
    mutant = copy.deepcopy(result); mutant['loads'][0]['file'] = '../outside.dx64fsl'
    try: bind_files(mutant, source, overrides, recorded_root)
    except ValueError as exc:
        if str(exc) != 'LOAD_OUTSIDE_ARCHIVE': raise
        outcomes.append({'name': 'file-outside-archive', 'status': 'REJECTED', 'reason': str(exc)})
    else: raise ValueError('file scope control escaped')
    return genuine, outcomes


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('events', 'source', 'changed-fasls', 'output'): p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args(); rows = read(a.events)
    overrides = {str(p.relative_to(a.changed_fasls)): p for p in a.changed_fasls.rglob('*.dx64fsl')}
    outcomes = controls(rows); files, more = file_controls(rows, a.source, overrides); outcomes += more
    result = {'status': 'PASS', 'positive_cases': 2, 'controls_rejected': len(outcomes), 'outcomes': outcomes,
              'files_checked': len(files['files']), 'opcode_witnesses': files['opcode_witnesses']}
    a.output.write_text(json.dumps(result, indent=2) + '\n'); print(json.dumps({k: v for k, v in result.items() if k != 'outcomes'}))
