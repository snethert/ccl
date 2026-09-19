"""Generated control/condition proposal for S1-LL19-a, never edits shared source."""
import importlib.util
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('apply_conditions',HERE.parent/'b-apply-errors/backend.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
replace=base.replace

def generate():
 s=base.generate()
 s=replace(s,"(defun b-special-symbol (symbol)\n",'''(defun b-special-symbol (symbol)
  (when (eq symbol 'ccl::%restarts%)
    (pushnew "condition_restarts" *b-symbols* :test #'equal)
    (return-from b-special-symbol "(global.get $symbol_condition_restarts)"))
''')
 s=replace(s,"(lambda-form (items form) '(ccl::%handlers%) 0)","(lambda-form (items form) '(ccl::%handlers% ccl::%restarts%) 0)")
 s=replace(s,"(*b-special-names* '(ccl::%handlers%))","(*b-special-names* '(ccl::%handlers% ccl::%restarts%))")
 s=replace(s,"(eq (first (ccl::acode-operands (second args))) 'ccl::%handlers%)","(member (first (ccl::acode-operands (second args))) '(ccl::%handlers% ccl::%restarts%))")
 s=replace(s,'(defun b-expand-conditions (form)', "(defun b-expand-conditions (form) (setq *b-restart-names* '(list cons function simple-vector integer fixnum or))")
 # Native condition expansion is still applied after validating user subforms.
 anchor='''                   ((handler-bind handler-case)'''
 s=replace(s,anchor,'''                   ((restart-case restart-bind)
                    (walk (b-expand-restart x #'walk #'lambda-list)))
                   (svref (cons '%wasm-svref (mapcar #'walk (cdr x))))
                   ((find-restart invoke-restart restart-name)
                    (when (and (consp (second x)) (eq (first (second x)) 'quote)) (pushnew (second (second x)) *b-restart-names*))
                    (cons (case (car x) (find-restart '%wasm-find-restart)
                                (invoke-restart '%wasm-invoke-restart) (restart-name '%wasm-restart-name))
                          (mapcar #'walk (cdr x))))
'''+anchor)
 s=replace(s,"(and (member head '(signal error)) (= n 1))", "(and (member head '(signal error)) (= n 1))\n                                       (member head '(%wasm-make-restart %wasm-find-restart %wasm-invoke-restart %wasm-restart-name %wasm-svref))")
 s=replace(s,"      (ccl::call\n       (when",'''      (ccl::call
       (when (and (eq (ccl::acode-operator-name (ccl::acode-operator (first args))) 'ccl::immediate)
                  (member (first (ccl::acode-operands (first args))) '(%wasm-make-restart %wasm-find-restart %wasm-invoke-restart %wasm-restart-name %wasm-svref)))
         (unless (and (null (third args)) (null (second (second args)))) (refuse :b-restart-spread))
         (return-from b-multiple (if (eq (first (ccl::acode-operands (first args))) '%wasm-svref) (b-svref (first (second args))) (b-restart-call (first (ccl::acode-operands (first args))) (first (second args))))))
       (when''')
 # Public readers compile to checked access through the class registry.
 s=replace(s, "                   (svref (cons", "                   ((type-error-datum type-error-expected-type cell-error-name) (cons (case (car x) (type-error-datum '%wasm-condition-datum) (type-error-expected-type '%wasm-condition-expected) (cell-error-name '%wasm-cell-name)) (mapcar #'walk (cdr x))))\n                   (svref (cons")
 s=s.replace('%wasm-restart-name %wasm-svref)', '%wasm-restart-name %wasm-svref %wasm-condition-datum %wasm-condition-expected %wasm-cell-name)')
 s=replace(s, "(b-restart-call (first (ccl::acode-operands (first args))) (first (second args)))", "(if (member (first (ccl::acode-operands (first args))) '(%wasm-condition-datum %wasm-condition-expected %wasm-cell-name)) (b-condition-field (first (ccl::acode-operands (first args))) (first (second args))) (b-restart-call (first (ccl::acode-operands (first args))) (first (second args))))")
 # Runtime is emitted only when the module needs it; its symbol is collected
 # before the import list is written.
 s=replace(s,'(entry-roots (b-runtime-roots', '(restart-runtime (when *b-restart-used* (b-restart-runtime)))\n           (entry-roots (b-runtime-roots')
 s=replace(s,'(write-string implicit-runtime s)','(write-string implicit-runtime s)\n             (when restart-runtime (write-string restart-runtime s))')
 # Non-keyword quoted restart names are owner-assigned symbols with an
 # injective package/name import key, never a case-folded spelling or fixnum.
 s=replace(s,"(pool-literal-p (second xs)) (assoc", "(pool-literal-p (second xs)) (member (second xs) *b-restart-names*) (assoc")
 s=replace(s,"((pool-literal-p (first args)) (pool-load (first args)))", "((pool-literal-p (first args)) (pool-load (first args)))\n             ((member (first args) *b-restart-names*) (b-restart-symbol (first args)))")
 # A fresh per-module flag; established before body emission.
 s=replace(s,'(defvar *b-condition-used* nil)','(defvar *b-condition-used* nil)\n(defvar *b-restart-used* nil)\n(defvar *b-restart-names* nil)')
 s=s.replace('(*b-condition-used* nil)', '(*b-condition-used* nil) (*b-restart-used* nil)')
 # Inactive restarts are control errors. Existing kind mappings are unchanged.
 s=replace(s,'(else (i32.const 156))))))))','(else (if (result i32) (i32.eq (local.get $kind) (i32.const 8)) (then (i32.const 284)) (else (i32.const 156))))))))))')
 s=replace(s,'(then (i32.const 284)) (else (i32.const 156))', '(then (i32.const 284)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 17)) (then (i32.const 124)) (else (i32.const 156))))')
 # Cons operands become roots before any handler can run; leaf entry is unchanged.
 a=s.index("      ((car cdr ccl::%car ccl::%cdr)\n",s.index('(defun b-scalar'))
 b=s.index('      (t (emit-expression ir))',a)
 s=s[:a]+"      ((car cdr ccl::%car ccl::%cdr rplaca rplacd ccl::%rplaca ccl::%rplacd)\n       (b-wat \"(block (result i32) ~a (i32.load (local.get $results)))\" (b-checked-cons-operation op args)))\n"+s[b:]
 s=replace(s,'((ccl::special-ref ccl::bound-special-ref) (b-wat "(call $special_read ~a)" (b-special-symbol (first args))))',
              '((ccl::special-ref ccl::bound-special-ref) (b-wat "(call $special_read_lisp ~a (local.get $top))" (b-special-symbol (first args))))')
 s=replace(s,'(write-string (b-dynamic-runtime) s)','(write-string (b-dynamic-runtime) s) (write-string (b-unbound-runtime) s)')
 for old,new in [('(undefined-function . 1024)','(undefined-function . 1024) (unbound-variable . 2048)'),
                 ('program-error undefined-function)', 'program-error undefined-function unbound-variable)')]:s=s.replace(old,new)
 s=replace(s,'(then (i32.const 124)) (else (i32.const 156))', '(then (i32.const 124)) (else (if (result i32) (i32.eq (local.get $kind) (i32.const 10)) (then (i32.const 8220)) (else (i32.const 156))))')
 s=replace(s,'(i32.eq (local.get $mask) (i32.const 1031))', '(i32.or (i32.eq (local.get $mask) (i32.const 1031)) (i32.eq (local.get $mask) (i32.const 2055)))')
 # The ordinary debugger service is activated explicitly in the production
 # TCR. Its hook executes generated Lisp with the hook masked and depth restored.
 s=replace(s,'(defun b-special-symbol (symbol)\n', '''(defun b-special-symbol (symbol)
  (when (eq symbol '*debugger-hook*)
    (pushnew "debugger_hook" *b-symbols* :test #'equal)
    (return-from b-special-symbol "(global.get $symbol_debugger_hook)"))
''')
 s=s.replace("'(ccl::%handlers% ccl::%restarts%)", "'(ccl::%handlers% ccl::%restarts% *debugger-hook*)")
 s=replace(s,'(defun b-discard-handler (handler condition)', '(defun b-discard-handler (handler condition &optional second-argument)')
 s=replace(s,'(b-call nil (list (list condition) nil) handler)', '(b-call nil (list (if second-argument (list condition second-argument) (list condition)) nil) handler)')
 s=replace(s,'(if fatal "(throw $call_error (i32.const 15))"', "(if fatal (concatenate 'string (b-debugger condition) \"(throw $call_error (i32.const 15))\")")
 s=replace(s,'(signal (b-signal (make-b-raw-code :text "(local.get $condition)") nil)))', '(signal (b-signal (make-b-raw-code :text "(local.get $condition)") nil))\n           (debugger (b-debugger "(local.get $condition)")))')
 s=replace(s,'(if (i32.eq (call $special_read ~a) (i32.const 77825)) (then (throw $call_error', '(if (i32.and (i32.ne (i32.load offset=192 (global.get $tcr)) (i32.const 1)) (i32.eq (call $special_read ~a) (i32.const 77825))) (then (throw $call_error')
 s=replace(s,'(write-string signal s)', '(write-string signal s) (write-string debugger s)')
 s += '\n'+(HERE/'debugger.lisp').read_text()
 s += '\n'+(HERE/'checks.lisp').read_text()
 s += '\n'+(HERE/'restarts.lisp').read_text()
 s=replace(s,'(defun b-implicit-runtime ()', '''(defun b-implicit-runtime ()
  (pushnew "error_message" *b-symbols* :test #'equal)
  (pushnew "expected_function" *b-symbols* :test #'equal)''')
 from objects import patch
 s=patch(s,replace)
 s=replace(s,'(call $implicit_error (i32.const 10) (local.get $top)) unreachable', '(call $implicit_error_details (i32.const 10) (local.get $top) (local.get $symbol) (i32.const 77825)) unreachable')
 from stacks import patch as stacks_patch
 s=stacks_patch(s,replace)
 s=replace(s,'(call $implicit_error (call $designator_error_kind (local.get $node)) (local.get $top))', '(call $implicit_error_details (call $designator_error_kind (local.get $node)) (local.get $top) (local.get $node) (i32.load offset=2 (global.get $symbol_expected_function)))')
 s=replace(s,'(call $implicit_error (i32.const 14) (local.get $top))', '(call $implicit_error_details (i32.const 14) (local.get $top) (local.get $node) (i32.const 77825))')

 # A missing catch is a control condition; damaged records remain fatal.
 from stacks import append_call_arg
 s=append_call_arg(s,'find_catch')
 s=replace(s,'(func $find_catch (param $tag i32)', '(func $find_catch (param $tag i32) (param $top i32)')
 s=replace(s,'(throw $call_error (i32.const 8)))\")', '(call $implicit_error (i32.const 8) (local.get $top)) unreachable)\")')
 # APPLY retains its evaluated list head; pass the whole improper list as native CCL's datum.
 s=replace(s,'(b-wat "(if (i32.ne (i32.and ~a (i32.const ~d)) (i32.const ~d)) (then (call $implicit_error (i32.const 5) (local.get $top)) unreachable))" node wasm32::fulltagmask wasm32::fulltag-cons)', '(b-wat "(if (i32.ne (i32.and ~a (i32.const ~d)) (i32.const ~d)) (then ~a))" node wasm32::fulltagmask wasm32::fulltag-cons (b-type-failure node \'list))')
 s=replace(s,'(defun b-checked-cdr (node)', '''(defun b-checked-cdr (node &optional whole-list) (when whole-list (pushnew "expected_proper_list" *b-symbols* :test #'equal))''')
 s=replace(s,"(b-type-failure node 'list))", "(if whole-list (b-wat \"(call $implicit_error_details (i32.const 5) (local.get $top) ~a (global.get $symbol_expected_proper_list)) unreachable\" whole-list) (b-type-failure node 'list)))")
 for variable in ('cursor','slow'):
  s=s.replace('(b-checked-cdr (b-local '+variable+'))', '(b-checked-cdr (b-local '+variable+') (b-wat "(i32.load offset=12 (local.get ~a))" evaluated))')
 from poll import patch as poll_patch
 s=poll_patch(s,replace)
 return s
