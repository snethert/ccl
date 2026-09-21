from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
def replace(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)
def generate():
    text = (ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
    text = replace(text, '(defun b-scalar (ir)', '(defvar *bootstrap-front-end* nil)\n\n(defun b-scalar (ir)')
    text = replace(text, '(ccl::typed-form\n       (unless', "(ccl::typed-form\n       (when *bootstrap-front-end*\n         ;; NX1's optional third operand requests a runtime type check.\n         ;; Do not erase a check which the target cannot yet implement.\n         (when (third args) (refuse :bootstrap-typecheck))\n         (return-from b-scalar-inner (b-scalar (second args))))\n       (unless")
    text = replace(text, '(ccl::%decls-body (b-multiple (first args)))', '(ccl::typed-form\n       (if *bootstrap-front-end*\n         (progn\n           (when (third args) (refuse :bootstrap-typecheck))\n           (b-multiple (second args)))\n         (b-multiple (make-b-raw-code :text (b-scalar ir)))))\n      (ccl::%decls-body (b-multiple (first args)))')
    text = replace(text, '(ccl::list\n       (b-raw-code-text', '''((not)
       (unless (and *bootstrap-front-end* (= (length args) 2)
                    (member (ccl::acode-immediate-operand (first args)) '(:eq :ne)))
         (refuse :bootstrap-not))
       (b-wat "(if (result i32) (i32.~a ~a (i32.const 77825)) (then (i32.const 77838)) (else (i32.const 77825)))"
              (if (eq (ccl::acode-immediate-operand (first args)) :eq) "eq" "ne")
              (b-scalar (second args))))
      (ccl::list
       (b-raw-code-text''')
    text = replace(text, '((ccl::call ccl::values', '((ccl::builtin-call ccl::call ccl::values')
    text = replace(text, '(ccl::call\n       (when', '''(ccl::builtin-call
       (unless *bootstrap-front-end* (refuse :bootstrap-builtin))
       (let ((index (ccl::acode-fixnum-form-p (first args))))
         (unless (and index (<= 0 index) (< index (length ccl::%builtin-functions%)))
           (refuse :bootstrap-builtin-index))
         (b-call (ccl::make-acode (ccl::%nx1-operator ccl::immediate)
                                 (elt ccl::%builtin-functions% index))
                 (second args))))
      (ccl::call
       (when''')
    text = replace(text, '(ccl::eq\n       (unless', '(ccl::eq\n       (when *bootstrap-front-end* (return-from b-scalar-inner (bootstrap-eq args)))\n       (unless')
    text = replace(text, '((car cdr ccl::%car ccl::%cdr rplaca rplacd ccl::%rplaca ccl::%rplacd)', '((car cdr ccl::%car ccl::%cdr rplaca rplacd ccl::%rplaca ccl::%rplacd ccl::set-car ccl::set-cdr)')
    text = replace(text, "(carp (member op '(car rplaca ccl::%car ccl::%rplaca)))", "(carp (member op '(car rplaca ccl::%car ccl::%rplaca ccl::set-car)))")
    text = replace(text, 'p offset v p))))) s)))))))', "p offset v (if (member op '(ccl::set-car ccl::set-cdr)) v p)))))) s)))))))")
    return text + '\n' + (HERE/'entry.lisp').read_text()
