"""Dcode's literal program errors reuse the rooted condition constructor."""
from pathlib import Path
import importlib.util

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('gcd_backend', HERE.parent / 'bootstrap-gcd/backend.py')
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)
prior_generate = parent.generate


def generate():
    text = prior_generate()
    needle = "    (cond ((eq name 'make-condition)"
    assert text.count(needle) == 1
    return text.replace(needle, """    (cond ((and (eq name 'assoc) (= (length forms) 2))
           (b-call (bootstrap-constant 'ccl::asseql) (list forms nil)))
          ((eq name 'ccl::signal-program-error)
           (multiple-value-bind (control constant) (bootstrap-immediate (car forms))
             (when (and constant (stringp control))
               (let ((*b-tail-position* nil) (*b-producer-target* nil))
                 (b-wat "(drop ~a)"
                   (bootstrap-operands forms
                     (lambda (values)
                       (let ((arguments
                               (reduce (lambda (value tail)
                                         (b-cons (make-b-raw-code :text value)
                                                 (make-b-raw-code :text tail)))
                                       (cdr values) :from-end t
                                       :initial-value "(i32.const 77825)")))
                         (b-signal (make-b-raw-code :text
                                     (bootstrap-condition 2108
                                       (list (car values) arguments))) t)))))))))
          ((eq name 'make-condition)""")


parent.generate = generate
arch = parent.arch
source_files = parent.source_files
runtime_files = parent.runtime_files
proposal = parent.proposal
