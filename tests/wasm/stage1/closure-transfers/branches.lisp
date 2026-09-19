(in-package :wasm32-compiler)

;;; A branch is legal only in a statement/IF-arm position beneath this
;;; TAGBODY, with no intervening emitter-owned root or dynamic extent.
;;; Other operators may execute freely, but must contain no local GO.
;;; In particular a GO in IF's test, call operands, LET, PROG1, cleanup,
;;; binding, or another TAGBODY takes the existing addressed-exit path.
(defun b-branch-tagbody-p (tags forms)
  (labels ((no-go (x)
             (cond ((ccl::acode-p x)
                    (let ((op (ccl::acode-operator-name (ccl::acode-operator x))))
                      (case op
                        (ccl::local-go nil)
                        ((ccl::tag-label ccl::immediate ccl::closed-function ccl::simple-function) t)
                        (t (every #'no-go (ccl::acode-operands x))))))
                   ((consp x) (and (no-go (car x)) (no-go (cdr x))))
                   (t t)))
           (statement (x)
             (if (not (ccl::acode-p x)) (no-go x)
               (let ((op (ccl::acode-operator-name (ccl::acode-operator x)))
                     (args (ccl::acode-operands x)))
                 (case op
                   (ccl::local-go (member (first args) tags :test #'eq))
                   (ccl::tag-label t)
                   (ccl::%decls-body (statement (first args)))
                   (ccl::progn (every #'statement (first args)))
                   (ccl::if (and (no-go (first args)) (statement (second args)) (statement (third args))))
                   (t (no-go x)))))))
    (every #'statement forms)))

(defun b-tagbody (tags forms)
  (unless (b-branch-tagbody-p tags forms)
    (return-from b-tagbody (b-unwinding-tagbody tags forms)))
  (let* ((pc (temporary)) (label (concatenate 'string "$tag_branch_" (subseq pc 1)))
         (segments (list nil)) (positions nil) (index 0))
    (dolist (form forms)
      (if (eq (ccl::acode-operator-name (ccl::acode-operator form)) 'ccl::tag-label)
        (progn (incf index) (push nil segments)
               (push (cons (first (ccl::acode-operands form)) index) positions))
        (push form (car segments))))
    (unless (every (lambda (tag) (assoc tag positions :test #'eq)) tags)
      (refuse :b-tag-identity))
    (setq segments (mapcar #'reverse (reverse segments)))
    (let* ((*b-tail-position* nil)
           (*b-local-tags* (append (mapcar (lambda (p) (list (car p) pc (cdr p) nil label)) positions) *b-local-tags*))
           (body (with-output-to-string (s)
             (loop for segment in segments for n from 0 do
               (format s "(if (i32.le_u (local.get ~a) (i32.const ~d)) (then " pc n)
               (dolist (form segment) (format s "(drop ~a)" (b-scalar form)))
               (write-string "))" s)))))
      (b-wat "(local.set ~a (i32.const 0)) (loop ~a ~a) ~a"
        pc label body (b-multiple (make-b-raw-code :text "(i32.const 77825)"))))))
