;;; Directed producer guard tests; all writes are private scratch streams.
(in-package :ccl)
(let ((rows nil)
      (scratch (concatenate 'string (getenv "CROSS_LOAD_OUTPUT") "guard-scratch.bin")))
  (labels ((refusal (name expected thunk)
             (let ((observed nil))
               (handler-case (funcall thunk)
                 (wasm32-compiler::unsupported-wasm32-code (condition)
                   (setq observed (wasm32-compiler::unsupported-operation condition))))
               (assert (eq observed expected))
               (push (list name (symbol-name observed)) rows)))
           (function-with (record &optional (size 3))
             (let ((function (%alloc-misc size target::subtag-xfunction)))
               (setf (%svref function 0) record)
               function))
           (dump (function)
             (with-open-file (*fasdump-stream* scratch :direction :output
                              :element-type '(unsigned-byte 8) :if-exists :supersede)
               (let ((*fasdump-epush* nil)) (wasm32-fasl-dump-function function)))))
    (refusal "file-context" :fasl-file-context
             (lambda () (wasm32-compiler::wasm32-fasl-pass2 nil)))
    (refusal "function-owner" :fasl-function-owner
             (lambda () (wasm32-xload-function-name 0)))
    (refusal "cross-load-target" :cross-load-target
             (lambda () (wasm32-cross-load scratch)))
    (refusal "native-image-operation" :native-image-operation
             (lambda () (wasm32-xload-unavailable)))
    (refusal "function-kind" :fasl-function-representation
             (lambda () (dump #())))
    (refusal "function-size" :fasl-function-representation
             (lambda () (dump (function-with nil 2))))
    (dolist (entry (list (list "record-kind" nil)
                         (list "record-size" #())
                         (list "record-version" #(:unknown "n" "w" nil nil))))
      (refusal (first entry) :fasl-function-version
               (lambda () (dump (function-with (second entry))))))
    (dolist (index '(1 2))
      (dolist (entry (list (list "kind" 3) (list "empty" "")
                           (list "upper-bound" (make-string (1+ (ash 1 24)) :initial-element #\a))
                           (list "ascii" (string (code-char 128)))))
        (let ((record (vector :wasm32-fasl-v1 "name" "wat" nil nil)))
          (setf (svref record index) (second entry))
          (refusal (format nil "text-~d-~a" index (first entry)) :fasl-module-text
                   (lambda () (dump (function-with record)))))))
    (dolist (entry '(("array-count-kind" 191 nil "Invalid Wasm array element count")
                     ("array-count-lower" 191 -1 "Invalid Wasm array element count")
                     ("array-count-upper" 191 #x40000000 "Invalid Wasm array element count")
                     ("array-kind" 0 1 "Wasm cross-loader array kind not admitted")))
      (let ((message nil))
        (handler-case (wasm32::cross-load-array-data-size (second entry) (third entry))
          (error (condition) (setq message (format nil "~a" condition))))
        (assert (and message (search (fourth entry) message)))
        (push (list (first entry) message) rows))))
  (when (probe-file scratch) (delete-file scratch))
  (with-open-file (stream (concatenate 'string (getenv "CROSS_LOAD_OUTPUT") "guards.json")
                          :direction :output :if-exists :error)
    (wasm32-xload-json (reverse rows) stream))
  (format t "PRODUCER-GUARDS-PASS ~d~%" (length rows)))

;;; Manufacture invalid pools with the ordinary dumper. The loader still reads
;;; complete real FASLs, so each independent pool clause is exercised in place.
(let ((original (fdefinition 'wasm32-fasl-dump-function))
      (*warn-if-redefine-kernel* nil))
  (unwind-protect
      (dolist (entry '(("pool-kind" 42) ("pool-subtype" "") ("pool-size" #(0))))
        (let ((pool (second entry)))
          (setf (fdefinition 'wasm32-fasl-dump-function)
                (lambda (function)
                  (let ((record (copy-seq (%svref function 0))))
                    (setf (svref record 3) pool
                          (%svref function 0) record)
                    (funcall original function))))
          (with-cross-compilation-target (:wasm32)
            (let ((*target-backend* (find-backend :wasm32))
                  ;; These controls deliberately recompile the same fixture.
                  (*compiler-warn-on-duplicate-definitions* nil))
              (multiple-value-bind (path warnings failure)
                  (compile-file "ccl:tests;wasm;stage1;cross-load;fixture.lisp"
                                :target :wasm32 :save-source-locations nil
                                :output-file (concatenate 'string (getenv "CROSS_LOAD_OUTPUT")
                                                          (first entry) ".w32fsl"))
                (declare (ignore warnings))
                (assert (and path (not failure))))))))
    (setf (fdefinition 'wasm32-fasl-dump-function) original)))
