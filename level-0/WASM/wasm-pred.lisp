;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; WASM level-0 predicates.
;;; On ARM these are fast LAP paths. On WASM they are pure Lisp fallbacks.
;;; The compiler may inline %ptr-eql and other comparison intrinsics for
;;; direct calls; these definitions handle dynamic (funcall) dispatch.

(in-package "CCL")

(defun eql (x y)
  "Return T if OBJ1 and OBJ2 represent the same object, otherwise NIL."
  (or (eq x y)
      (and (typep x 'double-float)
           (typep y 'double-float)
           (= x y))
      (and (typep x 'short-float)
           (typep y 'short-float)
           (= x y))
      (and (typep x 'bignum)
           (typep y 'bignum)
           (= x y))
      (and (typep x 'ratio)
           (typep y 'ratio)
           (= x y))
      (and (typep x 'complex)
           (typep y 'complex)
           (= x y))))

(defun equal (x y)
  "Return T if X and Y are EQL or if they are structured components
  whose elements are EQUAL. Strings and bit-vectors are EQUAL if they
  are the same length and have identical components. Other arrays must be
  EQ to be EQUAL.  Pathnames are EQUAL if their components are."
  (cond
    ((eql x y) t)
    ((and (consp x) (consp y))
     (and (equal (car x) (car y))
          (equal (cdr x) (cdr y))))
    ((and (stringp x) (stringp y))
     (string= x y))
    ((and (bit-vector-p x) (bit-vector-p y))
     (let ((len (length x)))
       (and (= len (length y))
            (dotimes (i len t)
              (unless (eql (aref x i) (aref y i))
                (return nil))))))
    ((and (pathnamep x) (pathnamep y))
     (hairy-equal x y))
    (t nil)))
