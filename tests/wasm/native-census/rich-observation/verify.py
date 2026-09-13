#!/usr/bin/env python3
"""Check collected joins and run omissions against the actual native observer."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
from unit import RichUnit
from install import write_install
from analyze import analyze, events, write
from check import check_probe
from test_controls import test as semantic_controls
from test_unit import test as unit_controls

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def run(work, output, pack=None):
    output.mkdir(parents=True, exist_ok=False)
    source = work / 'ccl'; unit = RichUnit(work)
    with unit: write_install(source, output / 'install.lisp')
    for p in HERE.glob('probe-l*.lisp'): shutil.copyfile(p, work / p.name)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'CCL_DEFAULT_DIRECTORY': str(source)}
    report = {'status': 'FAIL', 'commands': [],
              'native_inputs_sha256': {str(source / name): sha(source / name) for name in ('dx86cl64', 'dx86cl64.image')},
              'fixture_sha256': {p.name: sha(p) for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py', '.lisp', '.patch', '.json')},
              'shared_sha256': {str(p): sha(p) for p in (HERE.parent / 'observer.lisp', HERE.parent / 'dependencies.lisp', HERE.parent / 'reversible.py')},
              'install_sha256': sha(output / 'install.lisp')}
    def lisp(name, expression, extra=()):
        argv = [str(source / 'dx86cl64'), '--no-init', '--batch']
        for p in [HERE.parent / 'observer.lisp', HERE.parent / 'dependencies.lisp', output / 'install.lisp',
                  HERE / 'observer.lisp', *extra]: argv += ['--load', str(p)]
        argv += ['--eval', '(progn ' + expression + ' (ccl:quit))']
        with (output / (name + '.log')).open('wb') as log:
            result = subprocess.run(argv, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=180)
        report['commands'].append({'name': name, 'argv': argv, 'cwd': str(source), 'environment': env,
                                   'exit_code': result.returncode, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})
        if result.returncode: raise ValueError(name + ' native execution failed; see log')

    def compress(path):
        with path.open('rb') as src, gzip.open(str(path) + '.gz', 'wb') as dst: shutil.copyfileobj(src, dst)
        path.unlink()

    try:
        results = []; baseline = None
        for mode in ('normal', 'missing-installation', 'missing-expander', 'missing-loader-functions'):
            path = output / (mode + '.jsonl')
            expression = '(cl-user::run-rich-mutant #p' + json.dumps(str(work) + '/') + ' ' + json.dumps(str(path)) + ' ' + json.dumps(mode) + ')'
            lisp(mode, expression, [HERE / 'probe-driver.lisp', HERE / 'mutant-driver.lisp'])
            binaries = {p.name: sha(p) for p in work.glob('probe-l*.dx64fsl')}
            if mode == 'normal':
                baseline = binaries
                for p in work.glob('probe-l*.dx64fsl'): shutil.copyfile(p, output / p.name)
            elif binaries != baseline: raise ValueError('omission changed native output: ' + mode)
            data = analyze(events(path))
            if mode == 'normal':
                result = check_probe(data); write(output / 'probe-joins.json.gz', data)
                report['semantic_controls'] = semantic_controls(data)
            else:
                try: check_probe(data)
                except ValueError as exc: result = {'status': 'REJECTED', 'reason': str(exc)}
                else: raise ValueError('actual collector omission escaped: ' + mode)
            results.append({'mode': mode, 'native_execution': 'PASS', 'native_fasls_sha256': binaries, **result})
            compress(path)
        report['collector_controls'] = results
        windows = []
        for label, symbol in [('metadata', 'ccl::%lfun-info-index'), ('string', 'common-lisp:string-downcase')]:
            for mutant in (False, True):
                name = 'window-' + label + ('-mutant' if mutant else '-positive'); path = output / (name + '.jsonl')
                lisp(name, '(cl-user::run-rich-redefinition-control ' + json.dumps(str(path)) + ' ' +
                     ('t' if mutant else 'nil') + ' (quote ' + symbol + '))', [HERE / 'redefinition-control.lisp'])
                status = 'REJECTED' if mutant else 'PASS'
                if 'REDEFINITION-CONTROL ' + status not in (output / (name + '.log')).read_text():
                    raise ValueError('missing window control oracle')
                compress(path); windows.append({'name': name, 'status': status})
        report['window_controls'] = windows
        lisp('json-writer', '(ccl-rich-census::check-json-writer ' + json.dumps(str(output / 'reference-json.jsonl')) +
             ' ' + json.dumps(str(output / 'current-json.jsonl')) + ')', [HERE / 'json-check.lisp'])
        if (output / 'reference-json.jsonl').read_bytes() != (output / 'current-json.jsonl').read_bytes():
            raise ValueError('JSON writer bytes differ')
        values = [json.loads(line) for line in (output / 'current-json.jsonl').read_text().splitlines()]
        if len(values) != 12 or values[8] != ''.join(chr(i) for i in range(128)) or values[9] != '\u0080\u00ff\u20ac\U0001f642':
            raise ValueError('JSON parser round trip differs')
        report['json_writer'] = {'status': 'PASS', 'cases': len(values), 'byte_identical': True}
        report['unit_controls'] = unit_controls()
        if pack:
            native = json.loads((pack / 'run.json').read_text())
            if native['execution_status'] != 'PASS': raise ValueError('full native run has not passed')
            observed = 'observed' + ('-r' + str(native['attempt']) if native['attempt'] > 1 else '')
            report['full_run'] = {'run': str(pack / 'run.json'), 'sha256': sha(pack / 'run.json'), 'streams': {}}
            for name in (observed, 'observed-probe', 'cold-start'):
                data = analyze(events(pack / (name + '.jsonl.gz')))
                if name == 'observed-probe': check_probe(data)
                write(output / (name + '-joins.json.gz'), data)
                report['full_run']['streams'][name] = data['summary']
        report['status'] = 'PASS'
    finally:
        report['source_restoration'] = json.loads(unit.state.read_text())
        (output / 'run.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'collector_controls_rejected': 3,
                      'window_controls_rejected': 2, 'semantic_controls_rejected': report['semantic_controls']['controls_rejected'],
                      'unit_controls_rejected': 5, 'full_run': report.get('full_run', {}).get('streams')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('work', 'output'): p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--pack', type=Path, help='Also validate a completed full native run.')
    args = p.parse_args(); run(args.work.resolve(), args.output.resolve(), args.pack.resolve() if args.pack else None)
