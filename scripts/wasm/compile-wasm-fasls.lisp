;;; -*- Mode: Lisp; Package: CCL -*-
;;;
;;; Cross-compile the WASM32 level-1 + bin fasls needed for bootstrapping.

(in-package "CCL")

(defparameter *wasm-os-constants-by-name*
  '(("SEEK_SET" . 0)
    ("SEEK_CUR" . 1)
    ("SEEK_END" . 2)
    ;; WASI fcntl/errno values (see wasi-libc headers under wasm32-wasi).
    ("O_APPEND" . #x1)
    ("O_NONBLOCK" . #x4)
    ("O_CREAT" . #x1000)
    ("O_EXCL" . #x4000)
    ("O_TRUNC" . #x8000)
    ("O_RDONLY" . #x04000000)
    ("O_WRONLY" . #x10000000)
    ("O_RDWR" . #x14000000)
    ("O_ACCMODE" . #x1E000000)
    ("E2BIG" . 1)
    ("EACCES" . 2)
    ("EAGAIN" . 6)
    ("EWOULDBLOCK" . 6)
    ("EBADF" . 8)
    ("EEXIST" . 20)
    ("EINTR" . 27)
    ("EINVAL" . 28)
    ("EIO" . 29)
    ("EISDIR" . 31)
    ("EMFILE" . 33)
    ("ENFILE" . 41)
    ("ENOENT" . 44)
    ("ENOSYS" . 52)
    ("ENOTDIR" . 54)
    ("ENOTEMPTY" . 55)
    ("EPERM" . 63)
    ("EPIPE" . 64)
    ("EROFS" . 69)
    ("EXDEV" . 75)))

;; POSIX file type bits (used by %file-kind).
(setf *wasm-os-constants-by-name*
      (append *wasm-os-constants-by-name*
              '(("RUSAGE_SELF" . 0)
                ("F_GETFL" . 3)
                ("F_SETFL" . 4)
                ("S_IFMT" . #xF000)
                ("S_IFDIR" . #x4000)
                ("S_IFREG" . #x8000)
                ("S_IFLNK" . #xA000)
                ("S_IFIFO" . #x1000)
                ("S_IFSOCK" . #xC000)
                ("S_IFCHR" . #x2000))))

(defvar *wasm-load-os-constant-orig* nil)

(defun json-escape-string (s)
  (with-output-to-string (out)
    (loop for ch across s do
      (case ch
        (#\" (write-string "\\\"" out))
        (#\\ (write-string "\\\\" out))
        (#\Newline (write-string "\\n" out))
        (#\Return (write-string "\\r" out))
        (#\Tab (write-string "\\t" out))
        (t (write-char ch out))))))

(defun json-write-string (out s)
  (write-char #\" out)
  (write-string (json-escape-string s) out)
  (write-char #\" out))

(defun json-write-bytes (out bytes)
  (write-char #\[ out)
  (let ((len (length bytes)))
    (dotimes (i len)
      (when (> i 0)
        (write-char #\, out))
      (princ (aref bytes i) out)))
  (write-char #\] out))

(defun install-wasm-os-constants ()
  (unless *wasm-load-os-constant-orig*
    (setf *wasm-load-os-constant-orig* (fdefinition 'load-os-constant))
    (let ((*warn-if-redefine-kernel* nil))
      (setf (fdefinition 'load-os-constant)
            (lambda (sym &optional query)
              (block load-os-constant
                (let* ((ftd *target-ftd*)
                       (iface (and ftd (ftd-interface-package-name ftd))))
                  (when (and iface (string= iface "WASM"))
                    (let* ((entry (assoc (string sym) *wasm-os-constants-by-name*
                                         :test #'string=)))
                      (when entry
                        (if query
                          (return-from load-os-constant t)
                          (let ((*record-source-file* nil))
                            (%defconstant sym (cdr entry))
                            (return-from load-os-constant (cdr entry))))))))
                (funcall *wasm-load-os-constant-orig* sym query)))))))

(defun repo-root-from-script ()
  (let* ((script (or *load-truename*
                     (probe-file "scripts/wasm/compile-wasm-fasls.lisp"))))
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

(let ((*warn-if-redefine-kernel* nil))
  (require "compile-ccl")
  ;; Reload macros from source so WASM-specific guards are visible in this session.
  (load "ccl:lib;macros.lisp")
  ;; Reload db-io so the WASM FFI reader tweaks are active.
  (load "ccl:lib;db-io.lisp"))

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
          (load-rel "compiler/WASM/wasm-backend.lisp")))))
  (unless (find-backend :wasm32)
    (error "WASM32 backend not available after loading wasm compiler modules.")))

(defun ensure-wasm-target-nickname ()
  (let* ((wasm (find-package "WASM"))
         (target (find-package "TARGET")))
    (when (and target wasm (not (eq target wasm)))
      (rename-package target (package-name target)
                      (remove "TARGET" (package-nicknames target) :test #'string=)))
    (when wasm
      (unless (member "TARGET" (package-nicknames wasm) :test #'string=)
        (rename-package wasm (package-name wasm)
                        (cons "TARGET" (package-nicknames wasm)))))))

(defparameter *wasm-runtime-modules*
  (append *level-1-modules*
          '(lists sequences hash defstruct dll-node chars dumplisp))
  "Modules required by level-1.lisp plus dumplisp for save-application.")

(defun wasm-target-compile-modules (modules target force-compile &key trace-modules)
  (when (not (listp modules))
    (setf modules (list modules)))
  (let ((total (length modules))
        (index 0))
    (in-development-mode
     (dolist (module modules t)
       (incf index)
       (when trace-modules
         (format t "~&[~d/~d] ~s~%" index total module)
         (finish-output))
       (multiple-value-bind (fasl sources) (find-module module target)
         (when (needs-compile-p fasl sources force-compile)
           ;; Some earlier compiles can drop the TARGET nickname; refresh it
           ;; before each module compile to keep target:: references readable.
           (ensure-wasm-target-nickname)
           (require 'nfcomp)
           (compile-file (car sources)
                         :output-file fasl
                         :verbose t
                         :target target)))))))

(defun compile-wasm-real-image-entry (root)
  (let* ((source (merge-pathnames "scripts/wasm/make-real-image-entry.lisp" root))
         (output (merge-pathnames "doc/wasm/make-real-image-entry.lafsl" root)))
    (unless (probe-file source)
      (error "Missing helper source: ~a" source))
    (compile-file source
                  :output-file output
                  :verbose t
                  :target :wasm32)))

(defun reset-wasm-entry-index ()
  (declare (special *wasm2-next-entry-index*))
  (when (boundp '*wasm2-next-entry-index*)
    (setf *wasm2-next-entry-index* 300)))

(defun validate-wasm-compiled-modules ()
  (dolist (entry %wasm-compiled-modules%)
    (unless (and (vectorp entry) (>= (length entry) 4))
      (error "Unexpected wasm compiled module entry: ~s" entry))
    (let ((entry-index (svref entry 2)))
      (unless (fixnump entry-index)
        (error "Non-fixnum wasm entry index: ~s" entry-index))))
  t)

(defun sorted-compiled-modules ()
  (sort (copy-list %wasm-compiled-modules%)
        #'<
        :key (lambda (entry) (svref entry 2))))

(defun write-module-bundle (output-path modules)
  (let* ((json-path (pathname output-path))
         (bin-path (make-pathname :type "bin" :defaults json-path))
         (bin-name (file-namestring bin-path))
         (entries nil)
         (offset 0))
    (ensure-directories-exist json-path)
    (with-open-file (bin bin-path
                         :direction :output
                         :if-exists :supersede
                         :if-does-not-exist :create
                         :element-type '(unsigned-byte 8))
      (dolist (entry modules)
        (let* ((module-bytes (svref entry 0))
               (module-len (length module-bytes))
               (module-offset offset)
               (const-bytes (and (> (length entry) 4) (svref entry 4)))
               (const-len (if const-bytes (length const-bytes) 0))
               (const-offset (and const-bytes (+ offset module-len))))
          (when (> module-len 0)
            (write-sequence module-bytes bin))
          (when const-bytes
            (write-sequence const-bytes bin))
          (incf offset (+ module-len const-len))
          (push (list entry module-offset module-len const-offset const-len) entries))))
    (setf entries (nreverse entries))
    (with-open-file (out json-path
                         :direction :output
                         :if-exists :supersede
                         :if-does-not-exist :create)
      (write-char #\{ out)
      (write-string "\"binary\":" out)
      (json-write-string out bin-name)
      (write-string ",\"functions\":[]" out)
      (write-string ",\"modules\":[" out)
      (loop for info in entries
            for idx from 0
            do (when (> idx 0) (write-char #\, out))
               (destructuring-bind (entry module-offset module-len const-offset const-len) info
                 (write-char #\{ out)
                 (write-string "\"exportName\":" out)
                 (json-write-string out (svref entry 1))
                 (write-string ",\"entryIndex\":" out)
                 (princ (svref entry 2) out)
                 (write-string ",\"moduleVersion\":" out)
                 (princ (svref entry 3) out)
                 (write-string ",\"offset\":" out)
                 (princ module-offset out)
                 (write-string ",\"length\":" out)
                 (princ module-len out)
                 (when const-offset
                   (write-string ",\"constPoolOffset\":" out)
                   (princ const-offset out)
                   (write-string ",\"constPoolLength\":" out)
                   (princ const-len out))
                 (write-char #\} out)))
      (write-string "]}" out)
      (terpri out))))

(defun json-write-string-list (out items)
  (write-char #\[ out)
  (loop for item in items
        for idx from 0
        do (when (> idx 0) (write-char #\, out))
           (json-write-string out item))
  (write-char #\] out))

(defun write-module-debug (output-path entries)
  (let* ((json-path (pathname output-path))
         (sorted (sort (copy-list entries)
                       #'<
                       :key (lambda (entry) (getf entry :entry-index)))))
    (ensure-directories-exist json-path)
    (with-open-file (out json-path
                         :direction :output
                         :if-exists :supersede
                         :if-does-not-exist :create)
      (write-char #\[ out)
      (loop for entry in sorted
            for idx from 0
            do (when (> idx 0) (write-char #\, out))
               (write-char #\{ out)
               (write-string "\"exportName\":" out)
               (json-write-string out (or (getf entry :export-name) ""))
               (write-string ",\"entryIndex\":" out)
               (princ (or (getf entry :entry-index) 0) out)
               (write-string ",\"moduleVersion\":" out)
               (princ (or (getf entry :module-version) 0) out)
               (let ((name (getf entry :afunc-name)))
                 (when name
                   (write-string ",\"afuncName\":" out)
                   (json-write-string out name)))
               (let ((ir-len (getf entry :ir-len)))
                 (when ir-len
                   (write-string ",\"irLen\":" out)
                   (princ ir-len out)))
               (let ((if-count (getf entry :if-count)))
                 (when if-count
                   (write-string ",\"ifCount\":" out)
                   (princ if-count out)))
               (let ((ifv-count (getf entry :if-void-count)))
                 (when ifv-count
                   (write-string ",\"ifVoidCount\":" out)
                   (princ ifv-count out)))
              (let ((tail (getf entry :ir-tail)))
                (when tail
                  (write-string ",\"irTail\":" out)
                  (json-write-string-list out tail)))
              (let ((ir-short (getf entry :ir-short)))
                (when ir-short
                  (write-string ",\"irShort\":" out)
                  (json-write-string-list out ir-short)))
              (write-char #\} out))
      (write-char #\] out)
      (terpri out))))

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
          ((string= arg "--trace-modules")
           (push (cons :trace-modules t) out))
          ((string= arg "--modules-out")
           (let ((val (pop args)))
             (unless val
               (error "Missing value for --modules-out"))
             (push (cons :modules-out val) out)))
          ((string= arg "--modules-debug-out")
           (let ((val (pop args)))
             (unless val
               (error "Missing value for --modules-debug-out"))
             (push (cons :modules-debug-out val) out)))
          (seen-delimiter
           (error "Unknown argument: ~s" arg))
          (t
           nil))))
    out))

(defun usage ()
  (format t "~&Usage: ccl --no-init --batch -l scripts/wasm/compile-wasm-fasls.lisp [-- --force]~%")
  (format t "       ccl --no-init --batch -l scripts/wasm/compile-wasm-fasls.lisp [-- --trace-modules]~%")
  (format t "       ccl --no-init --batch -l scripts/wasm/compile-wasm-fasls.lisp [-- --modules-out PATH]~%")
  (format t "       ccl --no-init --batch -l scripts/wasm/compile-wasm-fasls.lisp [-- --modules-debug-out PATH]~%")
  (format t "Cross-compiles level-1 + bin fasls for the WASM32 target.~%"))

(defun main ()
  (let* ((argv (parse-argv ccl:*command-line-argument-list*))
         (root (repo-root-from-script))
         (force (cdr (assoc :force argv)))
         (trace-modules (cdr (assoc :trace-modules argv)))
         (modules-out (cdr (assoc :modules-out argv)))
         (modules-debug-out (cdr (assoc :modules-debug-out argv))))
    (declare (special *wasm2-collect-module-debug*
                      *wasm2-compiled-modules-debug*))
    (when (cdr (assoc :help argv))
      (usage)
      (quit 0))
    (load-wasm-backend)
    (ensure-wasm-target-nickname)
    (with-cross-compilation-target (:wasm32)
      ;; Avoid redefining core package ops (e.g. RENAME-PACKAGE) while
      ;; cross-compiling: those host-side redefinitions can drop the
      ;; TARGET nickname mid-compile.
      (let ((*target-backend* (find-backend :wasm32))
            (*compile-definitions* nil))
        (install-wasm-os-constants)
        (setf %wasm-compiled-modules% nil)
        (when modules-debug-out
          (setf *wasm2-collect-module-debug* t)
          (wasm2-reset-compiled-modules-debug))
        (reset-wasm-entry-index)
        (format t "~&Cross-compiling ~d WASM32 modules...~%" (length *wasm-runtime-modules*))
        (wasm-target-compile-modules *wasm-runtime-modules* :wasm32 force
                                     :trace-modules trace-modules)
        (format t "~&Cross-compiling wasm real-image helper module...~%")
        (compile-wasm-real-image-entry root)
        (validate-wasm-compiled-modules)
        (when modules-out
          (let ((modules (sorted-compiled-modules)))
            (write-module-bundle modules-out modules)
            (format t "~&Wrote ~d compiled modules to ~a~%" (length modules) modules-out)))
        (when modules-debug-out
          (write-module-debug modules-debug-out *wasm2-compiled-modules-debug*)
          (format t "~&Wrote compiled module debug info to ~a~%" modules-debug-out))
        (format t "~&WASM32 fasl compilation done.~%")
        (finish-output)))))

(main)
(ccl:quit)
