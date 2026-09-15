"""Run a source-qualified, reversible native call-site observation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import traceback

HERE = Path(__file__).resolve().parent
CENSUS = HERE.parent


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def save(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')


def execute(source_root, source, function, image, kernel, output, *, scenario=None,
            selection=None, timeout=120, limit=10000, observer_path=None):
    output.mkdir(parents=True, exist_ok=False)
    if timeout <= 0 or limit < 1: raise ValueError('positive timeout and event limit required')
    original = source.read_bytes()
    source_hash = hashlib.sha256(original).hexdigest()
    if selection is not None:
        if selection['source_sha256'] != source_hash or selection['function'] != function:
            raise ValueError('site selection belongs to another source or function')
        if scenario is None: raise ValueError('witness requires a scenario')
    helper_paths = [CENSUS / n for n in ('observer.lisp', 'dependencies.lisp',
        'rich-observation/observer.lisp', 'resident-bodies/export.lisp', 'query/site-probe.lisp')]
    labels = [str(p.relative_to(CENSUS)) for p in helper_paths]
    if observer_path is not None: helper_paths[-1] = observer_path
    tools = {name: digest(p) for name, p in zip(labels, helper_paths)}
    shutil.copyfile(helper_paths[-1], output / 'site-probe.lisp')
    shutil.copyfile(Path(__file__), output / 'native.py')
    shutil.copyfile(source, output / 'input.lisp')
    if scenario: shutil.copyfile(scenario, output / 'scenario.lisp')
    argv = [str(kernel), '--image-name', str(image), '--no-init', '--batch',
            '--load', str(source_root / 'lib/x8664env.lisp')]
    for path in helper_paths: argv += ['--load', str(path)]
    argv += ['--eval', '(progn (ccl-census-query::run) (ccl:quit))']
    env = dict(os.environ, CCL_DEFAULT_DIRECTORY=str(source_root), QUERY_SOURCE=str(source),
               QUERY_FUNCTION=function, QUERY_OUTPUT=str(output / 'native.json'),
               QUERY_EVENT_LIMIT=str(limit))
    for name in ('QUERY_SITE', 'QUERY_SCENARIO'): env.pop(name, None)
    if selection is not None:
        env.update(QUERY_SITE=str(selection['site']['index']), QUERY_SCENARIO=str(output / 'scenario.lisp'))
    record = dict(version=1, status='ERROR', argv=argv, cwd=str(source_root),
        source_sha256=source_hash, function=function, helpers=tools,
        kernel_sha256=digest(kernel), image_sha256=digest(image), timeout_seconds=timeout,
        selection=selection, scenario_sha256=digest(scenario) if scenario else None,
        observer_override=str(observer_path) if observer_path is not None else None,
        scope='Source-derived native recompilation, selected scenario only; no exhaustive bound or resident-code equivalence.')
    save(output / 'run.json', record)
    try:
        with (output / 'native.log').open('wb') as log:
            child = subprocess.Popen(argv, cwd=source_root, env=env, stdout=log,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            try: record['exit_code'] = child.wait(timeout=timeout)
            except BaseException:
                os.killpg(child.pid, signal.SIGKILL); child.wait(); raise
        if record['exit_code'] != 0 or 'CENSUS-QUERY-PASS' not in (output / 'native.log').read_text():
            raise ValueError('native query failed; see native.log')
        native = json.loads((output / 'native.json').read_text())
        if source.read_bytes() != original: raise ValueError('source changed during observation')
        selections = [dict(source_sha256=source_hash, function=function, site=s) for s in native['sites']]
        if selection is not None:
            if selection not in selections: raise ValueError('compiled site identity changed')
            if not native['scenario_equal'] or not native['restored_code_identical'] or native['bound']:
                raise ValueError('witness scope or restoration failure')
            total = native['total_events']; events = native['events']
            if (type(total) is not int or total < 0 or len(events) != min(total, limit) or
                    native['dropped_events'] != max(0, total - limit) or
                    [r['event'] for r in events] != list(range(len(events)))):
                raise ValueError('witness event coverage or ordering differs')
        answer = dict(version=1, kind='call-site-witness' if selection is not None else 'call-sites',
            status='TRUNCATED' if native.get('dropped_events', 0) else
                   'NOT_REACHED' if selection is not None and not native['total_events'] else 'PASS',
            namespace='this native invocation only', source_sha256=source_hash,
            function=function, selections=selections, native=native, exhaustive=False,
            evidence=dict(native_sha256=digest(output / 'native.json'), helpers=tools))
        save(output / 'answer.json', answer)
        record.update(status=answer['status'], source_unchanged=True, fasls_written=False)
        return answer
    except BaseException:
        (output / 'failure.txt').write_text(traceback.format_exc())
        raise
    finally: save(output / 'run.json', record)
