(in-package :wasm32-compiler)

(defun bootstrap-or (forms)
  (if (null (cdr forms))
    (b-multiple (car forms))
    (let ((value (temporary)))
      ;; Only the last operand inherits tail position and multiple values.
      ;; No call or safepoint intervenes between testing and publishing a
      ;; successful primary value. Result assurance cannot collect.
      (b-wat "(local.set ~a ~a) (if (i32.ne (local.get ~a) (i32.const 77825)) (then ~a) (else ~a))"
             value (let ((*b-tail-position* nil)) (b-scalar (car forms)))
             value
             (b-multiple (make-b-raw-code :text (b-local value)))
             (bootstrap-or (cdr forms))))))
