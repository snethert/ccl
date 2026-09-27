(in-package "CCL")

(defun target-loader-add-seven (value)
  (+ value 7))

(defun target-loader-extrema (first second)
  (values (min first second) (max first second)))

(defun target-loader-type-member (value)
  (typep value '(member * :other)))

(defun target-loader-vector-init (size kind)
  (declare (fixnum size))
  (let ((vector (ecase kind
                  (0 (make-array size))
                  (1 (make-array size :initial-element 0))
                  (2 (make-array size :initial-element nil))
                  (3 (make-array size :initial-element 42)))))
    (values (svref vector 0) (svref vector (1- size)))))

(defun target-loader-require (kind value)
  (declare (optimize (safety 3)))
  (ecase kind
    (0 (require-fixnum value)) (1 (require-symbol value))
    (2 (require-list value)) (3 (require-real value))
    (4 (require-simple-string value)) (5 (require-simple-vector value))
    (6 (require-character value)) (7 (require-number value))
    (8 (require-integer value)) (9 (require-s8 value)) (10 (require-u8 value))
    (11 (require-s16 value)) (12 (require-u16 value))
    (13 (require-s32 value)) (14 (require-u32 value))
    (15 (require-s64 value)) (16 (require-u64 value))))

(defvar *target-loader-reset-value*)
(defun target-loader-reset-binding (new)
  (setq *target-loader-reset-value* 10)
  (let (inner outer)
    (let ((*target-loader-reset-value* 20))
      (let ((*target-loader-reset-value* 30))
        (#-wasm32-target %reset-outermost-binding
         #+wasm32-target %wasm-reset-outermost-binding
         '*target-loader-reset-value* new)
        (setq inner *target-loader-reset-value*))
      (setq outer *target-loader-reset-value*))
    (values inner outer *target-loader-reset-value*)))

(defun target-loader-ordinary-keys (value &key (amount 1))
  (+ value amount))

(defun target-loader-method-keys (&method context value &key (amount 1))
  (declare (ignore context))
  (+ value amount))

(defun target-loader-nested (value)
  (labels ((even-step (n) (if (zerop n) value (odd-step (1- n))))
           (odd-step (n) (if (zerop n) (+ value 1) (even-step (1- n)))))
    (even-step 4)))

(defparameter *target-loader-effect* 41)
