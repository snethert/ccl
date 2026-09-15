#!/usr/bin/env python3
"""Kernel-import census (D6): one record per U1 defimport spelling with caller evidence and profile dispositions."""
import argparse, copy, hashlib, json, platform, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path
import inventory as D
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[3]; DOCS = ROOT / 'doc/WASM'
U1 = 'c994217adc56b3f8a564526cee4695893ac84d86'
ID = 'KERNEL-IMPORTS-R1'
SCOPE = ('Source-inspection census of the 65 U1 kernel imports: the C defimport table and the x8632 KERNEL-IMPORT enumeration joined by '
         'index, every Lisp caller site with its form and x8632 applicability, every C or assembly definition and C call-site count, and a '
         'closed disposition ledger giving each import its D6 group, a disposition per profile, closure phase, replacement and regression '
         'obligations. Emits census-shaped import nodes to replace the unresolved gap:imports placeholder. Control execution over pinned U1 '
         'sources; no Wasm executed, no gate credit; the evaluated compiler census (S0-LL15-b) resolves target conditionals and reachability.')
COMMITTED = DOCS / 'contracts/kernel-imports.v1.json'
IMPORTS_S = ROOT / 'lisp-kernel/imports.s'; ARCH = ROOT / 'compiler/X86/X8632/x8632-arch.lisp'
VOCABULARY = ('wasm-runtime', 'js-host-service', 'atomics-memory', 'unsupported')
PHASES = ('loader', 'definitions', 'runtime', 'none')
CENSUS_DISPOSITION = {'wasm-runtime': 'replaced', 'js-host-service': 'replaced', 'atomics-memory': 'replaced', 'unsupported': 'unsupported'}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def save(p, x): p.write_text(json.dumps(x, indent=2, ensure_ascii=False) + '\n')
def canonical(x): return json.dumps(x, indent=2, ensure_ascii=False) + '\n'
def require(x, reason):
    if not x: raise ValueError(reason)


def sources():
    return [HERE / n for n in ('run.py', 'inventory.py', 'dispositions.json')] + [HERE.parent / 'contracts/derive.py', IMPORTS_S, ARCH, COMMITTED, DOCS / 'contracts/census.schema.json']


def u1_pin(path):
    blob = subprocess.run(['git', '-C', str(ROOT), 'cat-file', '-p', U1 + ':' + path.relative_to(ROOT).as_posix()], capture_output=True, timeout=60)
    require(blob.returncode == 0, 'U1_BLOB ' + str(path))
    digest = hashlib.sha256(blob.stdout).hexdigest(); require(digest == sha(path), 'U1_PIN ' + path.relative_to(ROOT).as_posix()); return digest


def build(root, imports_text, arch_text, ledger):
    rows = D.join(D.c_table(imports_text), D.lisp_table(arch_text))
    callers = D.lisp_callers(root, rows); definitions, calls = D.c_definitions(root, rows)
    records = []
    for r in rows:
        led = ledger['imports'].get(r['lisp_name']); require(isinstance(led, dict), 'LEDGER ' + r['lisp_name'])
        disp = led.get('dispositions') or {}
        require(set(disp) == set(ledger['profiles']) and all(v in VOCABULARY for v in disp.values()), 'LEDGER dispositions ' + r['lisp_name'])
        require(led.get('closure_phase') in PHASES and isinstance(led.get('replacement'), str) and led['replacement'], 'LEDGER phase/replacement ' + r['lisp_name'])
        require(isinstance(led.get('regression'), list) and all(isinstance(x, str) and x.startswith('LL') for x in led['regression']), 'LEDGER regression ' + r['lisp_name'])
        sites = callers[r['lisp_name']]; x8632 = [s for s in sites if s['x8632']]
        require(len(sites) == led['expected_lisp_callers'], 'CALLERS ' + r['lisp_name'] + ' expected %s found %d' % (led['expected_lisp_callers'], len(sites)))
        require(len(x8632) == led['expected_x8632_callers'], 'CALLERS x8632 ' + r['lisp_name'] + ' expected %s found %d' % (led['expected_x8632_callers'], len(x8632)))
        defs = definitions[r['c_name']]; require(defs, 'DEFINITION ' + r['c_name'])
        required = bool(x8632) or led['closure_phase'] != 'none'
        node = dict(id='import:' + r['c_name'], kind='import', disposition=CENSUS_DISPOSITION[disp['full']], required=required,
                    implementation=led['replacement'] if disp['full'] != 'unsupported' else None, evidence='contracts/kernel-imports.v1.json#' + r['c_name'],
                    tests=['S0-LL15-b', 'S0-LL15-c'], reason=(led['note'] or led['group']) + '; full profile ' + disp['full'])
        records.append(dict(index=r['index'], offset=r['offset'], lisp_name=r['lisp_name'], c_name=r['c_name'], group=led['group'], c_definitions=defs, c_call_sites=calls[r['c_name']],
                            lisp_callers=sites, x8632_callers=len(x8632), dispositions=disp, closure_phase=led['closure_phase'], replacement=led['replacement'],
                            regression=led['regression'], note=led['note'], required_in_x8632_closure=required, census_node=node))
    require(set(ledger['imports']) == {r['lisp_name'] for r in rows}, 'LEDGER extra entries')
    counts = {p: {v: sum(1 for x in records if x['dispositions'][p] == v) for v in VOCABULARY} for p in ledger['profiles']}
    groups = {}
    for x in records:
        groups.setdefault(x['group'], []).append(x['c_name'])
    return dict(schema='kernel-imports', version=1, source_revision=U1, sources={IMPORTS_S.relative_to(ROOT).as_posix(): hashlib.sha256(imports_text.encode()).hexdigest(), ARCH.relative_to(ROOT).as_posix(): hashlib.sha256(arch_text.encode()).hexdigest()},
                ledger_sha256=hashlib.sha256(json.dumps(ledger, sort_keys=True).encode()).hexdigest(), vocabulary=ledger['vocabulary'], profiles=ledger['profiles'], closure_phases=list(PHASES),
                counts=dict(imports=len(records), with_x8632_callers=sum(1 for x in records if x['x8632_callers']), required_in_closure=sum(1 for x in records if x['required_in_x8632_closure']),
                            by_profile=counts, by_phase={p: sum(1 for x in records if x['closure_phase'] == p) for p in PHASES}, lisp_caller_sites=sum(len(x['lisp_callers']) for x in records)),
                groups=groups, imports=records, census_nodes=[x['census_node'] for x in records],
                placeholder='the working census graph carries one unresolved node gap:imports; these 65 nodes are its resolution once the evaluated census joins reachability')


def check(contract, schema):
    node_schema = schema['properties']['nodes']['items']
    for n in contract['census_nodes']:
        require(set(n) == set(node_schema['required']), 'NODE fields ' + n.get('id', '?'))
        require(n['kind'] == 'import' and n['disposition'] in node_schema['properties']['disposition']['enum'] and isinstance(n['required'], bool) and n['tests'] and n['evidence'], 'NODE ' + n['id'])
    ids = [n['id'] for n in contract['census_nodes']]; require(len(ids) == 65 == len(set(ids)), 'NODE count')
    require(contract['counts']['imports'] == 65, 'COUNT imports')
    for x in contract['imports']:
        require(x['dispositions']['full'] in VOCABULARY and x['closure_phase'] in PHASES, 'RECORD ' + x['c_name'])
        require(x['dispositions']['precompiled_callback'] != 'atomics-memory' or x['dispositions']['full'] == 'atomics-memory', 'RECORD profile monotonicity ' + x['c_name'])
        require(not (x['closure_phase'] != 'none' and x['dispositions']['full'] == 'unsupported'), 'RECORD unsupported in closure ' + x['c_name'])
    return dict(imports=65, required=contract['counts']['required_in_closure'], caller_sites=contract['counts']['lisp_caller_sites'])


def exercise(out):
    require(platform.system() == 'Darwin', 'MACOS_REFERENCE'); out.mkdir(parents=True, exist_ok=False)
    pins = {p.relative_to(ROOT).as_posix(): u1_pin(p) for p in (IMPORTS_S, ARCH)}
    save(out / 'environment.json', dict(python=sys.version, platform=platform.platform(), u1_pins=pins))
    ledger = read(HERE / 'dispositions.json'); schema = read(DOCS / 'contracts/census.schema.json')
    contract = build(ROOT, IMPORTS_S.read_text(), ARCH.read_text(), ledger); summary = check(contract, schema)
    save(out / 'kernel-imports.v1.json', contract)
    require(canonical(contract) == COMMITTED.read_text(), 'COMMITTED differs from the regeneration')
    q = out / 'quarantine'; q.mkdir(); refusals = []
    def control(name, fn, expected):
        try: fn()
        except ValueError as e: reason = str(e)
        else: raise ValueError('CONTROL_ESCAPED ' + name)
        require(reason.startswith(expected), 'CONTROL_REASON ' + name + ': ' + reason)
        refusals.append(dict(control=name, refused=reason)); save(q / (name + '.json'), dict(control=name, refused=reason))
    bad = copy.deepcopy(ledger); del bad['imports']['lisp-read']
    control('disposition-omitted', lambda: build(ROOT, IMPORTS_S.read_text(), ARCH.read_text(), bad), 'LEDGER lisp-read')
    control('c-table-shortened', lambda: build(ROOT, IMPORTS_S.read_text().replace('        defimport(lisp_read)\n', ''), ARCH.read_text(), ledger), 'TABLE count')
    control('lisp-table-reordered', lambda: build(ROOT, IMPORTS_S.read_text(), ARCH.read_text().replace('  lisp-read\n  lisp-write\n', '  lisp-write\n  lisp-read\n'), ledger), 'TABLE name lisp-write versus lisp_read')
    bad2 = copy.deepcopy(ledger); bad2['imports']['lisp-futex']['expected_x8632_callers'] = 0
    control('caller-count-wrong', lambda: build(ROOT, IMPORTS_S.read_text(), ARCH.read_text(), bad2), 'CALLERS x8632 lisp-futex')
    bad3 = copy.deepcopy(ledger); bad3['imports']['malloc']['dispositions']['full'] = 'host-malloc'
    control('vocabulary-outside', lambda: build(ROOT, IMPORTS_S.read_text(), ARCH.read_text(), bad3), 'LEDGER dispositions malloc')
    bad4 = copy.deepcopy(contract); bad4['census_nodes'][0]['disposition'] = 'implemented-later'
    control('node-outside-census-schema', lambda: check(bad4, schema), 'NODE import:fd_setsize_bytes')
    bad5 = copy.deepcopy(ledger); bad5['imports']['lisp-pipe']['closure_phase'] = 'loader'
    control('unsupported-in-closure', lambda: check(build(ROOT, IMPORTS_S.read_text(), ARCH.read_text(), bad5), schema), 'RECORD unsupported in closure lisp_pipe')
    save(out / 'controls.json', refusals)
    observations = dict(summary=summary, counts=contract['counts'], controls=[r['control'] for r in refusals])
    save(out / 'observations.json', observations)
    save(out / 'summary.json', dict(version=1, id=ID, status='PASS', scope=SCOPE, review_disposition='NOT_REVIEWED', **observations))
    return observations


def run(out):
    require(ROOT not in out.parents and out != ROOT and not out.exists(), 'FRESH_OUTPUT_OUTSIDE_CHECKOUT')
    snapshots = {str(p.relative_to(ROOT)): p.read_bytes() for p in sources()}
    source_sha = {str(p.relative_to(ROOT)): sha(p) for p in sources()}
    record = dict(version=1, status='FAIL', command=[sys.executable, *sys.argv], timestamp=datetime.now(timezone.utc).isoformat(), source_sha256=source_sha)
    try:
        exercise(out); (out / 'source').mkdir()
        for p in sources(): (out / 'source' / (('contracts-' if p.parent.name == 'contracts' and p.name == 'derive.py' else '') + p.name)).write_bytes(p.read_bytes())
        require(record['source_sha256'] == {str(p.relative_to(ROOT)): sha(p) for p in sources()}, 'SOURCE_CHANGED')
        record.update(status='PASS')
        print('PASS: kernel-import census, 65 records, seven controls refused. Review pending; no gate credit.')
    except BaseException as e:
        record['error'] = type(e).__name__ + ': ' + str(e); raise
    finally:
        if out.exists():
            save(out / 'run.json', record); (out / 'source').mkdir(exist_ok=True)
            for name, data in snapshots.items():
                p = Path(name); (out / 'source' / (('contracts-' if p.parent.name == 'contracts' and p.name == 'derive.py' else '') + p.name)).write_bytes(data)


def verify(packet):
    record = read(packet / 'run.json'); require(record['status'] == 'PASS', 'RUN_STATUS')
    for name, h in record['source_sha256'].items(): require(sha(ROOT / name) == h, 'SOURCE_PIN ' + name)
    temp = Path(tempfile.mkdtemp(prefix='ccl-kernel-imports-verify-'))
    try:
        fresh = temp / 'replay'; observations = exercise(fresh)
        require(observations == read(packet / 'observations.json'), 'REPLAY_OBSERVATIONS')
        names = [p.relative_to(fresh) for p in fresh.rglob('*') if p.is_file() and p.name != 'environment.json']
        for n in names: require((fresh / n).read_bytes() == (packet / n).read_bytes(), 'REPLAY_BYTES ' + str(n))
        require(read(fresh / 'environment.json')['u1_pins'] == read(packet / 'environment.json')['u1_pins'], 'U1_PINS')
    except BaseException as e:
        save(temp / 'failure.json', dict(status='FAIL', packet=str(packet), error=str(e)))
        print('Original verification failure retained at ' + str(temp), file=sys.stderr); raise
    else:
        shutil.rmtree(temp)
    print('PASS: census regenerated; ' + str(len(names)) + ' identical deterministic files and U1 pins.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output', type=Path); g.add_argument('--verify', type=Path); g.add_argument('--generate', action='store_true'); a = p.parse_args()
    if a.generate:
        contract = build(ROOT, IMPORTS_S.read_text(), ARCH.read_text(), read(HERE / 'dispositions.json')); check(contract, read(DOCS / 'contracts/census.schema.json'))
        COMMITTED.write_text(canonical(contract)); print('generated', COMMITTED, contract['counts'])
    elif a.verify: verify(a.verify.resolve())
    else: run(a.output.resolve())
