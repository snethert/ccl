from pathlib import Path
HERE=Path(__file__).resolve().parent

def patch(s,replace):
 s=replace(s,'(defun b-special-symbol (symbol)\n', '''(defun b-special-symbol (symbol)
  (let ((pair (assoc symbol '((ccl::*interrupt-level* . "interrupt_level") (ccl::%wasm-gc-service% . "gc_service") (ccl::%wasm-interrupt-service% . "interrupt_service")))))
    (when pair (pushnew (cdr pair) *b-symbols* :test #'equal)
      (return-from b-special-symbol (b-wat "(global.get $symbol_~a)" (cdr pair)))))
''')
 s=s.replace("ccl::%restarts% *debugger-hook*)", "ccl::%restarts% *debugger-hook* ccl::*interrupt-level*)")
 s=replace(s,'                   (svref (cons', '''                   ((ccl::without-interrupts ccl::with-interrupts-enabled)
                    (walk `(unwind-protect (let* ((ccl::*interrupt-level* ,(if (eq (car x) 'ccl::without-interrupts) -1 0))) ,@(mapcar #'walk (cdr x))) (%wasm-poll))))
                   (ccl::%interrupt-poll (unless (null (cdr x)) (refuse :poll-arity)) '(%wasm-poll))
                   (svref (cons''')
 s=replace(s, "(member head '(%wasm-make-restart", "(and (eq head '%wasm-poll) (zerop n)) (member head '(%wasm-make-restart")
 # Intercept before the field/restart branch, whose arity must not apply.
 s=replace(s,'      (ccl::call\n       (when', '''      (ccl::call
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (eq (first (ccl::acode-operands (first args))) '%wasm-poll))
         (unless (and (null (third args)) (equal (second args) '(nil nil))) (refuse :poll-arity))
         (return-from b-multiple (b-poll)))
       (when''')
 s=replace(s,'(handler condition &optional second-argument)', '(handler condition &optional second-argument no-arguments)')
 s=replace(s,'(if second-argument (list condition second-argument) (list condition))', '(if no-arguments nil (if second-argument (list condition second-argument) (list condition)))')
 return s+'\n'+(HERE/'poll.lisp').read_text()
