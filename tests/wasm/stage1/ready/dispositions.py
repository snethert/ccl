"""Join immutable native startup membership to the selected READY code graph."""
from pathlib import Path
import json
from closure import read, digest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

# Named effects for callbacks whose registration name is not their state cell.
# The original source locations and obligations remain in the retained input.
EFFECTS = {
    'KERNEL-LOCKS': ['*KERNEL-TCR-AREA-LOCK*', '*KERNEL-EXCEPTION-LOCK*'],
    'INITIAL-THREAD': ['*INITIAL-LISP-THREAD*'],
    'LISTENER-STACK-SIZES': ['*INITIAL-LISTENER-DEFAULT-CONTROL-STACK-SIZE*',
        '*INITIAL-LISTENER-DEFAULT-VALUE-STACK-SIZE*', '*INITIAL-LISTENER-DEFAULT-TEMP-STACK-SIZE*'],
    'INIT-LOGICAL-DIRECTORIES': ['INIT-LOGICAL-DIRECTORIES', 'REPLACE-BASE-TRANSLATION',
                                'COMMON-LISP::USER-HOMEDIR-PATHNAME', 'CCL-DIRECTORY'],
    'RESET-WINNERS': ['*STACK-ACCESS-WINNERS*'],
    'RESET-DB-FILES': ['RESET-DB-FILES', '*INTERFACE-DIRECTORIES*'],
    'STARTUP-SHUTDOWN-PROCESSES': ['STARTUP-SHUTDOWN-PROCESSES', 'POP-SHUTDOWN-PROCESSES'],
    'SPIN-COUNT': ['*CPU-COUNT*', '*SPIN-LOCK-TRIES*', '*SPIN-LOCK-TIMEOUTS*'],
}


def dispositions(closure):
    selection = HERE.parent / 'startup-resets/selection.json'
    old = HERE.parent / 'startup-runtime/classification.json'
    assert digest(selection) == '24492ad2324651a014c88edea986b3d812615fd478dd49f4765199216344a169'
    selected = read(selection)
    prior = {r['key']:r for r in read(old)['callbacks']}
    rows = []
    for callback in selected['callbacks']:
        key = callback['group'] + ':' + str(callback['ordinal'])
        name = callback['name'].split('::', 1)[1]
        effects = [n if '::' in n else 'CCL::' + n for n in EFFECTS.get(name, [name])]
        consumers = sorted({m['module'] for m in closure['modules']
                            if set(effects) & set(m['imported_symbols'])})
        # Absence from this walk is useful evidence, not a proof that an
        # unresolved callback or dynamically computed callee cannot use it.
        state = 'CONSUMER_OBLIGATION' if consumers else 'OUTSIDE_CURRENT_STATIC_GRAPH'
        rows.append(dict(key=key, name=callback['name'], snapshot_function=callback['function'],
                         source=callback['source'], position=callback['position'],
                         effects=effects, potential_consumers=consumers,
                         disposition=state, previous_obligation=prior[key]['obligation'],
                         discharged=False,
                         reason='Missing and indirect edges must be resolved before absence is an exclusion proof.'))
    assert len(rows) == 35 and len({r['key'] for r in rows}) == 35
    return dict(version=1, snapshot=selected['snapshot'],
                selection_sha256=digest(selection), prior_classification_sha256=digest(old),
                decision_sha256=digest(ROOT/'doc/WASM/stage1/ready-decision.json'),
                callbacks=rows, count=35, complete=False,
                scope='Disposition overlay only; historical selections are unchanged. No host input, '
                      'native lock, clock, interface database or scheduler service is invented to fill a row.')


if __name__ == '__main__':
    import sys
    Path(sys.argv[2]).write_text(json.dumps(dispositions(read(Path(sys.argv[1]))), indent=2) + '\n')
