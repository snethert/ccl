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
          ;; NB: Do NOT redirect TARGET → WASM here.  Shared code (nfcomp.lisp
          ;; etc.) uses #.target:: at read time for HOST arch values.  The ivector
          ;; const pool code in wasm2.lisp uses wasm:: directly, so the redirect
          ;; is not needed.
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
          ((string= arg "--boot-modules-out")
           (let ((val (pop args)))
             (unless val
               (error "Missing value for --boot-modules-out"))
             (push (cons :boot-modules-out val) out)))
          (seen-delimiter
           (error "Unknown argument: ~s" arg))
          (t
           nil))))
    out))

(defun usage ()
  (format t "~&Usage: ccl --no-init --batch -l scripts/wasm/build-wasm-boot.lisp [-- --force] [-- --boot-modules-out PATH]~%")
  (format t "Builds wasm-boot.image via cross-xload-level-0.~%")
  (format t "  --boot-modules-out PATH  Export level-0 compiled modules as V1 inline bundle~%"))

(defun boot-json-escape-string (s)
  (with-output-to-string (out)
    (loop for ch across s do
      (case ch
        (#\" (write-string "\\\"" out))
        (#\\ (write-string "\\\\" out))
        (#\Newline (write-string "\\n" out))
        (#\Return (write-string "\\r" out))
        (#\Tab (write-string "\\t" out))
        (t (write-char ch out))))))

(defun boot-json-write-string (out s)
  (write-char #\" out)
  (write-string (boot-json-escape-string s) out)
  (write-char #\" out))

(defun write-boot-module-bundle (output-path modules)
  "Write level-0 compiled modules as an inline V1 bundle (JSON + binary)."
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
               (const-offset nil))
          (when (> module-len 0)
            (write-sequence module-bytes bin))
          (incf offset module-len)
          (when (and const-bytes (> const-len 0))
            (setf const-offset offset)
            (write-sequence const-bytes bin)
            (incf offset const-len))
          (push (list entry module-offset module-len const-offset const-len) entries))))
    (setf entries (nreverse entries))
    (with-open-file (out json-path
                         :direction :output
                         :if-exists :supersede
                         :if-does-not-exist :create)
      (write-char #\{ out)
      (write-string "\"binary\":" out)
      (boot-json-write-string out bin-name)
      ;; Emit functions array with name→entryIndex for lookup tools
      (write-string ",\"functions\":[" out)
      (let ((first-fn t))
        (dolist (info entries)
          (let* ((entry (first info))
                 (fn-name (and (>= (length entry) 7) (svref entry 6))))
            (when fn-name
              (if first-fn
                (setf first-fn nil)
                (write-char #\, out))
              (write-char #\{ out)
              (write-string "\"name\":" out)
              (boot-json-write-string out fn-name)
              (write-string ",\"entryIndex\":" out)
              (princ (svref entry 2) out)
              (write-char #\} out)))))
      (write-char #\] out)
      (write-string ",\"modules\":[" out)
      (loop for info in entries
            for idx from 0
            do (when (> idx 0) (write-char #\, out))
               (destructuring-bind (entry module-offset module-len const-offset const-len) info
                 (write-char #\{ out)
                 (write-string "\"exportName\":" out)
                 (boot-json-write-string out (svref entry 1))
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
      (write-char #\] out)
      (write-char #\} out)
      (terpri out))
    (length entries)))

(defun main ()
  (let* ((argv (parse-argv ccl:*command-line-argument-list*))
         (force (cdr (assoc :force argv)))
         (boot-modules-out (cdr (assoc :boot-modules-out argv))))
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
    ;; Report the final entry index counter for downstream start-entry-index.
    (let ((next-idx (and (boundp '*wasm2-next-entry-index*) *wasm2-next-entry-index*)))
      (format t "~&*wasm2-next-entry-index* after cross-xload = ~a~%" next-idx))
    ;; Diagnostic: check %wasm-compiled-modules% for the range of entry indices
    (let ((modules (and (boundp '%wasm-compiled-modules%) %wasm-compiled-modules%)))
      (when modules
        (let* ((indices (mapcar (lambda (e) (svref e 2)) modules))
               (min-idx (reduce #'min indices))
               (max-idx (reduce #'max indices)))
          (format t "~&DIAG: %wasm-compiled-modules% count=~d min-entry=~d max-entry=~d~%"
                  (length modules) min-idx max-idx)
          (format t "~&DIAG: All compiled modules:~%")
          (dolist (m (sort (copy-list modules) #'< :key (lambda (e) (svref e 2))))
            (format t "  entry=~d name=~s~%"
                    (svref m 2)
                    (and (>= (length m) 7) (svref m 6)))))))
    (when boot-modules-out
      (let ((modules (and (boundp '%wasm-compiled-modules%) %wasm-compiled-modules%)))
        (if (null modules)
          (format t "~&No level-0 compiled modules to export.~%")
          (let* ((sorted (sort (copy-list modules) #'<
                               :key (lambda (e) (svref e 2))))
                 (count (write-boot-module-bundle boot-modules-out sorted)))
            (format t "~&Wrote ~d level-0 compiled modules to ~a~%" count boot-modules-out)))
        ;; Write the next entry index to a sidecar file for rebuild-everything.sh
        (let ((next-idx (and (boundp '*wasm2-next-entry-index*) *wasm2-next-entry-index*)))
          (when (and next-idx boot-modules-out)
            (let ((idx-file (concatenate 'string
                              (subseq boot-modules-out 0
                                      (or (position #\. boot-modules-out :from-end t)
                                          (length boot-modules-out)))
                              ".next-entry-index")))
              (with-open-file (s idx-file :direction :output :if-exists :supersede)
                (format s "~d~%" next-idx))
              (format t "~&Wrote next-entry-index=~d to ~a~%" next-idx idx-file))))))
    (finish-output)))

(main)
(ccl:quit)
