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
  (core-compile-file "ccl:level-1;l1-error-system.lisp"))

;;; Keep the file compiler's lexical macro environment while selecting the
;;; runtime helpers it emits; macro expander functions are not runtime APIs.
(dolist (entry '(("ccl:lib;level-2.lisp" ccl::prepare-to-destructure)
                 ("ccl:level-1;l1-utils.lisp" ccl::check-keywords adjoin caddr cdddr)
                 ("ccl:lib;lists.lisp" cadddr)))
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
