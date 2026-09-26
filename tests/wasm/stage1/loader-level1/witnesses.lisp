(in-package "CCL")

(defvar *wasm-random-source*)

;;; The native sides state target-specific expectations explicitly.
(defun loader-level1-platform ()
  #+wasm32-target
  (multiple-value-bind (os bits cpu) (host-platform)
    (values (eq os :wasm) bits (eq cpu :wasm)))
  #-wasm32-target (values t 32 t))

(defun loader-level1-metrics ()
  #+wasm32-target (values *total-gc-microseconds* *total-bytes-freed*)
  #-wasm32-target (values nil nil))

(defun loader-level1-metadata ()
  ;; This prefix leaves %LAMBDA-LISTS% unbound in the serialized image.
  ;; Its runtime DEFVAR therefore creates a weak table. Owner-built metadata
  ;; in other image paths still follows the explicit strong-table policy.
  #+wasm32-target
  (values (hash-table-p %lambda-lists%)
          (logbitp $nhash_weak_bit
                   (nhash.vector.flags (nhash.vector %lambda-lists%))))
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

(defun (setf loader-level1-cell) (value cell)
  (setf (car cell) value))

(defun loader-level1-setter ()
  (let* ((name '#.(setf-function-name 'loader-level1-cell))
         (cell (list 3)))
    (values (eq name (setf-function-name 'loader-level1-cell))
            (eq name (loader-level1-setter-second))
            (eq name (existing-setf-function-name 'loader-level1-cell))
            (equal (maybe-setf-name name) '(setf loader-level1-cell))
            (funcall #'(setf loader-level1-cell) 37 cell)
            (car cell))))

(defun loader-level1-seed-zero ()
  #+wasm32-target
  (let ((*wasm-random-source* (lambda () 0))) (init-random-state-seeds))
  #-wasm32-target (values 1 0))

(defun loader-level1-seed-high ()
  #+wasm32-target
  (let ((*wasm-random-source* (lambda () #x80000001))) (init-random-state-seeds))
  #-wasm32-target (values #x8000 1))

(defun loader-level1-seed-max ()
  #+wasm32-target
  (let ((*wasm-random-source* (lambda () #xffffffff))) (init-random-state-seeds))
  #-wasm32-target (values #xffff #xffff))

(defun loader-level1-seed-refusals ()
  #+wasm32-target
  (values
   (let ((*wasm-random-source* nil))
     (handler-case (%wasm-random-u32) (error () t)))
   (let ((*wasm-random-source* (lambda () -1)))
     (handler-case (%wasm-random-u32) (type-error () t)))
   (let ((*wasm-random-source* (lambda () #x100000000)))
     (handler-case (%wasm-random-u32) (type-error () t)))
   (let ((*wasm-random-source* (lambda () 'bad)))
     (handler-case (%wasm-random-u32) (type-error () t))))
  #-wasm32-target (values t t t t))

(defun loader-level1-seed-collect ()
  #+wasm32-target
  (let* ((count 0)
         (*wasm-random-source* (lambda ()
                                (dotimes (i 12000) (cons i i))
                                (incf count)
                                #x12345678)))
    (multiple-value-bind (high low) (init-random-state-seeds)
      (values high low count)))
  #-wasm32-target (values #x1234 #x5678 1))

(defun loader-level1-random-state ()
  (let* ((state (initial-random-state))
         (copy (make-random-state state))
         (*random-state* copy))
    (values (random-state-p state)
            (not (eq state copy))
            (not (eq (random.mrg31k3p-state state) (random.mrg31k3p-state copy)))
            (%mrg31k3p state)
            (%mrg31k3p copy)
            (random 1000 state)
            (random 1000)
            (%mrg31k3p (make-random-state)))))

(defun loader-level1-random-fresh ()
  (let* ((count 0)
         (*wasm-random-source* (lambda () (incf count) #xffffffff))
         (state #+wasm32-target (make-random-state t)
                #-wasm32-target (progn (setq count 6)
                                      (initialize-mrg31k3p-state 4 4 4 4 4 4)))
         (seed (random.mrg31k3p-state state)))
    (values count (aref seed 0) (aref seed 1) (aref seed 2)
            (aref seed 3) (aref seed 4) (aref seed 5)
            (%mrg31k3p state))))

(defun loader-level1-local-special ()
  (let ((loader-local-special 17))
    (declare (special loader-local-special))
    (flet ((read-it () (declare (special loader-local-special)) loader-local-special))
      (values (read-it)
              (let ((loader-local-special 29))
                (declare (special loader-local-special))
                (read-it))
              (read-it)))))

(defun loader-level1-local-functions ()
  (labels ((walk-even (n) (if (zerop n) t (walk-odd (1- n))))
           (walk-odd (n) (if (zerop n) nil (walk-even (1- n)))))
    (values (walk-even 18) (walk-odd 19) (walk-even 19) (walk-odd 18))))

(defun loader-level1-random-bounds ()
  (let ((state (initial-random-state)) (copy (initial-random-state)))
    (values
     (dolist (bound '(1 1000 #x20000000 #x100000000 #x10000000000000000) t)
       (dotimes (i 8)
         (let ((value (random bound state)))
           (unless (and (<= 0 value) (< value bound)
                        (= value (random bound copy)))
             (return-from loader-level1-random-bounds nil)))))
     (let ((value (random 1.0f0 state))) (and (<= 0.0f0 value) (< value 1.0f0)))
     (let ((value (random 1.0d0 state))) (and (<= 0.0d0 value) (< value 1.0d0))))))

(defun loader-level1-sort ()
  (values (sort-list (list 9 1 7 3 5 3) #'< nil)
          (%sort-list-no-key (list 1 9 3 7 5) #'>)
          (sort-list nil #'< nil)
          (sort-list (list 11) #'< nil)))

(defun loader-level1-sort-key ()
  (let* ((a (cons 2 :a)) (b (cons 1 :b)) (c (cons 2 :c))
         (d (cons 1 :d))
         (sorted (sort-list (list a b c d) #'< #'car)))
    (values (eq (first sorted) b) (eq (second sorted) d)
            (eq (third sorted) a) (eq (fourth sorted) c))))

(defun loader-level1-namespace-tables ()
  ;; Invoke the real namespace initializer after level-0 has made its tables.
  ;; Native has no namespace initializer; compare its unchanged bindings/table.
  (let ((names '(make-hash-table gethash puthash remhash clrhash maphash
                 hash-table-count sxhash))
        (functions nil)
        (preserved t)
        (table *lfun-names*))
    (dolist (name names)
      (push (cons name (symbol-function name)) functions))
    #+wasm32-target (%wasm-namespace-support-initialize)
    (dolist (entry functions)
      (unless (eq (cdr entry) (symbol-function (car entry)))
        (setq preserved nil)))
    (values preserved
            (eq table *lfun-names*)
            (eq (hash-table-weak-p *lfun-names*) :key))))
