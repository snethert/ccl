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
          (load-rel "compiler/WASM/wasm-ffi.lisp")
          (load-rel "compiler/acode-rewrite.lisp")
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
