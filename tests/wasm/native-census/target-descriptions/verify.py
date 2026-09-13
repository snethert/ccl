#!/usr/bin/env python3
"""Replay the retained description capture and scoped controls without native execution."""
import argparse
import gzip
import json
from pathlib import Path
from analysis import ROOT, NATIVE_CONTROLS, check_descriptions, check_capture, check_projection
from controls import run


def read(p):
    with gzip.open(p, 'rt') if p.suffix == '.gz' else p.open() as s: return json.load(s)


def verify(packet):
    c = read(packet/'normal.json.gz'); d = read(packet/'descriptions.json')
    check_descriptions(d)
    source = (ROOT/'lib/dumplisp.lisp').read_bytes()
    counts = check_capture(c, source, d)
    f = read(packet/'facts.json.gz'); check_projection(f, c, d)
    tests = run(c, f, d, source)
    if tests != read(packet/'controls.json'): raise ValueError('controls differ')
    for mode, expected in NATIVE_CONTROLS.items():
        try: check_capture(read(packet/(mode+'.json.gz')), source, d)
        except ValueError as e:
            if str(e) != expected: raise ValueError('native control reason differs: '+mode)
        else: raise ValueError('native control escaped: '+mode)
    summary = read(packet/'summary.json')
    if any(summary[k] != v for k, v in counts.items()): raise ValueError('summary counts differ')
    print(f'PASS: {counts["captured_definitions"]} definitions, {counts["load_time_initializer_bodies"]} deferred initializers; '
          f'{tests["controls_rejected"]} analysis and {len(NATIVE_CONTROLS)} native controls; '
          f'{counts["unsupported_definitions"]} source gaps remain.')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--packet', required=True, type=Path)
    verify(p.parse_args().packet)
