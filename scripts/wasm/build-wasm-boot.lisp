;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; Build the WASM32 boot image via cross-xload.

(in-package "CCL")

(defun repo-root-from-script ()
  (let* ((script (or *load-truename*
                     (probe-file "scripts/wasm/build-wasm-boot.lisp"))))
    (unless script
      (error "Cannot determine repository root"))
    (truename (merge-pathnames "../../" (make-pathname :name nil :type nil :defaults script)))))

(defun ensure-ccl-logical-host (root)
  (setf (logical-pathname-translations "ccl")
        `(("l1;**;*.*" ,(merge-pathnames "level-1/**/*.*" root))
          ("l1f;**;*.*" ,(merge-pathnames "l1-fasls/**/*.*" root))
          ("ccl;*.*" ,(merge-pathnames "*.*" root))
          ("**;*.*" ,(merge-pathnames "**/*.*" root)))))

(let* ((root (repo-root-from-script)))
  (ensure-ccl-logical-host root))

(let* ((root (repo-root-from-script)))
  (let ((*warn-if-redefine-kernel* nil))
    ;; Ensure fasl reader macros are available before loading xfasload.lisp.
    (require "FASLENV" "ccl:xdump;faslenv")
    (let* ((xfasload (or (probe-file (merge-pathnames "xdump/xfasload.dx64fsl" root))
                         (merge-pathnames "xdump/xfasload.lisp" root))))
      (load xfasload))
    ;; Ensure ARM-ARCH is provided before xwasmfasload's REQUIRE runs.
    (load (merge-pathnames "compiler/ARM/arm-arch.lisp" root))
    (load (merge-pathnames "xdump/xwasmfasload.lisp" root))))

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
          (load-rel "compiler/nx1.lisp")
          ;; Refresh fasl dumping to pick up local compiler edits.
          (load-rel "lib/nfcomp.lisp")
          (load-rel "compiler/WASM/wasm2.lisp")
          (load-rel "compiler/WASM/wasm-backend.lisp")))))
  (unless (find-backend :wasm32)
    (error "WASM32 backend not available after loading wasm compiler modules.")))

(defun parse-argv (argv)
  (let ((out nil)
        (args argv)
        (seen-delimiter nil))
    (loop while args do
      (let ((arg (pop args)))
        (cond
          ((string= arg "--")
           (setf seen-delimiter t))
          ((or (string= arg "-h") (string= arg "--help"))
           (push (cons :help t) out))
          ((string= arg "--force")
           (push (cons :force t) out))
          (seen-delimiter
           (error "Unknown argument: ~s" arg))
          (t
           nil))))
    out))

(defun usage ()
  (format t "~&Usage: ccl --no-init --batch -l scripts/wasm/build-wasm-boot.lisp [-- --force]~%")
  (format t "Builds wasm-boot.image via cross-xload-level-0.~%"))

(defun main ()
  (let* ((argv (parse-argv ccl:*command-line-argument-list*))
         (force (cdr (assoc :force argv))))
    (when (cdr (assoc :help argv))
      (usage)
      (quit 0))
    (load-wasm-backend)
    (let* ((root (repo-root-from-script)))
      (let ((*features* (cons :wasm32-target *features*)))
        ;; Reload number-macros with wasm32-target enabled so macroexpansion
        ;; avoids wasm-unimplemented complex-float ops.
        (load (merge-pathnames "lib/number-macros.lisp" root)))
      ;; Refresh macros so wasm-aware variants are visible during cross-compile.
      (let ((*warn-if-redefine-kernel* nil))
        (load (merge-pathnames "lib/macros.lisp" root))))
    (format t "~&Building wasm-boot.image...~%")
    (cross-xload-level-0 :wasm32 (if force :force t))
    (finish-output)))

(main)
(ccl:quit)
