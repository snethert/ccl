(in-package "CCL")
(eval-when (:compile-toplevel :execute)
  (require "HASHENV" "ccl:xdump;hashenv"))

;;; Audit 182's component-address vector: this must not call an absent leaf.
(defun loader-gc-fresh ()
  (let ((vector (%cons-nhash-vector 3)))
    (setf (nhash.vector.flags vector) (ash 1 $nhash_component_address_bit))
    (values (%needs-rehashing-p vector)
            (not (eql (%get-gc-count) (nhash.vector.gc-count vector))))))

(defvar *loader-gc-table* nil)
(defun loader-gc-hold (tracking)
  (setq *loader-gc-table*
        (funcall (symbol-function 'make-hash-table) :test 'eq))
  (let ((vector (nhash.vector *loader-gc-table*)))
    (setf (nhash.vector.flags vector)
          (ash 1 (if tracking $nhash_track_keys_bit $nhash_component_address_bit)))
    ;; A sole rooted bucket whose key has a moving component.
    (setf (%svref vector 14) (list (cons 41 43))
          (%svref vector 15) (cons 97 101)
          (nhash.vector.count vector) 1)
    (%set-does-not-need-rehashing vector))
  nil)

(defun loader-gc-state ()
  (let ((vector (nhash.vector *loader-gc-table*)))
    (values (%get-gc-count) (nhash.vector.gc-count vector)
            (%needs-rehashing-p vector)
            (logbitp $nhash_key_moved_bit (nhash.vector.flags vector))
            (car (car (%svref vector 14))) (cdr (car (%svref vector 14)))
            (car (%svref vector 15)) (cdr (%svref vector 15)))))

(defun loader-gc-reset ()
  (%set-does-not-need-rehashing (nhash.vector *loader-gc-table*))
  nil)

(defun loader-gc-force ()
  (%set-needs-rehashing *loader-gc-table*)
  nil)

(defun loader-gc-constructor-flags ()
  (let ((vector (%cons-nhash-vector 3)))
    (values (logbitp $nhash_track_keys_bit (nhash.vector.flags vector))
            (eql (nhash.vector.gc-count vector) (%get-gc-count)))))
