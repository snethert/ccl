(in-package :ccl)

;;; SXHASH is implementation-dependent. Hash semantic contents without native
;;; addresses, so EQUAL keys retain their hash when the collector moves them.
;;; Opaque objects and non-integral numbers share a bucket; collisions are
;;; resolved by the caller's equality test. Bounded cons descent handles cycles.
(defun %wasm-sxhash (object)
  (labels ((mix (hash value)
             ;; Two 24-bit operands keep the result within a 29-bit fixnum.
             (+ (* 31 (logand hash #xffffff)) (logand value #xffffff)))
           (walk (object depth)
             (cond ((zerop depth) 0)
                   ((integerp object) (logand object target::target-most-positive-fixnum))
                   ((characterp object) (char-code object))
                   ((symbolp object) (walk (symbol-name object) depth))
                   ((stringp object)
                    (let ((hash 17))
                      (dotimes (i (length object) hash)
                        (setq hash (mix hash (char-code (aref object i)))))))
                   ((typep object 'bit-vector)
                    (let ((hash 19))
                      (dotimes (i (length object) hash)
                        (setq hash (mix hash (aref object i))))))
                   ((consp object)
                    (mix (walk (car object) (1- depth))
                         (walk (cdr object) (1- depth))))
                   (t 23))))
    (walk object 7)))

;;; Existing generated callers enter these representation-boundary functions
;;; directly. Keep their strong EQ leaf and dispatch other admitted tests to
;;; the traced pair representation below.
(defun %wasm-class-gethash (key table &optional default)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-eq-table-get (nhash.vector table) key default)
    (%wasm-gethash key table default)))

(defun %wasm-class-puthash (key table default &optional (value default))
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (progn
      (%wasm-class-writeable table)
      (let ((vector (nhash.vector table)))
        (when (= (nhash.vector.count vector) (nhash.vector.size vector))
          (unless (nth-value 1 (%wasm-eq-table-get vector key nil))
            (%wasm-grow-class-table table))))
      (%wasm-eq-table-set (nhash.vector table) key value))
    (%wasm-puthash key table value)))

(defun %wasm-class-remhash (key table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (progn (%wasm-class-writeable table)
           (%wasm-eq-table-remove (nhash.vector table) key nil))
    (%wasm-remhash key table)))

(defun %wasm-class-clrhash (table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (progn
      (%wasm-class-writeable table)
      (setf (nhash.vector table)
            (%alloc-misc (+ 14 (* 2 (nhash.vector.size (nhash.vector table))))
                         target::subtag-hash-vector))
      table)
    (%wasm-clrhash table)))

;;; Strong, synchronous tables used while the target initializes its type
;;; environment. EQ retains the collector's existing address-hash leaf.
;;; Other tests keep traced key/value pairs: collection cannot invalidate an
;;; index computed from an object's address. These tables need no native lock.
(defun %wasm-make-hash-table (&key (test 'eql) (size 60)
                                 (rehash-size 1.5) (rehash-threshold .85)
                                 hash-function weak finalizeable
                                 (address-based t) lock-free shared)
  (declare (ignore address-based lock-free shared))
  (unless (and (integerp size) (>= size 0))
    (error "Invalid hash table size: ~s" size))
  (unless (or (and (integerp rehash-size) (> rehash-size 0))
              (and (floatp rehash-size) (> rehash-size 1)))
    (error "Invalid hash table rehash size: ~s" rehash-size))
  (unless (and (realp rehash-threshold) (<= 0 rehash-threshold 1))
    (error "Invalid hash table rehash threshold: ~s" rehash-threshold))
  (when (or hash-function weak finalizeable)
    (error "This target does not support custom hash functions or weak tables."))
  (let ((name (cond ((or (eq test 'eq) (eq test #'eq)) 'eq)
                    ((or (eq test 'eql) (eq test #'eql)) 'eql)
                    ((or (eq test 'equal) (eq test #'equal)) 'equal)
                    ((or (eq test 'equalp) (eq test #'equalp)) 'equalp)
                    (t (error "Invalid hash table test: ~s" test)))))
    (if (eq name 'eq)
      (%wasm-make-class-table (min size 16384))
      (%istruct 'hash-table nil name nil (vector nil 0 size rehash-size rehash-threshold)
                nil nil nil nil nil nil nil nil nil nil nil))))

(defun %wasm-table-pairs (table)
  (unless (and (hash-table-p table) (memq (nhash.comparef table) '(eql equal equalp)))
    (error "Invalid target hash table: ~s" table))
  (nhash.vector table))

(defun %wasm-gethash (key table &optional default)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-class-gethash key table default)
    (let ((pair (assoc key (svref (%wasm-table-pairs table) 0) :test (nhash.comparef table))))
      (if pair (values (cdr pair) t) (values default nil)))))

(defun %wasm-puthash (key table default &optional (value default))
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-class-puthash key table value)
    (let* ((state (%wasm-table-pairs table))
           (pair (assoc key (svref state 0) :test (nhash.comparef table))))
      (when (nhash.read-only table) (error "Cannot modify a read-only hash table."))
      (if pair
        (setf (cdr pair) value)
        (progn
          (push (cons key value) (svref state 0))
          (incf (svref state 1))))
      value)))

(defun %wasm-remhash (key table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-class-remhash key table)
    (let* ((state (%wasm-table-pairs table))
           (pair (assoc key (svref state 0) :test (nhash.comparef table))))
      (when (nhash.read-only table) (error "Cannot modify a read-only hash table."))
      (when pair
        (setf (svref state 0) (delq pair (svref state 0)))
        (decf (svref state 1)))
      (not (null pair)))))

(defun %wasm-clrhash (table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (%wasm-class-clrhash table)
    (let ((state (%wasm-table-pairs table)))
      (when (nhash.read-only table) (error "Cannot modify a read-only hash table."))
      (setf (svref state 0) nil (svref state 1) 0)
      table)))

(defun %wasm-hash-table-count (table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (nhash.vector.count (nhash.vector table))
    (svref (%wasm-table-pairs table) 1)))

(defun %wasm-maphash (function table)
  (if (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (let* ((vector (nhash.vector table)) (size (nhash.vector.size vector)))
      (dotimes (i size)
        (let* ((index (+ 14 (* 2 i))) (key (%svref vector index)))
          (when (%wasm-eq-hash-key-p key)
            (funcall function key (%svref vector (1+ index)))))))
    (dolist (pair (svref (%wasm-table-pairs table) 0))
      (funcall function (car pair) (cdr pair))))
  nil)
