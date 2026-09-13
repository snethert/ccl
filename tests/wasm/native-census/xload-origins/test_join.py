"""Controls derived from genuine xload and boot observations."""
import copy
from join import join


def controls(origins, boot, source, fasls, overrides):
    outcomes = []
    def check(name, mutation, reason):
        o, b = copy.deepcopy(origins), copy.deepcopy(boot); mutation(o,b)
        try: join(o,b,source,fasls,overrides)
        except ValueError as e:
            if str(e) != reason: raise ValueError(name + ': ' + str(e))
            outcomes.append({'name': name, 'status': 'REJECTED', 'reason': reason})
        else: raise ValueError('control escaped: ' + name)
    check('omit-insertion', lambda o,b:o['entries'].pop(), 'QUEUE_COUNT')
    check('insert-extra-insertion', lambda o,b:o['entries'].append(copy.deepcopy(o['entries'][0])), 'QUEUE_COUNT')
    check('change-position', lambda o,b:o['entries'][0].update(position=2), 'QUEUE_POSITION')
    check('change-saved-queue', lambda o,b:o['image_queue'].reverse(), 'SAVED_QUEUE_ORDER')
    check('change-host-queue', lambda o,b:o['host_queue'].reverse(), 'SAVED_QUEUE_ORDER')
    check('change-target-identity', lambda o,b:o['entries'][0].update(target_function=o['entries'][1]['target_function']), 'SAVED_QUEUE_ORDER')
    check('change-boot-order', lambda o,b:b[0]['original_cold_queue'].reverse(), 'BOOT_QUEUE_EXECUTION')
    check('omit-loader-input', lambda o,b:o['paths'].pop(), 'ENTRY_MODULE')
    check('reverse-loader-order', lambda o,b:o['paths'].reverse(), 'XLOAD_LOAD_ORDER')
    check('outside-loader-root', lambda o,b:o['entries'][0].update(file='/outside.dx64fsl'), 'PATH_SCOPE')
    check('wrong-opcode-offset', lambda o,b:o['entries'][0].update(opcode_offset=1), 'INITIALIZER_OPCODE')
    check('wrong-source-module', lambda o,b:o['entries'][0].update(source_file=o['entries'][1]['source_file']), 'SOURCE_MODULE_JOIN')
    check('wrong-note-file', lambda o,b:o['entries'][0]['location'].update(filename='ccl:wrong.lisp.newest'), 'SOURCE_NOTE_FILE')
    check('wrong-note-layout', lambda o,b:o['entries'][0]['location'].update(header=0), 'SOURCE_NOTE_LAYOUT')
    check('omitted-source-context', lambda o,b:o['entries'][0].update(location=None), 'SOURCE_LOCATION_PRESENCE')
    check('substituted-source-note', lambda o,b:o['entries'][0]['location'].update(address=0), 'SOURCE_NOTE_ADDRESS')
    check('wrong-source-range', lambda o,b:o['entries'][0]['location'].update(start=0), 'RANGE_DECODE')
    check('wrong-range-tag', lambda o,b:o['entries'][0]['location']['range_words'].__setitem__(0,1), 'RANGE_TAGS')
    check('surplus-entry-field', lambda o,b:o['entries'][0].update(implemented=True), 'ENTRY_FIELDS')
    check('surplus-root-field', lambda o,b:o.update(accepted=True), 'ORIGIN_SCHEMA')
    return {'status':'PASS','controls_rejected':len(outcomes),'outcomes':outcomes}
