#!/usr/bin/env python3
"""Replay only the retained first-module capture, facts and omission controls."""
import argparse
import gzip
import json
from pathlib import Path
from check import check_capture, check_projection
from test_controls import run


def read(path):
    with gzip.open(path, 'rt') if path.suffix == '.gz' else path.open() as stream:
        return json.load(stream)


def verify(packet, source):
    raw = source.read_bytes()
    capture = read(packet/'normal.json.gz')
    counts = check_capture(capture, raw)
    check_projection(read(packet/'facts.json.gz'), capture)
    controls = run(capture, read(packet/'facts.json.gz'), raw)
    if controls != read(packet/'controls.json'):
        raise ValueError('control replay differs')
    for mode, reason in [('stop-after-first-capture', 'FORM_COVERAGE'), ('host-reader', 'TARGET_CONTEXT')]:
        try: check_capture(read(packet/(mode+'.json.gz')), raw)
        except ValueError as e:
            if str(e) != reason: raise ValueError('native control reason differs')
        else: raise ValueError('retained native control escaped')
    summary = read(packet/'summary.json')
    if any(summary[k] != v for k, v in counts.items()):
        raise ValueError('summary counts differ')
    print(f'PASS: {counts["top_level_forms"]} forms accounted for; '
          f'{counts["unsupported_definitions"]} unsupported definitions remain; '
          f'{controls["controls_rejected"]} analysis and 2 retained native controls reject.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    a = p.parse_args(); verify(a.packet, a.source)
