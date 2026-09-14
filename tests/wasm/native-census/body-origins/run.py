#!/usr/bin/env python3
"""Produce or replay the remaining-body origin worklist without native execution."""
import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import traceback

from classify import assemble, binding_view, canonical, controls, require, scan, targets

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUTPUTS = ('capture.json.gz', 'witnesses.jsonl.gz', 'origins.json.gz', 'summary.json', 'controls.json')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(gzip.decompress(raw) if path.suffix == '.gz' else raw)


def save(path, value):
    raw = (canonical(value) + '\n').encode()
    path.write_bytes(gzip.compress(raw, mtime=0) if path.suffix == '.gz' else raw)


def execute(store, out):
    manifest = read(HERE/'inputs.json')
    inputs = {}
    for name, pin in manifest['inputs'].items():
        path = store/pin['path']
        require(digest(path) == pin['sha256'], 'INPUT_IDENTITY '+name)
        inputs[name] = path if name == 'events' else read(path)
    wanted = targets(inputs['bodies'], inputs['delta'])
    facts = inputs['bindings']
    view = binding_view(facts, inputs['histories'], wanted)
    parent_ids = {r['first_binding']['parent'] for r in view.values()} - {None}
    print('Scanning first descriptors in the original stream; no native execution.', flush=True)
    with gzip.open(inputs['events'], 'rb') as stream:
        capture, witnesses = scan(stream, wanted, parent_ids, facts['counts'])
    readonly_codes = [r['code'] for r in inputs['bodies']['bodies']]
    result, summary = assemble(wanted, view, capture, facts['inventories'], readonly_codes)
    checks = controls(wanted, view, capture, facts['inventories'], readonly_codes, result, summary)
    for name, value in [('capture.json.gz', capture), ('origins.json.gz', result),
                        ('summary.json', summary), ('controls.json', checks)]:
        save(out/name, value)
    (out/'witnesses.jsonl.gz').write_bytes(gzip.compress(b''.join(witnesses), mtime=0))
    print(canonical(dict(summary, controls_rejected=checks['controls_rejected'])), flush=True)


def main(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sources = list(sorted(HERE.glob('*.py'))) + [HERE/'inputs.json',
               HERE.parent/'binding-versions/collect.py', HERE.parent/'binding-versions/history.py',
               HERE.parent/'rich-observation/observer.lisp']
    report = dict(status='FAIL', timestamp=datetime.now(timezone.utc).isoformat(),command=sys.argv,
                  source_sha256={str(p.relative_to(ROOT)): digest(p) for p in sources},
                  inputs=read(HERE/'inputs.json'),native_execution=False,historical_archive_scan=False)
    for path in sources:
        dest=out/'sources'/path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path,dest)
    save(out/'run.json',report)
    try:
        if args.packet:
            packet=args.packet.resolve()
            manifest=read(packet/'packet.json')
            require(manifest['id']=='NATIVE-BODY-ORIGINS-R1','PACKET_IDENTITY')
            rows=manifest['files']
            require(len({r['path'] for r in rows})==len(rows)
                    and {p.name for p in packet.iterdir()}=={'packet.json'}|{r['path'] for r in rows},'PACKET_MEMBERSHIP')
            for row in rows:
                p=packet/row['path']
                require(p.parent==packet and p.is_file() and p.stat().st_size==row['bytes']
                        and digest(p)==row['sha256'],'PACKET_ARTIFACT '+row['path'])
            require(read(packet/'sources.json')==report['source_sha256'],'PACKET_SOURCES')
            require(read(packet/'inputs.json')==report['inputs'],'PACKET_INPUTS')
        execute(args.evidence.resolve(),out)
        if args.packet:
            for name in OUTPUTS:
                require((out/name).read_bytes()==(args.packet/name).read_bytes(),'REPRODUCTION '+name)
            report['analysis_outputs_byte_identical']=len(OUTPUTS)
        report['status']='PASS'
    except BaseException:
        (out/'failure.txt').write_text(traceback.format_exc())
        raise
    finally:
        save(out/'run.json',report)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--packet',type=Path)
    main(parser.parse_args())
