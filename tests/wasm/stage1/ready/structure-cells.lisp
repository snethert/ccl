;;; DEFSTRUCT's hidden ancestry slot contains class cells, not foreign heap
;;; constants. Resolve the same names as CLASS-CELL's native MAKE-LOAD-FORM.
;;; The list spine is private to this instance; its cells have image identity.
(defun bootstrap-structure-cell-list (form)
  (when (and *b-cpl-conditions*
             (ccl::acode-p form)
             (eq (ccl::acode-operator-name (ccl::acode-operator form))
                 'ccl::immediate))
    (let ((cells (car (ccl::acode-operands form))))
      (and (consp cells) (ccl::proper-list-p cells)
           (every (lambda (cell) (typep cell 'ccl::class-cell)) cells)
           cells))))

(defun bootstrap-structure-cells (form)
  (let ((cells (bootstrap-structure-cell-list form)))
    (when cells
      (make-b-raw-code
       :text
       (reduce (lambda (cell tail)
                 (b-cons
                  (make-b-raw-code
                   :text (bootstrap-predicate-call
                          'ccl::find-class-cell
                          (list (make-b-raw-code
                                 :text (bootstrap-symbol (ccl::class-cell-name cell)))
                                (bootstrap-constant t))))
                  (make-b-raw-code :text tail)))
               cells :from-end t :initial-value "(i32.const 77825)")))))
