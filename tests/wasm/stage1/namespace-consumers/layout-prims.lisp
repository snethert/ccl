(in-package :ccl)

;;; Return bytes after the D1 header, including the alignment word of double
;;; and complex float vectors, but excluding trailing allocation padding.
(defun subtag-bytes (subtag element-count)
  (unless (and (integerp element-count) (>= element-count 0))
    (error "Invalid vector element count: ~s" element-count))
  (case subtag
    ((#.target::subtag-u8-vector #.target::subtag-s8-vector) element-count)
    ((#.target::subtag-u16-vector #.target::subtag-s16-vector) (* element-count 2))
    ((#.target::subtag-single-float-vector #.target::subtag-u32-vector
      #.target::subtag-s32-vector #.target::subtag-fixnum-vector
      #.target::subtag-simple-base-string) (* element-count 4))
    ((#.target::subtag-double-float-vector #.target::subtag-complex-single-float-vector)
     (+ 4 (* element-count 8)))
    (#.target::subtag-complex-double-float-vector (+ 4 (* element-count 16)))
    (#.target::subtag-bit-vector (ash (+ element-count 7) -3))
    (t (error "Not an ivector subtag: ~s" subtag))))

;;; Inverse of the Wasm array-element representation chosen by
;;; ELEMENT-TYPE-SUBTYPE. All thirteen specialized vector tags are covered.
(defun element-subtype-type (subtype)
  (case subtype
    (#.target::subtag-simple-vector t)
    (#.target::subtag-single-float-vector 'single-float)
    (#.target::subtag-u32-vector '(unsigned-byte 32))
    (#.target::subtag-s32-vector '(signed-byte 32))
    (#.target::subtag-fixnum-vector 'fixnum)
    (#.target::subtag-simple-base-string 'base-char)
    (#.target::subtag-u8-vector '(unsigned-byte 8))
    (#.target::subtag-s8-vector '(signed-byte 8))
    (#.target::subtag-u16-vector '(unsigned-byte 16))
    (#.target::subtag-s16-vector '(signed-byte 16))
    (#.target::subtag-double-float-vector 'double-float)
    (#.target::subtag-complex-single-float-vector '(complex single-float))
    (#.target::subtag-complex-double-float-vector '(complex double-float))
    (#.target::subtag-bit-vector 'bit)
    (t 'bogus)))
