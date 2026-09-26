(in-package "CCL")

;;; The native sides state target-specific expectations explicitly.
(defun loader-level1-platform ()
  #+wasm32-target
  (multiple-value-bind (os bits cpu) (host-platform)
    (values (eq os :wasm) bits (eq cpu :wasm32)))
  #-wasm32-target (values t 32 t))

(defun loader-level1-metrics ()
  #+wasm32-target (values *total-gc-microseconds* *total-bytes-freed*)
  #-wasm32-target (values nil nil))

(defun loader-level1-metadata ()
  #+wasm32-target
  (values (hash-table-p %lambda-lists%)
          (not (logbitp $nhash_weak_bit
                        (nhash.vector.flags (nhash.vector %lambda-lists%)))))
  #-wasm32-target (values t t))

(defun loader-level1-plist ()
  (let ((plist (list :a 7 :b 9)))
    (setq plist (setprop plist :c 13))
    (setq plist (setprop plist :b 17))
    (values (getf-test plist :a #'eq)
            (getf-test plist :b #'eq)
            (getf-test plist :c #'eq)
            (getf-test plist :d #'eq 23)
            (plistp plist))))

(defun loader-level1-keyword ()
  (values (not (null (%keyword-present-p '(:a 1 :b 2) :a)))
          (not (null (%keyword-present-p '(:a 1 :b 2) :c)))
          (quoted-form-p '(quote a))
          (quoted-form-p '(function a))))

(defun loader-level1-sets ()
  (let* ((tail (list :a :b))
         (same (adjoin-eq :a tail))
         (new (adjoin-eq :c tail)))
    (values (eq same tail) (eq (car new) :c) (eq (cdr new) tail)
            (identity 29))))
