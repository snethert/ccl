(in-package :wasm32-compiler)

;;; The worklist comes from the cross compiler, not a level-1 directory glob.
;;; In particular, reading l0-bignum64 under the Wasm features yields no DEFUNs.
;;; A read failure stops the file: never resume inside a suppressed #+ form.
(defun library-worklist ()
  (let ((files (directory "ccl:level-0;*.lisp")))
    (dolist (directory (ccl::backend-xload-info-subdirs (ccl::find-xload-backend :wasm32)))
      (setq files (append files (directory (merge-pathnames "*.lisp" directory)))))
    (dolist (module (ccl::target-level-1-modules :wasm32))
      (multiple-value-bind (fasl sources) (ccl::find-module module :wasm32)
        (declare (ignore fasl))
        (setq files (append files sources))))
    (remove-duplicates files :test #'equal)))

(defun library-read-functions (chunks)
  (declare (ignore chunks))
  (let ((functions nil) (skips nil) (macros nil) (files nil))
    (call-with-target
     (lambda ()
       (dolist (path (library-worklist))
         (let* ((file (let ((text (namestring (translate-logical-pathname path))))
                        (subseq text (or (search "level-0/" text) (search "level-1/" text)
                                         (error "Not a bootstrap source: ~s" path)))))
                (*package* (find-package "CCL")) (*read-eval* t)
                (definitions 0) (complete nil))
           (with-open-file (stream path)
             (loop
               (let ((offset (file-position stream)) (end (gensym "EOF")))
                 (handler-case
                     (let ((form (read stream nil end)))
                       (when (eq form end) (setq complete t) (return))
                       (dolist (name (frontend-file-macros form)) (push (cons file name) macros))
                       (labels ((visit (x)
                                  (when (consp x)
                                    (case (car x)
                                      (in-package (setq *package* (find-package (second x))))
                                      (defun
                                       (if (symbolp (second x))
                                         (progn (incf definitions) (push (list file offset x) functions))
                                         (push (list file offset "compound-function-name") skips)))
                                      (progn (mapc #'visit (cdr x)))
                                      (eval-when (mapc #'visit (cddr x)))))))
                         (visit form)))
                   (error (c)
                     (push (list file offset (format nil "~s: ~a" (type-of c) c)) skips)
                     (return))))))
           (push (list file definitions complete) files)))))
    (with-open-file (s (concatenate 'string (ccl:getenv "POOL_OUTPUT") "worklist.sexp")
                       :direction :output :if-exists :supersede)
      (let ((*print-pretty* nil)) (prin1 (nreverse files) s)))
    (values functions skips macros)))

(defun library-measure-worklist ()
  (multiple-value-bind (functions skips macros) (library-read-functions nil)
    (declare (ignore macros))
    (let ((out (ccl:getenv "POOL_OUTPUT")))
      (with-open-file (s (concatenate 'string out "worklist-throughput.json")
                         :direction :output :if-exists :supersede)
        (write-string "{\"functions\":[" s)
        (loop for (file offset form) in (reverse functions) for i from 0 do
          (let ((result
                  (frontend-outcome
                   (lambda ()
                     (let ((module (call-with-target
                                    (lambda () (compile-bootstrap-form form "worklist" nil)))))
                       (core-check-body form module)
                       module)))))
            (unless (zerop i) (write-char #\, s))
            (format s "{\"file\":~s,\"offset\":~d,\"name\":~s,\"outcome\":~s,\"message\":"
                    file offset (symbol-name (second form)) result)
            (if *frontend-message* (frontend-json-string *frontend-message* s) (write-string "null" s))
            (write-char #\} s)))
        (write-string "],\"read_errors\":[" s)
        (loop for (file offset reason) in (reverse skips) for i from 0 do
          (unless (zerop i) (write-char #\, s))
          (format s "{\"file\":~s,\"offset\":~d,\"message\":" file offset)
          (frontend-json-string reason s) (write-char #\} s))
        (write-string "],\"denominator_complete\":false}" s)))))
