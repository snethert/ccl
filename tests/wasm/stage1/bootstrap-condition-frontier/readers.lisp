(defun bootstrap-condition-reader (name forms)
  (unless (= (length forms) 1) (refuse :bootstrap-condition-reader-arity))
  (setq *b-condition-used* t)
  (pushnew "condition_registry" *b-symbols* :test #'equal)
  (let* ((simple (member name '(simple-condition-format-control simple-condition-format-arguments)))
         (class (case name
                  (stream-error-stream 'stream-error)
                  (file-error-pathname 'file-error)
                  (package-error-package 'package-error)
                  (t (if simple 'simple-condition 'type-error))))
         (offset (if (member name '(simple-condition-format-arguments type-error-expected-type)) 12 8)))
    (b-multiple
     (make-b-raw-code :text
       (bootstrap-operands forms
         (lambda (values)
           (let ((value (temporary)) (condition (car values)))
             (b-wat "(local.set ~a (call $condition_field ~a (i32.const ~d) ~a (local.get $top))) ~a (local.get ~a)"
                    value condition (b-condition-mask class)
                    (if (eq name 'package-error-package)
                      (b-wat "(if (result i32) (i32.and (call $condition_mask ~a) (i32.const ~d)) (then (i32.const 16)) (else (i32.const 8)))"
                             condition (b-condition-mask 'ccl::simple-package-error))
                      (b-wat "(i32.const ~d)" offset))
                    (b-condition (b-wat "(i32.eq (local.get ~a) (i32.const 83))" value) 4)
                    value))))))))
