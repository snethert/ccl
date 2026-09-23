(in-package :wasm32-compiler)

;;; Read metadata from the very module objects retained by the file compiler.
;;; In particular, do not reconstruct dependencies from printed Lisp forms.
(defun ready-write-module-metadata (probes)
  (with-open-file (stream (concatenate 'string (ccl:getenv "PROBE_OUTPUT")
                                      "ready-modules.json")
                          :direction :output :if-exists :error)
    (write-char #\[ stream)
    (loop for module in
          (remove-duplicates
           (loop for m in
                 (append (mapcar (lambda (entry)
                                   (let ((m (copy-list (second entry))))
                                     (setf (getf m :source-name) (second (first entry)))
                                     m))
                                 *core-candidates*)
                         *condition-default-modules* *condition-cpl-modules* probes)
                 append (cons m (getf m :children)))
           :key (lambda (m) (getf m :name)) :test #'equal)
          for i from 0 do
      (unless (zerop i) (write-char #\, stream))
      (format stream "{\"module\":~s,\"source\":" (getf module :name))
      (frontend-json-string (or (getf module :source-file) "") stream)
      (write-string ",\"function\":" stream)
      (if (getf module :source-name)
        (format stream "~s" (frontend-owner (ccl::maybe-setf-function-name
                                           (getf module :source-name))))
        (write-string "null" stream))
      (format stream ",\"dynamic\":~a,\"dependencies\":["
              (if (getf module :dynamic-call) "true" "false"))
      (loop for name in (getf module :dependencies) for j from 0 do
        (unless (zerop j) (write-char #\, stream))
        (format stream "~s" (frontend-owner (ccl::maybe-setf-function-name name))))
      (write-string "],\"children\":[" stream)
      (loop for child in (getf module :children) for j from 0 do
        (unless (zerop j) (write-char #\, stream))
        (format stream "~s" (getf child :name)))
      (write-string "],\"operators\":[" stream)
      (loop for (op . count) in (getf module :operators) for j from 0 do
        (unless (zerop j) (write-char #\, stream))
        (format stream "[~s,~d]" (symbol-name op) count))
      (write-string "]}" stream))
    (write-char #\] stream))
  ;; The probe driver consumes its module list. Recompile just this submitted
  ;; file in the same environment and require byte equality with its installed
  ;; modules; no retained corpus definition is compiled again.
  (dolist (module probes)
    (with-open-file (stream (concatenate 'string (ccl:getenv "PROBE_OUTPUT")
                                        (getf module :name) ".census-wat")
                            :direction :output :if-exists :error)
      (write-string (getf module :wat) stream))))

;;; The oracle entries share fixture state, not the native process's
;;; real GF population or scheduler state. PROGV restores even on an error.
(defun ready-isolate-native-entries ()
  (let* ((names '(ccl::%all-gfs% ccl::*enable-automatic-termination*
                  ccl::*%periodic-tasks%* ccl::*base-power* ccl::*fixnum-power--1*))
         (original (mapcar #'symbol-value names))
         (state (copy-list original)))
    (dolist (name '(ready-image-status ready-image-refusals ready-initialize ready-check ready-start ready-table-bindings ready-resource-strings ready-string-contract ready-integer-print-tables ready-integer-strings ready-list-callees))
      (let ((function (gethash name *core-native-functions*)))
        (setf (gethash name *core-native-functions*)
              (lambda (&rest arguments)
                (multiple-value-prog1
                    (progv names state
                      (multiple-value-prog1 (apply function arguments)
                        (setq state (mapcar #'symbol-value names))))
                  (assert (every #'eq original (mapcar #'symbol-value names)))
                  (format t "READY-NATIVE-STATE-RESTORED ~s~%" name))))))))

(defun ready-check-print-initializer ()
  (let ((original nil) (proposed nil))
    (let ((*package* (find-package :ccl)))
      (with-open-file (stream "ccl:level-0;l0-int.lisp")
        (loop for form = (read stream nil :eof) until (eq form :eof)
              when (and (consp form) (eq (car form) 'do*))
                do (setq original form) (return))))
    (with-open-file (stream (ccl:getenv "PROBE_SOURCE"))
      (loop for form = (read stream nil :eof) until (eq form :eof)
            when (and (consp form) (eq (car form) 'defun)
                      (eq (cadr form) 'ready-integer-print-tables))
              do (setq proposed (fifth form))))
    ;; Local variable symbols differ only by the containing source package.
    (labels ((normalize (form)
               (cond ((consp form) (cons (normalize (car form)) (normalize (cdr form))))
                     ((and (symbolp form)
                           (member (symbol-name form)
                                   '("B" "F" "BASE" "POWER-1" "NEW-DIVISOR" "DIVISOR")
                                   :test #'string=))
                      (symbol-name form))
                     (t form))))
      (assert (and original proposed
                   (equal (normalize original) (normalize proposed)))))
    (format t "READY-PRINT-INITIALIZER-SOURCE-EQUAL~%")))

(defun validation-probe-cases ()
  (ready-check-print-initializer)
  (let ((*core-modules* nil) (*core-records* nil) (*core-files* nil))
    (core-compile-file (ccl:getenv "PROBE_SOURCE"))
    (ready-write-module-metadata *core-modules*))
  (ready-isolate-native-entries)
  (let ((image (cpl-image 'cpl-left)))
    (setf (svref (svref image 0) wasm32::subtag-istruct) (find-class 'hash-table))
    ;; The CHECK entry observes startup, without invoking the initializer.
    ;; Native execution follows the explicit entry order below.
    (loop for name in '(ready-image-status ready-image-refusals ready-initialize ready-check ready-start ready-table-bindings ready-resource-strings ready-string-contract ready-integer-print-tables ready-integer-strings ready-list-callees)
          collect (list name (list (list image))))))
