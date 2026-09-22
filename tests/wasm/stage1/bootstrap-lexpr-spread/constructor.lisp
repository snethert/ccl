(defun bootstrap-condition (mask values)
  (setq *b-condition-used* t)
  (pushnew "condition_registry" *b-symbols* :test #'equal)
  (b-wat "(block (result i32) ~a)"
    (b-frame (max 2 (length values))
      (lambda (root)
        (let ((object (temporary)))
          (with-output-to-string (s)
            ;; NIL means an omitted initarg here. Leave its native default
            ;; in the instance; every supplied value is rooted before growth.
            (loop for value in values for offset from 8 by 4
                  when value do
              (format s "(i32.store offset=~d ~a ~a)" offset root value))
            (format s "(local.set ~a ~a)" object
                    (if *b-allocation-retry*
                      (b-wat "(call $condition_new (i32.const ~d) (i32.add ~a (i32.const 8)))"
                             mask root)
                      (b-wat "(call $condition_new (i32.const ~d) (i32.load offset=8 ~a) (i32.load offset=12 ~a))"
                             mask root root)))
            (loop for value in values for offset from 8 by 4
                  when value do
              (format s "(i32.store offset=~d (call $condition_slots (local.get ~a)) (i32.load offset=~d ~a))"
                      offset object offset root))
            (format s "(local.get ~a)" object)))))))
