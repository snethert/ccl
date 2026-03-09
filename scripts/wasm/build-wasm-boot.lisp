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
    (let* ((xfasload-src (merge-pathnames "xdump/xfasload.lisp" root))
           (xfasload-fsl (probe-file (merge-pathnames "xdump/xfasload.dx64fsl" root)))
           (xfasload (if (and xfasload-fsl
                              (> (file-write-date xfasload-fsl)
                                 (file-write-date xfasload-src)))
                       xfasload-fsl
                       xfasload-src)))
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
          ;; Register WASM-specific acode operators into empty () slots in the
          ;; live operator table.  The host CCL's compiled code uses baked-in
          ;; operator indices, so we must NOT change existing indices — only
          ;; fill empty slots.
          (let ((ops-to-patch
                 (list (list '%fixnum-set
                             (logior operator-single-valued-mask
                                     operator-acode-subforms-mask)
                             t)
                       (list '%fixnum-set-natural
                             (logior operator-single-valued-mask
                                     operator-acode-subforms-mask)
                             'natural)
                       (list '%single-to-fixnum
                             (logior operator-assignment-free-mask
                                     operator-single-valued-mask
                                     operator-acode-subforms-mask
                                     operator-side-effect-free-mask)
                             'fixnum)
                       (list '%double-to-fixnum
                             (logior operator-assignment-free-mask
                                     operator-single-valued-mask
                                     operator-acode-subforms-mask
                                     operator-side-effect-free-mask)
                             'fixnum)
                       (list '%single-round-to-fixnum
                             (logior operator-assignment-free-mask
                                     operator-single-valued-mask
                                     operator-acode-subforms-mask
                                     operator-side-effect-free-mask)
                             'fixnum)
                       (list '%double-round-to-fixnum
                             (logior operator-assignment-free-mask
                                     operator-single-valued-mask
                                     operator-acode-subforms-mask
                                     operator-side-effect-free-mask)
                             'fixnum)))
                (filled 0)
                (needed 6))
            (do ((tail *next-nx-operators* (cdr tail)))
                ((or (null tail) (>= filled needed)))
              (when (null (car tail))
                (setf (car tail) (nth filled ops-to-patch))
                (incf filled)))
            (format t "~&DIAG: Patched ~d operators into table~%" filled)
            (unless (= filled needed)
              (error "Failed to find ~d empty slots for WASM operators (found ~d)"
                     needed filled)))
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
          ((string= arg "--with-l1")
           (push (cons :with-l1 t) out))
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
              (let ((fn-slots (and (>= (length entry) 10) (svref entry 9))))
                (when fn-slots
                  (write-string ",\"fnSlots\":" out)
                  (princ fn-slots out)))
              (write-char #\} out))))
        ;; Also emit aliases for const-folded / bootstrap-entry functions.
        ;; These share a fixed entry index (202=const, 213=if, 214=if-arg,
        ;; 215=identity, 216=identity-y) so the module-level dedup discards
        ;; all but the first.  %wasm2-name-aliases% captures every name.
        (let ((aliases (and (boundp '%wasm2-name-aliases%) %wasm2-name-aliases%)))
          (dolist (alias aliases)
            (let ((fn-name (car alias))
                  (entry-idx (cdr alias)))
              (when fn-name
                (if first-fn
                  (setf first-fn nil)
                  (write-char #\, out))
                (write-char #\{ out)
                (write-string "\"name\":" out)
                (boot-json-write-string out fn-name)
                (write-string ",\"entryIndex\":" out)
                (princ entry-idx out)
                (write-char #\} out))))))
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

;;; L1 FASL loading into boot image — ordered list matching requiredFasls
;;; in make-real-image.mjs.  Each entry is (name subdir) where subdir is
;;; "l1-fasls" or "bin" under build/wasm32/.

(defparameter *wasm-l1-module-specs*
  '(("l1-cl-package" "l1-fasls") ("l1-utils" "l1-fasls")
    ("l1-init" "l1-fasls") ("l1-symhash" "l1-fasls")
    ("l1-numbers" "l1-fasls") ("l1-aprims" "l1-fasls")
    ("l1-callbacks" "l1-fasls") ("l1-sort" "l1-fasls")
    ("lists" "bin") ("sequences" "bin")
    ("l1-dcode" "l1-fasls") ("l1-clos-boot" "l1-fasls")
    ("hash" "bin") ("l1-clos" "l1-fasls")
    ("defstruct" "bin") ("dll-node" "bin")
    ("l1-unicode" "l1-fasls") ("l1-streams" "l1-fasls")
    ("linux-files" "l1-fasls") ("chars" "bin")
    ("l1-files" "l1-fasls") ("l1-typesys" "l1-fasls")
    ("sysutils" "l1-fasls") ("l1-lisp-threads" "l1-fasls")
    ("l1-application" "l1-fasls") ("l1-processes" "l1-fasls")
    ("l1-io" "l1-fasls") ("l1-reader" "l1-fasls")
    ("l1-readloop" "l1-fasls") ("l1-error-signal" "l1-fasls")
    ("l1-readloop-lds" "l1-fasls") ("l1-error-system" "l1-fasls")
    ("l1-events" "l1-fasls") ("l1-format" "l1-fasls")
    ("l1-sysio" "l1-fasls") ("l1-pathnames" "l1-fasls")
    ("l1-boot-lds" "l1-fasls") ("l1-boot-1" "l1-fasls")
    ("l1-boot-2" "l1-fasls") ("l1-boot-3" "l1-fasls")
    ("dumplisp" "bin")))

(defun wasm-l1-fasl-paths (root)
  "Return ordered list of L1 FASL pathnames from build/wasm32/."
  (let ((build-dir (namestring (merge-pathnames "build/wasm32/" root))))
    (mapcar (lambda (spec)
              (let* ((name (first spec))
                     (subdir (second spec))
                     (path (pathname (format nil "~a~a/~a.lafsl" build-dir subdir name))))
                (unless (probe-file path)
                  (error "L1 FASL missing: ~a (compile L1 first with compile-wasm-fasls.sh)" path))
                (truename path)))
            *wasm-l1-module-specs*)))

(defun cross-xload-wasm-with-l1 (&optional (recompile t))
  "Cross-load WASM32 boot image with L0 + L1 baked in."
  (with-cross-compilation-target (:wasm32)
    (let* ((*target-backend* (find-backend :wasm32))
           (*xload-target-backend* (or (find-xload-backend :wasm32)
                                       *xload-default-backend*))
           ;; No startup file needed — L1 is baked into the image.
           (*xload-startup-file* ""))
      (in-development-mode
       (when recompile
         (target-Xcompile-level-0 :wasm32 (eq recompile :force)))
       (let* ((*xload-image-base-address* *xload-image-base-address*)
              (*xload-readonly-space-address* *xload-readonly-space-address*)
              (*xload-dynamic-space-address* *xload-dynamic-space-address*)
              (*xload-target-nil* *xload-target-nil*)
              (*xload-target-unbound-marker* *xload-target-unbound-marker*)
              (*xload-target-misc-header-offset* *xload-target-misc-header-offset*)
              (*xload-target-misc-subtag-offset* *xload-target-misc-subtag-offset*)
              (*xload-target-fixnumshift* *xload-target-fixnumshift*)
              (*xload-target-fulltag-cons* *xload-target-fulltag-cons*)
              (*xload-target-car-offset* *xload-target-car-offset*)
              (*xload-target-cdr-offset* *xload-target-cdr-offset*)
              (*xload-target-cons-size* *xload-target-cons-size*)
              (*xload-target-fulltagmask* *xload-target-fulltagmask*)
              (*xload-target-misc-data-offset* *xload-target-misc-data-offset*)
              (*xload-target-fulltag-misc* *xload-target-fulltag-misc*)
              (*xload-target-subtag-char* *xload-target-subtag-char*)
              (*xload-target-charcode-shift* *xload-target-charcode-shift*)
              (*xload-target-big-endian* *xload-target-big-endian*)
              (*xload-host-big-endian* *xload-host-big-endian*)
              (*xload-target-use-code-vectors* *xload-target-use-code-vectors*)
              (*xload-target-fulltag-for-symbols* *xload-target-fulltag-for-symbols*)
              (*xload-target-fulltag-for-functions* *xload-target-fulltag-for-functions*)
              (*xload-target-char-code-limit* *xload-target-char-code-limit*)
              (*xload-purespace-reserve* *xload-purespace-reserve*)
              (*xload-static-space-address* *xload-static-space-address*))
         (setup-xload-target-parameters)
         (let* ((*load-verbose* t)
                (compiler-backend (find-backend
                                   (backend-xload-info-compiler-target-name
                                    *xload-target-backend*)))
                (wild-fasls (concatenate 'simple-string
                                         "*."
                                         (pathname-type
                                          (backend-target-fasl-pathname
                                           compiler-backend))))
                (wild-root (merge-pathnames "ccl:level-0;" wild-fasls))
                (wild-subdirs
                 (mapcar #'(lambda (d) (merge-pathnames d wild-fasls))
                         (backend-xload-info-subdirs *xload-target-backend*)))
                (*xload-image-file-name* (backend-xload-info-default-image-name
                                          *xload-target-backend*))
                (root (repo-root-from-script))
                (l0-fasls (append
                           (apply #'append
                                  (mapcar #'(lambda (d)
                                              (sort (directory d) #'string< :key #'namestring))
                                          wild-subdirs))
                           (sort (directory wild-root) #'string< :key #'namestring)))
                (l1-fasls (wasm-l1-fasl-paths root)))
           (format t "~&;Loading ~d L0 + ~d L1 FASLs into boot image~%"
                   (length l0-fasls) (length l1-fasls))
           (apply #'xfasload *xload-image-file-name*
                  (append l0-fasls l1-fasls))
           (format t "~&;Wrote bootstrapping image: ~s" (truename *xload-image-file-name*))))))))

(defun main ()
  (let* ((argv (parse-argv ccl:*command-line-argument-list*))
         (force (cdr (assoc :force argv)))
         (with-l1 (cdr (assoc :with-l1 argv)))
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
        (load (merge-pathnames "lib/macros.lisp" root)))
      ;; Reload number-case-macro so the expansion-time *target-backend* check
      ;; disables the retry loop on WASM (the host's built-in version lacks this).
      (load (merge-pathnames "lib/number-case-macro.lisp" root)))
    ;; DIAG: Log cold-load functions pushed during xdump
    (setq *xload-show-cold-load-functions* t)
    (if with-l1
      (progn
        (format t "~&Building wasm-boot.image with L1 baked in...~%")
        (cross-xload-wasm-with-l1 (if force :force t)))
      (progn
        (format t "~&Building wasm-boot.image...~%")
        (cross-xload-level-0 :wasm32 (if force :force t))))
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
