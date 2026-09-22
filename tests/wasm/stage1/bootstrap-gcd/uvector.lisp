(defun bootstrap-uvector-access (op forms)
  (bootstrap-operands forms
    (lambda (values)
      (let* ((object (first values)) (value (third values))
             (tag (temporary))
             (raw (mapcar (lambda (x) (make-b-raw-code :text x)) values)))
        (flet ((typed (kind)
                 (bootstrap-typed-access
                   (if value 'ccl::%typed-uvset 'ccl::%typed-uvref)
                   (cons (bootstrap-constant kind) raw))))
          (b-wat "(local.set ~a ~a)
                   (if (result i32) (i32.eq (local.get ~a) (i32.const 764))
                     (then ~a)
                     (else (if (result i32) (i32.eq (local.get ~a) (i32.const 796))
                       (then ~a)
                       (else (if (result i32) (i32.eq (local.get ~a) (i32.const 28))
                         (then ~a) (else ~a))))))"
                 tag (bootstrap-typecode object) tag
                 (bootstrap-string-access (if value 'ccl::%set-sbchar 'ccl::%sbchar) raw)
                 tag (typed :unsigned-8-bit-vector)
                 tag (typed :bignum)
                 (bootstrap-node-access
                   (if (eq op 'ccl::uvset) 'ccl::%svset 'ccl::%svref) raw)))))))
