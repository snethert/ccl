;;; Classification alone: these layout witnesses own no OS lock resource.
;;; The native classifier and the target classifier must select the same class.
  (mapcar (lambda (kind)
            (let* ((lock (ccl::gvector :lock nil kind 0 nil nil nil))
                   (name (case kind
                           (ccl::recursive-lock 'ccl::recursive-lock)
                           (ccl::read-write-lock 'ccl::read-write-lock)
                           (t 'ccl:lock)))
                   (class (find-class name)))
              (list (eq (class-of lock) class)
                    (progn (core-collect) (eq (class-of lock) class)))))
          '(ccl::recursive-lock ccl::read-write-lock :other))
