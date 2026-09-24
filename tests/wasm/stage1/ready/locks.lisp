;;; Recursive locks for the exclusive, scheduler-disabled Worker profile.
;;; The native lock object keeps its six fields. Its value is a traced pair
;;; of owner token and recursion depth instead of a foreign lock pointer.
#+wasm32-target
(defun %make-recursive-lock-ptr ()
  (vector 0 0))

#+wasm32-target
(defun %wasm-recursive-lock-state (ptr lock)
  (unless (and (eq (typecode lock) target::subtag-lock)
               (eq (%svref lock target::lock.kind-cell) 'recursive-lock)
               (eq ptr (%svref lock target::lock._value-cell))
               (simple-vector-p ptr) (= (length ptr) 2))
    (error "Invalid single-Worker recursive lock."))
  (let ((owner (svref ptr 0)) (depth (svref ptr 1)))
    (unless (and (typep owner 'fixnum) (typep depth 'fixnum)
                 (>= owner 0) (>= depth 0)
                 (eq (zerop owner) (zerop depth)))
      (error "Invalid single-Worker recursive lock state.")))
  ptr)

#+wasm32-target
(defun %lock-recursive-lock-ptr (ptr lock flag)
  (%wasm-recursive-lock-state ptr lock)
  (if (istruct-typep flag 'lock-acquisition)
    (setf (lock-acquisition.status flag) nil)
    (when flag (report-bad-arg flag 'lock-acquisition)))
  (let ((self (%wasm-lock-owner-token)) (owner (svref ptr 0)))
    (unless (or (zerop owner) (eql owner self))
      (error "A single-Worker lock cannot wait for another owner."))
    (when (= (svref ptr 1) target::target-most-positive-fixnum)
      (error "Single-Worker recursive lock depth exhausted."))
    (setf (svref ptr 0) self)
    (incf (svref ptr 1))
    (when flag (setf (lock-acquisition.status flag) t))
    t))

#+wasm32-target
(defun %try-recursive-lock-object (lock &optional flag)
  (let* ((ptr (recursive-lock-ptr lock)))
    (%wasm-recursive-lock-state ptr lock)
    (if (istruct-typep flag 'lock-acquisition)
      (setf (lock-acquisition.status flag) nil)
      (when flag (report-bad-arg flag 'lock-acquisition)))
    (when (or (zerop (svref ptr 0))
              (eql (svref ptr 0) (%wasm-lock-owner-token)))
      (%lock-recursive-lock-ptr ptr lock flag))))

#+wasm32-target
(defun %unlock-recursive-lock-ptr (ptr lock)
  (%wasm-recursive-lock-state ptr lock)
  (unless (eql (svref ptr 0) (%wasm-lock-owner-token))
    (error 'not-lock-owner :lock lock))
  (when (zerop (decf (svref ptr 1)))
    (setf (svref ptr 0) 0))
  nil)
