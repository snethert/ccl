(in-package :wasm32-compiler)

;;; Retain the file's initialization order and original initializer forms.
;;; DEFSTRUCT definitions were compiled in the whole-file environment. Their
;;; foreign-type class registrations and method assignments execute here.
(defun namespace-foreign-startup-form ()
  (let ((*package* (find-package :ccl)) (forms nil))
    (labels ((select-form (form)
               (when (consp form)
                 (case (car form)
                   ((progn) (mapc #'select-form (cdr form)))
                   ((eval-when) (mapc #'select-form (cddr form)))
                   ((defvar)
                    (when (member (second form)
                            '(ccl::*host-ftd* ccl::*target-ftd* ccl::*foreign-type-classes*
                              ccl::*void-foreign-type* ccl::*unsigned-integer-types*
                              ccl::*signed-integer-types* ccl::*bool-type*
                              ccl::*values-type-okay* ccl::*auxiliary-type-definitions*))
                      (push `(makunbound ',(second form)) forms)
                      (push form forms)))
                   ((ccl::find-or-create-foreign-type-class) (push form forms))
                   ((ccl::def-foreign-type-class)
                    (let ((expansion (macroexpand-1 form)))
                      (assert (eq (car expansion) 'progn))
                      (select-form (second expansion))))
                   ((ccl::def-foreign-type-method)
                    (let ((expansion (macroexpand-1 form)))
                      (assert (and (eq (car expansion) 'progn)
                                   (eq (car (third expansion)) 'setf)))
                      (push (third expansion) forms)))))))
      (call-with-target
       (lambda ()
         (with-open-file (stream "ccl:lib;foreign-types.lisp")
           (loop for form = (read stream nil :end) until (eq form :end)
                 do (select-form form))))))
    `(defun namespace-foreign-initialize ()
       ,@(nreverse forms)
       (ccl::install-standard-foreign-types ccl::*host-ftd*)
       t)))
