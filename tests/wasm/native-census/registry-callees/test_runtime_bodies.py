"""Exercise assembly and generic-entry joins against retained native objects."""
from copy import deepcopy
from pathlib import Path
from payloads import read, save, require
from runtime_bodies import join


def run(a):
    fs = {r['id']: r for r in read(a.bodies / 'functions.json.gz')}
    definitions = read(a.bodies / 'assembly.json.gz')
    states = {r['gf']: r for r in read(a.bodies / 'checkpoints.json.gz')[0]['entries']}
    runtime = read(a.bodies / 'runtime-inputs.json')[0]
    retained = read(a.walk / 'runtime-bodies.json.gz')
    requested = [r['function'] for r in retained]
    got, missing = join(fs, definitions, states, runtime, requested)
    require(got == retained and not missing, 'RUNTIME_BODY_REPLAY')
    assembly = next(r['function'] for r in retained if r['kind'] == 'ASSEMBLED_BODY')
    generic = next(r['function'] for r in retained if r['kind'] == 'GENERIC_FUNCTION_ENTRY')
    controls = []

    def refuses(name, ident, functions=fs, defs=definitions, registries=states, reason=None):
        accepted, open_ = join(functions, defs, registries, runtime, [ident])
        require(not accepted and len(open_) == 1 and open_[0]['function'] == ident,
                'RUNTIME_MUTANT_ESCAPED ' + name)
        require(reason is None or open_[0]['reason'] == reason, 'RUNTIME_MUTANT_REASON ' + name)
        controls.append(dict(name=name, status='REJECTED', reason=open_[0]['reason']))

    for kind, ident in [('assembly', assembly), ('generic', generic)]:
        bad = dict(fs); bad[ident] = deepcopy(fs[ident])
        raw = bytearray.fromhex(bad[ident]['payload_hex']); raw[5] ^= 1
        bad[ident]['payload_hex'] = raw.hex()
        refuses(kind + '-instruction', ident, functions=bad)
    bad = dict(fs); bad[assembly] = deepcopy(fs[assembly]); bad[assembly]['bits'] ^= 1
    refuses('assembly-arity', assembly, functions=bad, reason='no-matching-assembly-definition')
    name = fs[assembly]['literals'][-1]['symbol']
    bad = deepcopy(definitions)
    for row in bad:
        if row['name'] and row['name'].get('id') == name: row['name']['id'] = -1
    refuses('same-printed-name-other-symbol', assembly, defs=bad, reason='no-matching-assembly-definition')
    bad = [r for r in definitions if not (r['name'] and r['name'].get('id') == name)]
    refuses('missing-assembler-definition', assembly, defs=bad, reason='no-matching-assembly-definition')
    for index, label, field in [(0, 'wrapper', 'object'), (2, 'table', 'object'), (3, 'dcode', 'function')]:
        bad = dict(fs); bad[generic] = deepcopy(fs[generic]); bad[generic]['literals'][index][field] = -1
        refuses('generic-' + label, generic, functions=bad, reason='dispatch-literal-layout')
    bad = dict(states); del bad[generic]
    refuses('missing-generic-registry', generic, registries=bad)
    save(a.output, dict(status='PASS', native_bodies=len(got), controls=controls))
    print('PASS', len(got), 'native bodies,', len(controls), 'corruption controls', flush=True)


if __name__ == '__main__':
    import argparse, traceback
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('bodies', 'walk', 'output'): p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    try: run(a)
    except BaseException:
        a.output.with_suffix('.failure.txt').write_text(traceback.format_exc())
        a.output.with_suffix('.failed-source.py').write_bytes(Path(__file__).read_bytes())
        raise
