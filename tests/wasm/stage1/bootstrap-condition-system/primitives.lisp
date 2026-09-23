(in-package :ccl)

;;; The condition protocol uses the same classes as ordinary instances.
;;; SUBTYPEP's condition-designator case needs no representation-specific
;;; ancestry word: both names and class objects resolve to the real CPL.
(defun %wasm-condition-subtypep (name)
  (let ((class (if (classp name) name (find-class name))))
    (values (not (null (memq (find-class 'condition)
                            (%inited-class-cpl class))))
            t)))

(defun %wasm-signal (datum &rest arguments)
  (declare (dynamic-extent arguments))
  (%wasm-signal-condition (condition-arg datum arguments 'simple-condition)))

(defun %wasm-error (datum &rest arguments)
  (declare (dynamic-extent arguments))
  (%wasm-error-condition (condition-arg datum arguments 'simple-error)))

;;; The existing strong EQ leaf owns probing and relocation rehashing. Keep
;;; the ordinary HASH-TABLE wrapper and multiple-value contract in Lisp.
(defun %wasm-class-gethash (key table &optional default)
  (unless (and (hash-table-p table) (eql (nhash.comparef table) 0))
    (error "The bootstrap class table must be an EQ hash table."))
  (%wasm-eq-table-get (nhash.vector table) key default))

;;; The callable entry and the compiler's direct-call path share one protocol.
(defun signal (condition &rest arguments)
  (declare (dynamic-extent arguments))
  (apply #'%wasm-signal condition arguments))
