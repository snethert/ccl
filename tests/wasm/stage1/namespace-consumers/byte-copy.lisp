(in-package :wasm32-compiler)

;;; The native LAP operation copies payload bytes, independently of element
;;; type. Offsets start immediately after the header, including the D1
;;; four-byte alignment pad of double and complex float vectors.
(defun bootstrap-ivector-byte-extent (object base bytes stream)
  (let ((header (temporary)) (tag (temporary)) (count (temporary)) (width (temporary)))
    (write-string
     (b-condition (b-wat "(i32.ne (i32.and ~a (i32.const 7)) (i32.const 6))" object) 4)
     stream)
    (format stream "(local.set ~a (i32.sub ~a (i32.const 6)))
      (call $span (local.get ~a) (i32.const 4))
      (local.set ~a (i32.load (local.get ~a)))
      (local.set ~a (i32.and (local.get ~a) (i32.const 255)))
      (local.set ~a (i32.shr_u (local.get ~a) (i32.const 8)))
      (local.set ~a (i32.const 0))"
      base object base header base tag header count header width)
    (dolist (entry '((7 . 4) (159 . 4) (167 . 4) (175 . 4) (183 . 4)
                    (191 . 4) (199 . 1) (207 . 1) (215 . 2) (223 . 2)
                    (231 . 8) (239 . 8) (247 . 16)))
      (format stream "(if (i32.eq (local.get ~a) (i32.const ~d))
                        (then (local.set ~a (i32.const ~d))))"
              tag (car entry) width (cdr entry)))
    (write-string
     (b-condition
      (b-wat "(i32.or
        (i32.and (i32.eqz (local.get ~a)) (i32.ne (local.get ~a) (i32.const 255)))
        (i32.and (i32.eq (local.get ~a) (i32.const 7)) (i32.eqz (local.get ~a))))"
        width tag tag count) 4) stream)
    (format stream "(local.set ~a
      (if (result i32) (i32.eq (local.get ~a) (i32.const 255))
        (then (i32.shr_u (i32.add (local.get ~a) (i32.const 7)) (i32.const 3)))
        (else (i32.mul (local.get ~a) (local.get ~a)))))
      (if (i32.and (i32.ge_u (local.get ~a) (i32.const 231))
                   (i32.le_u (local.get ~a) (i32.const 247)))
        (then (local.set ~a (i32.add (local.get ~a) (i32.const 4)))))
      (call $span (local.get ~a) (i32.add (local.get ~a) (i32.const 4)))"
      bytes tag count count width tag tag bytes bytes base bytes)))

(defun bootstrap-ivector-byte-copy (forms)
  (unless (= (length forms) 5) (refuse :ivector-copy-arity))
  (bootstrap-operands forms
    (lambda (values)
      (destructuring-bind (source start destination to count) values
        (let ((src (temporary)) (dst (temporary))
              (src-bytes (temporary)) (dst-bytes (temporary)))
          (with-output-to-string (s)
            (bootstrap-ivector-byte-extent source src src-bytes s)
            (bootstrap-ivector-byte-extent destination dst dst-bytes s)
            (dolist (value (list start to count))
              (write-string
               (b-condition
                (b-wat "(i32.or (i32.and ~a (i32.const 3)) (i32.lt_s ~a (i32.const 0)))"
                       value value) 4) s))
            (loop for offset in (list start to)
                  for bytes in (list src-bytes dst-bytes) do
              (write-string
               (b-condition
                (b-wat "(i64.gt_u
                  (i64.add (i64.extend_i32_u (i32.shr_u ~a (i32.const 2)))
                           (i64.extend_i32_u (i32.shr_u ~a (i32.const 2))))
                  (i64.extend_i32_u (local.get ~a)))" offset count bytes) 4) s))
            ;; No call or allocation occurs after validation. MEMORY.COPY
            ;; preserves the native operation's overlapping-copy semantics.
            (format s "(memory.copy
              (i32.add (local.get ~a) (i32.add (i32.const 4) (i32.shr_u ~a (i32.const 2))))
              (i32.add (local.get ~a) (i32.add (i32.const 4) (i32.shr_u ~a (i32.const 2))))
              (i32.shr_u ~a (i32.const 2))) ~a"
              dst to src start count destination)))))))
