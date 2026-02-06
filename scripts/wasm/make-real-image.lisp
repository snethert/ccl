;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; Build a WASM32 heap image with a wired toplevel function.

(in-package "CCL")

(defparameter *wasm-image-policy*
  '(:toplevel-function toplevel-loop
    :compiled-modules-var %wasm-compiled-modules%)
  "Minimal policy for WASM root images.")

(defun wasm32-target-p ()
  (member :wasm32-target *features*))

(defun ensure-wasm32-target ()
  (unless (wasm32-target-p)
    (error "This script must run under a WASM32-target CCL (:wasm32-target missing).")))

(defun repo-root-from-script ()
  (let* ((script (or *load-truename*
                     (probe-file "scripts/wasm/make-real-image.lisp"))))
    (unless script
      (error "Cannot determine repository root"))
    (truename (merge-pathnames "../../" (make-pathname :name nil :type nil :defaults script)))))

(defun ensure-wasm-toplevel ()
  (let ((sym (find-symbol "%TOPLEVEL-FUNCTION%" "CCL")))
    (unless sym
      (error "Missing CCL:%TOPLEVEL-FUNCTION% symbol; cannot seed image toplevel."))
    (set sym #'toplevel-loop)
    sym))

(defun validate-compiled-modules ()
  (when (boundp '%wasm-compiled-modules%)
    (let ((val %wasm-compiled-modules%))
      (unless (or (null val) (consp val))
        (error "Expected %wasm-compiled-modules% to be NIL or a list, got ~s" val)))))

(defun apply-wasm-image-policy ()
  (ensure-wasm-toplevel)
  (validate-compiled-modules)
  t)

(defun parse-argv (argv)
  (let ((out nil)
        (args argv)
        (seen-delimiter nil))
    (loop while args do
      (let ((arg (pop args)))
        (cond
          ((string= arg "--")
           (setf seen-delimiter t))
          ((string= arg "--output")
           (let ((val (pop args)))
             (unless val
               (error "Missing value for --output"))
             (push (cons :output val) out)))
          ((or (string= arg "-h") (string= arg "--help"))
           (push (cons :help t) out))
          (seen-delimiter
           (error "Unknown argument: ~s" arg))
          (t
           nil))))
    out))

(defun usage ()
  (format t "~&Usage: ccl --no-init --batch -l scripts/wasm/make-real-image.lisp -- --output PATH~%")
  (format t "Builds a WASM32 heap image with %toplevel-function% seeded to toplevel-loop.~%"))

(defun main ()
  (let* ((argv (parse-argv ccl:*command-line-argument-list*)))
    (when (cdr (assoc :help argv))
      (usage)
      (quit 0))
    (ensure-wasm32-target)
    (apply-wasm-image-policy)
    (let* ((root (repo-root-from-script))
           (output (or (cdr (assoc :output argv))
                       (namestring (merge-pathnames "doc/wasm/root.image" root)))))
      (format t "~&WASM image policy: ~s~%" *wasm-image-policy*)
      (format t "~&Saving WASM image to ~a~%" output)
      (save-application output :toplevel-function #'toplevel-loop)
      (finish-output))))

(main)
(ccl:quit)
