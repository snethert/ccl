#!/usr/bin/env python3
"""Capture a single clean CCL process with fs_usage; only the tracer uses sudo."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid


def capture(kernel, image, source, output):
    kernel, image, source, output = [p.resolve() for p in (kernel, image, source, output)]
    output.mkdir(parents=True, exist_ok=True)
    if any(output.iterdir()): raise ValueError('trace output must be new and empty')
    if not kernel.is_file() or not image.is_file(): raise ValueError('kernel/image missing')
    shutil.copyfile(__file__, output / 'trace-startup.py')
    control = output / 'trace-control-read.txt'; control.write_text('CCL external trace coverage control\n')
    native_control = output / 'native-control-read.txt'
    native_control.write_text('CCL post-exec trace coverage control\n')
    # A unique command name lets ktrace select the new executable as well as
    # the held launcher's PID. Retain the byte-identical executable and its hash.
    traced_kernel = output / ('ccltr' + uuid.uuid4().hex[:8])
    shutil.copyfile(kernel, traced_kernel); traced_kernel.chmod(0o755)
    env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LANG': 'C', 'LC_ALL': 'C',
           'CCL_DEFAULT_DIRECTORY': str(source)}
    expression = ('(progn (with-open-file (s ' + json.dumps(str(native_control)) + ') '
                  '(assert (equal (read-line s) "CCL post-exec trace coverage control"))) '
                  '(format t "CCL-TRACE-PID ~d~%CCL-CLEAN-START-COMPLETE~%" (ccl::getpid)) '
                  '(finish-output) (ccl:quit))')
    client = [str(traced_kernel), '--image-name', str(image), '--no-init', '--batch', '--eval', expression]
    # The held process keeps its PID across exec. Attach the tracer before
    # reading the coverage marker or starting any native CCL code.
    launcher = ('import os,sys; '
                'assert sys.stdin.buffer.read(1)==b"G"; '
                'open(sys.argv[1],"rb").read(); '
                'os.execve(sys.argv[2],sys.argv[2:],dict(os.environ))')
    report = {'version': 2, 'status': 'UNAVAILABLE', 'client_command': client,
              'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'inputs_sha256': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [kernel, traced_kernel, image, Path(__file__)]},
              'kernel_copy_byte_identical': kernel.read_bytes() == traced_kernel.read_bytes(),
              'environment': env, 'scope': 'One clean native image startup, external file operations only'}
    with (output / 'client.log').open('wb') as client_log, (output / 'fs_usage.log').open('wb') as trace_log:
        report['launcher_command'] = [sys.executable, '-c', launcher, str(control)] + client
        child = subprocess.Popen(report['launcher_command'],
                                 cwd=source, env=env, stdin=subprocess.PIPE,
                                 stdout=client_log, stderr=subprocess.STDOUT)
        prefix = [] if os.geteuid() == 0 else ['/usr/bin/sudo', '-n']
        command = prefix + ['/usr/bin/fs_usage', '-w', '-f', 'filesys', '-f', 'exec',
                            '-t', '8', str(child.pid), traced_kernel.name]
        report.update({'pid': child.pid, 'tracer_command': command})
        tracer = None
        try:
            tracer = subprocess.Popen(command, stdout=trace_log, stderr=subprocess.STDOUT)
            time.sleep(0.5)
            if tracer.poll() is not None:
                report['reason'] = 'fs_usage could not remain active; retain its permission/error output'
            else:
                child.stdin.write(b'G'); child.stdin.flush(); child.stdin.close()
                report['client_exit_code'] = child.wait(timeout=20)
                report['tracer_exit_code'] = tracer.wait(timeout=20)
                client_log.flush(); trace_log.flush()
                raw = (output / 'fs_usage.log').read_text(errors='replace')
                client_text = (output / 'client.log').read_text(errors='replace')
                completed = 'CCL-CLEAN-START-COMPLETE' in client_text
                native_pid = re.search(r'^CCL-TRACE-PID (\d+)$', client_text, re.M)
                same_pid = bool(native_pid and int(native_pid[1]) == child.pid)
                loss = bool(re.search(r'(?i)(lost\s+\d+|\d+\s+events?\s+(?:lost|dropped)|buffer\s+overrun)', raw))
                control_seen = str(control) in raw
                native_control_seen = str(native_control) in raw
                image_seen = str(image) in raw
                report.update({'control_path_observed': control_seen, 'image_path_observed': image_seen,
                               'native_control_path_observed': native_control_seen,
                               'native_pid': int(native_pid[1]) if native_pid else None,
                               'native_pid_matches_launcher': same_pid,
                               'event_loss_reported': loss, 'completion_marker': completed})
                good = (report['client_exit_code'] == 0 and report['tracer_exit_code'] == 0
                        and completed and control_seen and native_control_seen and image_seen
                        and same_pid and report['kernel_copy_byte_identical'] and not loss)
                report['status'] = 'CAPTURED_REQUIRES_RECONCILIATION' if good else 'FAIL'
                if not good: report['reason'] = 'missing completion, coverage, image open, or clean trace termination'
        except BaseException as exc:
            report['status'] = 'FAIL'
            report['reason'] = type(exc).__name__ + ': ' + str(exc)
        finally:
            for process in [child, tracer]:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=5)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
    report['artifacts'] = [{'path': p.name, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                           for p in sorted(output.iterdir()) if p.is_file()]
    (output / 'trace.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ['kernel', 'image', 'source', 'output']: parser.add_argument('--' + field, type=Path, required=True)
    args = parser.parse_args()
    report = capture(args.kernel, args.image, args.source, args.output)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report['status'] == 'CAPTURED_REQUIRES_RECONCILIATION' else 2 if report['status'] == 'UNAVAILABLE' else 1)
