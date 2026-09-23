(in-package :ccl)

;;; PUTHASH's optional default is evaluated even when the value is supplied.
;;; The ordinary wrapper and the accepted EQ leaf keep their native roles.
(defun %wasm-class-puthash (key table default &optional (value default))
  (unless (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (error "The bootstrap class table must be an EQ hash table."))
  (when (nhash.read-only table)
    (error "Cannot modify a read-only hash table."))
  (%wasm-eq-table-set (nhash.vector table) key value))
