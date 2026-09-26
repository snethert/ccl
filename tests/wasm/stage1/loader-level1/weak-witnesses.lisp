(in-package "CCL")

;;; Indirect calls deliberately exercise the installed public function cells.
;;; Direct generated hash access can use the Wasm representation dispatchers;
;;; these calls check that native constructors/counting remain callable too.
;;; The product l0-def/l1-utils initializers also call MAKE-HASH-TABLE directly.
(defvar *loader-weak-table* nil)
(defvar *loader-weak-reference* nil)

(defun loader-weak-prepare (kind retain)
  (setq *loader-weak-reference* nil
        *loader-weak-table*
        (funcall (symbol-function 'make-hash-table)
                 :test (if (= kind 3) 'equal 'eq)
                 :weak (case kind (0 t) (1 :key) (t :value))
                 :shared t))
  (let* ((object (cons 41 43))
         (key (if (< kind 2) object (if (= kind 3) (list 71) 71)))
         (value (if (< kind 2) 97 object)))
    (puthash key *loader-weak-table* value)
    (unless (zerop retain) (setq *loader-weak-reference* object)))
  nil)

(defun loader-weak-result (kind retain)
  ;; The target runner performs PREPARE, then collects at an owner boundary.
  ;; Native uses the same producer/observer with GC between their activations.
  #-wasm32-target (progn (loader-weak-prepare kind retain) (gc))
  #+wasm32-target (declare (ignore retain))
  (let* ((weak (hash-table-weak-p *loader-weak-table*))
         (key (if (< kind 2) (or *loader-weak-reference* (cons 41 43))
                  (if (= kind 3) (list 71) 71))))
    (multiple-value-bind (value present)
        (gethash key *loader-weak-table* -1)
      (values (eq weak :key) (eq weak :value)
              (funcall (symbol-function 'hash-table-count) *loader-weak-table*)
              present (if (and present (>= kind 2)) (car value) value)))))

(defun loader-weak-types ()
  (values (typep (funcall (symbol-function 'make-hash-table) :test 'eq :weak t)
                 'hash-table)
          (typep 7 'hash-table) (typep (cons 1 2) 'hash-table)
          (typep (vector 1 2) 'hash-table)))

(defun loader-weak-operations (kind)
  (let* ((table (funcall (symbol-function 'make-hash-table)
                         :test (if (= kind 3) 'equal 'eq)
                         :weak (case kind (0 t) (1 :key) (t :value))
                         :shared t))
         (key (list 73))
         (sum 0))
    (puthash key table 17)
    (maphash (lambda (key value) (declare (ignore key)) (incf sum value)) table)
    (let* ((before (hash-table-count table))
           (removed (remhash key table))
           (after (hash-table-count table)))
      (puthash key table 19)
      (clrhash table)
      (values before sum removed after (hash-table-count table)))))
