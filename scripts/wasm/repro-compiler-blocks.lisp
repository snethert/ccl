;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Repro for WASM2 compiler blockers: non-immediate constants + external-call.

(in-package "CCL")

(defun repo-root-from-script ()
  (let* ((script (or *load-truename*
                     (probe-file "scripts/wasm/repro-compiler-blocks.lisp"))))
    (unless script
      (error "Cannot determine repository root"))
    (truename (merge-pathnames "../../" (make-pathname :name nil :type nil :defaults script)))))

(defun load-wasm-backend ()
  (let* ((root (repo-root-from-script)))
    (flet ((load-rel (path)
             (load (merge-pathnames path root))))
      (let ((*warn-if-redefine-kernel* nil))
        (let ((*compile-definitions* nil))
          (load-rel "compiler/ARM/arm-arch.lisp")
          (load-rel "lib/armenv.lisp")
          (load-rel "lib/wasmenv.lisp")
          (load-rel "compiler/backend.lisp")
          (unless (boundp 'platform-cpu-wasm)
            (defconstant platform-cpu-wasm (ash 4 3)))
          (unless (boundp 'platform-os-wasm)
            (defconstant platform-os-wasm 7))
          (load-rel "compiler/WASM/wasm-arch.lisp")
          (load-rel "compiler/WASM/wasm-vinsns.lisp"))
        (let ((*compile-definitions* t))
          ;; Register %fixnum-set and %fixnum-set-natural as acode operators.
          ;; Find empty () slots in the live operator table and fill them.
          (let ((filled 0))
            (do ((tail *next-nx-operators* (cdr tail)))
                ((or (null tail) (>= filled 2)))
              (when (null (car tail))
                (cond ((= filled 0)
                       (setf (car tail)
                             (list '%fixnum-set
                                   (logior operator-single-valued-mask
                                           operator-acode-subforms-mask)
                                   t))
                       (incf filled))
                      ((= filled 1)
                       (setf (car tail)
                             (list '%fixnum-set-natural
                                   (logior operator-single-valued-mask
                                           operator-acode-subforms-mask)
                                   'natural))
                       (incf filled)))))
            (format t "~&DIAG: Patched ~d operators into table~%" filled)
            (unless (= filled 2)
              (error "Failed to find empty slots for %fixnum-set operators")))
          (load-rel "compiler/WASM/wasm-ffi.lisp")
          (load-rel "compiler/acode-rewrite.lisp")
          (load-rel "compiler/nx1.lisp")
          ;; Refresh fasl dumping to pick up local compiler edits.
          (load-rel "lib/nfcomp.lisp")
          (load-rel "compiler/WASM/wasm2.lisp")
          (load-rel "compiler/WASM/wasm-backend.lisp"))))))

(defun try-compile (name lambda-form)
  (format t "~&~a: " name)
  (handler-case
      (progn
        (compile-named-function lambda-form :name name :target :wasm32)
        (format t "OK~%")
        t)
    (error (e)
      (format t "FAIL (~a)~%" e)
      nil)))

(defun main ()
  (load-wasm-backend)
  ;; Redirect TARGET → WASM so that target:: references in cross-compiled
  ;; code resolve to WASM target values, not the host architecture.
  ;; Must be AFTER load-wasm-backend (which loads wasm2.lisp whose HOST-correct
  ;; target:: references have already been read at load time).
  (let* ((wasm (find-package "WASM"))
         (cur  (find-package "TARGET")))
    (when (and cur wasm (not (eq cur wasm)))
      (rename-package cur (package-name cur)
                      (remove "TARGET" (package-nicknames cur) :test #'string=)))
    (when (and wasm (not (member "TARGET" (package-nicknames wasm) :test #'string=)))
      (rename-package wasm (package-name wasm)
                      (cons "TARGET" (package-nicknames wasm)))))
  (let* ((backend (find-backend :wasm32))
         (*target-ftd* (or (and backend (backend-target-foreign-type-data backend))
                           *target-ftd*)))
    (let ((const-sym-ok (try-compile 'WASM-REPRO-CONST-SYM
                                     '(lambda () 'FOO)))
          (const-str-ok (try-compile 'WASM-REPRO-CONST-STR
                                     '(lambda () "FOO")))
          (ffi-ok (try-compile 'WASM-REPRO-FFI
                               '(lambda () (external-call "getpid" :signed-long)))))
      (when (or const-sym-ok const-str-ok ffi-ok)
        (format t "~&NOTE: Expected failures; one or more repros compiled successfully.~%"))
      (finish-output))))

(main)
(ccl:quit)
