from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
def generate(stage='or'):
    s=(ROOT/'compiler/WASM32/wasm32-backend.lisp').read_text()
    def edit(old,new):
        nonlocal s
        assert s.count(old)==1,(old,s.count(old))
        s=s.replace(old,new)
    edit('(or (integerp x) (floatp x) (characterp x) (consp x)', '(or (and *bootstrap-front-end* (symbolp x))\n           (integerp x) (floatp x) (characterp x) (consp x)')
    edit("(cond ((member (first args) '(condition serious-condition", "(cond ((and *bootstrap-front-end* (pool-literal-p (first args)))\n              (pool-load (first args)))\n             ((member (first args) '(condition serious-condition")
    if stage!='constants':
        edit('(defvar *bootstrap-front-end* nil)', '(defvar *bootstrap-front-end* nil)\n(defvar *bootstrap-symbols* nil)\n(defvar *bootstrap-callees* nil)\n(defvar *bootstrap-dynamic-call* nil)')
        edit('(let ((*bootstrap-front-end* t)', '(let ((*bootstrap-front-end* t)\n        (*bootstrap-symbols* nil)\n        (*bootstrap-callees* nil)\n        (*bootstrap-dynamic-call* nil)')
        edit('(defun b-special-symbol (symbol)\n', '(defun b-special-symbol (symbol)\n  (when *bootstrap-front-end*\n    (return-from b-special-symbol (bootstrap-symbol symbol)))\n')
        edit('(defun b-keyword (key)\n', '(defun b-keyword (key)\n  (when *bootstrap-front-end*\n    (return-from b-keyword (bootstrap-symbol key)))\n')
        edit('(defun b-symbol (name)\n', '(defun b-symbol (name)\n  (when *bootstrap-front-end*\n    (pushnew name *bootstrap-callees*)\n    (return-from b-symbol (bootstrap-symbol name)))\n')
        edit('(list :pool (cdr (assoc afunc', '(list :symbols (copy-list *bootstrap-symbols*)\n            :callees (copy-list *bootstrap-callees*)\n            :pool (cdr (assoc afunc')
        edit('(defun b-call (callee argument-list &optional local-self)\n', '(defun b-call (callee argument-list &optional local-self)\n  (when (and *bootstrap-front-end* (not local-self)\n             (not (eq (ccl::acode-operator-name (ccl::acode-operator callee)) \'ccl::immediate)))\n    (setq *bootstrap-dynamic-call* t))\n')
        edit('(setf (getf (first modules) :children) (rest modules))', '(setf (getf (first modules) :children) (rest modules))\n      (when *bootstrap-front-end*\n        (setf (getf (first modules) :dependencies) (copy-list *bootstrap-callees*)\n              (getf (first modules) :dynamic-call) *bootstrap-dynamic-call*))')
        edit('(defun b-multiple-call (callee forms)\n', '(defun b-multiple-call (callee forms)\n  (when *bootstrap-front-end* (setq *bootstrap-dynamic-call* t))\n')
        s+='\n'+(HERE/'symbols.lisp').read_text()
    if stage=='or':
        edit('(ccl::%decls-body (b-multiple (first args)))', '(ccl::%decls-body (b-multiple (first args)))\n      (ccl::or\n       (unless *bootstrap-front-end* (refuse :or))\n       (bootstrap-or (first args)))')
        edit('ccl::multiple-value-prog1 ccl::prog1 ccl::if ccl::let', 'ccl::multiple-value-prog1 ccl::prog1 ccl::or ccl::if ccl::let')
        s+='\n'+(HERE/'or.lisp').read_text()
    return s
