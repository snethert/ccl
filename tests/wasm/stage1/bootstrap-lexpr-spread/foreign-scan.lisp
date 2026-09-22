(in-package :wasm32-compiler)

;;; Inventory only: retain foreign reader tokens instead of acquiring native
;;; interfaces. CCL itself handles reader conditionals, including suppression.
;;; None of these forms is compiled or evaluated.
(defun host-foreign-inventory ()
  (let ((rows nil) (failures nil))
    (call-with-target
     (lambda ()
       (dolist (path (library-worklist))
         (let ((*readtable* (copy-readtable)) (*package* (find-package :ccl))
               (file (namestring path)) (*read-eval* nil))
           (flet ((foreign-token (stream char arg)
                    (declare (ignore arg))
                    (let* ((offset (- (file-position stream) 2))
                           (name (read stream t nil t)))
                      (unless *read-suppress*
                        (push (list file offset char (string name)) rows))
                      (list :foreign char name)))
                  (read-time-form (stream char arg)
                    (declare (ignore char arg))
                    (list :read-time-form (read stream t nil t))))
             (dolist (char '(#\$ #\_ #\> #\&))
               (set-dispatch-macro-character #\# char #'foreign-token))
             (set-dispatch-macro-character #\# #\. #'read-time-form)
             (with-open-file (stream path)
               (handler-case
                   (loop for form = (read stream nil :eof) until (eq form :eof)
                         do (when (and (consp form) (eq (car form) 'in-package))
                              (setq *package* (find-package (second form)))))
                 (error (c) (push (list file (file-position stream) (format nil "~a" c)) failures)))))))))
    (with-open-file (s (concatenate 'string (ccl:getenv "POOL_OUTPUT") "foreign-active.json")
                       :direction :output :if-exists :error)
      (write-string "{\"rows\":[" s)
      (loop for (file offset char name) in (reverse rows) for i from 0 do
        (unless (zerop i) (write-char #\, s))
        (format s "{\"file\":~s,\"offset\":~d,\"kind\":~s,\"name\":~s}"
                file offset (string char) name))
      (write-string "],\"failures\":[" s)
      (loop for row in (reverse failures) for i from 0 do
        (unless (zerop i) (write-char #\, s))
        (frontend-json-string (prin1-to-string row) s))
      (write-string "]}" s))))
