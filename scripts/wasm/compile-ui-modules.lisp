;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Generate a JSON bundle of WASM compiled modules for the UI bridge demo.

(in-package "CCL")

(eval-when (:compile-toplevel :load-toplevel :execute)
  (unless (find-package "CCL.WASM-UI")
    (make-package "CCL.WASM-UI" :use '(:cl))))

(defvar %wasm-compiled-modules% nil)
(declaim (special %wasm-compiled-modules *wasm2-next-entry-index*))

(defparameter *wasm-ui-functions*
  '((ccl::wasm-ui-demo
     (lambda ()
       (ccl.wasm-ui::ui-render-tree (ccl.wasm-ui::ui-example-tree))
       0))
    (ccl::wasm-ui-turn
     (lambda ()
       (ccl::wasm-ui-turn)))
    (ccl::wasm-ui-poll
     (lambda ()
       (multiple-value-bind (_events count)
           (ccl.wasm-ui::ui-poll-events :max-events 8 :max-bytes 65536 :allow-pending nil)
         (declare (ignore _events))
         count)))))

(defparameter *wasm-ui-stub-functions*
  '((ccl::wasm-ui-demo
     (lambda ()
       0))
    (ccl::wasm-ui-turn
     (lambda ()
       0))
    (ccl::wasm-ui-poll
     (lambda ()
       0))))

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

(defun function-entry-index (fn)
  (let* ((info (%lfun-info fn))
         (entry (and info (getf info 'wasm-entry-index))))
    (if entry
      entry
      (let* ((raw (uvref fn 0)))
        (unless (fixnump raw)
          (error "Unexpected function entry: ~s" raw))
        (let* ((host-shift (arch::target-fixnum-shift
                            (backend-target-arch *host-backend*)))
               (target-shift (arch::target-fixnum-shift
                              (backend-target-arch (find-backend :wasm32))))
               (host-unboxed (ash raw (- host-shift))))
          (ash host-unboxed (- target-shift)))))))

(defun compile-ui-functions ()
  (setf %wasm-compiled-modules% nil)
  (when (boundp '*wasm2-next-entry-index*)
    (setf *wasm2-next-entry-index* 320))
  (labels ((compile-entries (entries)
             (let ((results nil))
               (dolist (entry entries)
                 (destructuring-bind (name lambda-form) entry
                   (multiple-value-bind (fn warnings)
                       (compile-named-function lambda-form :name name :target :wasm32)
                     (declare (ignore warnings))
                     (push (list :name (symbol-name name)
                                 :entry-index (function-entry-index fn))
                           results))))
               (nreverse results))))
    (handler-case
        (compile-entries *wasm-ui-functions*)
      (type-error (err)
        (declare (ignore err))
        ;; WASM2 cannot compile non-immediate symbol constants yet.
        ;; Fall back to stub functions until constant pools/FFI land.
        (setf %wasm-compiled-modules% nil)
        (compile-entries *wasm-ui-stub-functions*)))))

(defun repo-root-from-script ()
  (let* ((script (or *load-truename*
                     (probe-file "scripts/wasm/compile-ui-modules.lisp"))))
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
          (load-rel "compiler/WASM/wasm2.lisp")
          (load-rel "compiler/WASM/wasm-backend.lisp"))))))

(defun sorted-compiled-modules ()
  (sort (copy-list %wasm-compiled-modules%)
        #'<
        :key (lambda (entry) (svref entry 2))))

(defun write-module-bundle (output-path functions modules)
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
             (write-char #\} out))
    (write-string "]}" out)
    (terpri out)))

(defun main ()
  (load-wasm-backend)
  (load (merge-pathnames "lib/wasm-ui.lisp" (repo-root-from-script)))
  (let* ((argv (parse-argv ccl:*command-line-argument-list*))
         (output (or (cdr (assoc :output argv))
                     (namestring (merge-pathnames "doc/wasm/wasm-ui-modules.json")))))
    (let* ((functions (compile-ui-functions))
           (modules (sorted-compiled-modules)))
      (write-module-bundle output functions modules)
      (format t "Wrote ~d modules to ~a~%" (length modules) output)))
  (finish-output))

(main)
(ccl:quit)
