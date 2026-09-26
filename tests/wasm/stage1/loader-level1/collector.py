"""Current collector: inherited admission controls plus weak-pair mutations."""
from pathlib import Path
import sys
import product
import storage

MUTANTS = [
    ('WEAK-FIXPOINT', 'if(s->live!=before){progress=1;drain(s);}',
     'if(s->live!=before){drain(s);}', 'weak-chain-reverse'),
    ('WEAK-UNCONDITIONAL', 'if(s->error||(wi?vd:kd))continue;',
     'if(s->error)continue;', 'weak-key-unfrozen-reaped'),
    ('WEAK-COUNTS', 'STORE(h+36,LOAD(h+36)-4);\n   if(!(f&0x800))STORE(h+32,LOAD(h+32)+4);',
     '', 'weak-key-unfrozen-reaped'),
    ('WEAK-KEY-MARKER', 'STORE(h+4+4*k,83);',
     'STORE(h+4+4*k,NIL);', 'weak-key-unfrozen-reaped'),
    ('WEAK-VALUE', 'if(s->error||(wi?vd:kd))continue;',
     'if(s->error||kd)continue;', 'weak-value-unfrozen-retained'),
    ('WEAK-FROZEN', '(f&0x800)?83:NIL', 'NIL', 'weak-key-frozen-reaped'),
    ('WEAK-FINALIZEABLE', 'flags&~0x780c6800u', 'flags&~0x780c7800u', 'native-hash-finalizeable'),
]

if __name__ == '__main__':
    out = Path(sys.argv[1]).resolve()
    with storage.lease([out]):
        product.module('weak_collector', product.HERE.parent / 'loader-gc/collector.py').run(
            out, product, [product.HERE / 'weak-collector-cases.mjs'], MUTANTS)
