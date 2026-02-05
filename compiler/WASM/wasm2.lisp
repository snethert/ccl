;;;-*- Mode: Lisp; Package: CCL -*-
;;;
;;; Minimal WASM32 backend (MVP bring-up).

(in-package "CCL")

(eval-when (:compile-toplevel :load-toplevel :execute)
  (require "NXENV")
  (require "WASMENV"))

(eval-when (:compile-toplevel :load-toplevel :execute)
  (unless (assq 'with-downward-closures *next-nx-operators*)
    (push '(with-downward-closures 0 :infer) *next-nx-operators*)))

(defun wasm2-unimplemented (&rest args)
  (error "WASM2: unimplemented opcode or feature: ~s" args))

(defvar *wasm2-specials* nil)
(defvar *wasm2-record-symbols* nil)
(defvar %wasm-compiled-modules% nil)
(defvar *wasm2-spillable-locals* nil)
(defvar *wasm2-spilling-p* nil)

(defconstant +wasm2-closure-cells-base+ 3)

(declaim (special *wasm2-skip-next-nx-defops* *nx1-operators*
                  *wasm2-cur-afunc* *wasm2-vstack* *wasm2-cstack*
                  *wasm2-target-fixnum-shift* *wasm2-target-node-shift*
                  *wasm2-target-bits-in-word* *wasm2-target-node-size*
                  *wasm2-ir* *wasm2-locals* *wasm2-local-count*
                  *wasm2-temp-local* *wasm2-label-counter*
                  *wasm2-spillable-locals*
                  *wasm2-spilling-p*
                  *wasm2-block-stack* *wasm2-tagbody-stack*
                  *wasm2-tagbody-global-map*
                  *wasm2-next-entry-index* *wasm2-emit-local-count*
                  *wasm2-emit-spillable-locals*
                  *wasm2-pending-throw-label*
                  *wasm2-use-arg-regs*
                  %wasm-compiled-modules%))
(unless (or (and (boundp '*wasm2-skip-next-nx-defops*)
                 *wasm2-skip-next-nx-defops*)
            (and (boundp '*nx1-operators*)
                 (hash-table-p *nx1-operators*)
                 (> (hash-table-count *nx1-operators*) 0)
                 (gethash 'with-downward-closures *nx1-operators*)))
  (next-nx-defops))

(defun initialize-wasm2-specials ()
  (let* ((newsize (%i+ (next-nx-num-ops) 10))
         (old *wasm2-specials*)
         (oldsize (if old (length old) 0)))
    (unless (>= oldsize newsize)
      (let* ((v (make-array newsize :initial-element #'wasm2-unimplemented)))
        (dotimes (i oldsize (setq *wasm2-specials* v))
          (setf (svref v i) (svref old i)))))))

(eval-when (:compile-toplevel :load-toplevel :execute)
  (initialize-wasm2-specials))

(defun wasm2-form (seg vreg xfer form)
  (let* ((op (acode-operator form)))
    (apply (svref *wasm2-specials* (%ilogand operator-id-mask op))
           seg vreg xfer (acode-operands form))))

(eval-when (:compile-toplevel :execute :load-toplevel)
  (defmacro defwasm2 (name locative arglist &body forms)
    (multiple-value-bind (body decls)
        (parse-body forms nil t)
      (destructuring-bind (seg dest control &rest other-args) arglist
        (let* ((fun `(nfunction ,name
                      (lambda (,seg ,dest ,control ,@other-args) ,@decls
                        (block ,name ,@body)))))
          `(progn
             (record-source-file ',name 'function)
             (svset *wasm2-specials* (%ilogand #.operator-id-mask (%nx1-operator ,locative)) ,fun)))))))

(defwasm2 wasm2-nil nil (seg vreg xfer)
  (declare (ignore seg vreg))
  (if (wasm2-returning-p xfer)
    (wasm2-emit-constant-return (target-nil-value))
    (wasm2-emit-const (target-nil-value)))
  nil)

(defwasm2 wasm2-t t (seg vreg xfer)
  (declare (ignore seg vreg))
  (if (wasm2-returning-p xfer)
    (wasm2-emit-constant-return (target-t-value))
    (wasm2-emit-const (target-t-value)))
  nil)

(defwasm2 wasm2-fixnum fixnum (seg vreg xfer value)
  (declare (ignore seg vreg))
  (let* ((boxed (wasm2-box-fixnum value)))
    (if (wasm2-returning-p xfer)
      (wasm2-emit-constant-return boxed)
      (wasm2-emit-const boxed)))
  nil)

(defwasm2 wasm2-fixnum-add-no-overflow fixnum-add-no-overflow (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-add)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-add)))
  nil)

(defwasm2 wasm2-fixnum-add-overflow fixnum-add-overflow (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-add)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-add)))
  nil)

(defwasm2 wasm2-add2 add2 (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-add)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-add)))
  nil)

(defwasm2 wasm2-fixnum-sub-no-overflow fixnum-sub-no-overflow (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-sub)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-sub)))
  nil)

(defwasm2 wasm2-fixnum-sub-overflow fixnum-sub-overflow (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-sub)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-sub)))
  nil)

(defwasm2 wasm2-sub2 sub2 (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-sub)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-sub)))
  nil)

(defwasm2 wasm2-%i+ %i+ (seg vreg xfer x y &optional overflow)
  (declare (ignore vreg overflow))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-add)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-add)))
  nil)

(defwasm2 wasm2-%i- %i- (seg vreg xfer x y &optional overflow)
  (declare (ignore vreg overflow))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-sub)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-sub)))
  nil)

(defwasm2 wasm2-%i* %i* (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-mul)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-mul)))
  nil)

(defwasm2 wasm2-mul2 mul2 (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-mul)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-mul)))
  nil)

(defwasm2 wasm2-fixnum-ash fixnum-ash (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-ash)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-ash)))
  nil)

(defwasm2 wasm2-%ilogand2 %ilogand2 (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-logand)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-logand)))
  nil)

(defwasm2 wasm2-%ilogior2 %ilogior2 (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-logior)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-logior)))
  nil)

(defwasm2 wasm2-%ilogxor2 %ilogxor2 (seg vreg xfer x y)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x)
           (wasm2-arg1-form-p y))
    (wasm2-emit-fixnum-logxor)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-form seg nil nil y)
      (wasm2-emit :fixnum-logxor)))
  nil)

(defwasm2 wasm2-%ilognot %ilognot (seg vreg xfer x)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x))
    (wasm2-emit-fixnum-lognot)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-emit :fixnum-lognot)))
  nil)

(defwasm2 wasm2-%ineg %ineg (seg vreg xfer x)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x))
    (wasm2-emit-fixnum-neg)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-emit :fixnum-neg)))
  nil)

(defwasm2 wasm2-%%ineg %%ineg (seg vreg xfer x)
  (declare (ignore vreg))
  (if (and (wasm2-returning-p xfer)
           (wasm2-arg0-form-p x))
    (wasm2-emit-fixnum-neg)
    (progn
      (wasm2-form seg nil nil x)
      (wasm2-emit :fixnum-neg)))
  nil)

(defwasm2 wasm2-fixnum-overflow fixnum-overflow (seg vreg xfer form)
  (destructuring-bind (op n0 n1) (acode-unwrapped-form form)
    (backend-use-operator op seg vreg xfer n0 n1 (make-nx-t))))

(defwasm2 wasm2-immediate immediate (seg vreg xfer value)
  (declare (ignore seg vreg))
  (if (wasm2-returning-p xfer)
    (wasm2-emit-constant-return value)
    (wasm2-emit-const value))
  nil)

(defwasm2 wasm2-lexical-reference lexical-reference (seg vreg xfer varnode)
  (declare (ignore seg vreg))
  (when (wasm2-var-closed-p varnode)
    (if (wasm2-returning-p xfer)
      (progn
        (wasm2-emit-closed-var-value varnode)
        (wasm2-emit :set-arg0)
        (wasm2-emit :set-nargs 1)
        (wasm2-emit :return))
      (wasm2-emit-closed-var-value varnode))
    (return-from wasm2-lexical-reference nil))
  (cond
    ((wasm2-arg0-var-p varnode)
     (if (wasm2-returning-p xfer)
       (progn
         (wasm2-emit :return-arg0)
         (wasm2-emit :return))
       (wasm2-emit :arg0)))
    ((wasm2-arg1-var-p varnode)
     (if (wasm2-returning-p xfer)
       (progn
         (wasm2-emit :return-arg1)
         (wasm2-emit :return))
       (wasm2-emit :arg1)))
    (t
     (let* ((idx (wasm2-ensure-local varnode)))
       (wasm2-emit :local.get idx))))
  nil)

(defun wasm2-simple-arglist (afunc)
  (let* ((lambda-form (afunc-lambdaform afunc)))
    (when (and (consp lambda-form) (consp (cdr lambda-form)))
      (let* ((args (cadr lambda-form)))
        (when (and (listp args)
                   (<= 1 (length args) 2)
                   (every #'symbolp args)
                   (notany (lambda (sym) (member sym lambda-list-keywords)) args))
          args)))))

(defun wasm2-arg0-name (afunc)
  (let* ((args (wasm2-simple-arglist afunc)))
    (when args
      (car args))))

(defun wasm2-arg1-name (afunc)
  (let* ((args (wasm2-simple-arglist afunc)))
    (when (and args (cdr args))
      (cadr args))))

(defun wasm2-arglist-forms (arglist)
  (destructuring-bind (stack-forms reg-forms) arglist
    (append stack-forms (nreverse reg-forms))))

(defun wasm2-constant-lispobj (form)
  (let* ((val (nx2-constant-form-value (acode-unwrapped-form-value form))))
    (cond ((null val) (values nil nil))
          ((nx-null val) (values (target-nil-value) t))
          ((nx-t val) (values (target-t-value) t))
          ((and (acode-p val) (eq (acode-operator val) (%nx1-operator fixnum)))
           (values (wasm2-box-fixnum (car (acode-operands val))) t))
          ((and (acode-p val) (eq (acode-operator val) (%nx1-operator immediate)))
           (values (car (acode-operands val)) t))
          (t (values nil nil)))))

(defun wasm2-constant-symbol (form)
  (let* ((val (nx2-constant-form-value (acode-unwrapped-form-value form))))
    (when (and val (symbolp val))
      (return-from wasm2-constant-symbol val)))
  (when (and (acode-p form)
             (eq (acode-operator form) (%nx1-operator immediate)))
    (let* ((val (car (acode-operands form))))
      (when (symbolp val)
        val))))

(defun wasm2-trivial-p (form)
  (let* ((op (acode-operator form)))
    (or (eq op (%nx1-operator nil))
        (eq op (%nx1-operator t))
        (eq op (%nx1-operator fixnum))
        (eq op (%nx1-operator immediate))
        (eq op (%nx1-operator lexical-reference))
        (eq op (%nx1-operator simple-function)))))

(defun wasm2-test-arg0-p (testform)
  (when *wasm2-use-arg-regs*
    (let* ((var (nx2-lexical-reference-p testform))
           (arg0 (wasm2-arg0-name *wasm2-cur-afunc*)))
      (and var arg0 (eq (var-name var) arg0) (not (wasm2-var-closed-p var))))))

(defun wasm2-test-arg1-p (testform)
  (when *wasm2-use-arg-regs*
    (let* ((var (nx2-lexical-reference-p testform))
           (arg1 (wasm2-arg1-name *wasm2-cur-afunc*)))
      (and var arg1 (eq (var-name var) arg1) (not (wasm2-var-closed-p var))))))

(defvar *wasm2-use-arg-regs* nil)

(defun wasm2-arg0-form-p (form)
  (when *wasm2-use-arg-regs*
    (let* ((var (nx2-lexical-reference-p form))
           (arg0 (wasm2-arg0-name *wasm2-cur-afunc*)))
      (and var arg0 (eq (var-name var) arg0) (not (wasm2-var-closed-p var))))))

(defun wasm2-arg1-form-p (form)
  (when *wasm2-use-arg-regs*
    (let* ((var (nx2-lexical-reference-p form))
           (arg1 (wasm2-arg1-name *wasm2-cur-afunc*)))
      (and var arg1 (eq (var-name var) arg1) (not (wasm2-var-closed-p var))))))

(defwasm2 wasm2-if if (seg vreg xfer testform true false)
  (let* ((test-val (nx2-constant-form-value (acode-unwrapped-form-value testform))))
    (when test-val
      (wasm2-form seg vreg xfer (if (nx-null test-val) false true))
      (return-from wasm2-if nil)))
  (when (and (wasm2-returning-p xfer)
             (wasm2-test-arg0-p testform))
    (when (wasm2-arg0-form-p true)
      (multiple-value-bind (else-val else-ok) (wasm2-constant-lispobj false)
        (when else-ok
          (wasm2-emit :if-arg0-else else-val)
          (wasm2-emit :return)
          (return-from wasm2-if nil))))
    (multiple-value-bind (true-val true-ok) (wasm2-constant-lispobj true)
      (multiple-value-bind (false-val false-ok) (wasm2-constant-lispobj false)
        (when (and true-ok false-ok)
          (wasm2-emit :if-arg0 true-val false-val)
          (wasm2-emit :return)
          (return-from wasm2-if nil)))))
  (wasm2-form seg nil nil testform)
  (let* ((then-ir (wasm2-with-ir (lambda () (wasm2-form seg nil nil true))))
         (else-ir (wasm2-with-ir (lambda () (wasm2-form seg nil nil false)))))
    (wasm2-emit :if then-ir else-ir))
  nil)

(defwasm2 wasm2-throw throw (seg vreg xfer tag valform)
  (declare (ignore vreg xfer))
  (let* ((throw-fixnum (wasm2-box-fixnum (subprim-name->offset '.SPthrow))))
    (wasm2-form seg nil nil tag)
    (wasm2-emit :vpush)
    (if (wasm2-trivial-p valform)
      (progn
        (wasm2-form seg nil nil valform)
        (wasm2-emit :vpush)
        (wasm2-emit :set-nargs 1))
      (progn
    (wasm2-multiple-value-body seg valform)
    (wasm2-emit :drop)))
    (wasm2-emit-call-subprim-no-spill throw-fixnum)
    (wasm2-emit :pending-throw-branch)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-catch catch (seg vreg xfer tag valform)
  (declare (ignore vreg))
  (let* ((mv-pass (wasm2-mv-p xfer))
         (mkcatch-fixnum (wasm2-box-fixnum
                          (subprim-name->offset (if mv-pass '.SPmkcatchmv '.SPmkcatch1v))))
         (nthrow-fixnum (wasm2-box-fixnum
                         (subprim-name->offset (if mv-pass '.SPnthrowvalues '.SPnthrow1value)))))
    (wasm2-form seg nil nil tag)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim-no-spill mkcatch-fixnum)
    (if mv-pass
      (wasm2-multiple-value-body seg valform)
      (wasm2-form seg nil nil valform))
    (wasm2-emit :set-arg0)
    (wasm2-emit :set-imm0 (wasm2-box-fixnum 1))
    (wasm2-emit-call-subprim-no-spill nthrow-fixnum)
    (wasm2-emit :clear-pending-throw)
    (if (wasm2-returning-p xfer)
      (wasm2-emit :return)
      (wasm2-emit :arg0)))
  nil)

(defwasm2 wasm2-unwind-protect unwind-protect (seg vreg xfer protected-form cleanup-form)
  (declare (ignore vreg))
  (let* ((cleanup-label (wasm2-allocate-label))
         (mvpass (wasm2-mv-p xfer)))
    (if mvpass
      (let* ((save-fixnum (wasm2-subprim-fixnum '.SPsave-values))
             (recover-fixnum (wasm2-subprim-fixnum '.SPrecover-values))
             (protected-ir (wasm2-with-ir
                             (lambda ()
                               (let ((*wasm2-pending-throw-label* cleanup-label))
                                 (wasm2-form seg nil $backend-mvpass protected-form)
                                 (wasm2-emit-call-subprim-no-spill save-fixnum)
                                 (wasm2-emit :drop))))))
        (wasm2-emit :block cleanup-label protected-ir)
        (wasm2-form seg nil nil cleanup-form)
        (wasm2-emit :drop)
        (wasm2-emit :pending-throw-return)
        (wasm2-emit-call-subprim-no-spill recover-fixnum)
        (if (wasm2-returning-p xfer)
          (wasm2-emit :return)
          (wasm2-emit :arg0)))
      (let* ((result-temp (wasm2-allocate-temp))
             (protected-ir (wasm2-with-ir
                             (lambda ()
                               (let ((*wasm2-pending-throw-label* cleanup-label))
                                 (wasm2-form seg nil nil protected-form)
                                 (wasm2-emit :local.set result-temp))))))
        (wasm2-emit :block cleanup-label protected-ir)
        (wasm2-form seg nil nil cleanup-form)
        (wasm2-emit :drop)
        (wasm2-emit :pending-throw-return)
        (if (wasm2-returning-p xfer)
          (progn
            (wasm2-emit :local.get result-temp)
            (wasm2-emit :set-arg0)
            (wasm2-emit :set-nargs 1)
            (wasm2-emit :return))
          (wasm2-emit :local.get result-temp)))))
  nil)

(defwasm2 wasm2-local-block local-block (seg vreg xfer blocktag body)
  (declare (ignore vreg))
  (let* ((label (wasm2-allocate-label))
         (result-local (wasm2-allocate-temp))
         (mvpass (wasm2-mv-p xfer)))
    (setf (car blocktag) (list label result-local mvpass))
    (let* ((body-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-form seg nil (if mvpass $backend-mvpass nil) body)
                        (wasm2-emit :local.set result-local)))))
      (wasm2-emit :block label body-ir)
      (wasm2-emit :local.get result-local)))
  nil)

(defwasm2 wasm2-local-return-from local-return-from (seg vreg xfer blocktag value)
  (declare (ignore vreg xfer))
  (let* ((info (car blocktag)))
    (unless info
      (wasm2-unimplemented))
    (destructuring-bind (label result-local mvpass) info
      (wasm2-form seg nil (if mvpass $backend-mvpass nil) value)
      (wasm2-emit :local.set result-local)
      (wasm2-emit :br label)))
  nil)

(defwasm2 wasm2-local-tagbody local-tagbody (seg vreg xfer taglist body)
  (declare (ignore vreg xfer))
  (let* ((tagop (%nx1-operator tag-label)))
    (if (null taglist)
      (progn
        (dolist (form body)
          (wasm2-form seg nil nil form)
          (wasm2-emit :drop))
        (wasm2-emit-const (target-nil-value)))
      (let* ((entry-label (wasm2-allocate-label))
             (loop-label (wasm2-allocate-label))
             (exit-label (wasm2-allocate-label))
             (state-local (wasm2-allocate-raw-temp))
             (tag-map (make-hash-table :test #'eq))
             (tag-label-map (make-hash-table :test #'eq))
             (tag-labels (mapcar (lambda (_tag) (declare (ignore _tag)) (wasm2-allocate-label))
                                 taglist)))
        (loop for tag in taglist
              for idx from 1
              for label in tag-labels
              do (let* ((key (wasm2-tag-key tag)))
                   (setf (gethash key tag-map) idx)
                   (setf (gethash key tag-label-map) label)
                   (unless (eq key tag)
                     (setf (gethash tag tag-map) idx)
                     (setf (gethash tag tag-label-map) label))))
        (let* ((ctx (make-wasm2-tagbody-context :tag-map tag-map
                                                :loop-label loop-label
                                                :state-local state-local))
               (*wasm2-tagbody-stack* (cons ctx *wasm2-tagbody-stack*)))
          (when *wasm2-tagbody-global-map*
            (dolist (tag taglist)
              (let* ((key (wasm2-tag-key tag)))
                (setf (gethash key *wasm2-tagbody-global-map*) ctx)
                (unless (eq key tag)
                  (setf (gethash tag *wasm2-tagbody-global-map*) ctx)))))
          (let* ((segments nil)
                 (current-label entry-label)
                 (current-forms nil))
            (dolist (form body)
              (if (and (acode-p form) (eq (acode-operator form) tagop))
                (let* ((tag (cdar (acode-operands form)))
                       (label (or (gethash tag tag-label-map)
                                  (gethash (wasm2-tag-key tag) tag-label-map))))
                  (push (cons current-label (nreverse current-forms)) segments)
                  (setf current-label label)
                  (setf current-forms nil))
                (push form current-forms)))
            (push (cons current-label (nreverse current-forms)) segments)
            (setf segments (nreverse segments))
            (let* ((dispatch-labels (mapcar #'car segments))
                   (segment-count (length segments)))
              (labels
                  ((segment-ir (forms)
                     (wasm2-with-ir
                       (lambda ()
                         (dolist (form forms)
                           (wasm2-form seg nil nil form)
                           (wasm2-emit :drop)))))
                   (dispatch-ir ()
                     (list (cons :local.get (list state-local))
                           (cons :br-table (list dispatch-labels exit-label)))))
                (let* ((inner (dispatch-ir)))
                  (loop for segment in (reverse segments)
                        for idx from (1- segment-count) downto 0
                        do (let* ((seg-label (car segment))
                                  (forms (cdr segment))
                                  (seg-body (append (segment-ir forms)
                                                   (list (cons :const (list (1+ idx)))
                                                         (cons :local.set (list state-local))
                                                         (cons :br (list loop-label))))))
                             (setf inner (append (list (cons :block (list seg-label inner)))
                                                 seg-body))))
                  (wasm2-emit :const 0)
                  (wasm2-emit :local.set state-local)
                  (wasm2-emit :block exit-label (list (list :loop loop-label inner)))
                  (wasm2-emit-const (target-nil-value)))))))))
  nil))

(defwasm2 wasm2-local-go local-go (seg vreg xfer tag)
  (declare (ignore seg vreg xfer))
  (let* ((ctx (or (wasm2-find-tagbody-context tag)
                  (car *wasm2-tagbody-stack*))))
    (unless ctx
      (wasm2-unimplemented))
    (let* ((idx (or (gethash tag (wasm2-tagbody-context-tag-map ctx))
                    (gethash (wasm2-tag-key tag) (wasm2-tagbody-context-tag-map ctx)))))
      (unless idx
        (wasm2-unimplemented))
      (wasm2-emit :const idx)
      (wasm2-emit :local.set (wasm2-tagbody-context-state-local ctx))
      (wasm2-emit :br (wasm2-tagbody-context-loop-label ctx))))
  nil)

(defwasm2 wasm2-progn progn (seg vreg xfer forms)
  (if forms
    (progn
      (dolist (form (butlast forms))
        (wasm2-form seg nil nil form)
        (wasm2-emit :drop))
      (wasm2-form seg vreg xfer (car (last forms))))
    (wasm2-form seg vreg xfer (make-acode (%nx1-operator nil)))))

(defwasm2 wasm2-setq-lexical setq-lexical (seg vreg xfer varspec form)
  (declare (ignore vreg xfer))
  (when (wasm2-var-closed-p varspec)
    (wasm2-emit-closed-var-set seg varspec form)
    (return-from wasm2-setq-lexical nil))
  (wasm2-form seg nil nil form)
  (cond
    ((wasm2-arg0-var-p varspec)
     (let* ((tmp (wasm2-ensure-temp-local)))
       (wasm2-emit :local.tee tmp)
       (wasm2-emit :set-arg0)
       (wasm2-emit :local.get tmp)))
    ((wasm2-arg1-var-p varspec)
     (let* ((tmp (wasm2-ensure-temp-local)))
       (wasm2-emit :local.tee tmp)
       (wasm2-emit :set-arg1)
       (wasm2-emit :local.get tmp)))
    (t
     (let* ((idx (wasm2-ensure-local varspec)))
       (wasm2-emit :local.tee idx))))
  nil)

(defwasm2 wasm2-let let (seg vreg xfer vars vals body p2decls)
  (declare (ignore vreg p2decls))
  (let* ((temps (mapcar (lambda (_v) (declare (ignore _v)) (wasm2-allocate-temp)) vars)))
    (loop for val in vals
          for var in vars
          for tmp in temps
          do (if (wasm2-var-closed-p var)
               (wasm2-emit-make-closed-var-cell seg val)
               (wasm2-form seg nil nil val))
             (wasm2-emit :local.set tmp))
    (loop for var in vars
          for tmp in temps
          do (let* ((idx (wasm2-ensure-local var)))
               (wasm2-emit :local.get tmp)
               (wasm2-emit :local.set idx))))
  (wasm2-form seg nil xfer body)
  nil)

(defwasm2 wasm2-let* let* (seg vreg xfer vars vals body p2decls)
  (declare (ignore vreg p2decls))
  (loop for var in vars
        for val in vals
        do (if (wasm2-var-closed-p var)
             (wasm2-emit-make-closed-var-cell seg val)
             (wasm2-form seg nil nil val))
           (wasm2-emit :local.set (wasm2-ensure-local var)))
  (wasm2-form seg nil xfer body)
  nil)

(defwasm2 wasm2-with-downward-closures with-downward-closures (seg vreg xfer vars vals body p2decls)
  (wasm2-let* seg vreg xfer vars vals body p2decls))

(defwasm2 wasm2-lambda lambda-list (seg vreg xfer req opt rest keys auxen body p2decls &optional code-note)
  (declare (ignore vreg xfer p2decls code-note))
  (flet ((empty-spec-p (spec)
           (or (null spec)
               (and (listp spec) (every #'null spec)))))
    (when (or (not (empty-spec-p opt))
              rest
              (not (empty-spec-p keys))
              (not (empty-spec-p auxen)))
      (wasm2-unimplemented)))
  (when (> (length req) 2)
    (wasm2-unimplemented))
  (when (some #'wasm2-var-closed-p req)
    (wasm2-unimplemented))
  (wasm2-form seg nil $backend-return body)
  nil)

(defwasm2 wasm2-typed-form typed-form (seg vreg xfer typespec form &optional check)
  (declare (ignore typespec check))
  (wasm2-form seg vreg xfer form)
  nil)

(defwasm2 wasm2-type-asserted-form type-asserted-form (seg vreg xfer typespec form &optional check)
  (declare (ignore typespec check))
  (wasm2-form seg vreg xfer form)
  nil)

(defwasm2 wasm2-%decls-body %decls-body (seg vreg xfer form p2decls)
  (declare (ignore p2decls))
  (wasm2-form seg vreg xfer form)
  nil)

(defwasm2 wasm2-values values (seg vreg xfer forms)
  (declare (ignore vreg))
  (let* ((count (length forms))
         (mv-p (wasm2-mv-p xfer)))
    (cond
      ((= count 0)
       (if (wasm2-returning-p xfer)
         (wasm2-emit-constant-return (target-nil-value))
         (wasm2-emit-const (target-nil-value))))
      ((= count 1)
       (wasm2-form seg nil xfer (car forms)))
      (mv-p
       (let* ((temps (loop repeat count collect (wasm2-allocate-temp))))
         (loop for form in forms
               for tmp in temps
               do (wasm2-form seg nil nil form)
                  (wasm2-emit :local.set tmp))
         (if (<= count 4)
           (progn
             (dolist (tmp temps)
               (wasm2-emit :local.get tmp))
             (ecase count
               (2 (wasm2-emit :return-values2))
               (3 (wasm2-emit :return-values3))
               (4 (wasm2-emit :return-values4)))
             (when (wasm2-returning-p xfer)
               (wasm2-emit :drop)
               (wasm2-emit :return)))
           (progn
             (dolist (tmp (reverse temps))
               (wasm2-emit :local.get tmp)
               (wasm2-emit :vpush))
             (wasm2-emit :local.get (car temps))
             (wasm2-emit :set-arg0)
             (wasm2-emit :set-nargs count)
             (if (wasm2-returning-p xfer)
               (wasm2-emit :return)
               (wasm2-emit :arg0))))))
      ((= count 2)
       (let* ((tmp (wasm2-ensure-temp-local)))
         (wasm2-form seg nil nil (first forms))
         (wasm2-emit :local.set tmp)
         (wasm2-form seg nil nil (second forms))
         (wasm2-emit :drop)
         (wasm2-emit :local.get tmp)))
      (t
       (let* ((tmp (wasm2-ensure-temp-local)))
         (wasm2-form seg nil nil (first forms))
         (wasm2-emit :local.set tmp)
         (dolist (form (rest forms))
           (wasm2-form seg nil nil form)
           (wasm2-emit :drop))
         (wasm2-emit :local.get tmp)))))
  nil)

(defwasm2 wasm2-multiple-value-call multiple-value-call (seg vreg xfer fn arglist)
  (declare (ignore vreg))
  (let* ((args (wasm2-arglist-forms arglist))
         (argc (length args))
         (mvpass (wasm2-mv-p xfer))
         (fn-temp (wasm2-ensure-temp-local))
         (tmp (wasm2-ensure-temp-local))
         (funcall-fixnum (wasm2-subprim-fixnum '.SPfuncall))
         (save-fixnum (wasm2-subprim-fixnum '.SPsave-values))
         (add-fixnum (wasm2-subprim-fixnum '.SPadd-values))
         (recover-fixnum (wasm2-subprim-fixnum '.SPrecover-values)))
    (wasm2-form seg nil nil fn)
    (wasm2-emit :local.set fn-temp)
    (cond
      ((= argc 0)
       (wasm2-emit :local.get fn-temp)
       (wasm2-emit (if mvpass :call0-mv :call0) tmp))
      ((= argc 1)
       (wasm2-multiple-value-body seg (car args))
       (wasm2-emit :local.get fn-temp)
       (wasm2-emit :set-nfn)
       (wasm2-emit-call-subprim funcall-fixnum)
       (wasm2-emit :pending-throw-branch)
       (unless mvpass
         (wasm2-emit :restore-vsp))
       (if (wasm2-returning-p xfer)
         (wasm2-emit :return)
         (wasm2-emit :arg0)))
      (t
       (wasm2-multiple-value-body seg (car args))
       (wasm2-emit-call-subprim-no-spill save-fixnum)
       (dolist (form (cdr args))
         (wasm2-multiple-value-body seg form)
         (wasm2-emit-call-subprim-no-spill add-fixnum))
       (wasm2-emit-call-subprim-no-spill recover-fixnum)
       (wasm2-emit :local.get fn-temp)
       (wasm2-emit :set-nfn)
       (wasm2-emit-call-subprim funcall-fixnum)
       (wasm2-emit :pending-throw-branch)
       (unless mvpass
         (wasm2-emit :restore-vsp))
       (if (wasm2-returning-p xfer)
         (wasm2-emit :return)
         (wasm2-emit :arg0)))))
  nil)

(defwasm2 wasm2-multiple-value-bind multiple-value-bind (seg vreg xfer vars form body p2decls)
  (declare (ignore vreg p2decls))
  (wasm2-multiple-value-body seg form)
  (wasm2-emit :drop)
  (loop for var in vars
        for idx from 0
        do (wasm2-emit :get-mv idx)
           (if (wasm2-var-closed-p var)
             (progn
               (wasm2-emit-make-closed-var-cell-from-stack)
               (wasm2-emit :local.set (wasm2-ensure-local var)))
             (wasm2-emit :local.set (wasm2-ensure-local var))))
  (wasm2-emit :restore-vsp)
  (wasm2-form seg nil xfer body)
  nil)

(defwasm2 wasm2-nth-value nth-value (seg vreg xfer n form)
  (declare (ignore vreg xfer))
  (let* ((idx-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil n)
    (wasm2-emit :local.set idx-temp)
    (wasm2-multiple-value-body seg form)
    (wasm2-emit :drop)
    (wasm2-emit :local.get idx-temp)
    (wasm2-emit :get-mv-indexed)
    (wasm2-emit :restore-vsp))
  nil)

(defwasm2 wasm2-simple-function simple-function (seg vreg xfer afunc)
  (declare (ignore seg vreg xfer))
  (let* ((lfun (afunc-lfun afunc)))
    (unless lfun
      (wasm2-unimplemented))
    (wasm2-emit-const lfun))
  nil)

(defwasm2 wasm2-closed-function closed-function (seg vreg xfer afunc)
  (declare (ignore seg vreg xfer))
  (let* ((lfun (afunc-lfun afunc)))
    (unless lfun
      (wasm2-unimplemented))
    (let* ((inherited-vars (afunc-inherited-vars afunc))
           (vsize (+ (length inherited-vars) +wasm2-closure-cells-base+ 2))
           (subtag (wasm2-box-fixnum (nx-lookup-target-uvector-subtag :function)))
           (count (wasm2-box-fixnum vsize))
           (entry-index (getf (afunc-lfun-info afunc) 'wasm-entry-index))
           (entry-fixnum (if entry-index
                           (wasm2-box-fixnum entry-index)
                           (uvref lfun 0)))
           (code-fixnum entry-fixnum)
           (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
           (misc-set (wasm2-subprim-fixnum '.SPmisc-set))
           (vec-temp (wasm2-allocate-temp)))
      (wasm2-emit :const count)
      (wasm2-emit :set-arg1)
      (wasm2-emit :const subtag)
      (wasm2-emit :set-arg0)
      (wasm2-emit-call-subprim misc-alloc)
      (wasm2-emit :arg0)
      (wasm2-emit :local.set vec-temp)

      ;; slot 0: entrypoint
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit :const (wasm2-box-fixnum 0))
      (wasm2-emit :const entry-fixnum)
      (wasm2-emit :set-arg2)
      (wasm2-emit :set-arg1)
      (wasm2-emit :set-arg0)
      (wasm2-emit-call-subprim misc-set)

      ;; slot 1: codevector
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit :const (wasm2-box-fixnum 1))
      (wasm2-emit :const code-fixnum)
      (wasm2-emit :set-arg2)
      (wasm2-emit :set-arg1)
      (wasm2-emit :set-arg0)
      (wasm2-emit-call-subprim misc-set)

      ;; slot 2: lfun
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit :const (wasm2-box-fixnum 2))
      (wasm2-emit :const (target-nil-value))
      (wasm2-emit :set-arg2)
      (wasm2-emit :set-arg1)
      (wasm2-emit :set-arg0)
      (wasm2-emit-call-subprim misc-set)

      ;; slots 3..: captured cells
      (loop for var in inherited-vars
            for idx from 0
               do (wasm2-emit :local.get vec-temp)
                  (wasm2-emit :const (wasm2-box-fixnum (+ +wasm2-closure-cells-base+ idx)))
                  (wasm2-emit-closed-var-cell var)
                  (wasm2-emit :set-arg2)
                  (wasm2-emit :set-arg1)
                  (wasm2-emit :set-arg0)
                  (wasm2-emit-call-subprim misc-set))

      ;; name slot
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit :const (wasm2-box-fixnum (+ +wasm2-closure-cells-base+ (length inherited-vars))))
      (wasm2-emit :const (target-nil-value))
      (wasm2-emit :set-arg2)
      (wasm2-emit :set-arg1)
      (wasm2-emit :set-arg0)
      (wasm2-emit-call-subprim misc-set)

      ;; lfun-bits slot (trampoline)
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit :const (wasm2-box-fixnum (+ +wasm2-closure-cells-base+ (length inherited-vars) 1)))
      (wasm2-emit :const (wasm2-box-fixnum (ash 1 $lfbits-trampoline-bit)))
      (wasm2-emit :set-arg2)
      (wasm2-emit :set-arg1)
      (wasm2-emit :set-arg0)
      (wasm2-emit-call-subprim misc-set)

      (wasm2-emit :local.get vec-temp)))
  nil)

(defun wasm2-emit-call (seg fn arglist spread-p &optional xfer)
  (when spread-p
    (wasm2-unimplemented))
  (let* ((args (wasm2-arglist-forms arglist))
         (argc (length args))
         (mvpass (wasm2-mv-p xfer))
         (tmp (wasm2-ensure-temp-local)))
    (flet ((emit-fixnum-binary (opcode x y)
             (if (and (wasm2-returning-p xfer)
                      (wasm2-arg0-form-p x)
                      (wasm2-arg1-form-p y))
               (progn
                 (wasm2-emit opcode)
                 (wasm2-emit :return))
               (progn
                 (wasm2-form seg nil nil x)
                 (wasm2-form seg nil nil y)
                 (wasm2-emit opcode))))
           (emit-fixnum-unary (opcode x)
             (if (and (wasm2-returning-p xfer)
                      (wasm2-arg0-form-p x))
               (progn
                 (wasm2-emit opcode)
                 (wasm2-emit :return))
               (progn
                 (wasm2-form seg nil nil x)
                 (wasm2-emit opcode)))))
      (let* ((name (wasm2-constant-symbol fn)))
        (when name
          (case name
            ((fixnum-ash)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-ash (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((%i+)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-add (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((%i-)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-sub (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((%i*)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-mul (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((logand)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-logand (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((%ilogand2)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-logand (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((logior)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-logior (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((%ilogior2)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-logior (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((logxor)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-logxor (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((%ilogxor2)
             (when (= argc 2)
               (emit-fixnum-binary :fixnum-logxor (first args) (second args))
               (return-from wasm2-emit-call nil)))
            ((lognot)
             (when (= argc 1)
               (emit-fixnum-unary :fixnum-lognot (first args))
               (return-from wasm2-emit-call nil)))
            ((%ilognot)
             (when (= argc 1)
               (emit-fixnum-unary :fixnum-lognot (first args))
               (return-from wasm2-emit-call nil)))
            ((%ineg)
             (when (= argc 1)
               (emit-fixnum-unary :fixnum-neg (first args))
               (return-from wasm2-emit-call nil)))
            ((%%ineg)
             (when (= argc 1)
               (emit-fixnum-unary :fixnum-neg (first args))
               (return-from wasm2-emit-call nil)))))))
    (wasm2-form seg nil nil fn)
    (dolist (arg args)
      (wasm2-form seg nil nil arg))
    (ecase argc
      (0 (wasm2-emit (if mvpass :call0-mv :call0) tmp))
      (1 (wasm2-emit (if mvpass :call1-mv :call1) tmp))
      (2 (wasm2-emit (if mvpass :call2-mv :call2) tmp)))
    (when (wasm2-returning-p xfer)
      ;; Consume the wasm stack result; arg regs already hold the values.
      (wasm2-emit :drop)
      (wasm2-emit :return))))

(defwasm2 wasm2-call call (seg vreg xfer fn arglist &optional spread-p)
  (declare (ignore vreg))
  (wasm2-emit-call seg fn arglist spread-p xfer)
  nil)

(defwasm2 wasm2-builtin-call builtin-call (seg vreg xfer fn arglist)
  (declare (ignore vreg))
  (wasm2-emit-call seg fn arglist nil xfer)
  nil)

(defwasm2 wasm2-lexical-function-call lexical-function-call (seg vreg xfer afunc arglist &optional spread-p)
  (declare (ignore vreg))
  (let* ((lfun (afunc-lfun afunc)))
    (unless lfun
      (wasm2-unimplemented))
    (wasm2-emit-const lfun))
  (let* ((args (wasm2-arglist-forms arglist))
         (argc (length args))
         (mvpass (wasm2-mv-p xfer))
         (tmp (wasm2-ensure-temp-local)))
    (dolist (arg args)
      (wasm2-form seg nil nil arg))
    (when spread-p
      (wasm2-unimplemented))
    (ecase argc
      (0 (wasm2-emit (if mvpass :call0-mv :call0) tmp))
      (1 (wasm2-emit (if mvpass :call1-mv :call1) tmp))
      (2 (wasm2-emit (if mvpass :call2-mv :call2) tmp))))
  nil)

(defwasm2 wasm2-self-call self-call (seg vreg xfer arglist &optional spread-p)
  (declare (ignore vreg))
  (let* ((lfun (afunc-lfun *wasm2-cur-afunc*)))
    (unless lfun
      (wasm2-unimplemented))
    (wasm2-emit-const lfun))
  (let* ((args (wasm2-arglist-forms arglist))
         (argc (length args))
         (mvpass (wasm2-mv-p xfer))
         (tmp (wasm2-ensure-temp-local)))
    (dolist (arg args)
      (wasm2-form seg nil nil arg))
    (when spread-p
      (wasm2-unimplemented))
    (ecase argc
      (0 (wasm2-emit (if mvpass :call0-mv :call0) tmp))
      (1 (wasm2-emit (if mvpass :call1-mv :call1) tmp))
      (2 (wasm2-emit (if mvpass :call2-mv :call2) tmp))))
  nil)

(defvar *wasm2-cur-afunc* nil)
(defvar *wasm2-vstack* 0)
(defvar *wasm2-cstack* 0)
(defvar *wasm2-target-fixnum-shift* 0)
(defvar *wasm2-target-node-shift* 0)
(defvar *wasm2-target-bits-in-word* 0)
(defvar *wasm2-target-node-size* 0)
(defvar *wasm2-ir* nil)
(defvar *wasm2-locals* nil)
(defvar *wasm2-local-count* 0)
(defvar *wasm2-temp-local* nil)
(defvar *wasm2-label-counter* 0)
(defvar *wasm2-block-stack* nil)
(defvar *wasm2-tagbody-stack* nil)
(defvar *wasm2-tagbody-global-map* nil)
(defvar *wasm2-next-entry-index* 300)
(defvar *wasm2-emit-local-count* 0)
(defvar *wasm2-emit-spillable-locals* nil)
(defvar *wasm2-pending-throw-label* nil)

(defstruct wasm2-tagbody-context
  tag-map
  loop-label
  state-local)

(defun wasm2-register-compiled-module (module-bytes export-name entry-index module-version)
  (when module-bytes
    (let* ((entry (make-array 4 :initial-contents
                              (list module-bytes export-name entry-index module-version))))
      (unless (find entry-index %wasm-compiled-modules%
                    :key (lambda (item) (svref item 2))
                    :test #'eql)
        (setf %wasm-compiled-modules% (cons entry %wasm-compiled-modules%))))))

(defun wasm2-emit (opcode &rest operands)
  (push (cons opcode operands) *wasm2-ir*)
  nil)

(defun wasm2-returning-p (xfer)
  (eq xfer $backend-return))

(defun wasm2-mvpass-p (xfer)
  (and xfer (or (eq xfer $backend-mvpass)
                (logbitp $backend-mvpass-bit xfer))))

(defun wasm2-mv-p (xfer)
  (or (eq xfer $backend-return) (wasm2-mvpass-p xfer)))

(defun wasm2-allocate-label ()
  (prog1 *wasm2-label-counter*
    (incf *wasm2-label-counter*)))

(defun wasm2-tag-key (tag)
  (if (and (consp tag) (symbolp (car tag)))
    (car tag)
    tag))

(defun wasm2-find-tagbody-context (tag)
  (let* ((key (wasm2-tag-key tag)))
    (or (dolist (ctx *wasm2-tagbody-stack* nil)
          (when (or (gethash tag (wasm2-tagbody-context-tag-map ctx))
                    (gethash key (wasm2-tagbody-context-tag-map ctx)))
            (return ctx)))
        (when *wasm2-tagbody-global-map*
          (or (gethash tag *wasm2-tagbody-global-map*)
              (gethash key *wasm2-tagbody-global-map*))))))

(defun wasm2-reset-locals ()
  (setf *wasm2-locals* (make-hash-table :test #'eq))
  (setf *wasm2-local-count* 0)
  (setf *wasm2-temp-local* nil)
  (setf *wasm2-spillable-locals* nil)
  nil)

(defun wasm2-allocate-local (&optional (spillp t))
  (let* ((idx *wasm2-local-count*))
    (incf *wasm2-local-count*)
    (when spillp
      (push idx *wasm2-spillable-locals*))
    idx))

(defun wasm2-ensure-local (var)
  (or (gethash var *wasm2-locals*)
      (setf (gethash var *wasm2-locals*)
            (wasm2-allocate-local))))

(defun wasm2-allocate-temp ()
  (wasm2-allocate-local))

(defun wasm2-allocate-raw-temp ()
  (wasm2-allocate-local nil))

(defun wasm2-ensure-temp-local ()
  (or *wasm2-temp-local*
      (setf *wasm2-temp-local* (wasm2-allocate-temp))))

(defun wasm2-var-closed-p (var)
  (logbitp $vbitclosed (nx-var-bits var)))

(defun wasm2-closed-var-index (var)
  (let* ((vars (afunc-inherited-vars *wasm2-cur-afunc*)))
    (position var vars :test #'eq)))

(defun wasm2-closed-var-slot (var)
  (let* ((idx (wasm2-closed-var-index var)))
    (when idx
      (+ +wasm2-closure-cells-base+ idx))))

(defun wasm2-subprim-fixnum (name)
  (wasm2-box-fixnum (subprim-name->offset name)))

(defun wasm2-emit-closed-var-cell (var)
  (let* ((slot (wasm2-closed-var-slot var))
         (misc-ref (wasm2-subprim-fixnum '.SPmisc-ref)))
    (if slot
      (wasm2-with-spilled-locals
        (lambda ()
          (wasm2-emit :get-nfn)
          (wasm2-emit :const (wasm2-box-fixnum slot))
          (wasm2-emit :set-arg1)
          (wasm2-emit :set-arg0)
          (wasm2-emit-call-subprim misc-ref)
          (wasm2-emit :arg0)))
      (let* ((idx (wasm2-ensure-local (nx-root-var var))))
        (wasm2-emit :local.get idx)))))

(defun wasm2-emit-closed-var-value (var)
  (let* ((misc-ref (wasm2-subprim-fixnum '.SPmisc-ref)))
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit-closed-var-cell var)
        (wasm2-emit :const (wasm2-box-fixnum 0))
        (wasm2-emit :set-arg1)
        (wasm2-emit :set-arg0)
        (wasm2-emit-call-subprim misc-ref)
        (wasm2-emit :arg0)))))

(defun wasm2-emit-closed-var-set (seg var value-form)
  (let* ((misc-set (wasm2-subprim-fixnum '.SPmisc-set))
         (val-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil value-form)
    (wasm2-emit :local.set val-temp)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit-closed-var-cell var)
        (wasm2-emit :const (wasm2-box-fixnum 0))
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg2)
        (wasm2-emit :set-arg1)
        (wasm2-emit :set-arg0)
        (wasm2-emit-call-subprim misc-set)
        (wasm2-emit :arg0)))))

(defun wasm2-emit-make-closed-var-cell (seg value-form)
  (let* ((val-temp (wasm2-allocate-temp))
         (vec-temp (wasm2-allocate-temp))
         (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
         (misc-set (wasm2-subprim-fixnum '.SPmisc-set))
         (subtag (wasm2-box-fixnum (nx-lookup-target-uvector-subtag :simple-vector)))
         (count (wasm2-box-fixnum 1)))
    (wasm2-form seg nil nil value-form)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :const count)
    (wasm2-emit :set-arg1)
    (wasm2-emit :const subtag)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-alloc)
    (wasm2-emit :arg0)
    (wasm2-emit :local.set vec-temp)
    (wasm2-emit :local.get vec-temp)
    (wasm2-emit :const (wasm2-box-fixnum 0))
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :set-arg2)
    (wasm2-emit :set-arg1)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-set)
    (wasm2-emit :local.get vec-temp)))

(defun wasm2-emit-make-closed-var-cell-from-stack ()
  (let* ((val-temp (wasm2-allocate-temp))
         (vec-temp (wasm2-allocate-temp))
         (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
         (misc-set (wasm2-subprim-fixnum '.SPmisc-set))
         (subtag (wasm2-box-fixnum (nx-lookup-target-uvector-subtag :simple-vector)))
         (count (wasm2-box-fixnum 1)))
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :const count)
    (wasm2-emit :set-arg1)
    (wasm2-emit :const subtag)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-alloc)
    (wasm2-emit :arg0)
    (wasm2-emit :local.set vec-temp)
    (wasm2-emit :local.get vec-temp)
    (wasm2-emit :const (wasm2-box-fixnum 0))
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :set-arg2)
    (wasm2-emit :set-arg1)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-set)
    (wasm2-emit :local.get vec-temp)))

(defun wasm2-arg0-var-p (var)
  (and *wasm2-use-arg-regs*
       (wasm2-arg0-var-name-p var)
       (not (wasm2-var-closed-p var))))

(defun wasm2-arg1-var-p (var)
  (and *wasm2-use-arg-regs*
       (wasm2-arg1-var-name-p var)
       (not (wasm2-var-closed-p var))))

(defun wasm2-arg0-var-name-p (var)
  (let* ((arg0 (wasm2-arg0-name *wasm2-cur-afunc*)))
    (and arg0 (eq (var-name var) arg0))))

(defun wasm2-arg1-var-name-p (var)
  (let* ((arg1 (wasm2-arg1-name *wasm2-cur-afunc*)))
    (and arg1 (eq (var-name var) arg1))))

(defun wasm2-multiple-value-body (seg form)
  (wasm2-form seg nil $backend-mvpass form))

(defun wasm2-with-ir (thunk)
  (let ((*wasm2-ir* nil))
    (funcall thunk)
    (nreverse *wasm2-ir*)))

(defun wasm2-arg-prologue-ir ()
  (unless *wasm2-use-arg-regs*
    (wasm2-with-ir
      (lambda ()
        (dolist (var (afunc-all-vars *wasm2-cur-afunc*))
          (when (and (not (wasm2-var-closed-p var))
                     (or (wasm2-arg0-var-name-p var)
                         (wasm2-arg1-var-name-p var)))
            (let* ((idx (wasm2-ensure-local var)))
              (if (wasm2-arg0-var-name-p var)
                (wasm2-emit :arg0)
                (wasm2-emit :arg1))
              (wasm2-emit :local.set idx))))))))

(defun wasm2-closed-arg-prologue-ir ()
  (wasm2-with-ir
    (lambda ()
      (dolist (var (afunc-all-vars *wasm2-cur-afunc*))
        (when (wasm2-var-closed-p var)
          (cond
            ((wasm2-arg0-var-name-p var)
             (wasm2-emit :arg0))
            ((wasm2-arg1-var-name-p var)
             (wasm2-emit :arg1))
            (t
             (setf var nil)))
          (when var
            (wasm2-emit-make-closed-var-cell-from-stack)
            (wasm2-emit :local.set (wasm2-ensure-local var))))))))

(defun wasm2-emit-constant-return (value)
  (wasm2-emit :const value)
  (wasm2-emit :set-arg-z)
  (wasm2-emit :set-nargs 1)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-const (value)
  (wasm2-emit :const value)
  nil)

(defun wasm2-with-spilled-locals (thunk)
  (if *wasm2-spilling-p*
    (funcall thunk)
    (let ((*wasm2-spilling-p* t))
      (wasm2-emit :spill-locals)
      (funcall thunk)
      (wasm2-emit :restore-locals))))

(defun wasm2-emit-call-subprim (fixnum)
  (wasm2-with-spilled-locals
    (lambda ()
      (wasm2-emit :call-subprim fixnum))))

;; For VSP-sensitive subprims that do not GC: avoid spilling via VSP.
(defun wasm2-emit-call-subprim-no-spill (fixnum)
  (wasm2-emit :call-subprim fixnum))

(defun wasm2-emit-fixnum-add ()
  (wasm2-emit :fixnum-add)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-fixnum-sub ()
  (wasm2-emit :fixnum-sub)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-fixnum-mul ()
  (wasm2-emit :fixnum-mul)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-fixnum-ash ()
  (wasm2-emit :fixnum-ash)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-fixnum-logand ()
  (wasm2-emit :fixnum-logand)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-fixnum-logior ()
  (wasm2-emit :fixnum-logior)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-fixnum-logxor ()
  (wasm2-emit :fixnum-logxor)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-fixnum-lognot ()
  (wasm2-emit :fixnum-lognot)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-fixnum-neg ()
  (wasm2-emit :fixnum-neg)
  (wasm2-emit :return)
  nil)

(defconstant +wasm-const-entry-index+ 202)
(defconstant +wasm-const-export-name+ "ccl_const_entry")
(defconstant +wasm-const-module-version+ 1)
(defconstant +wasm-fixnum-add-entry-index+ 204)
(defconstant +wasm-fixnum-add-export-name+ "ccl_fixnum_add_entry")
(defconstant +wasm-fixnum-add-module-version+ 1)
(defconstant +wasm-fixnum-sub-entry-index+ 205)
(defconstant +wasm-fixnum-sub-export-name+ "ccl_fixnum_sub_entry")
(defconstant +wasm-fixnum-sub-module-version+ 1)
(defconstant +wasm-fixnum-mul-entry-index+ 206)
(defconstant +wasm-fixnum-mul-export-name+ "ccl_fixnum_mul_entry")
(defconstant +wasm-fixnum-mul-module-version+ 1)
(defconstant +wasm-fixnum-ash-entry-index+ 207)
(defconstant +wasm-fixnum-ash-export-name+ "ccl_fixnum_ash_entry")
(defconstant +wasm-fixnum-ash-module-version+ 1)
(defconstant +wasm-fixnum-logand-entry-index+ 208)
(defconstant +wasm-fixnum-logand-export-name+ "ccl_fixnum_logand_entry")
(defconstant +wasm-fixnum-logand-module-version+ 1)
(defconstant +wasm-fixnum-logior-entry-index+ 209)
(defconstant +wasm-fixnum-logior-export-name+ "ccl_fixnum_logior_entry")
(defconstant +wasm-fixnum-logior-module-version+ 1)
(defconstant +wasm-fixnum-logxor-entry-index+ 210)
(defconstant +wasm-fixnum-logxor-export-name+ "ccl_fixnum_logxor_entry")
(defconstant +wasm-fixnum-logxor-module-version+ 1)
(defconstant +wasm-fixnum-lognot-entry-index+ 211)
(defconstant +wasm-fixnum-lognot-export-name+ "ccl_fixnum_lognot_entry")
(defconstant +wasm-fixnum-lognot-module-version+ 1)
(defconstant +wasm-fixnum-neg-entry-index+ 212)
(defconstant +wasm-fixnum-neg-export-name+ "ccl_fixnum_neg_entry")
(defconstant +wasm-fixnum-neg-module-version+ 1)
(defconstant +wasm-if-entry-index+ 213)
(defconstant +wasm-if-export-name+ "ccl_if_entry")
(defconstant +wasm-if-module-version+ 1)
(defconstant +wasm-if-arg-entry-index+ 214)
(defconstant +wasm-if-arg-export-name+ "ccl_if_arg_entry")
(defconstant +wasm-if-arg-module-version+ 1)
(defconstant +wasm-identity-entry-index+ 215)
(defconstant +wasm-identity-export-name+ "ccl_identity_entry")
(defconstant +wasm-identity-module-version+ 1)
(defconstant +wasm-identity-y-entry-index+ 216)
(defconstant +wasm-identity-y-export-name+ "ccl_identity_y_entry")
(defconstant +wasm-identity-y-module-version+ 1)

(defun wasm2-push-u8 (vec byte)
  (vector-push-extend (logand byte #xff) vec)
  vec)

(defun wasm2-emit-uleb (vec value)
  (let ((v value))
    (loop
      (let* ((byte (logand v #x7f))
             (rest (ash v -7)))
        (if (zerop rest)
          (progn
            (wasm2-push-u8 vec byte)
            (return))
          (progn
            (wasm2-push-u8 vec (logior byte #x80))
            (setf v rest))))))
  vec)

(defun wasm2-emit-sleb32 (vec value)
  (let ((v value))
    (loop
      (let* ((byte (logand v #x7f))
             (sign-bit (logand byte #x40))
             (rest (ash v -7))
             (done (or (and (zerop rest) (zerop sign-bit))
                       (and (= rest -1) (not (zerop sign-bit))))))
        (when (not done)
          (setf byte (logior byte #x80)))
        (wasm2-push-u8 vec byte)
        (when done
          (return))
        (setf v rest))))
  vec)

(defun wasm2-emit-bytes (vec bytes)
  (dolist (b bytes vec)
    (wasm2-push-u8 vec b)))

(defun wasm2-emit-string (vec string)
  (let* ((octets (map 'vector #'char-code string)))
    (wasm2-emit-uleb vec (length octets))
    (dotimes (i (length octets) vec)
      (wasm2-push-u8 vec (aref octets i)))))

(defun wasm2-section (id contents)
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-push-u8 out id)
    (wasm2-emit-uleb out (length contents))
    (dotimes (i (length contents) out)
      (wasm2-push-u8 out (aref contents i)))))

(defconstant +wasm2-type-void-i32+ 0)
(defconstant +wasm2-type-i32-void+ 1)
(defconstant +wasm2-type-void-void+ 2)
(defconstant +wasm2-type-i32-i32+ 3)
(defconstant +wasm2-type-i32-i32-i32+ 4)
(defconstant +wasm2-type-i32-i32-ret+ 5)
(defconstant +wasm2-type-i32-i32-i32-i32+ 6)

(defparameter *wasm2-generic-imports*
  (list
   (list :pending-throw "wasm_pending_throw_p" +wasm2-type-void-i32+)
   (list :get-arg-z "wasm_get_arg_z" +wasm2-type-void-i32+)
   (list :get-arg-y "wasm_get_arg_y" +wasm2-type-void-i32+)
   (list :get-nfn "wasm_get_nfn" +wasm2-type-void-i32+)
   (list :get-nargs "wasm_get_nargs" +wasm2-type-void-i32+)
   (list :get-lisp-nil "wasm_get_lisp_nil" +wasm2-type-void-i32+)
   (list :return-constant "wasm_return_constant" +wasm2-type-i32-void+)
   (list :set-arg-z "wasm_set_arg_z" +wasm2-type-i32-void+)
   (list :set-arg-y "wasm_set_arg_y" +wasm2-type-i32-void+)
   (list :set-arg-x "wasm_set_arg_x" +wasm2-type-i32-void+)
   (list :set-nargs "wasm_set_nargs" +wasm2-type-i32-void+)
   (list :set-nfn "wasm_set_nfn" +wasm2-type-i32-void+)
   (list :return-fixnum-add "wasm_return_fixnum_add" +wasm2-type-void-void+)
   (list :return-fixnum-sub "wasm_return_fixnum_sub" +wasm2-type-void-void+)
   (list :return-fixnum-mul "wasm_return_fixnum_mul" +wasm2-type-void-void+)
   (list :return-fixnum-ash "wasm_return_fixnum_ash" +wasm2-type-void-void+)
   (list :return-fixnum-neg "wasm_return_fixnum_neg" +wasm2-type-void-void+)
   (list :return-fixnum-logand "wasm_return_fixnum_logand" +wasm2-type-void-void+)
   (list :return-fixnum-logior "wasm_return_fixnum_logior" +wasm2-type-void-void+)
   (list :return-fixnum-logxor "wasm_return_fixnum_logxor" +wasm2-type-void-void+)
   (list :return-fixnum-lognot "wasm_return_fixnum_lognot" +wasm2-type-void-void+)
   (list :funcall0 "wasm_funcall0" +wasm2-type-i32-i32-ret+)
   (list :funcall1 "wasm_funcall1" +wasm2-type-i32-i32+)
   (list :funcall2 "wasm_funcall2" +wasm2-type-i32-i32-i32+)
   (list :funcall0-mv "wasm_funcall0_mv" +wasm2-type-i32-i32-ret+)
   (list :funcall1-mv "wasm_funcall1_mv" +wasm2-type-i32-i32+)
   (list :funcall2-mv "wasm_funcall2_mv" +wasm2-type-i32-i32-i32+)
   (list :return-values2 "wasm_return_values2" +wasm2-type-i32-i32+)
   (list :return-values3 "wasm_return_values3" +wasm2-type-i32-i32-i32+)
   (list :return-values4 "wasm_return_values4" +wasm2-type-i32-i32-i32-i32+)
   (list :get-mv "wasm_get_mv" +wasm2-type-i32-i32-ret+)
   (list :get-mv-indexed "wasm_get_mv_indexed" +wasm2-type-i32-i32-ret+)
   (list :restore-vsp "wasm_restore_vsp" +wasm2-type-void-void+)
   (list :call-subprim "wasm_call_subprim_fixnum" +wasm2-type-i32-void+)
   (list :set-imm0 "wasm_set_imm0" +wasm2-type-i32-void+)
   (list :vpush "wasm_vpush" +wasm2-type-i32-void+)
   (list :vpop "wasm_vpop" +wasm2-type-void-i32+)
   (list :clear-pending-throw "wasm_clear_pending_throw" +wasm2-type-void-void+)))

(defun wasm2-generic-import-index (key)
  (or (position key *wasm2-generic-imports* :key #'car :test #'eq)
      (error "Unknown WASM import key: ~s" key)))

(defun wasm2-emit-call-index (body index)
  (wasm2-push-u8 body #x10)
  (wasm2-emit-uleb body index))

(defun wasm2-emit-spill-locals (body &optional locals)
  (let* ((spill-locals (or locals *wasm2-emit-spillable-locals*)))
    (dolist (idx spill-locals)
      (wasm2-push-u8 body #x20) ; local.get
      (wasm2-emit-uleb body idx)
      (wasm2-emit-call-index body (wasm2-generic-import-index :vpush)))))

(defun wasm2-emit-restore-locals (body &optional locals)
  (let* ((spill-locals (or locals *wasm2-emit-spillable-locals*)))
    (dolist (idx (reverse spill-locals))
      (wasm2-emit-call-index body (wasm2-generic-import-index :vpop))
      (wasm2-push-u8 body #x21) ; local.set
      (wasm2-emit-uleb body idx))))

(defun wasm2-emit-pending-throw-guard (body)
  (wasm2-emit-call-index body (wasm2-generic-import-index :pending-throw))
  (wasm2-push-u8 body #x04) ; if
  (wasm2-push-u8 body #x40) ; blocktype void
  (wasm2-push-u8 body #x0f) ; return
  (wasm2-push-u8 body #x0b)) ; end

(defun wasm2-emit-pending-throw-check (body &optional label-stack)
  (wasm2-emit-call-index body (wasm2-generic-import-index :pending-throw))
  (wasm2-push-u8 body #x04) ; if
  (wasm2-push-u8 body #x40) ; blocktype void
  (if *wasm2-pending-throw-label*
    (let* ((depth (position *wasm2-pending-throw-label* label-stack :test #'eql)))
      (unless depth
        (error "Unknown WASM label ~s" *wasm2-pending-throw-label*))
      (wasm2-push-u8 body #x0c) ; br
      (wasm2-emit-uleb body depth))
    (wasm2-push-u8 body #x0f)) ; return
  (wasm2-push-u8 body #x0b)) ; end

(defun wasm2-emit-generic-if (body then-ir else-ir label-stack)
  (let ((if-label :if))
    (wasm2-emit-call-index body (wasm2-generic-import-index :get-lisp-nil))
    (wasm2-push-u8 body #x47) ; i32.ne
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x7f) ; blocktype i32
    (wasm2-emit-generic-ir body then-ir (cons if-label label-stack))
    (wasm2-push-u8 body #x05) ; else
    (wasm2-emit-generic-ir body else-ir (cons if-label label-stack))
    (wasm2-push-u8 body #x0b))) ; end

(defun wasm2-emit-fixnum-op (body op-key)
  (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-y))
  (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-z))
  (wasm2-emit-spill-locals body)
  (wasm2-emit-call-index body (wasm2-generic-import-index op-key))
  (wasm2-emit-restore-locals body)
  (wasm2-emit-call-index body (wasm2-generic-import-index :get-arg-z)))

(defun wasm2-emit-fixnum-unary-op (body op-key)
  (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-z))
  (wasm2-emit-spill-locals body)
  (wasm2-emit-call-index body (wasm2-generic-import-index op-key))
  (wasm2-emit-restore-locals body)
  (wasm2-emit-call-index body (wasm2-generic-import-index :get-arg-z)))

(defun wasm2-emit-call-with-pending (body key tmp &optional label-stack)
  (wasm2-emit-spill-locals body)
  (wasm2-emit-call-index body (wasm2-generic-import-index key))
  (wasm2-push-u8 body #x21) ; local.set
  (wasm2-emit-uleb body tmp)
  (wasm2-emit-call-index body (wasm2-generic-import-index :pending-throw))
  (wasm2-push-u8 body #x04) ; if
  (wasm2-push-u8 body #x40) ; blocktype void
  (if *wasm2-pending-throw-label*
    (let* ((depth (position *wasm2-pending-throw-label* label-stack :test #'eql)))
      (unless depth
        (error "Unknown WASM label ~s" *wasm2-pending-throw-label*))
      (wasm2-push-u8 body #x0c) ; br
      (wasm2-emit-uleb body depth))
    (wasm2-push-u8 body #x0f)) ; return
  (wasm2-push-u8 body #x0b) ; end
  (wasm2-emit-restore-locals body)
  (wasm2-push-u8 body #x20) ; local.get
  (wasm2-emit-uleb body tmp))

(defun wasm2-emit-generic-ir (body ir &optional label-stack)
  (dolist (ins ir)
    (let* ((op (car ins))
           (args (cdr ins)))
      (case op
        (:const
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (logand (car args) #xffffffff)))
        (:arg0
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-arg-z)))
        (:arg1
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-arg-y)))
        (:get-nfn
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-nfn)))
        (:get-nargs
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-nargs)))
        (:local.get
         (wasm2-push-u8 body #x20)
         (wasm2-emit-uleb body (car args)))
        (:local.set
         (wasm2-push-u8 body #x21)
         (wasm2-emit-uleb body (car args)))
        (:local.tee
         (wasm2-push-u8 body #x22)
         (wasm2-emit-uleb body (car args)))
        (:drop
         (wasm2-push-u8 body #x1a))
        (:set-arg0
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-z)))
        (:set-arg1
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-y)))
        (:set-arg2
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-x)))
        (:set-arg-z
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-z)))
        (:set-arg-y
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-y)))
        (:set-arg-x
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-x)))
        (:set-nargs
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (car args))
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-nargs)))
        (:set-nfn
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-nfn)))
        (:set-imm0
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (logand (car args) #xffffffff))
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-imm0)))
        (:fixnum-add (wasm2-emit-fixnum-op body :return-fixnum-add))
        (:fixnum-sub (wasm2-emit-fixnum-op body :return-fixnum-sub))
        (:fixnum-mul (wasm2-emit-fixnum-op body :return-fixnum-mul))
        (:fixnum-ash (wasm2-emit-fixnum-op body :return-fixnum-ash))
        (:fixnum-logand (wasm2-emit-fixnum-op body :return-fixnum-logand))
        (:fixnum-logior (wasm2-emit-fixnum-op body :return-fixnum-logior))
        (:fixnum-logxor (wasm2-emit-fixnum-op body :return-fixnum-logxor))
        (:fixnum-lognot (wasm2-emit-fixnum-unary-op body :return-fixnum-lognot))
        (:fixnum-neg (wasm2-emit-fixnum-unary-op body :return-fixnum-neg))
        (:call0 (wasm2-emit-call-with-pending body :funcall0 (car args) label-stack))
        (:call1 (wasm2-emit-call-with-pending body :funcall1 (car args) label-stack))
        (:call2 (wasm2-emit-call-with-pending body :funcall2 (car args) label-stack))
        (:call0-mv (wasm2-emit-call-with-pending body :funcall0-mv (car args) label-stack))
        (:call1-mv (wasm2-emit-call-with-pending body :funcall1-mv (car args) label-stack))
        (:call2-mv (wasm2-emit-call-with-pending body :funcall2-mv (car args) label-stack))
        (:call-subprim
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (logand (car args) #xffffffff))
         (wasm2-emit-call-index body (wasm2-generic-import-index :call-subprim)))
        (:return-values2
         (wasm2-emit-call-index body (wasm2-generic-import-index :return-values2)))
        (:return-values3
         (wasm2-emit-call-index body (wasm2-generic-import-index :return-values3)))
        (:return-values4
         (wasm2-emit-call-index body (wasm2-generic-import-index :return-values4)))
        (:get-mv
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (car args))
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-mv)))
        (:get-mv-indexed
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-mv-indexed)))
        (:restore-vsp
         (wasm2-emit-call-index body (wasm2-generic-import-index :restore-vsp)))
        (:vpush
         (wasm2-emit-call-index body (wasm2-generic-import-index :vpush)))
        (:vpop
         (wasm2-emit-call-index body (wasm2-generic-import-index :vpop)))
        (:spill-locals
         (wasm2-emit-spill-locals body))
        (:restore-locals
         (wasm2-emit-restore-locals body))
        (:clear-pending-throw
         (wasm2-emit-call-index body (wasm2-generic-import-index :clear-pending-throw)))
        (:pending-throw-return
         (wasm2-emit-pending-throw-guard body))
        (:pending-throw-branch
         (wasm2-emit-pending-throw-check body label-stack))
        (:if
         (destructuring-bind (then-ir else-ir) args
           (wasm2-emit-generic-if body then-ir else-ir label-stack)))
        (:block
         (destructuring-bind (label block-ir) args
           (wasm2-push-u8 body #x02) ; block
           (wasm2-push-u8 body #x40) ; blocktype void
           (wasm2-emit-generic-ir body block-ir (cons label label-stack))
           (wasm2-push-u8 body #x0b)))
        (:loop
         (destructuring-bind (label loop-ir) args
           (wasm2-push-u8 body #x03) ; loop
           (wasm2-push-u8 body #x40) ; blocktype void
           (wasm2-emit-generic-ir body loop-ir (cons label label-stack))
           (wasm2-push-u8 body #x0b)))
        (:br
         (let* ((label (car args))
                (depth (position label label-stack :test #'eql)))
           (unless depth
             (error "Unknown WASM label ~s" label))
           (wasm2-push-u8 body #x0c)
           (wasm2-emit-uleb body depth)))
        (:br-table
         (destructuring-bind (labels default-label) args
           (let* ((depths (mapcar (lambda (label)
                                    (or (position label label-stack :test #'eql)
                                        (error "Unknown WASM label ~s" label)))
                                  labels))
                  (default-depth (or (position default-label label-stack :test #'eql)
                                     (error "Unknown WASM label ~s" default-label))))
             (wasm2-push-u8 body #x0e)
             (wasm2-emit-uleb body (length depths))
             (dolist (depth depths)
               (wasm2-emit-uleb body depth))
             (wasm2-emit-uleb body default-depth))))
        (:return
         (wasm2-push-u8 body #x0f))
        (t
         (error "Unhandled WASM2 IR opcode ~s" op))))))

(defun wasm2-generic-module-bytes (ir export-name local-count &optional spillable-locals)
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    ;; Types
    (wasm2-emit-uleb types 7)
    ;; 0: () -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 1: (i32) -> ()
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-emit-uleb types 0)
    ;; 2: () -> ()
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)
    ;; 3: (i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x7f)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 4: (i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 3)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x7f)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 5: (i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 6: (i32 i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 4)
    (dotimes (_i 4)
      (wasm2-push-u8 types #x7f))
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)

    ;; Imports
    (wasm2-emit-uleb imports (length *wasm2-generic-imports*))
    (dolist (imp *wasm2-generic-imports*)
      (destructuring-bind (_key name type-index) imp
        (declare (ignore _key))
        (wasm2-emit-string imports "ccl")
        (wasm2-emit-string imports name)
        (wasm2-push-u8 imports 0)
        (wasm2-emit-uleb imports type-index)))

    ;; Function section
    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs +wasm2-type-void-void+)

    ;; Export
    (let* ((func-index (length *wasm2-generic-imports*)))
      (wasm2-emit-uleb exports 1)
      (wasm2-emit-string exports export-name)
      (wasm2-push-u8 exports 0)
      (wasm2-emit-uleb exports func-index))

    ;; Code
    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (if (> local-count 0)
        (progn
          (wasm2-emit-uleb body 1)
          (wasm2-emit-uleb body local-count)
          (wasm2-push-u8 body #x7f))
        (wasm2-emit-uleb body 0))
      (when (> local-count 0)
        (let* ((nil-value (target-nil-value)))
          (dotimes (i local-count)
            (wasm2-push-u8 body #x41) ; i32.const
            (wasm2-emit-sleb32 body (logand nil-value #xffffffff))
            (wasm2-push-u8 body #x21) ; local.set
            (wasm2-emit-uleb body i))))
      (let* ((*wasm2-emit-local-count* local-count)
             (*wasm2-emit-spillable-locals* spillable-locals))
        (wasm2-emit-pending-throw-guard body)
        (wasm2-emit-generic-ir body ir))
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-const-module-bytes (const-value)
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    ;; Module header
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    ;; Types: [0] () -> i32, [1] (i32) -> (), [2] () -> ()
    (wasm2-emit-uleb types 3)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-emit-uleb types 0)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    ;; Imports: ccl.wasm_pending_throw_p (func type 0), ccl.wasm_return_constant (func type 1)
    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_constant")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    ;; Function section: one function of type 2
    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 2)

    ;; Export: ccl_const_entry -> func index 2 (after imports)
    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-const-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    ;; Code: local decls = 0, guard pending_throw then return constant
    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x41)
      (wasm2-emit-sleb32 body (logand const-value #xffffffff))
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-if-module-bytes (true-value false-value)
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    ;; Module header
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    ;; Types: [0] () -> i32, [1] (i32) -> (), [2] () -> ()
    (wasm2-emit-uleb types 3)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-emit-uleb types 0)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    ;; Imports: ccl.wasm_get_arg_z, ccl.wasm_get_lisp_nil,
    ;; ccl.wasm_return_constant, ccl.wasm_pending_throw_p
    (wasm2-emit-uleb imports 4)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_get_arg_z")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_get_lisp_nil")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_constant")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)

    ;; Function section: one function of type 2
    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 2)

    ;; Export: ccl_if_entry -> func index 4 (after imports)
    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-if-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 4)

    ;; Code: local decls = 0, branch on arg_z vs nil and return constant
    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      ;; if (pending_throw) return
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 3)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      ;; if (arg_z == nil) -> false_value else true_value
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x46)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x41)
      (wasm2-emit-sleb32 body false-value)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 2)
      (wasm2-push-u8 body #x05)
      (wasm2-push-u8 body #x41)
      (wasm2-emit-sleb32 body true-value)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 2)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-if-arg-module-bytes (else-value)
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    ;; Module header
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    ;; Types: [0] () -> i32, [1] (i32) -> (), [2] () -> ()
    (wasm2-emit-uleb types 3)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-emit-uleb types 0)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    ;; Imports: ccl.wasm_get_arg_z, ccl.wasm_get_lisp_nil,
    ;; ccl.wasm_return_constant, ccl.wasm_return_arg_z, ccl.wasm_pending_throw_p
    (wasm2-emit-uleb imports 5)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_get_arg_z")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_get_lisp_nil")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_constant")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_arg_z")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)

    ;; Function section: one function of type 2
    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 2)

    ;; Export: ccl_if_arg_entry -> func index 5 (after imports)
    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-if-arg-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 5)

    ;; Code: local decls = 0, branch on arg_z vs nil and return arg/constant
    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      ;; if (pending_throw) return
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 4)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      ;; if (arg_z == nil) -> else_value else return arg_z
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x46)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x41)
      (wasm2-emit-sleb32 body else-value)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 2)
      (wasm2-push-u8 body #x05)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 3)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-identity-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    ;; Types: [0] () -> i32, [1] () -> ()
    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    ;; Imports: ccl.wasm_pending_throw_p (type 0), ccl.wasm_return_arg_z (type 1)
    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_arg_z")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    ;; Function section: one function of type 1
    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    ;; Export: ccl_identity_entry -> func index 2 (after imports)
    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-identity-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    ;; Code: local decls = 0, guard pending_throw then return arg_z
    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-identity-y-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    ;; Types: [0] () -> i32, [1] () -> ()
    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    ;; Imports: ccl.wasm_pending_throw_p (type 0), ccl.wasm_return_arg_y (type 1)
    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_arg_y")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    ;; Function section: one function of type 1
    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    ;; Export: ccl_identity_y_entry -> func index 2 (after imports)
    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-identity-y-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    ;; Code: local decls = 0, guard pending_throw then return arg_y
    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-add-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_add")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-add-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-sub-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_sub")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-sub-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-mul-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_mul")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-mul-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-ash-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_ash")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-ash-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-logand-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_logand")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-logand-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-logior-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_logior")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-logior-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-logxor-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_logxor")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-logxor-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-lognot-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_lognot")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-lognot-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-fixnum-neg-module-bytes ()
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    (wasm2-emit-uleb types 2)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 0)
    (wasm2-emit-uleb types 0)

    (wasm2-emit-uleb imports 2)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_pending_throw_p")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 0)
    (wasm2-emit-string imports "ccl")
    (wasm2-emit-string imports "wasm_return_fixnum_neg")
    (wasm2-push-u8 imports 0)
    (wasm2-emit-uleb imports 1)

    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs 1)

    (wasm2-emit-uleb exports 1)
    (wasm2-emit-string exports +wasm-fixnum-neg-export-name+)
    (wasm2-push-u8 exports 0)
    (wasm2-emit-uleb exports 2)

    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 0)
      (wasm2-push-u8 body #x04)
      (wasm2-push-u8 body #x40)
      (wasm2-push-u8 body #x0f)
      (wasm2-push-u8 body #x0b)
      (wasm2-push-u8 body #x10)
      (wasm2-emit-uleb body 1)
      (wasm2-push-u8 body #x0b)
      (wasm2-emit-uleb code 1)
      (wasm2-emit-uleb code (length body))
      (dotimes (i (length body))
        (wasm2-push-u8 code (aref body i))))

    (dolist (section (list (wasm2-section 1 types)
                           (wasm2-section 2 imports)
                           (wasm2-section 3 funcs)
                           (wasm2-section 7 exports)
                           (wasm2-section 10 code))
                     out)
      (dotimes (i (length section))
        (wasm2-push-u8 out (aref section i))))))

(defun wasm2-box-fixnum (value)
  (ash value *wasm2-target-fixnum-shift*))

(defun wasm2-make-const-function (entry-index const-value &optional (lfun-bits 0))
  (let* ((entry-fixnum (wasm2-box-fixnum entry-index))
         (function (%alloc-misc 4 target::subtag-function)))
    (setf (uvref function 0) entry-fixnum
          (uvref function 1) entry-fixnum
          (uvref function 2) const-value
          (uvref function 3) lfun-bits)
    function))

(defun wasm2-const-ir-value (ir)
  (when (and (= (length ir) 4)
             (eq (caar ir) :const)
             (eq (caar (cdr ir)) :set-arg-z)
             (eq (caar (cddr ir)) :set-nargs)
             (eq (caar (cdddr ir)) :return))
    (values (cadar ir) t)))

(defun wasm2-fixnum-add-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-add)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-fixnum-sub-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-sub)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-fixnum-mul-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-mul)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-fixnum-ash-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-ash)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-fixnum-logand-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-logand)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-fixnum-logior-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-logior)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-fixnum-logxor-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-logxor)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-fixnum-lognot-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-lognot)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-fixnum-neg-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :fixnum-neg)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-if-arg0-const-ir-p (ir)
  (when (and (= (length ir) 2)
             (eq (caar ir) :if-arg0)
             (eq (caar (cdr ir)) :return))
    (values (cadar ir) (caddar ir) t)))

(defun wasm2-if-arg0-else-ir-p (ir)
  (when (and (= (length ir) 2)
             (eq (caar ir) :if-arg0-else)
             (eq (caar (cdr ir)) :return))
    (values (cadar ir) t)))

(defun wasm2-return-arg0-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :return-arg0)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-return-arg1-ir-p (ir)
  (and (= (length ir) 2)
       (eq (caar ir) :return-arg1)
       (eq (caar (cdr ir)) :return)))

(defun wasm2-ir-ends-with-return-p (ir)
  (and ir (eq (caar (last ir)) :return)))

(defun wasm2-allocate-entry-index ()
  (prog1 *wasm2-next-entry-index*
    (incf *wasm2-next-entry-index*)))

(defun wasm2-const-lfun-bits (afunc)
  (let* ((lambda-form (afunc-lambdaform afunc)))
    (when (and (consp lambda-form) (consp (cdr lambda-form)))
      (or (encode-lambda-list (cadr lambda-form)) 0))))

(defun wasm2-compile (afunc &optional lambda-form *wasm2-record-symbols*)
  (dolist (a (afunc-inner-functions afunc))
    (wasm2-compile a
                   (if lambda-form (afunc-lambdaform a))
                   *wasm2-record-symbols*))
  (let* ((*wasm2-cur-afunc* afunc)
         (*wasm2-vstack* 0)
         (*wasm2-cstack* 0)
         (*wasm2-target-fixnum-shift* (arch::target-fixnum-shift (backend-target-arch *target-backend*)))
         (*wasm2-target-node-shift* (arch::target-word-shift (backend-target-arch *target-backend*)))
         (*wasm2-target-bits-in-word* (arch::target-nbits-in-word (backend-target-arch *target-backend*)))
         (*wasm2-target-node-size* (arch::target-lisp-node-size (backend-target-arch *target-backend*)))
         (*backend-vinsns* (backend-p2-vinsn-templates *target-backend*))
         (*backend-node-regs* wasm-node-regs)
         (*backend-node-temps* wasm-temp-node-regs)
         (*available-backend-node-temps* wasm-temp-node-regs)
         (*backend-imm-temps* wasm-imm-regs)
         (*available-backend-imm-temps* wasm-imm-regs)
         (*backend-fp-temps* wasm-temp-fp-regs)
         (*available-backend-fp-temps* wasm-temp-fp-regs)
         (*backend-crf-temps* wasm-cr-fields)
         (*available-backend-crf-temps* wasm-cr-fields)
         (*wasm2-ir* nil)
         (*wasm2-locals* nil)
         (*wasm2-local-count* 0)
         (*wasm2-temp-local* nil)
         (*wasm2-label-counter* 0)
         (*wasm2-block-stack* nil)
         (*wasm2-tagbody-stack* nil)
         (*wasm2-tagbody-global-map* (make-hash-table :test #'eq)))
    (wasm2-reset-locals)
    (backend-apply-acode (afunc-acode afunc) nil nil $backend-return)
    (let* ((ir (nreverse *wasm2-ir*))
           (closed-prologue-ir (wasm2-closed-arg-prologue-ir))
           (arg-prologue-ir (wasm2-arg-prologue-ir)))
      (when closed-prologue-ir
        (setf ir (append closed-prologue-ir ir)))
      (when arg-prologue-ir
        (setf ir (append arg-prologue-ir ir)))
      (unless (wasm2-ir-ends-with-return-p ir)
        (setf ir (append ir
                         (list (cons :set-arg-z nil)
                               (cons :set-nargs (list 1))
                               (cons :return nil)))))
      (multiple-value-bind (const-value const-p) (wasm2-const-ir-value ir)
        (setf (afunc-lfun-info afunc)
              (list* 'wasm-ir ir
                   (if const-p
                     (list* 'wasm-const-value const-value
                            'wasm-entry-index +wasm-const-entry-index+
                            (afunc-lfun-info afunc))
                     (afunc-lfun-info afunc))))
        (when const-p
          (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
            (let* ((module-bytes (wasm2-const-module-bytes const-value)))
              (wasm2-register-compiled-module module-bytes
                                              +wasm-const-export-name+
                                              +wasm-const-entry-index+
                                              +wasm-const-module-version+)
              (setf (afunc-lfun-info afunc)
                    (list* 'wasm-module-bytes module-bytes
                           'wasm-module-export +wasm-const-export-name+
                           'wasm-module-version +wasm-const-module-version+
                           (afunc-lfun-info afunc))))
            (setf (afunc-argsword afunc) bits)
            (setf (afunc-lfun afunc)
                  (wasm2-make-const-function +wasm-const-entry-index+ const-value bits))
          (return-from wasm2-compile afunc))))
      (when (wasm2-fixnum-add-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-add-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-add-export-name+
                                            +wasm-fixnum-add-entry-index+
                                            +wasm-fixnum-add-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-add-export-name+
                         'wasm-module-version +wasm-fixnum-add-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-add-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-fixnum-sub-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-sub-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-sub-export-name+
                                            +wasm-fixnum-sub-entry-index+
                                            +wasm-fixnum-sub-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-sub-export-name+
                         'wasm-module-version +wasm-fixnum-sub-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-sub-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-fixnum-mul-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-mul-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-mul-export-name+
                                            +wasm-fixnum-mul-entry-index+
                                            +wasm-fixnum-mul-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-mul-export-name+
                         'wasm-module-version +wasm-fixnum-mul-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-mul-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-fixnum-ash-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-ash-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-ash-export-name+
                                            +wasm-fixnum-ash-entry-index+
                                            +wasm-fixnum-ash-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-ash-export-name+
                         'wasm-module-version +wasm-fixnum-ash-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-ash-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-fixnum-logand-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-logand-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-logand-export-name+
                                            +wasm-fixnum-logand-entry-index+
                                            +wasm-fixnum-logand-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-logand-export-name+
                         'wasm-module-version +wasm-fixnum-logand-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-logand-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-fixnum-logior-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-logior-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-logior-export-name+
                                            +wasm-fixnum-logior-entry-index+
                                            +wasm-fixnum-logior-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-logior-export-name+
                         'wasm-module-version +wasm-fixnum-logior-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-logior-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-fixnum-logxor-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-logxor-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-logxor-export-name+
                                            +wasm-fixnum-logxor-entry-index+
                                            +wasm-fixnum-logxor-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-logxor-export-name+
                         'wasm-module-version +wasm-fixnum-logxor-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-logxor-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-fixnum-lognot-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-lognot-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-lognot-export-name+
                                            +wasm-fixnum-lognot-entry-index+
                                            +wasm-fixnum-lognot-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-lognot-export-name+
                         'wasm-module-version +wasm-fixnum-lognot-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-lognot-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-fixnum-neg-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-fixnum-neg-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-fixnum-neg-export-name+
                                            +wasm-fixnum-neg-entry-index+
                                            +wasm-fixnum-neg-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-fixnum-neg-export-name+
                         'wasm-module-version +wasm-fixnum-neg-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-fixnum-neg-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (multiple-value-bind (true-val false-val ok) (wasm2-if-arg0-const-ir-p ir)
        (when ok
          (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
            (let* ((module-bytes (wasm2-if-module-bytes true-val false-val)))
              (wasm2-register-compiled-module module-bytes
                                              +wasm-if-export-name+
                                              +wasm-if-entry-index+
                                              +wasm-if-module-version+)
              (setf (afunc-lfun-info afunc)
                    (list* 'wasm-module-bytes module-bytes
                           'wasm-module-export +wasm-if-export-name+
                           'wasm-module-version +wasm-if-module-version+
                           (afunc-lfun-info afunc))))
            (setf (afunc-argsword afunc) bits)
            (setf (afunc-lfun afunc)
                  (wasm2-make-const-function +wasm-if-entry-index+ 0 bits))
          (return-from wasm2-compile afunc))))
      (multiple-value-bind (else-val ok) (wasm2-if-arg0-else-ir-p ir)
        (when ok
          (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
            (let* ((module-bytes (wasm2-if-arg-module-bytes else-val)))
              (wasm2-register-compiled-module module-bytes
                                              +wasm-if-arg-export-name+
                                              +wasm-if-arg-entry-index+
                                              +wasm-if-arg-module-version+)
              (setf (afunc-lfun-info afunc)
                    (list* 'wasm-module-bytes module-bytes
                           'wasm-module-export +wasm-if-arg-export-name+
                           'wasm-module-version +wasm-if-arg-module-version+
                           (afunc-lfun-info afunc))))
            (setf (afunc-argsword afunc) bits)
            (setf (afunc-lfun afunc)
                  (wasm2-make-const-function +wasm-if-arg-entry-index+ 0 bits))
          (return-from wasm2-compile afunc))))
      (when (wasm2-return-arg0-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-identity-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-identity-export-name+
                                            +wasm-identity-entry-index+
                                            +wasm-identity-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-identity-export-name+
                         'wasm-module-version +wasm-identity-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-identity-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (when (wasm2-return-arg1-ir-p ir)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-identity-y-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-identity-y-export-name+
                                            +wasm-identity-y-entry-index+
                                            +wasm-identity-y-module-version+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-identity-y-export-name+
                         'wasm-module-version +wasm-identity-y-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (setf (afunc-lfun afunc)
                (wasm2-make-const-function +wasm-identity-y-entry-index+ 0 bits))
        (return-from wasm2-compile afunc)))
      (let* ((bits (or (wasm2-const-lfun-bits afunc) 0))
             (entry-index (wasm2-allocate-entry-index))
             (export-name (format nil "ccl_generic_entry_~d" entry-index))
             (spillable-locals (nreverse *wasm2-spillable-locals*))
             (module-bytes (wasm2-generic-module-bytes ir export-name
                                                       *wasm2-local-count*
                                                       spillable-locals)))
        (wasm2-register-compiled-module module-bytes
                                        export-name
                                        entry-index
                                        1)
        (setf (afunc-lfun-info afunc)
              (list* 'wasm-module-bytes module-bytes
                     'wasm-module-export export-name
                     'wasm-module-version 1
                     'wasm-entry-index entry-index
                     (afunc-lfun-info afunc)))
        (setf (afunc-argsword afunc) bits)
        (setf (afunc-lfun afunc)
              (wasm2-make-const-function entry-index 0 bits))
        (return-from wasm2-compile afunc))))
  )

(provide "WASM2")
