#!/usr/bin/env python3
"""Quarantined command stimuli; execute the native producer's unchanged run/command."""
import argparse
import json
import os
from pathlib import Path
import runpy
import signal
import sys
import tarfile


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def child(config, step, marker):
    """Supply tiny synthetic build products, then apply a real process outcome."""
    source = Path(config['work']) / 'ccl'
    inputs = Path(config['inputs'])
    if step.startswith('extract-') or step.endswith('-restore-image'):
        kind = step.removeprefix('extract-') if step.startswith('extract-') else 'bootstrap'
        archive = inputs / {'source':'source.tar', 'tests':'tests.tar', 'bootstrap':'bootstrap.tar.gz'}[kind]
        dest = source if kind != 'tests' else Path(config['work']) / 'ccl-tests'
        with tarfile.open(archive) as stream:
            for entry in stream:
                if step.endswith('-restore-image') and entry.name != 'dx86cl64.image':
                    continue
                # Only the literal files constructed by this fixture are valid.
                if not entry.isfile() or entry.name not in ('source.lisp', 'tests.txt', 'dx86cl64', 'dx86cl64.image'):
                    raise ValueError('unexpected synthetic archive entry')
                (dest / entry.name).write_bytes(stream.extractfile(entry).read())
    elif step.endswith('-clean-rebuild'):
        (source / 'fixture.dx64fsl').write_bytes(b'SYNTHETIC FASL; never Lisp execution\n')
    elif step.endswith('-tests'):
        save(Path(os.environ['CCL_GATE0_OUTPUT']) / 'test-summary.json',
             dict(success=True, passed=1, eligible=1, actual_origin='SYNTHETIC COMMAND STIMULUS'))
    mode = config['mode'] if step == config['step'] else 'success'
    print('SYNTHETIC COMMAND STIMULUS ' + step, flush=True)
    # Even the failed commands supply their normal products and marker first.
    if marker and mode != 'missing-marker':
        print(marker, flush=True)
    print('TERMINAL MODE ' + mode, flush=True)
    if mode == 'exit':
        return 23
    if mode == 'kill':
        os.kill(os.getpid(), signal.SIGKILL)
    if mode == 'timeout':
        while True:
            signal.pause()
    return 0


def aggregate(config_path, config):
    # runpy loads the original functions without executing the __main__ branch.
    # Only their command invocation binding is adapted. No exception, status,
    # marker, aggregation or subprocess implementation is replaced.
    sys.argv = [config['producer'], '--inputs', config['inputs'], '--work', config['work'],
                '--output', config['output']]
    namespace = runpy.run_path(config['producer'], run_name='quarantined_native_producer')
    production_run = namespace['run']
    globals_ = production_run.__globals__
    production_command = globals_['command']
    invocations = []

    def adapted(name, argv, cwd=Path(config['work']), extra_env=None, timeout=1800, marker=None):
        effective = [sys.executable, str(Path(__file__).resolve()), '--config', str(config_path), '--child', name]
        if marker:
            effective += ['--marker', marker]
        effective_timeout = 1 if name == config['step'] and config['mode'] == 'timeout' else timeout
        invocations.append(dict(name=name, original_argv=argv, effective_argv=effective,
            cwd=str(cwd), extra_env=extra_env, original_timeout=timeout,
            effective_timeout=effective_timeout, marker=marker))
        save(config_path.parent / 'invocations.json', invocations)
        return production_command(name, effective, cwd=cwd, extra_env=extra_env,
                                  timeout=effective_timeout, marker=marker)

    globals_['command'] = adapted
    return production_run()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--child')
    parser.add_argument('--marker')
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    sys.exit(child(config, args.child, args.marker) if args.child else aggregate(args.config, config))
