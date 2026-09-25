"""Trace cross-loading and capture a bounded native stack on a stalled load."""
from pathlib import Path
import sys
import product
import storage
run = product.module('definition_driver', product.HERE / 'run.py')

c = product.c
command = c.command

def execute(argv, log, env=None, **kwargs):
    if Path(sys.argv[1]) / 'load-prefix.lisp' in argv:
        path = Path(sys.argv[1]) / 'load-prefix.lisp'
        path.write_text('''(in-package "CCL")
(setq *load-verbose* t)
(let ((target *current-process*))
  (process-run-function "loader watchdog"
    (lambda () (sleep 120)
      (process-interrupt target
        (lambda () (print-call-history :count 30) (force-output) (quit 2))))))
''' + path.read_text())
    return command(argv, log, env, **kwargs)

if __name__ == '__main__':
    c.command = execute
    with storage.lease([Path(sys.argv[1])]):
        run.run(Path(sys.argv[1]).resolve())
