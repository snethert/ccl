"""One delta over the accepted division packet; replay from any checkout."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('numeric_packet', HERE.parent / 'bootstrap-numeric-dispatch/packet.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
parent.HERE = HERE
parent.PARENT = parent.EVIDENCE / '2026-09-22-stage1-bootstrap-limb-division-r1'
parent.ID = 'STAGE1-BOOTSTRAP-GCD-R1'


def pins():
    prior = parent.read(parent.PARENT / 'source-pins.json')
    accepted = parent.read(parent.ROOT / 'doc/WASM/stage1/integration-bootstrap-stack.json')
    for row in accepted['files']:
        assert parent.sha(parent.ROOT / row['file']) == row['after'], row['file']
    # Integration deliberately changed the prior packet's shared inputs. Pin
    # their current bytes; immutable earlier packets keep their original pins.
    result = {name: parent.sha(parent.ROOT / name) for name in prior}
    result.update({str(p.relative_to(parent.ROOT)): parent.sha(p) for p in parent.files(HERE)})
    for name in ('doc/WASM/stage1/integration-bootstrap-stack.json',
                 'level-1/l1-error-signal.lisp', 'level-1/l1-error-system.lisp'):
        result[name] = parent.sha(parent.ROOT / name)
    return result


parent.pins = pins
if __name__ == '__main__':
    parent.main()
