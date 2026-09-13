#!/usr/bin/env python3
"""Replay only this macro packet and its direct source bindings."""
import argparse
from check import check, controls, read, require, ROOT, NATIVE_CONTROLS
from run import digest


def verify(packet):
    record = read(packet/'run.json')
    require(record['status'] == 'PASS', 'RUN_STATUS')
    for path, expected in record['source_sha256'].items():
        require(digest(ROOT/path) == expected, 'SOURCE_PIN: '+path)
    for row in record['artifacts']:
        require(digest(packet/row['path']) == row['sha256'] and
                (packet/row['path']).stat().st_size == row['bytes'], 'ARTIFACT: '+row['path'])
    c, t = (read(packet/('normal-'+k+'.json.gz')) for k in ('macros', 'traversal'))
    counts = check(c, t)
    require(controls(c, t) == read(packet/'controls.json'), 'CHECKER_CONTROLS')
    for mode, expected in NATIVE_CONTROLS.items():
        try:
            check(*(read(packet/(mode+'-'+k+'.json.gz')) for k in ('macros', 'traversal')))
        except ValueError as e:
            require(str(e) == expected, 'NATIVE_CONTROL_REASON: '+mode)
        else:
            raise ValueError('NATIVE_CONTROL_ESCAPED: '+mode)
    s = read(packet/'summary.json')
    require(all(s[k] == v for k, v in counts.items()) and s['macro_environment_qualified'] is False and
            s['graph_edges_replaced'] == 0 and s['checker_controls_rejected'] == 20 and
            s['native_controls_rejected'] == 4 and s['native_reproduction_equal'] is True, 'SUMMARY')
    print('PASS: macro packet, source bindings, 4 native controls, 20 checker controls.')


if __name__ == '__main__':
    from pathlib import Path
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet', type=Path, required=True)
    verify(p.parse_args().packet)
