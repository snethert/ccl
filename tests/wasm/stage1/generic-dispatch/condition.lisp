(in-package :wasm32-compiler)
(defun gd-condition-call (name forms)
  (setq *b-condition-used* t)
  (pushnew "condition_registry" *b-symbols* :test #'equal)
  (if (eq name 'gd_condition)
    (progn
      (unless (= (length forms) 2) (refuse :gd-constructor-arity))
      (let ((*b-tail-position* nil) (*b-producer-target* nil))
        (b-frame 2
          (lambda (root)
            (b-wat "(i32.store offset=8 ~a ~a) (i32.store offset=12 ~a ~a) ~a"
              root (b-scalar (first forms)) root (b-scalar (second forms))
              (b-multiple (make-b-raw-code :text
                (if *b-allocation-retry*
                  (b-wat "(call $condition_new (i32.const 32796) (i32.add ~a (i32.const 8)))" root)
                  (b-wat "(call $condition_new (i32.const 32796) (i32.load offset=8 ~a) (i32.load offset=12 ~a))" root root)))))))))
    (progn
      (unless (= (length forms) 1) (refuse :gd-reader-arity))
      (b-frame 1
        (lambda (root)
          (b-wat "(i32.store offset=8 ~a ~a) ~a" root (b-scalar (first forms))
            (b-multiple (make-b-raw-code :text
              (b-wat "(call $condition_field (i32.load offset=8 ~a) (i32.const 8192) (i32.const ~d) (local.get $top))"
                root (if (eq name 'gd_condition_gf) 8 12))))))))))
