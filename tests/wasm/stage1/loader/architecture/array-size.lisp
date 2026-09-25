;;; D1 ivector payload bytes after the header (double and complex vectors
;;; carry the four-byte alignment pad; bit vectors round up to bytes). Used by
;;; the cross-loader when it allocates strings, bignums and typed vectors.
(cl:defun array-data-size (subtag element-count)
  (cl:case subtag
    ((7 15 159 167 175 183 191) (cl:* 4 element-count))
    ((199 207) element-count)
    ((215 223) (cl:* 2 element-count))
    ((231 239) (cl:+ 4 (cl:* 8 element-count)))
    (247 (cl:+ 4 (cl:* 16 element-count)))
    (255 (cl:ceiling element-count 8))
    (cl:t (cl:error "Not a WASM32 ivector subtag: ~s" subtag))))
