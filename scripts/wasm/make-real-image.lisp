;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; Build a WASM32 heap image with a wired toplevel function.

(in-package "CCL")

(defparameter *wasm-image-policy*
  '(:toplevel-function toplevel-loop
    :compiled-modules-var %wasm-compiled-modules%)
  "Minimal policy for WASM root images.")

(defun running-in-wasm-runtime-p ()
  #+wasm32-target t
  #-wasm32-target nil)

(defun wasm32-target-p ()
  (member :wasm32-target *features*))

(defun ensure-wasm32-target ()
  (unless (wasm32-target-p)
    (pushnew :wasm32-target *features*)
    (format t "~&Note: injecting :wasm32-target into *features* for this image build.~%")
    (finish-output)))

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
    ;; Keep TCR slot aligned so wasm toplevel write telemetry sees the same seed.
    (let ((tcr (%current-tcr)))
      (when tcr
        (%set-tcr-toplevel-function tcr (symbol-value sym))))
    sym))

(defun validate-compiled-modules ()
  (let ((sym (find-symbol "%WASM-COMPILED-MODULES%" "CCL")))
    (when (and sym (boundp sym))
      (let ((val (symbol-value sym)))
        (unless (or (null val) (consp val))
          (error "Expected %wasm-compiled-modules% to be NIL or a list, got ~s" val))))))

(defun ensure-save-application ()
  (unless (fboundp 'save-application)
    (ignore-errors (require "DUMPLISP")))
  (unless (fboundp 'save-application)
    (error "save-application is unavailable; ensure the DUMPLISP module is loaded.")))

(defun apply-wasm-image-policy ()
  (ensure-wasm-toplevel)
  (ensure-save-application)
  (validate-compiled-modules)
  t)

(defun parse-argv (argv)
  (let ((out nil)
        (args argv)
        (seen-delimiter nil))
    (loop while args do
      (let ((arg (pop args)))
        (cond
          ((string-equal arg "--")
           (setf seen-delimiter t))
          ((string-equal arg "--output")
           (let ((val (pop args)))
             (unless val
               (error "Missing value for --output"))
             (push (cons :output val) out)))
          ((string-equal arg "--modules")
           (let ((val (pop args)))
             (unless val
               (error "Missing value for --modules"))
             (push (cons :modules val) out)))
          ((string-equal arg "--manifest-out")
           (let ((val (pop args)))
             (unless val
               (error "Missing value for --manifest-out"))
             (push (cons :manifest-out val) out)))
          ((or (string-equal arg "-h") (string-equal arg "--help"))
           (push (cons :help t) out))
          (seen-delimiter
           (error "Unknown argument: ~s" arg))
          (t
           nil))))
    out))

(defun usage ()
  (format t "~&Usage: ccl --no-init --batch -l scripts/wasm/make-real-image.lisp -- --output PATH~%")
  (format t "       ccl --no-init --batch -l scripts/wasm/make-real-image.lisp -- --modules PATH --output PATH~%")
  (format t "       ccl --no-init --batch -l scripts/wasm/make-real-image.lisp -- --manifest-out PATH --output PATH~%")
  (format t "Builds a WASM32 heap image with %toplevel-function% seeded to toplevel-loop.~%")
  (format t "On non-WASM hosts, this delegates to node doc/wasm/js/make-real-image.mjs.~%")
  (format t "If :wasm32-target is missing, this script injects it into *features*.~%"))

(defun shell-quote (s)
  (let ((s (string s)))
    (with-output-to-string (out)
      (write-char #\' out)
      (dotimes (i (length s))
        (let ((ch (char s i)))
          (if (char= ch #\')
            (write-string "'\\''" out)
            (write-char ch out))))
      (write-char #\' out))))

(defun run-host-node-helper (output &key modules manifest-out)
  (let* ((root (repo-root-from-script))
         (node-script (merge-pathnames "doc/wasm/js/make-real-image.mjs" root))
         (modules (or modules (namestring (merge-pathnames "doc/wasm/wasm-runtime-modules.json" root))))
         (command (with-output-to-string (out)
                    (format out "node ~a --modules ~a --output ~a"
                            (shell-quote (namestring node-script))
                            (shell-quote modules)
                            (shell-quote output))
                    (when manifest-out
                      (format out " --manifest-out ~a" (shell-quote manifest-out)))))
         (process (run-program "/bin/sh"
                               (list "-lc" command)
                               :output *standard-output*
                               :error *error-output*))
         (status (external-process-status process))
         (exit-code (ccl::external-process-%exit-code process)))
    (unless (and (eq status :exited) (zerop exit-code))
      (error "Node helper failed with status ~s exit-code ~s" status exit-code))
    t))

(defun main ()
  (let* ((argv (parse-argv ccl:*command-line-argument-list*)))
    (when (cdr (assoc :help argv))
      (usage)
      (quit 0))
    (let* ((output (cdr (assoc :output argv)))
           (modules (cdr (assoc :modules argv)))
           (manifest-out (cdr (assoc :manifest-out argv)))
           (wasm-runtime (running-in-wasm-runtime-p)))
      (unless output
        (let ((root (repo-root-from-script)))
          (setf output (namestring (merge-pathnames "doc/wasm/root.image" root)))))
      (when wasm-runtime
        (ensure-wasm32-target)
        (apply-wasm-image-policy))
      (format t "~&WASM image policy: ~s~%" *wasm-image-policy*)
      (format t "~&Saving WASM image to ~a~%" output)
      (if wasm-runtime
        (progn
          (when manifest-out
            (format t "~&Note: --manifest-out is ignored when saving directly in wasm runtime.~%"))
          (save-application output :toplevel-function #'toplevel-loop))
        (progn
          (format t "~&Host runtime detected; delegating image generation to Node helper.~%")
          (run-host-node-helper output :modules modules :manifest-out manifest-out)))
      (finish-output))))

(main)
#+wasm32-target
(progn
  ;; wasm32-target does not support CCL:QUIT; request toplevel exit instead.
  (%set-toplevel nil)
  (values))
#-wasm32-target
(ccl:quit)
