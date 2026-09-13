#!/usr/bin/env python3
"""Replay this retained source-expander packet and direct source bindings only."""
import argparse
from pathlib import Path
from check import ROOT, NATIVE_CONTROLS, check, controls, compare, manifest, read, require
from run import digest


def verify(packet):
    record = read(packet/'run.json')
    require(record['status'] == 'PASS', 'RUN_STATUS')
    for path, expected in record['source_sha256'].items():
        require(digest(ROOT/path) == expected, 'SOURCE_PIN '+path)
    for row in record['artifacts']:
        require(digest(packet/row['path']) == row['sha256'] and
                (packet/row['path']).stat().st_size == row['bytes'], 'ARTIFACT '+row['path'])
    selection = manifest()
    def captured(mode):
        return tuple(read(packet/(mode+'-'+kind+'.json.gz')) for kind in ('expanders', 'traversal'))
    c, t = captured('normal')
    ref, ref_t = captured('inherited')
    counts = check(c, t, selection)
    check(ref, ref_t, selection, reference=True)
    compare(c, t, ref, ref_t)
    require(controls(c, t, ref, ref_t, selection) == read(packet/'controls.json'), 'CONTROLS')
    for mode, expected in NATIVE_CONTROLS.items():
        try:
            check(*captured(mode), selection)
        except ValueError as e:
            require(str(e) == expected, 'NATIVE_CONTROL_REASON '+mode)
        else:
            raise ValueError('NATIVE_CONTROL_ESCAPED '+mode)
    s = read(packet/'summary.json')
    require(all(s[k] == v for k, v in counts.items()) and s['macro_environment_qualified'] is False and
            s['checker_controls_rejected'] == 27 and s['native_controls_rejected'] == 4 and
            s['inherited_traversal_byte_identical'] is True and s['inherited_expansion_equivalence'] is True, 'SUMMARY')
    commands = {r['mode']: r for r in record['commands']}
    require(commands['normal']['capture_sha256'] == commands['repeat']['capture_sha256'], 'REPEAT_IDENTITY')
    require(commands['normal']['capture_sha256']['traversal'] ==
            commands['inherited']['capture_sha256']['traversal'], 'REFERENCE_IDENTITY')
    print('PASS: 293 source expansion routes, reference equivalence, 4 native controls, 27 checker controls.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet', type=Path, required=True)
    verify(p.parse_args().packet)
