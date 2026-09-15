;;; A private copy of the existing inspector, with one same-execution hook.
(defpackage :ccl-seed-functions (:use :cl))
(in-package :ccl-seed-functions)
(defvar *calls* 0)
(defvar *inspection-functions* nil)

(defun export-functions (functions ids)
  (incf *calls*)
  (unless (= *calls* 1) (error "SEED-EXPORT-REPEATED"))
  (setf *inspection-functions*
        (mapcar (lambda (fn) (cons (or (gethash fn ids) (error "SEED-INSPECTION-ID")) fn)) functions))
  (when (ccl:getenv "SEED_ONLY_RETAIN") (return-from export-functions nil))
  (let ((ccl-complete-census::*owner* ccl:*current-process*)
        (ccl-complete-census::*serial* 0)
        (ccl-complete-census::*parents* nil)
        (ccl-complete-census::*native-functions* (make-hash-table :test #'eq))
        (ccl-complete-census::*pending-functions* nil)
        (ccl-startup-census::*dependency-identities* (make-hash-table :test #'eq))
        (ccl-startup-census::*dependency-counter* 0))
    (with-open-file (s (ccl:getenv "SEED_FUNCTION_BYTES") :direction :output :if-exists :error :external-format :utf-8)
      (let ((ccl-complete-census::*output* s))
        (ccl-complete-census::emit
         "inspection-map"
         "entries" (loop for fn in functions collect
                      (ccl-startup-census::object
                       "inspection_id" (or (gethash fn ids) (error "SEED-INSPECTION-ID"))
                       "function" (ccl-complete-census::function-id fn))))
        (let ((aliases nil))
          (maphash
           (lambda (original cell)
             (push (ccl-startup-census::object
                    "original" (ccl-startup-census::dependency-id original)
                    "original_name" (ccl-dispatch-registry::name-data original)
                    "cell" (ccl-startup-census::dependency-id cell)
                    "cell_name" (ccl-dispatch-registry::name-data cell)) aliases))
           ccl::%setf-function-names%)
          (ccl-complete-census::emit "setf-aliases" "entries" (nreverse aliases)))
        (ccl-complete-census::drain-functions)
        (ccl-complete-census::emit "complete" "inspected_functions" (length functions))))))

(defun run ()
  (let ((source nil) (replacements 0) (*calls* 0)
        (original (symbol-function 'ccl-image-inventory::inspect-image)))
    (with-open-file (s (ccl:getenv "SEED_INSPECTOR_SOURCE"))
      (let ((*package* (find-package :ccl-image-inventory)))
        (loop for form = (read s nil :eof) until (eq form :eof) do
          (when (and (consp form) (eq (car form) 'defun)
                     (eq (cadr form) 'ccl-image-inventory::inspect-image))
            (when source (error "SEED-INSPECTOR-DUPLICATE"))
            (setf source form)))))
    (unless source (error "SEED-INSPECTOR-MISSING"))
    (labels ((rewrite (form)
               (cond
                 ((equal form '(setf ccl-image-inventory::functions
                                     (nreverse ccl-image-inventory::functions)))
                  (incf replacements)
                  `(progn ,form (export-functions ccl-image-inventory::functions ccl-image-inventory::ids)))
                 ((consp form) (cons (rewrite (car form)) (rewrite (cdr form))))
                 (t form))))
      (let ((body (rewrite (cddr source))))
        (unless (= replacements 1) (error "SEED-INSPECTOR-HOOK-COUNT"))
        (funcall (compile nil (cons 'lambda body)) (ccl:getenv "SEED_IMAGE_INVENTORY"))))
    (unless (and (= *calls* 1) (eq original (symbol-function 'ccl-image-inventory::inspect-image))
                 (not ccl::*startup-census-hook*))
      (error "SEED-INSPECTOR-NATIVE-STATE"))
    (format t "SEED-FUNCTION-EXPORT-PASS~%")))
