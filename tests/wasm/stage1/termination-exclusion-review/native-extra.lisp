;; Untouched native empty-state API answers, including both optional-argument
;; shapes of cancellation. Compare exact multiple-value lists, not just truth.
(let ((objects (list nil t 7 (cons 17 nil) (lambda () nil))))
 (dolist (object objects)
  (dolist (vals (list (multiple-value-list (cancel-terminate-when-unreachable object))
                     (multiple-value-list (cancel-terminate-when-unreachable object nil))
                     (multiple-value-list (cancel-terminate-when-unreachable object #'identity))
                     (multiple-value-list (termination-function object))))
   (assert (equal vals '(nil)))))
 (assert (equal (multiple-value-list (drain-termination-queue)) '(nil)))
 (format t "EMPTY-NATIVE|21|NIL-one-value~%"))
;; Run real fd-stream-close via WITH-OPEN-FILE, untouched and with the corrected
;; empty-state replacements temporarily bound at their real CCL symbols.
;; Ordinary WITH-OPEN-FILE and explicit CLOSE during a nonlocal exit must
;; flush, close and preserve content. This does not qualify CLOSE :ABORT T.
(let* ((*warn-if-redefine-kernel* nil)
       (path (merge-pathnames "termination-close.tmp" *load-truename*))
       (symbols '(cancel-terminate-when-unreachable termination-function drain-termination-queue))
       (saved (mapcar #'fdefinition symbols)))
 (unwind-protect
  (dolist (replacement '(nil t))
   (when replacement
    (setf (fdefinition 'cancel-terminate-when-unreachable) (lambda (object &optional callback) (declare(ignore object callback)) nil)
          (fdefinition 'termination-function) (lambda (object) (declare(ignore object)) nil)
          (fdefinition 'drain-termination-queue) (lambda () nil)))
   (dolist (leave '(nil t))
    (let ((stream nil))
     (if leave
      (catch 'leave
       (setq stream (open path :direction :output :if-exists :supersede))
       (unwind-protect
        (progn (write-string "flushed-before-close" stream) (throw 'leave 7))
        (close stream)))
      (with-open-file (s path :direction :output :if-exists :supersede)
       (setq stream s)
       (write-string "flushed-before-close" s)))
     (assert (not (open-stream-p stream)))
     (with-open-file (s path)
      (assert (equal (read-line s nil nil) "flushed-before-close")))
     (format t "FILE-CLOSE|~a|~a|flushed,closed~%" (if replacement "replacement" "native") (if leave "transfer" "normal")))))
  (loop for symbol in symbols for function in saved do (setf (fdefinition symbol) function))
  (when (probe-file path) (delete-file path))))
