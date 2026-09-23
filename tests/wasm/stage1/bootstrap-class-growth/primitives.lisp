(in-package :ccl)

(defun %wasm-class-writeable (table)
  (unless (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (error "The bootstrap class table must be an EQ hash table."))
  (when (nhash.read-only table)
    (error "Cannot modify a read-only hash table."))
  table)

(defun %wasm-grow-class-table (table)
  (let* ((old (nhash.vector table))
         (size (nhash.vector.size old)))
    (when (>= size 16384)
      (error "The bootstrap class table has reached its capacity limit."))
    (let ((new (%alloc-misc (+ 14 (* 4 size)) target::subtag-hash-vector)))
      (dotimes (i size)
        (let* ((index (+ 14 (* 2 i)))
               (key (%svref old index)))
          (when (%wasm-eq-hash-key-p key)
            (%wasm-eq-table-set new key (%svref old (1+ index))))))
      ;; OLD remains published until allocation and all stores have succeeded.
      (setf (nhash.vector table) new))))

;;; Keep PUTHASH's optional default and its evaluation order.
(defun %wasm-class-puthash (key table default &optional (value default))
  (%wasm-class-writeable table)
  (let ((vector (nhash.vector table)))
    (when (= (nhash.vector.count vector) (nhash.vector.size vector))
      (unless (nth-value 1 (%wasm-eq-table-get vector key nil))
        (%wasm-grow-class-table table))))
  (%wasm-eq-table-set (nhash.vector table) key value))

(defun %wasm-class-remhash (key table)
  (%wasm-class-writeable table)
  (%wasm-eq-table-remove (nhash.vector table) key nil))

;;; The class owner uses the same wrapper shape as the admitted image tables.
;;; It is synchronous and strong; no process lock or weak state is installed.
(defun %wasm-make-class-table (size)
  (setq size (require-type size '(integer 0 16384)))
  (let ((capacity 4))
    (loop while (< capacity size) do (setq capacity (* 2 capacity)))
    (%istruct 'hash-table nil 0 nil
              (%alloc-misc (+ 14 (* 2 capacity)) target::subtag-hash-vector)
              nil nil nil nil nil nil nil nil nil nil nil)))

(defun %wasm-class-clrhash (table)
  (%wasm-class-writeable table)
  (setf (nhash.vector table)
        (%alloc-misc (+ 14 (* 2 (nhash.vector.size (nhash.vector table))))
                     target::subtag-hash-vector))
  table)

;;; These are checked-boundary reason codes, not condition-class masks.
;;; All objects are made by MAKE-CONDITION from the live class table.
(defun %wasm-implicit-condition (kind datum expected)
  (case kind
    (1 (make-condition 'program-error))
    (8 (make-condition 'control-error))
    (10 (make-condition 'unbound-variable :name datum))
    (14 (make-condition 'undefined-function :name datum))
    (16 (make-condition 'simple-program-error
          :format-control "Checked Lisp runtime operation failed."
          :format-arguments nil))
    (17 (make-condition 'simple-error
          :format-control "Checked Lisp runtime operation failed."
          :format-arguments nil))
    ((18 19 20) (make-condition 'storage-condition))
    ((34 35 36 37 38)
     (make-condition (case kind
                       (34 'division-by-zero)
                       (35 'floating-point-invalid-operation)
                       (36 'floating-point-overflow)
                       (37 'floating-point-underflow)
                       (38 'floating-point-inexact))
                     :operation datum :operands expected))
    (t (make-condition 'type-error :datum datum :expected-type expected))))
