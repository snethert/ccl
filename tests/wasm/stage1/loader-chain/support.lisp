;;; Temporary bootstrap witness: select complete original DEFUN forms, with
;;; no body rewriting. The incomplete source files receive no file credit.
(in-package "WASM32-COMPILER")
(let* ((out (ccl:getenv "LOADER_OUTPUT"))
       (path "ccl:tests;wasm;stage1;loader-level0;package-support.lisp")
       (rows nil))
  (with-open-file (s path :direction :output :if-exists :supersede)
    (let ((*package* (find-package "CCL")) (*print-pretty* nil))
      (write '(in-package "CCL") :stream s) (terpri s)
      (call-with-target
       (lambda ()
         (with-open-file (input (concatenate 'string out "bignum-boundary.lisp"))
           (loop for form = (read input nil :end) until (eq form :end) do
             (when (and (consp form) (eq (car form) 'eval-when))
               (write form :stream s) (terpri s) (return))))
         (dolist (group
                   '(("ccl:level-0;nfasload.lisp" ccl::package-%local-nicknames
                      find-package ccl::set-package ccl::%find-pkg ccl::pkg-arg)
                     ("ccl:level-0;l0-misc.lisp" length list-length
                      ccl::%wasm-rwlock-state ccl::%wasm-rwlock-acquisition
                      ccl::%read-lock-rwlock-ptr ccl::%write-lock-rwlock-ptr
                      ccl::%unlock-rwlock-ptr ccl::%promote-rwlock
                      ccl::read-lock-rwlock ccl::write-lock-rwlock ccl::unlock-rwlock)
                     ("ccl:level-0;l0-pred.lisp" ccl::sequence-type packagep
                      arrayp characterp symbolp stringp ccl::base-string-p listp ccl::fixnump simple-vector-p ccl::register-istruct-cell integerp compiled-function-p ccl::macptrp floatp ccl::double-float-p ccl::short-float-p ccl::bignump rationalp realp numberp)
                     
                     ("ccl:level-0;l0-symbol.lisp" symbol-name ccl::get-type-predicate ccl::set-type-predicate ccl::%symbol-bits ccl::%global-macro-function)
                     ("ccl:level-1;l1-processes.lisp" ccl::read-write-lock-p
                      ccl::lock-acquisition-status ccl::clear-lock-acquisition-status)
                     ("ccl:lib;sequences.lisp" make-string)
                     
                     ("ccl:level-1;l1-dcode.lisp" ccl::standard-generic-function-p)
                     ("ccl:level-1;l1-utils.lisp" fdefinition symbol-function)
                     ("ccl:level-0;l0-numbers.lisp"
                      ccl::logand-2 ccl::logior-2 ccl::logxor-2 lognot minusp oddp evenp
                      truncate ccl::truncate-no-rem ccl::%unary-truncate ccl::xform-truncate
                      ccl::+-2 ccl::+-2-into ccl::<-2 ccl::>-2 ccl::%negate
                      ccl::=-2 ccl::>=-2 ccl::<=-2)
                     ("ccl:level-1;l1-numbers.lisp" + max min ccl::max-2 ccl::min-2)
                     ("ccl:level-1;l1-symhash.lisp" package-name ccl::pkg-arg-allow-deleted)))
           (let ((found nil))
             (with-open-file (source (first group))
               (loop for form = (read source nil :end) until (eq form :end) do
                 ;; Keep the complete numeric file's macro/require prelude.
                 ;; These original forms establish the compilation environment
                 ;; of the selected complete definitions; no body is rewritten.
                 (when (and (member (first group)
                                    '("ccl:level-0;l0-numbers.lisp" "ccl:level-1;l1-numbers.lisp")
                                    :test #'equal)
                            (consp form) (eq (car form) 'eval-when))
                   (write form :stream s) (terpri s))
                 ;; HASHENV defines the read-time constants used before HASH-TABLE-P.
                 ;; Preserve and evaluate the complete original prelude.
                 (when (and (equal (first group) "ccl:level-0;l0-hash.lisp")
                            (consp form) (eq (car form) 'eval-when))
                   (eval form)
                   (write form :stream s) (terpri s))
                 (when (and (consp form) (eq (car form) 'defun)
                            (member (second form) (cdr group)))
                   (assert (not (member (second form) found)))
                   (push (second form) found)
                   (write form :stream s) (terpri s)
                   (when (eq (second form) 'ccl::%wasm-rwlock-state)
                     (dolist (clause '((ccl::loader-rwlock-mutant-state
                                       (eq (zerop ccl::owner) (zerop ccl::depth)))
                                      (ccl::loader-rwlock-mutant-owner (typep ccl::owner 'fixnum))
                                      (ccl::loader-rwlock-mutant-depth (typep ccl::depth 'fixnum))))
                       (let ((mutant (subst t (second clause) (copy-tree form) :test #'equal)))
                         (assert (not (equal mutant form)))
                         (setf (second mutant) (first clause))
                         (write mutant :stream s) (terpri s))))
                   (when (null (set-difference (cdr group) found)) (return)))))
             (assert (null (set-difference (cdr group) found)))
             (push (list :object (cons "source" (first group))
                         (cons "definitions" (mapcar #'symbol-name (reverse found)))) rows))))))
    ;; Independent diagnostic copies, never published as production functions.
    (call-with-target
     (lambda ()
       (let ((*package* (find-package "CCL")))
         (with-open-file (input (concatenate 'string out "array-boundary.lisp"))
           (loop for form = (read input nil :end) until (eq form :end) do
             (when (and (consp form) (eq (car form) 'defun))
               (dolist (row '((ccl::%wasm-array-subscript ccl::loader-array-mutant-lower
                              (>= ccl::index 0))
                             (ccl::%wasm-array-subscript ccl::loader-array-mutant-upper
                              (< ccl::index ccl::dimension))
                             (ccl::%wasm-array-index ccl::loader-array-mutant-header
                              "(= (the fixnum (typecode array)) target::subtag-arrayH)")
                             (ccl::%wasm-array-index ccl::loader-array-mutant-rank
                              "(= (the fixnum (ccl::%svref array target::arrayH.rank-cell)) ccl::rank)")))
                 (when (eq (second form) (first row))
                   (let* ((clause (if (stringp (third row)) (read-from-string (third row)) (third row)))
                          (copy (subst t clause (copy-tree form) :test #'equal)))
                     (assert (not (equal copy form)))
                     (setf (second copy) (second row))
                     (write copy :stream s) (terpri s))))))))))

    (with-open-file (probes (concatenate 'string (ccl:getenv "LOADER_SOURCE") "packages.lisp"))
      (loop for line = (read-line probes nil nil) while line do (write-line line s))))
  (with-open-file (s (concatenate 'string out "package-origins.json")
                    :direction :output :if-exists :supersede)
    (ccl::wasm32-json (reverse rows) s) (terpri s))
  (multiple-value-bind (fasl modules warnings failure)
      (wasm32-compile-file path :output-file (concatenate 'string out "package-support.w32fsl"))
    (declare (ignore modules warnings))
    (assert (and fasl (not failure))))
  (dolist (name '("package-first" "package-second"))
    (multiple-value-bind (fasl modules warnings failure)
        (wasm32-compile-file (concatenate 'string "ccl:tests;wasm;stage1;loader-level0;" name ".lisp")
                            :output-file (concatenate 'string out name ".w32fsl"))
      (declare (ignore modules warnings))
      (assert (and fasl (not failure))))))
;;; Compilation-owned function constants may cross initializer boundaries,
;;; but neither native functions nor another compilation's xfunctions enter.
(in-package "WASM32-COMPILER")
(defvar ccl::*loader-test-literal* nil)
(let* ((out (ccl:getenv "LOADER_OUTPUT"))
       ;; FASLs retain the source name even without source-location notes.
       ;; Use the same stable logical pathname convention as the other files.
       (source "ccl:tests;wasm;stage1;loader-level0;literal-control.lisp")
       (fasl (concatenate 'string out "literal-control.w32fsl"))
       (publish (symbol-function 'wasm32-xfunction))
       (outer (list :outer-compilation))
       (*wasm32-fasl-functions* outer)
       (rows nil))
  (with-open-file (s source :direction :output :if-exists :supersede)
    (write-line "(defun ccl::loader-control-original (x) (+ x 1))" s))
  (unwind-protect
       (progn
         (setf (symbol-function 'wasm32-xfunction)
               (lambda (module)
                 (setq ccl::*loader-test-literal* (funcall publish module))))
         (multiple-value-bind (path modules warnings failure)
             (wasm32-compile-file source :output-file fasl)
           (declare (ignore modules warnings))
           (assert (and path (not failure)))))
    (setf (symbol-function 'wasm32-xfunction) publish))
  (assert (eq outer *wasm32-fasl-functions*))
  (with-open-file (s source :direction :output :if-exists :supersede)
    (write-line "(defun ccl::loader-invalid-literal () #.ccl::*loader-test-literal*)" s))
  (dolist (kind '("foreign-compilation" "native-function"))
    (when (equal kind "native-function")
      (setq ccl::*loader-test-literal* #'car))
    (let ((reason
            (handler-case
                (progn (wasm32-compile-file source :output-file fasl) nil)
              (unsupported-wasm32-code (condition) (unsupported-operation condition)))))
      (assert (eq reason :heap-constant))
      (assert (eq outer *wasm32-fasl-functions*))
      (push (list :object (cons "name" kind) (cons "reason" (string reason))
                  (cons "scope_restored" t)) rows)))
  (with-open-file (s (concatenate 'string out "literal-controls.json")
                     :direction :output :if-exists :supersede)
    (ccl::wasm32-json (reverse rows) s) (terpri s)))

;;; Each entry rejects a missing or extra operand at the new accessor boundary.
(in-package "WASM32-COMPILER")
(let* ((out (ccl:getenv "LOADER_OUTPUT"))
       (source "ccl:tests;wasm;stage1;loader-level0;definition-control.lisp")
       (fasl (concatenate 'string out "definition-control.w32fsl"))
       (rows nil))
  (dolist (name '(ccl::%wasm-function-bits ccl::lfun-bits))
    (dolist (arguments '(nil (a b c)))
      (with-open-file (s source :direction :output :if-exists :supersede)
        (let ((*package* (find-package "CCL")))
          (write '(in-package "CCL") :stream s) (terpri s)
          (write `(defun ccl::loader-invalid-bits (a b c)
                    (declare (ignorable a b c)) (,name ,@arguments)) :stream s)))
      (let ((reason
              (handler-case
                  (progn (wasm32-compile-file source :output-file fasl) nil)
                (unsupported-wasm32-code (condition) (unsupported-operation condition)))))
        (assert (eq reason :function-bits-arity))
        (push (list :object (cons "name" (symbol-name name))
                    (cons "arguments" (length arguments))
                    (cons "reason" (string reason))) rows))))
  (with-open-file (s (concatenate 'string out "compiler-controls.json")
                     :direction :output :if-exists :supersede)
    (ccl::wasm32-json (reverse rows) s) (terpri s)))

(ccl:quit)
