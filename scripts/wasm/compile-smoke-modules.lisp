;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Generate a JSON bundle of WASM compiled modules for JS smoke tests.

(in-package "CCL")

(defvar %wasm-compiled-modules% nil)
(declaim (special %wasm-compiled-modules *wasm2-next-entry-index*
                  *wasm2-enable-const-pool*
                  *wasm2-collect-module-debug*
                  *wasm2-compiled-modules-debug*))

(defparameter *wasm-smoke-functions*
  '((ccl::wasm-smoke-const
     (lambda ()
       23))
    (ccl::wasm-smoke-symbol
     (lambda ()
       :allow-other-keys))
    (ccl::wasm-smoke-add
     (lambda (x y)
       (declare (fixnum x y))
       (%i+ x y)))
    (ccl::wasm-smoke-ffi-add
     (lambda (x y)
       (declare (fixnum x y))
       (external-call "wasm_ffi_test_add"
                      :signed-fullword x
                      :signed-fullword y
                      :signed-fullword)))
    (ccl::wasm-smoke-sub
     (lambda (x y)
       (declare (fixnum x y))
       (%i- x y)))
    (ccl::wasm-smoke-mul
     (lambda (x y)
       (declare (fixnum x y))
       (%i* x y)))
    (ccl::wasm-smoke-ash
     (lambda (x y)
       (declare (fixnum x y))
       (fixnum-ash x y)))
    (ccl::wasm-smoke-logand
     (lambda (x y)
       (declare (fixnum x y))
       (logand x y)))
    (ccl::wasm-smoke-logior
     (lambda (x y)
       (declare (fixnum x y))
       (logior x y)))
    (ccl::wasm-smoke-logxor
     (lambda (x y)
       (declare (fixnum x y))
       (logxor x y)))
    (ccl::wasm-smoke-lognot
     (lambda (x)
       (declare (fixnum x))
       (lognot x)))
    (ccl::wasm-smoke-neg
     (lambda (x)
       (declare (fixnum x))
       (%ineg x)))
    (ccl::wasm-smoke-if
     (lambda (x)
       (if x 11 22)))
    (ccl::wasm-smoke-if-arg
     (lambda (x)
       (if x x 17)))
    (ccl::wasm-smoke-identity
     (lambda (x)
       x))
    (ccl::wasm-smoke-identity-y
     (lambda (x y)
       (declare (ignore x))
       y))
    (ccl::wasm-smoke-block
     (lambda (x)
       (block done
         (if x
           (return-from done 7)
           9))))
    (ccl::wasm-smoke-tagbody
     (lambda (x)
       (let ((y 1))
         (tagbody
           (if x (go end))
           (setq y 2)
          end)
         y)))
    (ccl::wasm-smoke-misc-set-fallback
     (lambda (flag)
       (declare (fixnum flag))
       (let* ((vec (vector 10 20))
              (idx (logand flag 1)))
         (setf (uvref vec idx) 77))))
    (ccl::wasm-smoke-mvcall
     (lambda ()
       (multiple-value-call #'+
                            (values 10 32))))
    (ccl::wasm-smoke-closure-unwind-mv
     (lambda ()
       (let* ((x 11)
              (f (lambda () x)))
         (declare (ignore f))
         (multiple-value-bind (a b c d e fval)
             (unwind-protect
                 (values 1 2 3 4 5 6)
               (let ((tmp (cons x nil)))
                 (declare (ignore tmp))))
           (declare (ignore b c d e fval))
           (%i+ x a)))))
    (ccl::wasm-smoke-f64-add
     (lambda (x y)
       (declare (fixnum x y))
       (let* ((a (%double-float x))
              (b (%double-float y))
              (sum (+ a b)))
         (declare (double-float a b sum))
         (if (= sum 3.0d0) 1 0))))))

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
          (seen-delimiter
           (error "Unknown argument: ~s" arg))
          (t
           nil))))
    out))

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

(defun json-write-string-list (out items)
  (write-char #\[ out)
  (loop for item in items
        for idx from 0
        do (when (> idx 0)
             (write-char #\, out))
           (json-write-string out item))
  (write-char #\] out))

(defun function-entry-index (fn)
  (let* ((info (%lfun-info fn))
         (entry (and info (getf info 'wasm-entry-index))))
    (if entry
      entry
      (let* ((raw (uvref fn 0)))
        (unless (fixnump raw)
          (error "Unexpected function entry: ~s" raw))
        (let* ((target-shift (arch::target-fixnum-shift
                              (backend-target-arch (find-backend :wasm32)))))
          (ash raw (- target-shift)))))))

(defun compile-smoke-functions ()
  (setf %wasm-compiled-modules% nil)
  (when (boundp '*wasm2-compiled-modules-debug*)
    (setf *wasm2-compiled-modules-debug* nil))
  (when (boundp '*wasm2-next-entry-index*)
    (setf *wasm2-next-entry-index* 300))
  (let* ((backend (find-backend :wasm32))
         (*target-ftd* (or (and backend (backend-target-foreign-type-data backend))
                           *target-ftd*))
         (results nil))
    (let ((*wasm2-enable-const-pool* t)
          (*wasm2-collect-module-debug* t))
      (declare (special *wasm2-enable-const-pool*
                        *wasm2-collect-module-debug*))
      (dolist (entry *wasm-smoke-functions*)
        (destructuring-bind (name lambda-form) entry
          (multiple-value-bind (fn warnings)
              (compile-named-function lambda-form :name name :target :wasm32)
            (declare (ignore warnings))
            (push (list :name (symbol-name name)
                        :entry-index (function-entry-index fn))
                  results)))))
  (nreverse results)))

(defun repo-root-from-script ()
  (let* ((script (or *load-truename*
                     (probe-file "scripts/wasm/compile-smoke-modules.lisp"))))
    (unless script
      (error "Cannot determine repository root"))
    (truename (merge-pathnames "../../" (make-pathname :name nil :type nil :defaults script)))))

(defun load-wasm-backend ()
  (let* ((root (repo-root-from-script)))
    (flet ((load-rel (path)
             (load (merge-pathnames path root))))
      ;; Load WASM-specific modules explicitly to avoid require/module-provider issues.
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

(defun sorted-compiled-modules ()
  (sort (copy-list %wasm-compiled-modules%)
        #'<
        :key (lambda (entry) (svref entry 2))))

(defun module-gc-root-policy-mode (entry)
  (let ((mode (and (> (length entry) 5) (svref entry 5))))
    (when (and mode (fixnump mode) (>= mode 0))
      mode)))

(defun module-gc-root-boundary-op-index (debug-entries)
  (let ((index (make-hash-table :test #'eql)))
    (dolist (entry debug-entries index)
      (let* ((entry-index (getf entry :entry-index))
             (ops (getf entry :gc-root-boundary-ops)))
        (when (and (fixnump entry-index)
                   (listp ops)
                   (every #'stringp ops))
          (setf (gethash entry-index index) ops))))))

(defun write-module-bundle (output-path functions modules &key debug-entries)
  (let ((boundary-index (module-gc-root-boundary-op-index debug-entries)))
  (ensure-directories-exist output-path)
  (with-open-file (out output-path
                       :direction :output
                       :if-exists :supersede
                       :if-does-not-exist :create)
    (write-char #\{ out)
    (write-string "\"functions\":[" out)
    (loop for fn in functions
          for idx from 0
          do (when (> idx 0) (write-char #\, out))
             (write-char #\{ out)
             (write-string "\"name\":" out)
             (json-write-string out (getf fn :name))
             (write-string ",\"entryIndex\":" out)
             (princ (getf fn :entry-index) out)
             (write-char #\} out))
    (write-string "],\"modules\":[" out)
    (loop for entry in modules
          for idx from 0
          do (when (> idx 0) (write-char #\, out))
             (write-char #\{ out)
             (write-string "\"exportName\":" out)
             (json-write-string out (svref entry 1))
             (write-string ",\"entryIndex\":" out)
             (princ (svref entry 2) out)
             (write-string ",\"moduleVersion\":" out)
             (princ (svref entry 3) out)
             (write-string ",\"moduleBytes\":" out)
             (json-write-bytes out (svref entry 0))
             (when (and (> (length entry) 4) (svref entry 4))
               (write-string ",\"constPoolBytes\":" out)
               (json-write-bytes out (svref entry 4)))
             (let ((gc-mode (module-gc-root-policy-mode entry)))
               (when gc-mode
                 (write-string ",\"gcRootPolicyMode\":" out)
                 (princ gc-mode out)))
             (let ((gc-boundary-ops (gethash (svref entry 2) boundary-index)))
               (when gc-boundary-ops
                 (write-string ",\"gcRootBoundaryOps\":" out)
                 (json-write-string-list out gc-boundary-ops)))
             (write-char #\} out))
    (write-char #\] out)
    (let ((rows nil))
      (dolist (entry modules)
        (let ((gc-mode (module-gc-root-policy-mode entry)))
          (when gc-mode
            (push (cons (svref entry 2) gc-mode) rows))))
      (setf rows (nreverse rows))
      (when rows
        (write-string ",\"gcRootPolicyModes\":{" out)
        (loop for row in rows
              for idx from 0
              do (when (> idx 0) (write-char #\, out))
                 (json-write-string out (princ-to-string (car row)))
                 (write-char #\: out)
                 (princ (cdr row) out))
        (write-char #\} out)))
    (let ((rows nil))
      (dolist (entry modules)
        (let ((gc-boundary-ops (gethash (svref entry 2) boundary-index)))
          (when gc-boundary-ops
            (push (cons (svref entry 2) gc-boundary-ops) rows))))
      (setf rows (nreverse rows))
      (when rows
        (write-string ",\"gcRootBoundaryOps\":{" out)
        (loop for row in rows
              for idx from 0
              do (when (> idx 0) (write-char #\, out))
                 (json-write-string out (princ-to-string (car row)))
                 (write-char #\: out)
                 (json-write-string-list out (cdr row)))
        (write-char #\} out)))
    (write-char #\} out)
    (terpri out))))

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
  (let* ((argv (parse-argv ccl:*command-line-argument-list*))
         (output (or (cdr (assoc :output argv))
                     (namestring (merge-pathnames "doc/wasm/wasm-smoke-modules.json")))))
    (let* ((functions (compile-smoke-functions))
           (modules (sorted-compiled-modules))
           (debug-entries (copy-list *wasm2-compiled-modules-debug*)))
      (write-module-bundle output functions modules :debug-entries debug-entries)
      (format t "Wrote ~d modules to ~a~%" (length modules) output)))
  (finish-output))

(main)
(ccl:quit)
