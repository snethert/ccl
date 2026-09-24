(in-package :wasm32-compiler)

;;; Use the real file environments for the numeric implementation. An entry
;;; refused here must not fall back to its old standalone compilation.
(dolist (path '("ccl:level-1;l1-error-system.lisp" "ccl:level-1;l1-error-signal.lisp" "ccl:level-0;l0-numbers.lisp" "ccl:level-0;l0-float.lisp" "ccl:level-1;l1-numbers.lisp" "ccl:level-1;l1-aprims.lisp" "ccl:level-1;l1-clos-boot.lisp" "ccl:level-1;l1-dcode.lisp"))
  (if (equal path "ccl:level-1;l1-aprims.lisp")
    (let ((saved (loop for name being the hash-keys of *core-native-functions*
                      using (hash-value function) collect (cons name function))))
      (core-compile-file path t)
      ;; Keep each existing oracle paired with the source definition its
      ;; target module uses. L1-APRIMS redefines some earlier numeric names.
      (dolist (entry saved)
        (unless (eq (car entry) 'ccl::lfun-keyvect)
          (setf (gethash (car entry) *core-native-functions*) (cdr entry)))))
    (core-compile-file path t)))
(let ((previous *core-records*) (names nil))
  (dolist (path '("ccl:level-1;l1-error-system.lisp" "ccl:level-1;l1-error-signal.lisp" "ccl:level-0;l0-numbers.lisp" "ccl:level-0;l0-float.lisp"
                  "ccl:level-0;l0-bignum32.lisp" "ccl:level-1;l1-numbers.lisp" "ccl:level-1;l1-aprims.lisp" "ccl:level-1;l1-clos-boot.lisp" "ccl:level-1;l1-dcode.lisp"))
    (if (equal path "ccl:level-1;l1-error-signal.lisp")
      (handler-case (core-compile-file path)
        (error (condition)
          ;; Preserve the existing foreign-reader boundary. Only definitions
          ;; emitted before it are candidates; this file is not complete.
          (format t "KERNEL-RESTART-FILE-STOP ~a~%" condition)))
      (core-compile-file path)))
  (loop for tail on *core-records* until (eq tail previous) do
    (let ((name (second (car tail))))
      (when (and name (symbolp name))
        (pushnew name names)
        ;; The 64-bit image supplies the mathematical bignum counterpart.
        ;; Other entries use the same file's native compile, not a later
        ;; definition that happens to occupy its symbol in the saved image.
        (when (and (equal (first (car tail)) "ccl:level-0;l0-bignum32.lisp")
                   (fboundp name))
          (setf (gethash name *core-native-functions*) (fdefinition name))))))
  (setq *core-candidates*
        (remove-if (lambda (row) (member (second (first row)) names))
                   *core-candidates*)))

(core-compile-file "ccl:level-1;l1-sort.lisp" t)
(core-compile-file "ccl:level-1;l1-sort.lisp")

(core-compile-file "ccl:level-0;l0-aprims.lisp" t)
(core-compile-file "ccl:level-0;l0-aprims.lisp")
(core-compile-file "ccl:lib;chars.lisp" t)
(core-compile-file "ccl:lib;chars.lisp")

(core-compile-file "ccl:lib;sequences.lisp" t)
(core-compile-file "ccl:lib;sequences.lisp")

(core-compile-file "ccl:level-1;l1-clos.lisp" t)
(core-compile-file "ccl:level-1;l1-clos.lisp")

;;; Target definitions of native LAP entries.  The 64-bit image supplies the
;;; oracle for the entries whose contract does not depend on word size; the
;;; others are compared through arch probes with a native reference.
(let ((previous *core-records*))
  (core-compile-file "ccl:level-0;WASM32;w32-lap.lisp")
  (loop for tail on *core-records* until (eq tail previous) do
    (let ((name (second (car tail))))
      (when (and name (symbolp name)
                 (member name '(ccl::%ilogcount ccl::%fixnum-intlen ccl::%iash
                                ccl::%fixnum-truncate ccl::fast-mod
                                ccl::%init-gvector ccl::%copy-gvector-to-gvector

                                ccl::%symptr->symbol ccl::true ccl::false
                                ccl::single-float-bits ccl::double-float-bits
                                ccl::double-float-from-bits
                                ccl::%double-float-sign ccl::%short-float-sign
                                ccl::%double-float-exp ccl::set-%double-float-exp
                                ccl::%short-float-exp
                                ccl::%%double-float-abs! ccl::%double-float-negate!
                                ccl::%integer-decode-double-float
                                ccl::%make-float-from-fixnums ccl::%%scale-dfloat!
                                ccl::%short-float->double-float
                                ccl::%truncate-double-float->fixnum
                                ccl::%truncate-short-float->fixnum
                                ccl::%round-nearest-double-float->fixnum
                                ccl::%round-nearest-short-float->fixnum
                                ccl::%double-float-sqrt! ccl::%set-hash-table-vector-key))
                 (fboundp name))
        (setf (gethash name *core-native-functions*) (fdefinition name))))))

(in-package :wasm32-compiler)

;;; Compile the complete file environment. Only CLASS-TYPEP joins this
;;; execution unit: internal macro expander names are not replacement CL
;;; function definitions, and do not displace the numeric oracle entries.
(let ((candidates *core-candidates*) (modules *core-modules*)
      (native (loop for name being the hash-keys of *core-native-functions*
                    using (hash-value function) collect (cons name function))))
  (core-compile-file "ccl:level-1;l1-typesys.lisp" t)
  (core-compile-file "ccl:level-1;l1-typesys.lisp")
  (let ((entry (find 'ccl::class-typep *core-candidates*
                     :key (lambda (row) (second (first row))))))
    (assert entry)
    (setq *core-candidates* (cons entry candidates)
          *core-modules* (cons (second entry) modules)))
  (dolist (entry native)
    (unless (eq (car entry) 'ccl::class-typep)
      (setf (gethash (car entry) *core-native-functions*) (cdr entry)))))

(defparameter *condition-default-modules* *core-modules*)
(defvar *condition-cpl-modules* nil)

(let ((*b-cpl-conditions* t) (*b-allocation-retry* t))
  (core-compile-file "ccl:level-0;WASM32;w32-prims.lisp")
  (core-compile-file "ccl:level-0;l0-pred.lisp")
  (core-compile-file "ccl:level-0;l0-def.lisp")
  (core-compile-file "ccl:level-0;l0-symbol.lisp")
  ;; The source reader stops earlier at an excluded host hook. Read the target
  ;; SIGNAL definition with the target reader; do not manufacture its body.
  (let ((*package* (find-package :ccl)))
    (with-open-file (stream "ccl:level-1;l1-readloop.lisp")
    (loop for line = (read-line stream nil nil) while line
          when (string= line "#+wasm32-target") do
            (let ((form (read stream nil nil)))
              (when (and (consp form) (eq (car form) 'defun)
                         (eq (cadr form) 'signal))
                (let ((path (merge-pathnames "signal-entry.lisp" *load-pathname*)))
                  (with-open-file (out path :direction :output :if-exists :supersede)
                    (format out "(in-package :ccl)~%")
                    (let ((*package* (find-package :ccl))) (prin1 form out)))
                  (core-compile-file path nil "ccl:level-1;l1-readloop.lisp"))
                (return))))))
  (handler-case (core-compile-file "ccl:level-1;l1-error-signal.lisp")
    (error (condition)
      (format t "CONDITION-FILE-STOP ~a~%" condition)))
  (core-compile-file "ccl:level-1;l1-clos-boot.lisp")
  (core-compile-file "ccl:level-1;l1-clos.lisp")
  (core-compile-file "ccl:level-1;l1-error-system.lisp")
  ;; Error-producing callees must use the same class path as their callers.
  ;; Keep each complete file environment; no per-function source substitutions.
  (dolist (path '("ccl:level-0;l0-numbers.lisp" "ccl:level-0;l0-float.lisp"
                  "ccl:level-0;l0-bignum32.lisp" "ccl:level-1;l1-numbers.lisp"
                  "ccl:level-0;WASM32;w32-lap.lisp"))
    (core-compile-file path)))

;;; Keep the file compiler's lexical macro environment while selecting the
;;; runtime helpers it emits; macro expander functions are not runtime APIs.
(dolist (entry '(("ccl:level-1;l1-typesys.lisp" ccl::ctype-p ccl::csubtypep ccl::cell-csubtypep-2 ccl::type= ccl::type-union2 ccl::type-intersection2)
                 ("ccl:level-0;l0-int.lisp" ccl::%integer-abs ccl::%integer-to-string ccl::%pr-integer ccl::print-bignum-2)
                 ("ccl:lib;numbers.lisp" gcd)
                 ("ccl:level-0;nfasload.lisp" ccl::%get-hashed-htab-symbol)
                 ("ccl:lib;sequences.lisp" make-string)
                 ("ccl:lib;level-2.lisp" ccl::prepare-to-destructure)
                 ("ccl:level-1;l1-utils.lisp" ccl::check-keywords adjoin caddr cdddr fdefinition symbol-function)
                 ("ccl:level-1;l1-aprims.lisp" funcall apply ccl::%badarg)
                 ("ccl:lib;lists.lisp" cadddr ldiff mapc mapcar maplist mapl mapcan mapcon ccl::map1)))
  (let ((previous *core-modules*) (*b-cpl-conditions* t) (*b-allocation-retry* t))
    (core-compile-file (car entry))
    (setq *core-modules*
          (append (loop for tail on *core-modules* until (eq tail previous)
                        for module = (car tail)
                        when (member (getf module :source-name) (cdr entry))
                          collect module)
                  previous))))

;; The most recent file environment wins; keep one definition per symbol.
(let ((seen (make-hash-table :test #'equal)))
  (setq *core-modules*
    (remove-if (lambda (module)
                 (let ((name (getf module :source-name)))
                   (when name
                     (if (gethash name seen) t
                       (progn (setf (gethash name seen) t) nil)))))
               *core-modules*)))

(setq *condition-cpl-modules*
      (set-difference *core-modules* *condition-default-modules* :test #'eq)
      *core-modules* *condition-default-modules*)
(dolist (module *condition-cpl-modules*)
  (setf (getf module :source-name)
        (ccl::maybe-setf-function-name (getf module :source-name))))

(let ((*b-cpl-conditions* t))
  (let ((answer (handler-case
                  (progn (call-with-target
                           (lambda ()
                             (compile-bootstrap-form
                               '(defun eq-initializer-probe () (ccl::%alloc-misc 22 74 nil))
                               "eq_initializer_probe" nil)))
                         :admitted)
                (unsupported-wasm32-code (condition) (unsupported-operation condition)))))
    (assert (eq answer :eq-vector-initial-element))
    (with-open-file (out (concatenate 'string (ccl:getenv "POOL_OUTPUT") "eq-initializer-refusal.sexp")
                         :direction :output :if-exists :supersede)
      (prin1 answer out))))
