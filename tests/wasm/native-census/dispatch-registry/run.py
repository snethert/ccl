#!/usr/bin/env python3
"""Capture and qualify a native registry checkpoint, with retained negative evidence."""
import argparse
import traceback
from pathlib import Path
from native import HERE, capture, digest, read, require, save
from analyze import assess, check, controls

OUTPUTS = ('first.json.gz','repeat.json.gz','independent.json','joins.json.gz','summary.json','controls.json')


def run(args):
    data, report = capture(args)
    out = args.output.resolve()
    try:
        independent = read(out/'independent.json')
        facts, summary = assess(data, independent)
        check(facts,summary,data,independent)
        checked = controls(data,independent,facts,summary)
        for name,value in [('joins.json.gz',facts),('summary.json',summary),('controls.json',checked)]:
            save(out/name,value)
        if args.packet:
            packet = args.packet.resolve(); manifest = read(packet/'packet.json'); rows = manifest['files']
            require(manifest['id']=='NATIVE-DISPATCH-REGISTRY-R1', 'PACKET_IDENTITY')
            require(len({r['path'] for r in rows})==len(rows)
                    and {p.name for p in packet.iterdir()}=={'packet.json'}|{r['path'] for r in rows}, 'PACKET_MEMBERSHIP')
            for row in rows:
                path = packet/row['path']
                require(path.parent==packet and path.is_file() and path.stat().st_size==row['bytes']
                        and digest(path)==row['sha256'], 'PACKET_BYTES '+row['path'])
            require(read(packet/'sources.json')==report['source_sha256'], 'PACKET_SOURCES')
            for name in OUTPUTS:
                require((out/name).read_bytes()==(packet/name).read_bytes(), 'REPRODUCTION '+name)
            report['replayed_outputs_byte_identical'] = len(OUTPUTS)
        report.update(status='PASS', analysis='PASS', controls_rejected=checked['controls_rejected'],
                      native_semantics='KNOWN_EMPTY_METHOD_DEFECT_RETAINED', census_gate_credit=False)
        print(__import__('json').dumps(dict(summary,controls_rejected=checked['controls_rejected']),sort_keys=True),flush=True)
    except BaseException:
        report['status']='FAIL'; (out/'analysis-failure.txt').write_text(traceback.format_exc()); raise
    finally:
        save(out/'run.json',report)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','work','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--packet',type=Path)
    run(p.parse_args())
