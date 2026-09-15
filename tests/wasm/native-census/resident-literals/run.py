#!/usr/bin/env python3
"""Join retained resident function literals without native execution."""
import argparse
from datetime import datetime, timezone
import gc
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import traceback
from join import apply, canonical, check, collect, make_delta, require, summarize
from controls import run as controls

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTPUTS = ('facts.json.gz', 'delta.json.gz', 'summary.json', 'controls.json')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(path, value):
    raw = (canonical(value)+'\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


def execute(args, out):
    pins = read(HERE/'inputs.json'); inputs = {}
    for key, pin in pins['inputs'].items():
        path = args.base if key == 'base' else args.evidence/pin['path']
        require(digest(path) == pin['sha256'], 'INPUT_IDENTITY '+key)
        if key in ('witnesses', 'readonly_inventory'):
            lines = gzip.decompress(path.read_bytes()).splitlines(keepends=True)
            inputs[key] = lines
        else:
            inputs[key] = read(path)
    sources = {}
    for path, pin in pins['u1_sources'].items():
        require(digest(ROOT/path) == pin, 'U1_SOURCE_IDENTITY '+path)
        sources[path] = (ROOT/path).read_bytes()
    original = inputs['base']; flow = inputs['flow_delta']
    base = dict(original, nodes=original['nodes']+flow['nodes'], edges=original['edges']+flow['edges'],
                profile=original['profile']+'; '+flow['scope'])
    # Reuse the reviewed binding delta materializer, not a second implementation.
    sys.path.insert(0, str(HERE.parent/'binding-versions'))
    from links import apply as apply_bindings
    base = apply_bindings(base, inputs['binding_delta'])
    values = (inputs['origins'], inputs['witnesses'], inputs['readonly_inventory'],
              inputs['readonly_export'], inputs['readonly_summary'], sources)
    facts = collect(*values); delta = make_delta(facts, base); graph = apply(base, delta)
    check(facts, delta, graph, collect(*values), base)
    checks = controls(values, facts, delta, graph, base)
    spec = importlib.util.spec_from_file_location('literal_contract', ROOT/'doc/WASM/tools/check-census.py')
    contract = importlib.util.module_from_spec(spec); spec.loader.exec_module(contract)
    errors = contract.validate(graph)
    prefixes = ('unresolved reachable edge from ', 'unimplemented reachable node ')
    require(not [e for e in errors if not e.startswith(prefixes)], 'EXCHANGE_STRUCTURE')
    summary = summarize(facts, delta, graph)
    summary.update(structural_contract='PASS', closure='BLOCKED', controls_rejected=checks['controls_rejected'],
                   errors={p.strip():sum(e.startswith(p) for e in errors) for p in prefixes})
    for name, value in zip(OUTPUTS, (facts, delta, summary, checks)):
        save(out/name, value)
    print(canonical(summary), flush=True)


def main(args):
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=False)
    sources = sorted(HERE.glob('*.py')) + [HERE/'inputs.json',
        HERE.parent/'binding-versions/links.py', HERE.parent/'binding-versions/common.py',
        ROOT/'doc/WASM/tools/check-census.py', ROOT/'doc/WASM/contracts/census.schema.json',
        ROOT/'level-1/l1-dcode.lisp', ROOT/'lib/describe.lisp']
    report = dict(status='FAIL', timestamp=datetime.now(timezone.utc).isoformat(), command=sys.argv,
                  native_execution=False, source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sources},
                  inputs=read(HERE/'inputs.json'))
    for source in sources:
        dest = out/'sources'/source.relative_to(ROOT); dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, dest)
    save(out/'run.json', report)
    try:
        if args.packet:
            packet = args.packet.resolve(); manifest = read(packet/'packet.json')
            require(manifest['id']=='NATIVE-RESIDENT-LITERALS-R1', 'PACKET_IDENTITY')
            rows = manifest['files']
            require(len({r['path'] for r in rows})==len(rows)
                    and {p.name for p in packet.iterdir()}=={'packet.json'}|{r['path'] for r in rows}, 'PACKET_MEMBERSHIP')
            for row in rows:
                path = packet/row['path']
                require(path.parent==packet and path.is_file() and path.stat().st_size==row['bytes']
                        and digest(path)==row['sha256'], 'PACKET_ARTIFACT '+row['path'])
            require(read(packet/'sources.json')==report['source_sha256'], 'PACKET_SOURCES')
            require(read(packet/'inputs.json')==report['inputs'], 'PACKET_INPUTS')
        gc.disable()
        execute(args, out)
        if args.packet:
            for name in OUTPUTS:
                require((out/name).read_bytes()==(args.packet/name).read_bytes(), 'REPRODUCTION '+name)
            report['analysis_outputs_byte_identical'] = len(OUTPUTS)
        report['status'] = 'PASS'
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc())
        raise
    finally:
        gc.enable(); save(out/'run.json', report)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('evidence', 'base', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--packet', type=Path)
    main(p.parse_args())
