(defun bootstrap-condition-typep (object type)
  (setq *b-condition-used* t)
  (bootstrap-true-p
    (bootstrap-predicate-call 'ccl::class-typep
      (list (make-b-raw-code :text object)
            (make-b-raw-code :text
              (bootstrap-predicate-call 'find-class
                (list (make-b-raw-code :text type))))))))

(defun bootstrap-condition-class-runtime () "")
