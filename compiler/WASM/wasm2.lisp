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
;; Default const-pool on for wasm2; bind to NIL to reproduce pre-pool behavior.
(defvar *wasm2-enable-const-pool* t)
(defvar *wasm2-const-pool* nil)
(defvar *wasm2-const-pool-map* nil)
(defvar *wasm2-external-imports* nil)
(defvar *wasm2-external-import-map* nil)
(defvar *wasm2-emit-entry-index* nil)
(defvar *wasm2-fixnum-direct-scratch-base* nil)

(defconstant +wasm2-closure-cells-base+ 3)
(defconstant +wasm2-gc-root-mode-runtime-default+ 0)
(defconstant +wasm2-gc-root-mode-runtime-bootstrap+ 1)

(defparameter *wasm2-gc-root-default-required-ops*
  '(:call-subprim :call-subprim-no-spill
    :call0 :call1 :call2 :call3 :call4 :call5 :call6 :call7 :call8 :call9 :call10
    :call0-mv :call1-mv :call2-mv :call3-mv :call4-mv :call5-mv :call6-mv
    :call7-mv :call8-mv :call9-mv :call10-mv
    :call-external
    :spill-push :spill-pop
    :vpush :vpop))

(declaim (special *wasm2-skip-next-nx-defops* *nx1-operators*
                  *wasm2-cur-afunc* *wasm2-vstack* *wasm2-cstack*
                  *wasm2-target-fixnum-shift* *wasm2-target-node-shift*
                  *wasm2-target-bits-in-word* *wasm2-target-node-size*
                  *wasm2-target-lisptag-mask*
                  *wasm2-target-fulltag-misc* *wasm2-target-fulltagmask*
                  *wasm2-target-misc-data-offset* *wasm2-target-misc-dfloat-offset*
                  *wasm2-target-unbound-marker* *wasm2-target-slot-unbound-marker*
                  *wasm2-target-illegal-marker*
                  *wasm2-target-single-float-count* *wasm2-target-double-float-count*
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
                  *wasm2-enable-const-pool* *wasm2-const-pool* *wasm2-const-pool-map*
                  *wasm2-generic-imports*
                  *wasm2-external-imports* *wasm2-external-import-map*
                  *wasm2-emit-entry-index* *wasm2-fixnum-direct-scratch-base*
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
    (let* ((handler (svref *wasm2-specials* (%ilogand operator-id-mask op))))
      (when (eq handler #'wasm2-unimplemented)
        (error "WASM2: unimplemented opcode ~s operands ~s"
               (acode-operator-name op)
               (acode-operands form)))
      (apply handler seg vreg xfer (acode-operands form)))))

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
             (setf (fdefinition ',name) ,fun)
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

(defwasm2 wasm2-%unbound-marker %unbound-marker (seg vreg xfer)
  (declare (ignore seg vreg))
  (let* ((value *wasm2-target-unbound-marker*))
    (if (wasm2-returning-p xfer)
      (wasm2-emit-constant-return value)
      (wasm2-emit-const value)))
  nil)

(defwasm2 wasm2-slot-unbound-marker %slot-unbound-marker (seg vreg xfer)
  (declare (ignore seg vreg))
  (let* ((value *wasm2-target-slot-unbound-marker*))
    (if (wasm2-returning-p xfer)
      (wasm2-emit-constant-return value)
      (wasm2-emit-const value)))
  nil)

(defwasm2 wasm2-illegal-marker %illegal-marker (seg vreg xfer)
  (declare (ignore seg vreg))
  (let* ((value *wasm2-target-illegal-marker*))
    (if (wasm2-returning-p xfer)
      (wasm2-emit-constant-return value)
      (wasm2-emit-const value)))
  nil)

(defwasm2 wasm2-%debug-trap %debug-trap (seg vreg xfer arg)
  (wasm2-form seg vreg xfer arg))

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

(defparameter *wasm2-compat-boundary-subprim-map*
  '((:builtin-div . .SPbuiltin-div)
    (:builtin-negate . .SPbuiltin-negate)
    (:builtin-ash . .SPbuiltin-ash)))

(defparameter *wasm2-compat-boundary-subprim-symbols*
  (mapcar #'cdr *wasm2-compat-boundary-subprim-map*))

(defun wasm2-compat-boundary-subprim-symbol (compat-key)
  (let* ((entry (assoc compat-key *wasm2-compat-boundary-subprim-map* :test #'eq)))
    (if entry
      (cdr entry)
      (error "WASM2: unknown compat-boundary subprim key ~s" compat-key))))

(defun wasm2-emit-compat-boundary-subprim-binary-call (seg xfer compat-key x y)
  (let* ((subprim (wasm2-compat-boundary-subprim-fixnum compat-key)))
    (wasm2-form seg nil nil x)
    (wasm2-form seg nil nil y)
    (wasm2-emit :set-arg1)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim subprim)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return))))

(defun wasm2-emit-compat-boundary-subprim-unary-call (seg xfer compat-key x)
  (let* ((subprim (wasm2-compat-boundary-subprim-fixnum compat-key)))
    (wasm2-form seg nil nil x)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim subprim)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return))))

(defwasm2 wasm2-div2 div2 (seg vreg xfer x y)
  (declare (ignore vreg))
  (wasm2-emit-compat-boundary-subprim-binary-call seg xfer :builtin-div x y)
  nil)

(defwasm2 wasm2-minus1 minus1 (seg vreg xfer form)
  (declare (ignore vreg))
  (wasm2-emit-compat-boundary-subprim-unary-call seg xfer :builtin-negate form)
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

(defwasm2 wasm2-ash ash (seg vreg xfer x y)
  (declare (ignore vreg))
  (wasm2-emit-compat-boundary-subprim-binary-call seg xfer :builtin-ash x y)
  nil)

(defwasm2 wasm2-%iasr %iasr (seg vreg xfer form1 form2)
  (declare (ignore vreg xfer))
  (let* ((count (acode-fixnum-form-p form1))
         (max (1- *wasm2-target-bits-in-word*))
         (mask (logand #xffffffff
                       (lognot (1- (ash 1 *wasm2-target-fixnum-shift*)))))
         (count-temp (wasm2-allocate-temp))
         (value-temp (wasm2-allocate-temp)))
    (declare (fixnum max))
    (if count
      (let* ((shift (if (> count max) max count)))
        (wasm2-form seg nil nil form2)
        (wasm2-emit :local.set value-temp)
        (wasm2-emit :local.get value-temp)
        (wasm2-emit :const shift)
        (wasm2-emit :i32-shr-s)
        (wasm2-emit :const mask)
        (wasm2-emit :i32-and))
      (progn
        (wasm2-form seg nil nil form1)
        (wasm2-emit :local.set count-temp)
        (wasm2-form seg nil nil form2)
        (wasm2-emit :local.set value-temp)
        (wasm2-emit :local.get value-temp)
        (wasm2-emit :local.get count-temp)
        (wasm2-emit-unbox-fixnum)
        (wasm2-emit :i32-shr-s)
        (wasm2-emit :const mask)
        (wasm2-emit :i32-and))))
  nil)

(defwasm2 wasm2-%ilsr %ilsr (seg vreg xfer form1 form2)
  (declare (ignore vreg xfer))
  (let* ((count (acode-fixnum-form-p form1))
         (max (1- *wasm2-target-bits-in-word*))
         (mask (logand #xffffffff
                       (lognot (1- (ash 1 *wasm2-target-fixnum-shift*)))))
         (count-temp (wasm2-allocate-temp))
         (value-temp (wasm2-allocate-temp)))
    (declare (fixnum max))
    (if count
      (let* ((shift (if (> count max) max count)))
        (wasm2-form seg nil nil form2)
        (wasm2-emit :local.set value-temp)
        (wasm2-emit :local.get value-temp)
        (wasm2-emit :const shift)
        (wasm2-emit :i32-shr-u)
        (wasm2-emit :const mask)
        (wasm2-emit :i32-and))
      (progn
        (wasm2-form seg nil nil form1)
        (wasm2-emit :local.set count-temp)
        (wasm2-form seg nil nil form2)
        (wasm2-emit :local.set value-temp)
        (wasm2-emit :local.get value-temp)
        (wasm2-emit :local.get count-temp)
        (wasm2-emit-unbox-fixnum)
        (wasm2-emit :i32-shr-u)
        (wasm2-emit :const mask)
        (wasm2-emit :i32-and))))
  nil)

(defwasm2 wasm2-%ilsl %ilsl (seg vreg xfer form1 form2)
  (declare (ignore vreg xfer))
  (let* ((count (acode-fixnum-form-p form1))
         (max (1- *wasm2-target-bits-in-word*))
         (count-temp (wasm2-allocate-temp))
         (value-temp (wasm2-allocate-temp)))
    (declare (fixnum max))
    (if count
      (progn
        (wasm2-form seg nil nil form2)
        (wasm2-emit :local.set value-temp)
        (if (> count max)
          (wasm2-emit :const 0)
          (progn
            (wasm2-emit :local.get value-temp)
            (wasm2-emit :const count)
            (wasm2-emit :i32-shl))))
      (progn
        (wasm2-form seg nil nil form1)
        (wasm2-emit :local.set count-temp)
        (wasm2-form seg nil nil form2)
        (wasm2-emit :local.set value-temp)
        (wasm2-emit :local.get value-temp)
        (wasm2-emit :local.get count-temp)
        (wasm2-emit-unbox-fixnum)
        (wasm2-emit :i32-shl))))
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

(defwasm2 wasm2-logand2 logand2 (seg vreg xfer x y)
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

(defwasm2 wasm2-logior2 logior2 (seg vreg xfer x y)
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

(defwasm2 wasm2-logxor2 logxor2 (seg vreg xfer x y)
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

(defwasm2 wasm2-%fixnum-to-single %fixnum-to-single (seg vreg xfer arg)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil arg)
  (wasm2-emit-unbox-fixnum)
  (wasm2-emit :f32-convert-i32-s)
  (wasm2-emit-box-single)
  nil)

(defwasm2 wasm2-%fixnum-to-double %fixnum-to-double (seg vreg xfer arg)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil arg)
  (wasm2-emit-unbox-fixnum)
  (wasm2-emit :f64-convert-i32-s)
  (wasm2-emit-box-double)
  nil)

(defwasm2 wasm2-%single-to-double %single-to-double (seg vreg xfer arg)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil arg)
  (wasm2-emit-unbox-single)
  (wasm2-emit :f64-promote-f32)
  (wasm2-emit-box-double)
  nil)

(defwasm2 wasm2-%double-to-single %double-to-single (seg vreg xfer arg)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil arg)
  (wasm2-emit-unbox-double)
  (wasm2-emit :f32-demote-f64)
  (wasm2-emit-box-single)
  nil)

(defwasm2 wasm2-%word-to-int %word-to-int (seg vreg xfer arg)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil arg)
  (wasm2-emit-unbox-fixnum)
  (wasm2-emit :const 16)
  (wasm2-emit :i32-shl)
  (wasm2-emit :const 16)
  (wasm2-emit :i32-shr-s)
  (wasm2-emit-box-fixnum)
  nil)

(defwasm2 wasm2-%double-float-negate %double-float-negate (seg vreg xfer arg)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil arg)
  (wasm2-emit-unbox-double)
  (wasm2-emit :f64-neg)
  (wasm2-emit-box-double)
  nil)

(defwasm2 wasm2-%single-float-negate %single-float-negate (seg vreg xfer arg)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil arg)
  (wasm2-emit-unbox-single)
  (wasm2-emit :f32-neg)
  (wasm2-emit-box-single)
  nil)

(defwasm2 wasm2-%double-float+-2 %double-float+-2 (seg vreg xfer x y)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil x)
  (wasm2-emit-unbox-double)
  (wasm2-form seg nil nil y)
  (wasm2-emit-unbox-double)
  (wasm2-emit :f64-add)
  (wasm2-emit-box-double)
  nil)

(defwasm2 wasm2-%double-float--2 %double-float--2 (seg vreg xfer x y)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil x)
  (wasm2-emit-unbox-double)
  (wasm2-form seg nil nil y)
  (wasm2-emit-unbox-double)
  (wasm2-emit :f64-sub)
  (wasm2-emit-box-double)
  nil)

(defwasm2 wasm2-%double-float*-2 %double-float*-2 (seg vreg xfer x y)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil x)
  (wasm2-emit-unbox-double)
  (wasm2-form seg nil nil y)
  (wasm2-emit-unbox-double)
  (wasm2-emit :f64-mul)
  (wasm2-emit-box-double)
  nil)

(defwasm2 wasm2-%double-float/-2 %double-float/-2 (seg vreg xfer x y)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil x)
  (wasm2-emit-unbox-double)
  (wasm2-form seg nil nil y)
  (wasm2-emit-unbox-double)
  (wasm2-emit :f64-div)
  (wasm2-emit-box-double)
  nil)

(defwasm2 wasm2-%short-float+-2 %short-float+-2 (seg vreg xfer x y)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil x)
  (wasm2-emit-unbox-single)
  (wasm2-form seg nil nil y)
  (wasm2-emit-unbox-single)
  (wasm2-emit :f32-add)
  (wasm2-emit-box-single)
  nil)

(defwasm2 wasm2-%short-float--2 %short-float--2 (seg vreg xfer x y)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil x)
  (wasm2-emit-unbox-single)
  (wasm2-form seg nil nil y)
  (wasm2-emit-unbox-single)
  (wasm2-emit :f32-sub)
  (wasm2-emit-box-single)
  nil)

(defwasm2 wasm2-%short-float*-2 %short-float*-2 (seg vreg xfer x y)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil x)
  (wasm2-emit-unbox-single)
  (wasm2-form seg nil nil y)
  (wasm2-emit-unbox-single)
  (wasm2-emit :f32-mul)
  (wasm2-emit-box-single)
  nil)

(defwasm2 wasm2-%short-float/-2 %short-float/-2 (seg vreg xfer x y)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil x)
  (wasm2-emit-unbox-single)
  (wasm2-form seg nil nil y)
  (wasm2-emit-unbox-single)
  (wasm2-emit :f32-div)
  (wasm2-emit-box-single)
  nil)

(defwasm2 wasm2-double-float-compare double-float-compare (seg vreg xfer cc x y)
  (declare (ignore vreg xfer))
  (let* ((op (wasm2-float-cc-op (acode-immediate-operand cc) nil))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil x)
    (wasm2-emit-unbox-double)
    (wasm2-form seg nil nil y)
    (wasm2-emit-unbox-double)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-short-float-compare short-float-compare (seg vreg xfer cc x y)
  (declare (ignore vreg xfer))
  (let* ((op (wasm2-float-cc-op (acode-immediate-operand cc) t))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil x)
    (wasm2-emit-unbox-single)
    (wasm2-form seg nil nil y)
    (wasm2-emit-unbox-single)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-eq eq (seg vreg xfer cc x y)
  (declare (ignore vreg xfer))
  (let* ((cond (acode-immediate-operand cc))
         (op (ecase cond
               (:eq :i32-eq)
               (:ne :i32-ne)))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil x)
    (wasm2-form seg nil nil y)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-%ptr-eql %ptr-eql (seg vreg xfer cc x y)
  (declare (ignore vreg xfer))
  (let* ((cond (acode-immediate-operand cc))
         (op (ecase cond
               (:eq :i32-eq)
               (:ne :i32-ne)))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil x)
    (wasm2-form seg nil nil y)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-neq neq (seg vreg xfer cc x y)
  (declare (ignore vreg xfer))
  (let* ((cond (acode-immediate-operand cc))
         (op (ecase cond
               (:eq :i32-eq)
               (:ne :i32-ne)))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil x)
    (wasm2-form seg nil nil y)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-%i<> %i<> (seg vreg xfer cc x y)
  (declare (ignore vreg xfer))
  (let* ((op (wasm2-int-cc-op (acode-immediate-operand cc) t))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil x)
    (wasm2-emit-unbox-fixnum)
    (wasm2-form seg nil nil y)
    (wasm2-emit-unbox-fixnum)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-%ilogbitp %ilogbitp (seg vreg xfer cc bitnum form)
  (declare (ignore vreg xfer))
  (let* ((cond (acode-immediate-operand cc))
         (op (ecase cond
               (:eq :i32-eq)
               (:ne :i32-ne)))
         (fixbit (acode-fixnum-form-p bitnum))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil form)
    (wasm2-emit-unbox-fixnum)
    (if fixbit
      (let* ((max-bit (1- (- *wasm2-target-bits-in-word* *wasm2-target-fixnum-shift*)))
             (bit (min max-bit (max fixbit 0))))
        (wasm2-emit :const bit))
      (progn
        (wasm2-form seg nil nil bitnum)
        (wasm2-emit-unbox-fixnum)))
    (wasm2-emit :i32-shr-u)
    (wasm2-emit :const 1)
    (wasm2-emit :i32-and)
    (wasm2-emit :const 0)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-logbitp logbitp (seg vreg xfer bitnum int)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'logbitp)
                          (list nil (list int bitnum))))
  nil)

(defwasm2 wasm2-%new-ptr %new-ptr (seg vreg xfer size clear-p)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) '%new-gcable-ptr)
                          (list nil (list clear-p size))))
  nil)

(defwasm2 wasm2-realpart realpart (seg vreg xfer c)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'realpart)
                          (list nil (list c))))
  nil)

(defwasm2 wasm2-imagpart imagpart (seg vreg xfer c)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'imagpart)
                          (list nil (list c))))
  nil)

(defwasm2 wasm2-complex complex (seg vreg xfer r i)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'complex)
                          (list nil (list i r))))
  nil)

(defwasm2 wasm2-%natural- %natural- (seg vreg xfer x y)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) '-)
                          (list nil (list x y))))
  nil)

(defwasm2 wasm2-%natural+ %natural+ (seg vreg xfer x y)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) '+)
                          (list nil (list x y))))
  nil)

(defwasm2 wasm2-%natural-logand %natural-logand (seg vreg xfer x y)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'logand)
                          (list nil (list x y))))
  nil)

(defwasm2 wasm2-%natural-logior %natural-logior (seg vreg xfer x y)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'logior)
                          (list nil (list x y))))
  nil)

(defwasm2 wasm2-%natural-logxor %natural-logxor (seg vreg xfer x y)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'logxor)
                          (list nil (list x y))))
  nil)

(defwasm2 wasm2-natural-shift-left natural-shift-left (seg vreg xfer num amt)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'ash)
                          (list nil (list num amt))))
  nil)

(defwasm2 wasm2-natural-shift-right natural-shift-right (seg vreg xfer num amt)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'ash)
                          (list nil (list num
                                          (make-acode (%nx1-operator %ineg) amt)))))
  nil)

(defwasm2 wasm2-%natural<> %natural<> (seg vreg xfer cc x y)
  (declare (ignore vreg xfer))
  (let* ((op (wasm2-int-cc-op (acode-immediate-operand cc) nil))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil x)
    (wasm2-emit-unbox-fixnum)
    (wasm2-form seg nil nil y)
    (wasm2-emit-unbox-fixnum)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-numcmp numcmp (seg vreg xfer cc x y)
  (declare (ignore vreg xfer))
  (let* ((op (wasm2-int-cc-op (acode-immediate-operand cc) t))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil x)
    (wasm2-emit-unbox-fixnum)
    (wasm2-form seg nil nil y)
    (wasm2-emit-unbox-fixnum)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-int>0-p int>0-p (seg vreg xfer cc form)
  (declare (ignore vreg xfer))
  (let* ((op (wasm2-int-cc-op (acode-immediate-operand cc) t))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil form)
    (wasm2-emit-unbox-fixnum)
    (wasm2-emit :const 0)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-not not (seg vreg xfer cc form)
  (declare (ignore vreg xfer))
  (let* ((cond (acode-immediate-operand cc))
         (op (ecase cond
               (:eq :i32-eq)
               (:ne :i32-ne)))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil form)
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-endp endp (seg vreg xfer cc form)
  (declare (ignore vreg xfer))
  (let* ((cond (acode-immediate-operand cc))
         (op (ecase cond
               (:eq :i32-eq)
               (:ne :i32-ne)))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil form)
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-characterp characterp (seg vreg xfer cc form)
  (declare (ignore vreg xfer))
  (let* ((cond (acode-immediate-operand cc))
         (op (ecase cond
               (:eq :i32-eq)
               (:ne :i32-ne)))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil form)
    (wasm2-emit :const wasm::subtag-mask)
    (wasm2-emit :i32-and)
    (wasm2-emit :const wasm::subtag-character)
    (wasm2-emit op)
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defwasm2 wasm2-base-char-p base-char-p (seg vreg xfer cc form)
  (wasm2-characterp seg vreg xfer cc form))

(defwasm2 wasm2-istruct-typep istruct-typep (seg vreg xfer cc form type)
  (declare (ignore vreg xfer))
  (let* ((cond (acode-immediate-operand cc))
         (thing-temp (wasm2-allocate-temp))
         (type-temp (wasm2-allocate-temp))
         (tmp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil form)
    (wasm2-emit :local.set thing-temp)
    (wasm2-form seg nil nil type)
    (wasm2-emit :local.set type-temp)
    (wasm2-emit :local.get thing-temp)
    (wasm2-emit :const *wasm2-target-fulltagmask*)
    (wasm2-emit :i32-and)
    (wasm2-emit :const *wasm2-target-fulltag-misc*)
    (wasm2-emit :i32-eq)
    (let* ((then-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get thing-temp)
                        (unless (zerop wasm::misc-header-offset)
                          (wasm2-emit :const wasm::misc-header-offset)
                          (wasm2-emit :i32-add))
                        (wasm2-emit :i32-load)
                        (wasm2-emit :const wasm::subtag-mask)
                        (wasm2-emit :i32-and)
                        (wasm2-emit :const wasm::subtag-istruct)
                        (wasm2-emit :i32-eq)
                        (let* ((then2 (wasm2-with-ir
                                        (lambda ()
                                          (wasm2-emit :local.get thing-temp)
                                          (wasm2-emit :const (wasm2-box-fixnum 0))
                                          (wasm2-emit :lisp-word-ref)
                                          (wasm2-emit :local.get type-temp)
                                          (wasm2-emit :i32-eq)))
                               )
                               (else2 (wasm2-with-ir
                                        (lambda ()
                                          (wasm2-emit :const 0)))))
                          (wasm2-emit :if then2 else2)))))
           (else-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :const 0)))))
      (wasm2-emit :if then-ir else-ir))
    (case cond
      (:eq)
      (:ne (wasm2-emit :i32-eqz))
      (t (error "WASM2: unsupported istruct-typep condition ~s" cond)))
    (wasm2-emit :local.set tmp)
    (wasm2-emit :const (target-t-value))
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get tmp)
    (wasm2-emit :select))
  nil)

(defun wasm2-untag-mask ()
  (logand #xffffffff (lognot *wasm2-target-fulltagmask*)))

(defwasm2 wasm2-%car %car (seg vreg xfer form)
  (declare (ignore vreg))
  (wasm2-form seg nil nil form)
  (wasm2-emit :const (wasm2-untag-mask))
  (wasm2-emit :i32-and)
  (wasm2-emit-box-fixnum)
  (wasm2-emit :const (wasm2-box-fixnum 0))
  (wasm2-emit :lisp-word-ref)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%cdr %cdr (seg vreg xfer form)
  (declare (ignore vreg))
  (wasm2-form seg nil nil form)
  (wasm2-emit :const (wasm2-untag-mask))
  (wasm2-emit :i32-and)
  (wasm2-emit-box-fixnum)
  (wasm2-emit :const (wasm2-box-fixnum 1))
  (wasm2-emit :lisp-word-ref)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-car car (seg vreg xfer form)
  (declare (ignore vreg))
  (let* ((list-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil form)
    (wasm2-emit :local.set list-temp)
    (wasm2-emit :local.get list-temp)
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :i32-eq)
    (let* ((then-ir (wasm2-with-ir
                      (lambda () (wasm2-emit-const (target-nil-value)))))
           (else-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get list-temp)
                        (wasm2-emit :const (wasm2-untag-mask))
                        (wasm2-emit :i32-and)
                        (wasm2-emit-box-fixnum)
                        (wasm2-emit :const (wasm2-box-fixnum 0))
                        (wasm2-emit :lisp-word-ref)))))
      (wasm2-emit :if then-ir else-ir)))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-cdr cdr (seg vreg xfer form)
  (declare (ignore vreg))
  (let* ((list-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil form)
    (wasm2-emit :local.set list-temp)
    (wasm2-emit :local.get list-temp)
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :i32-eq)
    (let* ((then-ir (wasm2-with-ir
                      (lambda () (wasm2-emit-const (target-nil-value)))))
           (else-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get list-temp)
                        (wasm2-emit :const (wasm2-untag-mask))
                        (wasm2-emit :i32-and)
                        (wasm2-emit-box-fixnum)
                        (wasm2-emit :const (wasm2-box-fixnum 1))
                        (wasm2-emit :lisp-word-ref)))))
      (wasm2-emit :if then-ir else-ir)))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-lisptag lisptag (seg vreg xfer node)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil node)
  (wasm2-emit :const *wasm2-target-lisptag-mask*)
  (wasm2-emit :i32-and)
  (wasm2-emit-box-fixnum)
  nil)

(defwasm2 wasm2-fulltag fulltag (seg vreg xfer node)
  (declare (ignore vreg xfer))
  (wasm2-form seg nil nil node)
  (wasm2-emit :const *wasm2-target-fulltagmask*)
  (wasm2-emit :i32-and)
  (wasm2-emit-box-fixnum)
  nil)

(defwasm2 wasm2-typecode typecode (seg vreg xfer node)
  (declare (ignore vreg xfer))
  (let* ((obj-temp (wasm2-allocate-temp))
         (tag-temp (wasm2-allocate-temp))
         (tag-misc (logand *wasm2-target-fulltag-misc*
                           *wasm2-target-lisptag-mask*)))
    (wasm2-form seg nil nil node)
    (wasm2-emit :local.set obj-temp)
    (wasm2-emit :local.get obj-temp)
    (wasm2-emit :const *wasm2-target-lisptag-mask*)
    (wasm2-emit :i32-and)
    (wasm2-emit :local.set tag-temp)
    (wasm2-emit :local.get tag-temp)
    (wasm2-emit :const tag-misc)
    (wasm2-emit :i32-eq)
    (let* ((then-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get obj-temp)
                        (wasm2-emit :const (wasm2-untag-mask))
                        (wasm2-emit :i32-and)
                        (wasm2-emit-box-fixnum)
                        (wasm2-emit :const (wasm2-box-fixnum 0))
                        (wasm2-emit :lisp-word-ref)
                        (wasm2-emit :const #xff)
                        (wasm2-emit :i32-and)
                        (wasm2-emit-box-fixnum))))
           (else-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get tag-temp)
                        (wasm2-emit-box-fixnum)))))
      (wasm2-emit :if then-ir else-ir)))
  nil)

(defwasm2 wasm2-ivector-typecode-p ivector-typecode-p (seg vreg xfer val)
  (declare (ignore vreg))
  (let* ((val-temp (wasm2-allocate-temp))
         (cond-temp (wasm2-allocate-temp))
         (mask (logior *wasm2-target-lisptag-mask*
                       (ash *wasm2-target-fulltagmask* *wasm2-target-fixnum-shift*)))
         (needle (ash wasm::fulltag-immheader *wasm2-target-fixnum-shift*)))
    (wasm2-form seg nil nil val)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :const mask)
    (wasm2-emit :i32-and)
    (wasm2-emit :const needle)
    (wasm2-emit :i32-eq)
    (wasm2-emit :local.set cond-temp)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :const 0)
    (wasm2-emit :local.get cond-temp)
    (wasm2-emit :select)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-gvector-typecode-p gvector-typecode-p (seg vreg xfer val)
  (declare (ignore vreg))
  (let* ((val-temp (wasm2-allocate-temp))
         (cond-temp (wasm2-allocate-temp))
         (mask (logior *wasm2-target-lisptag-mask*
                       (ash *wasm2-target-fulltagmask* *wasm2-target-fixnum-shift*)))
         (needle (ash wasm::fulltag-nodeheader *wasm2-target-fixnum-shift*)))
    (wasm2-form seg nil nil val)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :const mask)
    (wasm2-emit :i32-and)
    (wasm2-emit :const needle)
    (wasm2-emit :i32-eq)
    (wasm2-emit :local.set cond-temp)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :const 0)
    (wasm2-emit :local.get cond-temp)
    (wasm2-emit :select)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-cons cons (seg vreg xfer y z)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPconslist-star)))
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-form seg nil nil y)
        (wasm2-emit :vpush)
        (wasm2-form seg nil nil z)
        (wasm2-emit :vpush)
        (wasm2-emit :set-nargs 2)
        (wasm2-emit :call-subprim subprim)
        (wasm2-emit :arg0))))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-list list (seg vreg xfer forms)
  (declare (ignore vreg))
  (if (null forms)
    (if (wasm2-returning-p xfer)
      (wasm2-emit-constant-return (target-nil-value))
      (wasm2-emit-const (target-nil-value)))
    (let* ((subprim (wasm2-subprim-fixnum '.SPconslist))
           (argc (length forms)))
      (wasm2-with-spilled-locals
        (lambda ()
          (dolist (form forms)
            (wasm2-form seg nil nil form)
            (wasm2-emit :vpush))
          (wasm2-emit :set-nargs argc)
          (wasm2-emit :call-subprim subprim)
          (wasm2-emit :arg0)))
      (when (wasm2-returning-p xfer)
        (wasm2-emit :return))))
  nil)

(defwasm2 wasm2-make-list make-list (seg vreg xfer size initial-element)
  (wasm2-form seg vreg xfer
              (make-acode (%nx1-operator call)
                          (make-acode (%nx1-operator immediate) 'make-list)
                          (list nil
                                (list initial-element
                                      (make-acode (%nx1-operator immediate)
                                                  :initial-element)
                                      size))))
  nil)

(defwasm2 wasm2-list* list* (seg vreg xfer forms)
  (declare (ignorable vreg))
  (let* ((args (if (and (consp forms)
                        (consp (cdr forms))
                        (null (cddr forms))
                        (listp (car forms))
                        (listp (cadr forms)))
                 (wasm2-arglist-forms forms)
                 forms))
         (argc (length args)))
    (cond
      ((= argc 0)
       (wasm2-unimplemented))
      ((= argc 1)
       (wasm2-form seg vreg xfer (car args)))
      (t
       (let* ((subprim (wasm2-subprim-fixnum '.SPconslist-star)))
         (wasm2-with-spilled-locals
           (lambda ()
             (dolist (form (butlast args))
               (wasm2-form seg nil nil form)
               (wasm2-emit :vpush))
             (wasm2-form seg nil nil (car (last args)))
             (wasm2-emit :set-arg0)
             (wasm2-emit :set-nargs (1- argc))
             (wasm2-emit :call-subprim subprim)
             (wasm2-emit :arg0)))
         (when (wasm2-returning-p xfer)
           (wasm2-emit :return))))))
  nil)

(defwasm2 wasm2-%double-float %double-float (seg vreg xfer arg)
  (declare (ignorable vreg xfer))
  (let* ((real (or (acode-fixnum-form-p arg) (wasm2-constant-real arg)))
         (dconst (and real (ignore-errors (float real 0.0d0)))))
    (cond
      (dconst
       (wasm2-emit :f64-const dconst)
       (wasm2-emit-box-double))
      ((acode-form-typep arg 'double-float t)
       (wasm2-form seg nil nil arg))
      ((acode-form-typep arg 'single-float t)
       (wasm2-form seg nil nil arg)
       (wasm2-emit-unbox-single)
       (wasm2-emit :f64-promote-f32)
       (wasm2-emit-box-double))
      ((acode-form-typep arg 'fixnum t)
       (wasm2-form seg nil nil arg)
       (wasm2-emit-unbox-fixnum)
       (wasm2-emit :f64-convert-i32-s)
       (wasm2-emit-box-double))
      (t
       (wasm2-form seg vreg xfer
                   (make-acode (%nx1-operator call)
                               (make-acode (%nx1-operator immediate) 'float)
                               (list nil
                                     (list arg
                                           (make-acode (%nx1-operator immediate) 0.0d0))))))))
  nil)

(defwasm2 wasm2-%single-float %single-float (seg vreg xfer arg)
  (declare (ignorable vreg xfer))
  (let* ((real (or (acode-fixnum-form-p arg) (wasm2-constant-real arg)))
         (sconst (and real (ignore-errors (float real 0.0f0)))))
    (cond
      (sconst
       (wasm2-emit :f32-const sconst)
       (wasm2-emit-box-single))
      ((acode-form-typep arg 'single-float t)
       (wasm2-form seg nil nil arg))
      ((acode-form-typep arg 'double-float t)
       (wasm2-form seg nil nil arg)
       (wasm2-emit-unbox-double)
       (wasm2-emit :f32-demote-f64)
       (wasm2-emit-box-single))
      ((acode-form-typep arg 'fixnum t)
       (wasm2-form seg nil nil arg)
       (wasm2-emit-unbox-fixnum)
       (wasm2-emit :f32-convert-i32-s)
       (wasm2-emit-box-single))
      (t
       (wasm2-form seg vreg xfer
                   (make-acode (%nx1-operator call)
                               (make-acode (%nx1-operator immediate) 'float)
                               (list nil
                                     (list arg
                                           (make-acode (%nx1-operator immediate) 0.0f0))))))))
  nil)

(defwasm2 wasm2-fixnum-overflow fixnum-overflow (seg vreg xfer form)
  (destructuring-bind (op n0 n1) (acode-unwrapped-form form)
    (backend-use-operator op seg vreg xfer n0 n1 (make-nx-t))))

(defwasm2 wasm2-immediate immediate (seg vreg xfer value)
  (declare (ignore seg vreg))
  (cond
    ((typep value 'double-float)
     (wasm2-emit :f64-const value)
     (wasm2-emit-box-double))
    ((typep value 'single-float)
     (wasm2-emit :f32-const value)
     (wasm2-emit-box-single))
    ((typep value 'float)
     (wasm2-emit :f64-const (float value 0.0d0))
     (wasm2-emit-box-double))
    (t
     (if (wasm2-returning-p xfer)
       (wasm2-emit-constant-return value)
       (wasm2-emit-const value))))
  nil)

(defwasm2 wasm2-%current-tcr %current-tcr (seg vreg xfer)
  (declare (ignore seg vreg))
  (wasm2-emit :get-current-tcr)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%current-frame-ptr %current-frame-ptr (seg vreg xfer)
  (declare (ignore seg vreg))
  ;; WASM doesn't expose native frame pointers; return NIL.
  (if (wasm2-returning-p xfer)
    (wasm2-emit-constant-return nil)
    (wasm2-emit-const nil))
  nil)

(when (and (boundp '*next-nx-operators*)
           (assq '%tcr-toplevel-function *next-nx-operators*))
  (defwasm2 wasm2-%tcr-toplevel-function %tcr-toplevel-function (seg vreg xfer tcr)
    (declare (ignore vreg))
    (wasm2-form seg nil nil tcr)
    (wasm2-emit :get-tcr-toplevel-function)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return))
    nil)

  (defwasm2 wasm2-%set-tcr-toplevel-function %set-tcr-toplevel-function (seg vreg xfer tcr fun)
    (declare (ignore vreg))
    (wasm2-form seg nil nil tcr)
    (wasm2-form seg nil nil fun)
    (wasm2-emit :set-tcr-toplevel-function)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return))
    nil))

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

(defun wasm2-arglist-forms-mvcall (arglist)
  (if (and (consp arglist)
           (consp (cdr arglist))
           (null (cddr arglist))
           (listp (car arglist))
           (listp (cadr arglist)))
    (wasm2-arglist-forms arglist)
    (if (listp arglist)
      arglist
      (error "Unexpected WASM mvcall arglist shape: ~s" arglist))))

(defun wasm2-constant-lispobj (form)
  (let* ((val (nx2-constant-form-value (acode-unwrapped-form-value form))))
    (cond ((null val) (values nil nil))
          ((nx-null val) (values (target-nil-value) t))
          ((nx-t val) (values (target-t-value) t))
          ((and (acode-p val) (eq (acode-operator val) (%nx1-operator fixnum)))
           (values (wasm2-box-fixnum (car (acode-operands val))) t))
          ((and (acode-p val) (eq (acode-operator val) (%nx1-operator immediate)))
           (let* ((imm (car (acode-operands val))))
             (if (typep imm 'float)
               (values nil nil)
               (values imm t))))
          (t (values nil nil)))))

(defun wasm2-constant-real (form)
  (let* ((val (acode-unwrapped-form-value form)))
    (when (acode-p val)
      (when (eq (acode-operator val) (%nx1-operator immediate))
        (let* ((imm (car (acode-operands val))))
          (when (typep imm 'real)
            imm))))))

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

(defwasm2 wasm2-progv progv (seg vreg xfer symbols values body)
  (declare (ignore vreg))
  (let* ((mvpass (wasm2-mv-p xfer))
         (progvsave (wasm2-subprim-fixnum '.SPprogvsave))
         (progvrestore (wasm2-subprim-fixnum '.SPprogvrestore))
         (save-fixnum (and mvpass (wasm2-subprim-fixnum '.SPsave-values)))
         (recover-fixnum (and mvpass (wasm2-subprim-fixnum '.SPrecover-values)))
         (result-temp (and (not mvpass) (wasm2-allocate-temp))))
    (wasm2-form seg nil nil symbols)
    (wasm2-emit :set-arg1)
    (wasm2-form seg nil nil values)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim-no-spill progvsave)
    (if mvpass
      (progn
        (wasm2-multiple-value-body seg body)
        (wasm2-emit-call-subprim-no-spill save-fixnum)
        (wasm2-emit :drop)
        (wasm2-emit-call-subprim-no-spill progvrestore)
        (wasm2-emit-call-subprim-no-spill recover-fixnum)
        (if (wasm2-returning-p xfer)
          (wasm2-emit :return)
          (wasm2-emit :arg0)))
      (progn
        (wasm2-form seg nil nil body)
        (wasm2-emit :local.set result-temp)
        (wasm2-emit-call-subprim-no-spill progvrestore)
        (wasm2-emit :local.get result-temp)
        (when (wasm2-returning-p xfer)
          (wasm2-emit :set-arg-z)
          (wasm2-emit :set-nargs 1)
          (wasm2-emit :return)))))
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

(defwasm2 wasm2-or or (seg vreg xfer forms)
  (declare (ignore vreg))
  (cond
    ((null forms)
     (wasm2-form seg nil xfer (make-acode (%nx1-operator nil))))
    ((null (cdr forms))
     (wasm2-form seg nil xfer (car forms)))
    (t
     (let* ((end-label (wasm2-allocate-label))
            (result-temp (wasm2-allocate-temp))
            (body-ir (wasm2-with-ir
                       (lambda ()
                         (dolist (form (butlast forms))
                           (wasm2-form seg nil nil form)
                           (wasm2-emit :local.set result-temp)
                           (wasm2-emit :local.get result-temp)
                           (wasm2-emit :if-void (list (list :br end-label)) nil))
                         (wasm2-form seg nil nil (car (last forms)))
                         (wasm2-emit :local.set result-temp)))))
       (wasm2-emit :block end-label body-ir)
       (wasm2-emit :local.get result-temp)
       (when (wasm2-returning-p xfer)
         (wasm2-emit :set-arg-z)
         (wasm2-emit :set-nargs 1)
         (wasm2-emit :return)))))
  nil)

(defwasm2 wasm2-progn progn (seg vreg xfer forms)
  (if forms
    (progn
      (dolist (form (butlast forms))
        (wasm2-form seg nil nil form)
        (wasm2-emit :drop))
      (wasm2-form seg vreg xfer (car (last forms))))
    (wasm2-form seg vreg xfer (make-acode (%nx1-operator nil)))))

(defun wasm2-emit-prog1 (seg vreg xfer forms)
  (if (eq (list-length forms) 1)
    (backend-use-operator (%nx1-operator values) seg vreg xfer forms)
    (let* ((tmp (wasm2-ensure-temp-local)))
      (wasm2-form seg nil nil (car forms))
      (wasm2-emit :local.set tmp)
      (dolist (form (cdr forms))
        (wasm2-form seg nil nil form)
        (wasm2-emit :drop))
      (wasm2-emit :local.get tmp)
      (when (wasm2-returning-p xfer)
        (wasm2-emit :set-arg-z)
        (wasm2-emit :set-nargs 1)
        (wasm2-emit :return))))
  nil)

(defwasm2 wasm2-prog1 prog1 (seg vreg xfer forms)
  (wasm2-emit-prog1 seg vreg xfer forms)
  nil)

(defwasm2 wasm2-multiple-value-prog1 multiple-value-prog1 (seg vreg xfer forms)
  (if (not (wasm2-mv-p xfer))
    (wasm2-emit-prog1 seg vreg xfer forms)
    (if (null (cdr forms))
      (wasm2-form seg vreg xfer (car forms))
      (let* ((save-fixnum (wasm2-subprim-fixnum '.SPsave-values))
             (recover-fixnum (wasm2-subprim-fixnum '.SPrecover-values)))
        (wasm2-multiple-value-body seg (car forms))
        (wasm2-emit-call-subprim-no-spill save-fixnum)
        (wasm2-emit :drop)
        (dolist (form (cdr forms))
          (wasm2-form seg nil nil form)
          (wasm2-emit :drop))
        (wasm2-emit-call-subprim-no-spill recover-fixnum)
        (if (wasm2-returning-p xfer)
          (wasm2-emit :return)
          (wasm2-emit :arg0)))))
  nil)

(defwasm2 wasm2-multiple-value-list multiple-value-list (seg vreg xfer form)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPconslist)))
    (wasm2-multiple-value-body seg form)
    ;; conslist consumes values from VSP; discard the primary value that
    ;; wasm2-multiple-value-body leaves on the wasm operand stack.
    (wasm2-emit :drop)
    ;; Values already live on VSP; avoid spills that would disturb them.
    (wasm2-emit-call-subprim-no-spill subprim)
    (if (wasm2-returning-p xfer)
      (wasm2-emit :return)
      (wasm2-emit :arg0)))
  nil)

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

(defun wasm2-emit-symbol-ref (sym check-boundp)
  (let* ((subprim (wasm2-subprim-fixnum (if check-boundp '.SPspecrefcheck '.SPspecref))))
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit-const sym)
        (wasm2-emit :set-arg0)
        (wasm2-emit-call-subprim subprim)
        (wasm2-emit :arg0))))
  nil)

(defun wasm2-emit-setq-symbol (seg sym val subprim-name)
  (let* ((subprim (wasm2-subprim-fixnum subprim-name))
         (val-temp (wasm2-ensure-temp-local)))
    (wasm2-form seg nil nil val)
    (wasm2-emit :local.set val-temp)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg0)
        (wasm2-emit-const sym)
        (wasm2-emit :set-arg1)
        (wasm2-emit-call-subprim subprim)))
    (wasm2-emit :local.get val-temp))
  nil)

(defwasm2 wasm2-special-ref special-ref (seg vreg xfer sym)
  (declare (ignore seg vreg xfer))
  (wasm2-emit-symbol-ref sym t)
  nil)

(defwasm2 wasm2-bound-special-ref bound-special-ref (seg vreg xfer sym)
  (declare (ignore seg vreg xfer))
  (wasm2-emit-symbol-ref sym nil)
  nil)

(defwasm2 wasm2-free-reference free-reference (seg vreg xfer sym)
  (declare (ignore seg vreg xfer))
  (wasm2-emit-symbol-ref sym t)
  nil)

(defwasm2 wasm2-global-ref global-ref (seg vreg xfer sym)
  (declare (ignore seg vreg xfer))
  (wasm2-emit-symbol-ref sym nil)
  nil)

(defwasm2 wasm2-setq-special setq-special (seg vreg xfer sym val)
  (declare (ignore vreg xfer))
  (wasm2-emit-setq-symbol seg sym val '.SPspecset)
  nil)

(defwasm2 wasm2-setq-free setq-free (seg vreg xfer sym val)
  (declare (ignore vreg xfer))
  (wasm2-emit-setq-symbol seg sym val '.SPsetqsym)
  nil)

(defwasm2 wasm2-global-setq global-setq (seg vreg xfer sym val)
  (declare (ignore vreg xfer))
  (wasm2-emit-setq-symbol seg sym val '.SPsetqsym)
  nil)

(defun wasm2-seq-bind-var (seg var value-form)
  (if (wasm2-var-closed-p var)
    (wasm2-emit-make-closed-var-cell seg value-form)
    (wasm2-form seg nil nil value-form))
  (wasm2-emit :local.set (wasm2-ensure-local var)))

(defun wasm2-seq-fbind (seg vreg xfer vars afuncs body)
  (declare (ignore vreg))
  (loop for var in vars
        for afunc in afuncs
        do (when (neq 0 (afunc-fn-refcount afunc))
             (wasm2-seq-bind-var seg var (nx1-afunc-ref afunc))))
  (wasm2-form seg nil xfer body)
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

(defwasm2 wasm2-flet flet (seg vreg xfer vars afuncs body p2decls)
  (declare (ignore vreg p2decls))
  (if (dolist (afunc afuncs)
        (unless (eql 0 (afunc-fn-refcount afunc))
          (return t)))
    (wasm2-seq-fbind seg nil xfer vars afuncs body)
    (wasm2-form seg nil xfer body))
  nil)

(defwasm2 wasm2-labels labels (seg vreg xfer vars afuncs body p2decls)
  (declare (ignore vreg p2decls))
  (let* ((fwd-refs nil)
         (func nil)
         (togo vars)
         (real-vars nil)
         (real-funcs nil)
         (funs afuncs))
    (dolist (v vars)
      (when (neq 0 (afunc-fn-refcount (setq func (pop funs))))
        (push v real-vars)
        (push func real-funcs)
        (let* ((i +wasm2-closure-cells-base+)
               (our-var nil)
               (item nil))
          (dolist (ref (afunc-inherited-vars func))
            (when (memq (setq our-var (var-bits ref)) togo)
              (setq item (cons i our-var))
              (let* ((refs (assq v fwd-refs)))
                (if refs
                  (push item (cdr refs))
                  (push (list v item) fwd-refs))))
            (incf i)))
        (setq togo (%cdr togo))))
    (setq real-vars (nreverse real-vars)
          real-funcs (nreverse real-funcs))
    (if (null fwd-refs)
      (wasm2-seq-fbind seg nil xfer real-vars real-funcs body)
      (let* ((funcs real-funcs))
        (dolist (var real-vars)
          (wasm2-seq-bind-var seg var (nx1-afunc-ref (pop funcs))))
        (dolist (ref fwd-refs)
          (let* ((closure-var (pop ref)))
            (dolist (r ref)
              (wasm2-emit-set-closure-forward-ref closure-var (car r) (cdr r)))))
        (wasm2-form seg nil xfer body))))
  nil)

(defwasm2 wasm2-lambda lambda-list (seg vreg xfer req opt rest keys auxen body p2decls &optional code-note)
  (declare (ignore vreg xfer p2decls code-note))
  (let* ((rest-var (if (consp rest) (car rest) rest))
         (optvars (and opt (car opt)))
         (optinits (and opt (cadr opt)))
         (optsups (and opt (caddr opt)))
         (allow-other-keys (and keys (car keys)))
         (keyvars (and keys (cadr keys)))
         (keysupps (and keys (caddr keys)))
         (keyinits (and keys (cadddr keys)))
         (keyvect (and keys (nth 4 keys)))
         (auxvars (and auxen (car auxen)))
         (auxinits (and auxen (cadr auxen)))
         (nargs-temp (and (or optvars rest-var)
                          (wasm2-allocate-temp))))
    (declare (ignore keyvect))
    (when nargs-temp
      (wasm2-emit :get-nargs)
      (wasm2-emit :local.set nargs-temp))
    (labels ((emit-assign (var emitter)
             (when var
               (funcall emitter)
               (when (wasm2-var-closed-p var)
                 (wasm2-emit-make-closed-var-cell-from-stack))
               (wasm2-emit :local.set (wasm2-ensure-local var))))
           (emit-assign-const (var value)
             (emit-assign var (lambda () (wasm2-emit-const value))))
           (emit-assign-from-local (var idx)
             (emit-assign var (lambda () (wasm2-emit :local.get idx))))
           (emit-assign-from-vsp (var idx)
             (emit-assign var (lambda () (wasm2-emit :vsp-ref idx))))
           (req-var-populated-by-arg-prologue-p (var idx)
             ;; When arg-reg compatibility prologue is active, req arg0/arg1
             ;; locals are already populated before lambda binding.
             (and (not *wasm2-use-arg-regs*)
                  (not (wasm2-var-closed-p var))
                  (or (and (= idx 0) (wasm2-arg0-var-name-p var))
                      (and (= idx 1) (wasm2-arg1-var-name-p var))))))
      (loop for var in req
            for idx from 0
            do (unless (req-var-populated-by-arg-prologue-p var idx)
                 (emit-assign-from-vsp var idx)))
      (when optvars
        (loop for var in optvars
              for init in optinits
              for spvar in optsups
              for idx from (length req)
              do
                (let* ((then-ir (wasm2-with-ir
                                  (lambda ()
                                    (emit-assign-from-vsp var idx)
                                    (when spvar
                                      (emit-assign-const spvar (target-t-value))))))
                       (else-ir (wasm2-with-ir
                                  (lambda ()
                                    (emit-assign var (lambda () (wasm2-form seg nil nil init)))
                                    (when spvar
                                      (emit-assign-const spvar (target-nil-value)))))))
                  (wasm2-emit :local.get nargs-temp)
                  (wasm2-emit :const idx)
                  (wasm2-emit :i32-gt-u)
                  (wasm2-emit :if-void then-ir else-ir))))
      (when keys
        (let* ((flags (if allow-other-keys 1 0))
               (subprim (wasm2-subprim-fixnum '.SPkeyword-bind))
               (prev-count (+ (length req) (length optvars))))
          (wasm2-emit :const (wasm2-box-fixnum flags))
          (wasm2-emit :set-arg1)
          (wasm2-emit :set-imm0 (wasm2-box-fixnum prev-count))
          (wasm2-emit-call-subprim subprim)
          (when keyvars
            (let* ((keycount (length keyvars)))
              (loop for var in keyvars
                    for init in keyinits
                    for spvar in keysupps
                    for i from 0
                    do
                      (let* ((sup-offset (* 2 (- keycount 1 i)))
                             (val-offset (1+ sup-offset))
                             (sup-temp (wasm2-allocate-temp)))
                        (wasm2-emit :vsp-ref sup-offset)
                        (wasm2-emit :local.set sup-temp)
                        (when spvar
                          (emit-assign-from-local spvar sup-temp))
                        (let* ((then-ir (wasm2-with-ir
                                          (lambda ()
                                            (emit-assign-from-vsp var val-offset))))
                               (else-ir (wasm2-with-ir
                                          (lambda ()
                                            (emit-assign var (lambda () (wasm2-form seg nil nil init)))))))
                          (wasm2-emit :local.get sup-temp)
                          (wasm2-emit :if-void then-ir else-ir))))
              (dotimes (_ (* 2 keycount))
                (wasm2-emit :vpop)
                (wasm2-emit :drop))))))
      (when rest-var
        (let* ((rest-start (+ (length req) (length optvars)))
               (rest-count (wasm2-allocate-temp))
               (loop-idx (wasm2-allocate-temp))
               (exit-label (wasm2-allocate-label))
               (loop-label (wasm2-allocate-label))
               (conslist (wasm2-subprim-fixnum '.SPconslist)))
          (let* ((then-ir (wasm2-with-ir
                            (lambda ()
                              (wasm2-emit :local.get nargs-temp)
                              (wasm2-emit :const rest-start)
                              (wasm2-emit :i32-sub)
                              (wasm2-emit :local.set rest-count))))
                 (else-ir (wasm2-with-ir
                            (lambda ()
                              (wasm2-emit :const 0)
                              (wasm2-emit :local.set rest-count)))))
            (wasm2-emit :local.get nargs-temp)
            (wasm2-emit :const rest-start)
            (wasm2-emit :i32-gt-u)
            (wasm2-emit :if-void then-ir else-ir))
          (wasm2-emit :const 0)
          (wasm2-emit :local.set loop-idx)
          (let* ((inner (wasm2-with-ir
                          (lambda ()
                            (wasm2-emit :local.get loop-idx)
                            (wasm2-emit :local.get rest-count)
                            (wasm2-emit :i32-ge-u)
                            (wasm2-emit :if-void (list (list :br exit-label)) nil)
                            (wasm2-emit :local.get loop-idx)
                            (wasm2-emit :const rest-start)
                            (wasm2-emit :i32-add)
                            (wasm2-emit :vsp-ref-dynamic)
                            (wasm2-emit :vpush)
                            (wasm2-emit :local.get loop-idx)
                            (wasm2-emit :const 1)
                            (wasm2-emit :i32-add)
                            (wasm2-emit :local.set loop-idx)
                            (wasm2-emit :br loop-label)))))
            (wasm2-emit :block exit-label (list (list :loop loop-label inner))))
          (wasm2-emit :local.get rest-count)
          (wasm2-emit :set-nargs-dynamic)
          (wasm2-emit-call-subprim conslist)
          (emit-assign rest-var (lambda () (wasm2-emit :arg0)))))
      (when auxvars
        (loop for var in auxvars
              for init in auxinits
              do (emit-assign var (lambda () (wasm2-form seg nil nil init)))))
      (wasm2-form seg nil $backend-return body)))
  nil)

(defwasm2 wasm2-lambda-bind lambda-bind (seg vreg xfer vals req rest keys-p auxen body p2decls)
  (declare (ignore vreg p2decls keys-p))
  (let* ((nreq (length req))
         (rest-args (nthcdr nreq vals))
         (conslist (wasm2-subprim-fixnum '.SPconslist)))
    (labels ((emit-assign (var emitter)
             (when var
               (funcall emitter)
               (when (wasm2-var-closed-p var)
                 (wasm2-emit-make-closed-var-cell-from-stack))
               (wasm2-emit :local.set (wasm2-ensure-local var)))))
      (loop for var in req
            for val in vals
            do (wasm2-seq-bind-var seg var val))
      (when rest
        (if rest-args
          (progn
            (dolist (val rest-args)
              (wasm2-form seg nil nil val)
              (wasm2-emit :vpush))
            (wasm2-emit :set-nargs (length rest-args))
            (wasm2-emit-call-subprim conslist)
            (emit-assign rest (lambda () (wasm2-emit :arg0))))
          (emit-assign rest (lambda () (wasm2-emit-const (target-nil-value))))))
      (destructuring-bind (vars inits) auxen
        (loop for var in vars
              for init in inits
              do (if (fixnump init)
                   (emit-assign var (lambda () (wasm2-emit-const (wasm2-box-fixnum init))))
                   (emit-assign var (lambda () (wasm2-form seg nil nil init))))))
      (wasm2-form seg nil xfer body)))
  nil)

(defwasm2 wasm2-typed-form typed-form (seg vreg xfer typespec form &optional check)
  (declare (ignore typespec check))
  (wasm2-form seg vreg xfer form)
  nil)

(eval-when (:compile-toplevel :load-toplevel :execute)
  (defmacro defwasm2-require (name)
    (let* ((fname (intern (format nil "WASM2-~A" name) (find-package "CCL"))))
      `(defwasm2 ,fname ,name (seg vreg xfer form)
         (wasm2-form seg vreg xfer form)
         nil))))

(defwasm2-require require-list)
(defwasm2-require require-fixnum)
(defwasm2-require require-integer)
(defwasm2-require require-real)
(defwasm2-require require-number)
(defwasm2-require require-symbol)
(defwasm2-require require-simple-vector)
(defwasm2-require require-simple-string)
(defwasm2-require require-character)
(defwasm2-require require-s8)
(defwasm2-require require-u8)
(defwasm2-require require-s16)
(defwasm2-require require-u16)
(defwasm2-require require-s32)
(defwasm2-require require-u32)
(defwasm2-require require-s64)
(defwasm2-require require-u64)

(defwasm2 wasm2-%badarg2 %badarg2 (seg vreg xfer badthing goodthing)
  (declare (ignore vreg xfer))
  (let* ((bad-temp (wasm2-allocate-temp))
         (good-temp (wasm2-allocate-temp))
         (subprim (wasm2-subprim-fixnum '.SPksignalerr))
         (err-code (wasm2-box-fixnum $XWRONGTYPE)))
    (wasm2-form seg nil nil badthing)
    (wasm2-emit :local.set bad-temp)
    (wasm2-form seg nil nil goodthing)
    (wasm2-emit :local.set good-temp)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :local.get good-temp)
        (wasm2-emit :local.get bad-temp)
        (wasm2-emit :const err-code)
        (wasm2-emit :set-arg2)
        (wasm2-emit :set-arg1)
        (wasm2-emit :set-arg0)
        (wasm2-emit :set-nargs 3)
        (wasm2-emit :call-subprim subprim)))
    (wasm2-emit-const (target-nil-value)))
  nil)

(defwasm2 wasm2-%err-disp %err-disp (seg vreg xfer arglist)
  (declare (ignore vreg xfer))
  (let* ((args (wasm2-arglist-forms arglist))
         (argc (length args))
         (subprim (wasm2-subprim-fixnum '.SPksignalerr)))
    (dolist (arg args)
      (wasm2-form seg nil nil arg)
      (wasm2-emit :vpush))
    (wasm2-emit :set-nargs argc)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :call-subprim subprim)))
    (wasm2-emit :restore-vsp)
    (wasm2-emit-const (target-nil-value)))
  nil)

(defwasm2 wasm2-%lisp-word-ref %lisp-word-ref (seg vreg xfer base offset)
  (declare (ignore vreg))
  (wasm2-form seg nil nil base)
  (wasm2-form seg nil nil offset)
  (wasm2-emit :lisp-word-ref)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%fixnum-ref %fixnum-ref (seg vreg xfer base offset)
  (declare (ignore vreg))
  (wasm2-form seg nil nil base)
  (wasm2-form seg nil nil offset)
  (wasm2-emit :lisp-word-ref)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%fixnum-ref-natural %fixnum-ref-natural (seg vreg xfer base offset)
  (declare (ignore vreg))
  (wasm2-form seg nil nil base)
  (wasm2-form seg nil nil offset)
  (wasm2-emit :lisp-word-ref)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defun wasm2-emit-misc-node-slot-address (index)
  (wasm2-emit :const *wasm2-target-fulltag-misc*)
  (wasm2-emit :i32-sub)
  (cond
    ((minusp *wasm2-target-misc-data-offset*)
     (wasm2-emit :const (- *wasm2-target-misc-data-offset*))
     (wasm2-emit :i32-sub))
    ((plusp *wasm2-target-misc-data-offset*)
     (wasm2-emit :const *wasm2-target-misc-data-offset*)
     (wasm2-emit :i32-add)))
  (unless (zerop index)
    (wasm2-emit :const (* index *wasm2-target-node-size*))
    (wasm2-emit :i32-add)))

(defun wasm2-emit-misc-subtag-test (obj-local subtag)
  (wasm2-emit :local.get obj-local)
  (wasm2-emit :const *wasm2-target-fulltagmask*)
  (wasm2-emit :i32-and)
  (wasm2-emit :const *wasm2-target-fulltag-misc*)
  (wasm2-emit :i32-eq)
  (let* ((then-ir (wasm2-with-ir
                    (lambda ()
                      (wasm2-emit :local.get obj-local)
                      (unless (zerop wasm::misc-header-offset)
                        (wasm2-emit :const wasm::misc-header-offset)
                        (wasm2-emit :i32-add))
                      (wasm2-emit :i32-load)
                      (wasm2-emit :const wasm::subtag-mask)
                      (wasm2-emit :i32-and)
                      (wasm2-emit :const subtag)
                      (wasm2-emit :i32-eq))))
         (else-ir (wasm2-with-ir
                    (lambda ()
                      (wasm2-emit :const 0)))))
    (wasm2-emit :if then-ir else-ir)))

(defwasm2 wasm2-%setf-macptr %setf-macptr (seg vreg xfer ptr val)
  (declare (ignore vreg))
  (let* ((ptr-temp (wasm2-allocate-temp))
         (val-temp (wasm2-allocate-temp))
         (raw-temp (wasm2-allocate-temp))
         (misc-ref (wasm2-subprim-fixnum '.SPmisc-ref))
         (misc-set (wasm2-subprim-fixnum '.SPmisc-set)))
    (wasm2-form seg nil nil ptr)
    (wasm2-emit :local.set ptr-temp)
    (wasm2-form seg nil nil val)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit-misc-subtag-test val-temp wasm::subtag-macptr)
    (let* ((then-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get val-temp)
                        (wasm2-emit :const (wasm2-box-fixnum 1))
                        (wasm2-emit :set-arg1)
                        (wasm2-emit :set-arg0)
                        (wasm2-emit-call-subprim misc-ref)
                        (wasm2-emit :arg0))))
           (else-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get val-temp)
                        (wasm2-emit-unbox-fixnum)))))
      (wasm2-emit :if then-ir else-ir))
    (wasm2-emit :local.set raw-temp)
    (wasm2-emit-misc-subtag-test ptr-temp wasm::subtag-macptr)
    (let* ((then-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get ptr-temp)
                        (wasm2-emit-misc-node-slot-address 1)
                        (wasm2-emit :local.get raw-temp)
                        (wasm2-emit :i32-store)
                        (wasm2-emit :local.get raw-temp))))
           (else-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get ptr-temp)
                        (wasm2-emit :const (wasm2-box-fixnum 1))
                        (wasm2-emit :local.get raw-temp)
                        (wasm2-emit :set-arg2)
                        (wasm2-emit :set-arg1)
                        (wasm2-emit :set-arg0)
                        (wasm2-emit-call-subprim misc-set)
                        (wasm2-emit :arg0)))))
      (wasm2-emit :if then-ir else-ir))
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%setf-double-float %setf-double-float (seg vreg xfer double-node double-val)
  (declare (ignore vreg))
  (let* ((returning (wasm2-returning-p xfer))
         (val-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil double-node)
    (wasm2-emit :const *wasm2-target-fulltag-misc*)
    (wasm2-emit :i32-sub)
    (when (minusp *wasm2-target-misc-dfloat-offset*)
      (wasm2-emit :const (- *wasm2-target-misc-dfloat-offset*))
      (wasm2-emit :i32-sub))
    (wasm2-form seg nil nil double-val)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit-unbox-double)
    (wasm2-emit :f64-store (if (minusp *wasm2-target-misc-dfloat-offset*) 0 *wasm2-target-misc-dfloat-offset*))
    (if returning
      (progn
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg-z)
        (wasm2-emit :set-nargs 1)
        (wasm2-emit :return))
      (wasm2-emit :local.get val-temp)))
  nil)

(defwasm2 wasm2-%setf-short-float %setf-short-float (seg vreg xfer single-node single-val)
  (declare (ignore vreg))
  (let* ((returning (wasm2-returning-p xfer))
         (val-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil single-node)
    (wasm2-emit :const *wasm2-target-fulltag-misc*)
    (wasm2-emit :i32-sub)
    (when (minusp *wasm2-target-misc-data-offset*)
      (wasm2-emit :const (- *wasm2-target-misc-data-offset*))
      (wasm2-emit :i32-sub))
    (wasm2-form seg nil nil single-val)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit-unbox-single)
    (wasm2-emit :f32-store (if (minusp *wasm2-target-misc-data-offset*) 0 *wasm2-target-misc-data-offset*))
    (if returning
      (progn
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg-z)
        (wasm2-emit :set-nargs 1)
        (wasm2-emit :return))
      (wasm2-emit :local.get val-temp)))
  nil)

(defwasm2 wasm2-%macptrptr% %macptrptr% (seg vreg xfer form)
  (declare (ignore vreg))
  (let* ((misc-ref (wasm2-subprim-fixnum '.SPmisc-ref)))
    (wasm2-form seg nil nil form)
    (wasm2-emit :const (wasm2-box-fixnum 1))
    (wasm2-emit :set-arg1)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-ref)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%consmacptr% %consmacptr% (seg vreg xfer form)
  (declare (ignore vreg))
  (let* ((addr-temp (wasm2-allocate-temp))
         (obj-temp (wasm2-allocate-temp))
         (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc)))
    (wasm2-form seg nil nil form)
    (wasm2-emit :local.set addr-temp)
    (wasm2-emit :const (wasm2-box-fixnum wasm::macptr.element-count))
    (wasm2-emit :set-arg1)
    (wasm2-emit :const (wasm2-box-fixnum wasm::subtag-macptr))
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-alloc)
    (wasm2-emit :arg0)
    (wasm2-emit :local.set obj-temp)
    (wasm2-emit :local.get obj-temp)
    (wasm2-emit-misc-node-slot-address 1)
    (wasm2-emit :local.get addr-temp)
    (wasm2-emit :i32-store)
    (wasm2-emit :local.get addr-temp)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%immediate-ptr-to-int %immediate-ptr-to-int (seg vreg xfer form)
  (declare (ignore vreg))
  (wasm2-form seg nil nil form)
  (wasm2-emit-box-fixnum)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%immediate-int-to-ptr %immediate-int-to-ptr (seg vreg xfer form)
  (declare (ignore vreg))
  (wasm2-form seg nil nil form)
  (wasm2-emit-unbox-fixnum)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%immediate-inc-ptr %immediate-inc-ptr (seg vreg xfer ptr by)
  (declare (ignore vreg))
  (wasm2-form seg nil nil ptr)
  (wasm2-form seg nil nil by)
  (wasm2-emit-unbox-fixnum)
  (wasm2-emit :i32-add)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-immediate-get-xxx immediate-get-xxx (seg vreg xfer bits ptr offset)
  (declare (ignore vreg))
  (let* ((fixnump (logbitp 6 bits))
         (signed (logbitp 5 bits))
         (size (logand 15 bits)))
    (wasm2-form seg nil nil ptr)
    (wasm2-form seg nil nil offset)
    (wasm2-emit-unbox-fixnum)
    (wasm2-emit :i32-add)
    (case size
      (1 (wasm2-emit (if signed :i32-load8-s :i32-load8-u)))
      (2 (wasm2-emit (if signed :i32-load16-s :i32-load16-u)))
      (4 (wasm2-emit :i32-load))
      (t (error "WASM2: unsupported immediate-get-xxx size: ~s" size)))
    (unless fixnump
      (wasm2-emit-box-fixnum))
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-immediate-get-ptr immediate-get-ptr (seg vreg xfer ptr offset)
  (declare (ignore vreg))
  (wasm2-form seg nil nil ptr)
  (wasm2-form seg nil nil offset)
  (wasm2-emit-unbox-fixnum)
  (wasm2-emit :i32-add)
  (wasm2-emit :i32-load)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-immediate-set-xxx %immediate-set-xxx (seg vreg xfer bits ptr offset val)
  (declare (ignore vreg))
  (let* ((size (logand 15 bits))
         (store-ptr (zerop size))
         (store-size (if store-ptr 4 size))
         (returning (wasm2-returning-p xfer))
         (val-temp (wasm2-allocate-temp))
         (addr-temp (when store-ptr (wasm2-allocate-temp)))
         (raw-temp (when store-ptr (wasm2-allocate-temp))))
    (wasm2-form seg nil nil ptr)
    (wasm2-form seg nil nil offset)
    (wasm2-emit-unbox-fixnum)
    (wasm2-emit :i32-add)
    (when store-ptr
      (wasm2-emit :local.set addr-temp))
    (wasm2-form seg nil nil val)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :local.get val-temp)
    (if store-ptr
      (let* ((misc-ref (wasm2-subprim-fixnum '.SPmisc-ref)))
        (wasm2-emit :const (wasm2-box-fixnum 1))
        (wasm2-emit :set-arg1)
        (wasm2-emit :set-arg0)
        (wasm2-emit-call-subprim misc-ref)
        (wasm2-emit :arg0)
        (wasm2-emit :local.set raw-temp)
        (wasm2-emit :local.get addr-temp)
        (wasm2-emit :local.get raw-temp))
      (wasm2-emit-unbox-fixnum))
    (case store-size
      (1 (wasm2-emit :i32-store8))
      (2 (wasm2-emit :i32-store16))
      (4 (wasm2-emit :i32-store))
      (t (error "WASM2: unsupported immediate-set-xxx size: ~s" store-size)))
    (if returning
      (progn
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg-z)
        (wasm2-emit :set-nargs 1)
        (wasm2-emit :return))
      (wasm2-emit :local.get val-temp)))
  nil)

(defun wasm2-string-index-8bit-p ()
  (let* ((arch (backend-target-arch *target-backend*))
         (limit (arch::target-char-code-limit arch)))
    (<= limit 256)))

(defun wasm2-emit-char-code (seg xfer form)
  (let* ((shift (arch::target-charcode-shift (backend-target-arch *target-backend*))))
    (wasm2-form seg nil nil form)
    (when (not (zerop shift))
      (wasm2-emit :const shift)
      (wasm2-emit :i32-shr-u))
    (wasm2-emit-box-fixnum)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return))))

(defwasm2 wasm2-%char-code %char-code (seg vreg xfer c)
  (declare (ignore vreg))
  (wasm2-emit-char-code seg xfer c)
  nil)

(defwasm2 wasm2-char-code char-code (seg vreg xfer c)
  (declare (ignore vreg))
  (wasm2-emit-char-code seg xfer c)
  nil)

(defwasm2 wasm2-%scharcode %scharcode (seg vreg xfer str idx)
  (declare (ignore vreg))
  (let* ((bytep (wasm2-string-index-8bit-p)))
    (wasm2-form seg nil nil str)
    (wasm2-form seg nil nil idx)
    (when bytep
      (wasm2-emit-unbox-fixnum))
    (wasm2-emit :i32-add)
    (unless (zerop *wasm2-target-misc-data-offset*)
      (wasm2-emit :const *wasm2-target-misc-data-offset*)
      (wasm2-emit :i32-add))
    (if bytep
      (wasm2-emit :i32-load8-u)
      (wasm2-emit :i32-load))
    (wasm2-emit-box-fixnum)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%sbchar %sbchar (seg vreg xfer str idx)
  (declare (ignore vreg))
  (let* ((bytep (wasm2-string-index-8bit-p))
         (shift (arch::target-charcode-shift (backend-target-arch *target-backend*))))
    (wasm2-form seg nil nil str)
    (wasm2-form seg nil nil idx)
    (when bytep
      (wasm2-emit-unbox-fixnum))
    (wasm2-emit :i32-add)
    (unless (zerop *wasm2-target-misc-data-offset*)
      (wasm2-emit :const *wasm2-target-misc-data-offset*)
      (wasm2-emit :i32-add))
    (if bytep
      (wasm2-emit :i32-load8-u)
      (wasm2-emit :i32-load))
    (when (not (zerop shift))
      (wasm2-emit :const shift)
      (wasm2-emit :i32-shl))
    (wasm2-emit :const wasm::subtag-character)
    (wasm2-emit :i32-add)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%set-sbchar %set-sbchar (seg vreg xfer str idx value)
  (declare (ignore vreg))
  (let* ((bytep (wasm2-string-index-8bit-p))
         (shift (arch::target-charcode-shift (backend-target-arch *target-backend*)))
         (returning (wasm2-returning-p xfer))
         (val-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil str)
    (wasm2-form seg nil nil idx)
    (when bytep
      (wasm2-emit-unbox-fixnum))
    (wasm2-emit :i32-add)
    (unless (zerop *wasm2-target-misc-data-offset*)
      (wasm2-emit :const *wasm2-target-misc-data-offset*)
      (wasm2-emit :i32-add))
    (wasm2-form seg nil nil value)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :const shift)
    (wasm2-emit :i32-shr-u)
    (if bytep
      (wasm2-emit :i32-store8)
      (wasm2-emit :i32-store))
    (if returning
      (progn
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg-z)
        (wasm2-emit :set-nargs 1)
        (wasm2-emit :return))
      (wasm2-emit :local.get val-temp)))
  nil)

(defwasm2 wasm2-%code-char %code-char (seg vreg xfer c)
  (declare (ignore vreg))
  (let* ((arch (backend-target-arch *target-backend*))
         (delta (- (arch::target-charcode-shift arch)
                   (arch::target-fixnum-shift arch))))
    (wasm2-form seg nil nil c)
    (when (not (zerop delta))
      (wasm2-emit :const delta)
      (wasm2-emit :i32-shl))
    (wasm2-emit :const wasm::subtag-character)
    (wasm2-emit :i32-add)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-code-char code-char (seg vreg xfer c)
  (declare (ignore vreg))
  (let* ((arch (backend-target-arch *target-backend*))
         (delta (- (arch::target-charcode-shift arch)
                   (arch::target-fixnum-shift arch)))
         (limit (arch::target-char-code-limit arch))
         (limit-fixnum (wasm2-box-fixnum limit))
         (code-temp (wasm2-allocate-temp))
         (cond-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil c)
    (wasm2-emit :local.set code-temp)
    (wasm2-emit :local.get code-temp)
    (wasm2-emit :const limit-fixnum)
    (wasm2-emit :i32-le-u)
    (wasm2-emit :local.set cond-temp)
    (wasm2-emit :local.get code-temp)
    (when (not (zerop delta))
      (wasm2-emit :const delta)
      (wasm2-emit :i32-shl))
    (wasm2-emit :const wasm::subtag-character)
    (wasm2-emit :i32-add)
    (wasm2-emit :const (target-nil-value))
    (wasm2-emit :local.get cond-temp)
    (wasm2-emit :select)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%valid-code-char %valid-code-char (seg vreg xfer c)
  (declare (ignore vreg))
  (let* ((arch (backend-target-arch *target-backend*))
         (delta (- (arch::target-charcode-shift arch)
                   (arch::target-fixnum-shift arch))))
    (wasm2-form seg nil nil c)
    (when (not (zerop delta))
      (wasm2-emit :const delta)
      (wasm2-emit :i32-shl))
    (wasm2-emit :const wasm::subtag-character)
    (wasm2-emit :i32-add)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%set-scharcode %set-scharcode (seg vreg xfer str idx code)
  (declare (ignore vreg))
  (let* ((bytep (wasm2-string-index-8bit-p))
         (returning (wasm2-returning-p xfer))
         (val-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil str)
    (wasm2-form seg nil nil idx)
    (when bytep
      (wasm2-emit-unbox-fixnum))
    (wasm2-emit :i32-add)
    (unless (zerop *wasm2-target-misc-data-offset*)
      (wasm2-emit :const *wasm2-target-misc-data-offset*)
      (wasm2-emit :i32-add))
    (wasm2-form seg nil nil code)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit-unbox-fixnum)
    (if bytep
      (wasm2-emit :i32-store8)
      (wasm2-emit :i32-store))
    (if returning
      (progn
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg-z)
        (wasm2-emit :set-nargs 1)
        (wasm2-emit :return))
      (wasm2-emit :local.get val-temp)))
  nil)

(defwasm2 wasm2-%symbol->symptr %symbol->symptr (seg vreg xfer sym)
  (declare (ignore vreg))
  (let* ((sym-temp (wasm2-allocate-temp))
         (nilsym-offset wasm::nilsym-offset))
    (wasm2-form seg nil nil sym)
    (wasm2-emit :local.set sym-temp)
    (let* ((then-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get sym-temp)
                        (wasm2-emit :const nilsym-offset)
                        (wasm2-emit :i32-add))))
           (else-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get sym-temp)))))
      (wasm2-emit :local.get sym-temp)
      (wasm2-emit :const (target-nil-value))
      (wasm2-emit :i32-eq)
      (wasm2-emit :if then-ir else-ir))
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defun wasm2-emit-rplac (seg ptr val subprim returnptr)
  (let* ((ptr-temp (wasm2-allocate-temp))
         (val-temp (wasm2-allocate-temp)))
    (wasm2-form seg nil nil ptr)
    (wasm2-emit :local.set ptr-temp)
    (wasm2-form seg nil nil val)
    (wasm2-emit :local.set val-temp)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :local.get ptr-temp)
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg0)
        (wasm2-emit :set-arg1)
        (wasm2-emit-call-subprim subprim)
        (if returnptr
          (wasm2-emit :local.get ptr-temp)
          (wasm2-emit :local.get val-temp))))))

(defwasm2 wasm2-%rplaca %rplaca (seg vreg xfer ptr val)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPrplaca)))
    (wasm2-emit-rplac seg ptr val subprim t))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%rplacd %rplacd (seg vreg xfer ptr val)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPrplacd)))
    (wasm2-emit-rplac seg ptr val subprim t))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-rplaca rplaca (seg vreg xfer ptr val)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPrplaca)))
    (wasm2-emit-rplac seg ptr val subprim t))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-rplacd rplacd (seg vreg xfer ptr val)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPrplacd)))
    (wasm2-emit-rplac seg ptr val subprim t))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-set-car set-car (seg vreg xfer ptr val)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPrplaca)))
    (wasm2-emit-rplac seg ptr val subprim nil))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-set-cdr set-cdr (seg vreg xfer ptr val)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPrplacd)))
    (wasm2-emit-rplac seg ptr val subprim nil))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%slot-ref %slot-ref (seg vreg xfer instance idx)
  (declare (ignore vreg))
  (wasm2-form seg nil nil instance)
  (wasm2-form seg nil nil idx)
  (wasm2-emit :lisp-word-ref)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-struct-ref struct-ref (seg vreg xfer struct offset)
  (declare (ignore vreg))
  (wasm2-form seg nil nil struct)
  (wasm2-form seg nil nil offset)
  (wasm2-emit :lisp-word-ref)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-struct-set struct-set (seg vreg xfer struct offset value)
  (wasm2-%svset seg vreg xfer struct offset value))

(defwasm2 wasm2-%svref %svref (seg vreg xfer vector index)
  (declare (ignore vreg))
  (wasm2-form seg nil nil vector)
  (wasm2-form seg nil nil index)
  (wasm2-emit :lisp-word-ref)
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-svref svref (seg vreg xfer vector index)
  (wasm2-%svref seg vreg xfer vector index))

(defwasm2 wasm2-vector vector (seg vreg xfer arglist)
  (declare (ignore vreg))
  (let* ((args (wasm2-arglist-forms-mvcall arglist))
         (argc (1+ (length args)))
         (subprim (wasm2-subprim-fixnum '.SPgvector))
         (subtag (wasm2-box-fixnum (nx-lookup-target-uvector-subtag :simple-vector))))
    (wasm2-emit :const subtag)
    (wasm2-emit :vpush)
    (dolist (arg args)
      (wasm2-form seg nil nil arg)
      (wasm2-emit :vpush))
    (wasm2-emit :set-nargs argc)
    (wasm2-emit-call-subprim subprim)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%gvector %gvector (seg vreg xfer arglist)
  (declare (ignore vreg))
  (let* ((args (wasm2-arglist-forms arglist))
         (argc (length args))
         (subprim (wasm2-subprim-fixnum '.SPgvector)))
    (dolist (arg args)
      (wasm2-form seg nil nil arg)
      (wasm2-emit :vpush))
    (wasm2-emit :set-nargs argc)
    (wasm2-emit-call-subprim subprim)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%svset %svset (seg vreg xfer vector index value)
  (declare (ignore vreg))
  (let* ((vec-temp (wasm2-allocate-temp))
         (idx-temp (wasm2-allocate-temp))
         (val-temp (wasm2-allocate-temp))
         (proven-slot (wasm2-proven-svset-slot-p index))
         (simple-vector-subtag (nx-lookup-target-uvector-subtag :simple-vector)))
    (wasm2-form seg nil nil vector)
    (wasm2-emit :local.set vec-temp)
    (if proven-slot
      (progn
        (wasm2-form seg nil nil value)
        (wasm2-emit :local.set val-temp)
        (wasm2-emit-misc-slot-set-with-subtag-guard vec-temp proven-slot val-temp
                                                     simple-vector-subtag t))
      (progn
        (wasm2-form seg nil nil index)
        (wasm2-emit :local.set idx-temp)
        (wasm2-form seg nil nil value)
        (wasm2-emit :local.set val-temp)
        (wasm2-emit-misc-set-fallback-local vec-temp idx-temp val-temp t t))))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-svset svset (seg vreg xfer vector index value)
  (declare (ignore vreg))
  (let* ((vec-temp (wasm2-allocate-temp))
         (idx-temp (wasm2-allocate-temp))
         (val-temp (wasm2-allocate-temp))
         (misc-set (wasm2-subprim-fixnum '.SPsubtag-misc-set))
         (subtag (wasm2-box-fixnum (nx-lookup-target-uvector-subtag :simple-vector))))
    (wasm2-form seg nil nil vector)
    (wasm2-emit :local.set vec-temp)
    (wasm2-form seg nil nil index)
    (wasm2-emit :local.set idx-temp)
    (wasm2-form seg nil nil value)
    (wasm2-emit :local.set val-temp)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :local.get vec-temp)
        (wasm2-emit :local.get idx-temp)
        (wasm2-emit :local.get val-temp)
        (wasm2-emit :set-arg2)
        (wasm2-emit :set-arg1)
        (wasm2-emit :set-arg0)
        (wasm2-emit :set-imm0 subtag)
        (wasm2-emit-call-subprim misc-set)
        (wasm2-emit :arg0))))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%typed-uvref %typed-uvref (seg vreg xfer subtag uvector index)
  (declare (ignore vreg))
  (let* ((subtag-value (or (acode-fixnum-form-p subtag)
                           (let ((kw (acode-immediate-operand subtag)))
                             (when kw
                               (nx-lookup-target-uvector-subtag kw)))))
         (boxed-subtag (and subtag-value (wasm2-box-fixnum subtag-value))))
    (unless boxed-subtag
      (wasm2-unimplemented))
    (let* ((vec-temp (wasm2-allocate-temp))
           (idx-temp (wasm2-allocate-temp))
           (misc-ref (wasm2-subprim-fixnum '.SPsubtag-misc-ref)))
      (wasm2-form seg nil nil uvector)
      (wasm2-emit :local.set vec-temp)
      (wasm2-form seg nil nil index)
      (wasm2-emit :local.set idx-temp)
      (wasm2-with-spilled-locals
        (lambda ()
          (wasm2-emit :local.get vec-temp)
          (wasm2-emit :local.get idx-temp)
          (wasm2-emit :set-arg1)
          (wasm2-emit :set-arg0)
          (wasm2-emit :set-imm0 boxed-subtag)
          (wasm2-emit-call-subprim misc-ref)
          (wasm2-emit :arg0)))))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
  nil)

(defwasm2 wasm2-%typed-uvset %typed-uvset (seg vreg xfer subtag uvector index newval)
  (declare (ignore vreg))
  (let* ((subtag-value (or (acode-fixnum-form-p subtag)
                           (let ((kw (acode-immediate-operand subtag)))
                             (when kw
                               (nx-lookup-target-uvector-subtag kw)))))
         (boxed-subtag (and subtag-value (wasm2-box-fixnum subtag-value))))
    (unless boxed-subtag
      (wasm2-unimplemented))
    (let* ((vec-temp (wasm2-allocate-temp))
           (idx-temp (wasm2-allocate-temp))
           (val-temp (wasm2-allocate-temp))
           (misc-set (wasm2-subprim-fixnum '.SPsubtag-misc-set)))
      (wasm2-form seg nil nil uvector)
      (wasm2-emit :local.set vec-temp)
      (wasm2-form seg nil nil index)
      (wasm2-emit :local.set idx-temp)
      (wasm2-form seg nil nil newval)
      (wasm2-emit :local.set val-temp)
      (wasm2-with-spilled-locals
        (lambda ()
          (wasm2-emit :local.get vec-temp)
          (wasm2-emit :local.get idx-temp)
          (wasm2-emit :local.get val-temp)
          (wasm2-emit :set-arg2)
          (wasm2-emit :set-arg1)
          (wasm2-emit :set-arg0)
          (wasm2-emit :set-imm0 boxed-subtag)
          (wasm2-emit-call-subprim misc-set)
          (wasm2-emit :arg0)))))
  (when (wasm2-returning-p xfer)
    (wasm2-emit :set-arg-z)
    (wasm2-emit :set-nargs 1)
    (wasm2-emit :return))
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
  (let* ((args (wasm2-arglist-forms-mvcall arglist))
         (argc (length args))
         (mvpass (wasm2-mv-p xfer))
         (funcall-fixnum (wasm2-subprim-fixnum '.SPfuncall))
         (save-fixnum (wasm2-subprim-fixnum '.SPsave-values))
         (add-fixnum (wasm2-subprim-fixnum '.SPadd-values))
         (recover-fixnum (wasm2-subprim-fixnum '.SPrecover-values)))
    (cond
      ((= argc 0)
       (let* ((tmp (wasm2-ensure-temp-local)))
         (wasm2-form seg nil nil fn)
         (wasm2-emit (if mvpass :call0-mv :call0) tmp)))
      ((= argc 1)
       (let* ((fn-temp (wasm2-ensure-temp-local)))
         (wasm2-form seg nil nil fn)
         (wasm2-emit :local.set fn-temp)
        (wasm2-multiple-value-body seg (car args))
        (wasm2-emit :local.get fn-temp)
        (wasm2-emit :set-nfn)
        ;; Preserve live locals/roots across funcall.
        (wasm2-emit-call-subprim funcall-fixnum)
         (wasm2-emit :pending-throw-branch)
         (unless mvpass
           (wasm2-emit :restore-vsp))
         (if (wasm2-returning-p xfer)
           (wasm2-emit :return)
           (wasm2-emit :arg0))))
      (t
       (let* ((fn-temp (wasm2-ensure-temp-local)))
         (wasm2-form seg nil nil fn)
         (wasm2-emit :local.set fn-temp)
         (wasm2-multiple-value-body seg (car args))
         (wasm2-emit-call-subprim-no-spill save-fixnum)
         (dolist (form (cdr args))
           (wasm2-multiple-value-body seg form)
           (wasm2-emit-call-subprim-no-spill add-fixnum))
        (wasm2-emit-call-subprim-no-spill recover-fixnum)
        (wasm2-emit :local.get fn-temp)
        (wasm2-emit :set-nfn)
        ;; Preserve live locals/roots across funcall.
        (wasm2-emit-call-subprim funcall-fixnum)
         (wasm2-emit :pending-throw-branch)
         (unless mvpass
           (wasm2-emit :restore-vsp))
         (if (wasm2-returning-p xfer)
           (wasm2-emit :return)
           (wasm2-emit :arg0))))))
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

(defwasm2 wasm2-%function %function (seg vreg xfer sym)
  (declare (ignore seg vreg xfer))
  (unless (symbolp sym)
    (wasm2-unimplemented))
  (let* ((index (truncate (- wasm::symbol.fcell *wasm2-target-misc-data-offset*)
                          *wasm2-target-node-size*)))
    (wasm2-emit-const sym)
    (wasm2-emit :const (wasm2-box-fixnum index))
    (wasm2-emit :lisp-word-ref))
  nil)

(defwasm2 wasm2-simple-function simple-function (seg vreg xfer afunc)
  (declare (ignore seg vreg xfer))
  (let* ((lfun (wasm2-afunc-lfun afunc)))
    (wasm2-emit-const lfun))
  nil)

(defwasm2 wasm2-closed-function closed-function (seg vreg xfer afunc)
  (declare (ignore seg vreg xfer))
  (let* ((lfun (wasm2-afunc-lfun afunc)))
    (let* ((inherited-vars (afunc-inherited-vars afunc))
           (vsize (+ (length inherited-vars) +wasm2-closure-cells-base+ 2))
           (subtag (wasm2-box-fixnum (nx-lookup-target-uvector-subtag :function)))
           (count (wasm2-box-fixnum vsize))
           (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
           (vec-temp (wasm2-allocate-temp))
           (code-temp (wasm2-allocate-temp))
           (entry-temp (wasm2-allocate-temp)))
      (wasm2-emit :const count)
      (wasm2-emit :set-arg1)
      (wasm2-emit :const subtag)
      (wasm2-emit :set-arg0)
      (wasm2-emit-call-subprim misc-alloc)
      (wasm2-emit :arg0)
      (wasm2-emit :local.set vec-temp)

      ;; closure codevector and entrypoint
      (wasm2-emit-symbol-ref '%closure-code% nil)
      (wasm2-emit :local.set code-temp)
      (wasm2-emit :local.get code-temp)
      (wasm2-emit :const (wasm2-box-fixnum 0))
      (wasm2-emit :lisp-word-ref)
      (wasm2-emit :local.set entry-temp)

      ;; slot 0: entrypoint
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit-misc-node-slot-address 0)
      (wasm2-emit :local.get entry-temp)
      (wasm2-emit :i32-store)

      ;; slot 1: codevector
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit-misc-node-slot-address 1)
      (wasm2-emit :local.get code-temp)
      (wasm2-emit :i32-store)

      ;; slot 2: lfun
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit-misc-node-slot-address 2)
      (wasm2-emit-const lfun)
      (wasm2-emit :i32-store)

      ;; slots 3..: captured cells
      (loop for var in inherited-vars
            for idx from 0
               do (wasm2-emit :local.get vec-temp)
                  (wasm2-emit-misc-node-slot-address (+ +wasm2-closure-cells-base+ idx))
                  (wasm2-emit-closed-var-cell var)
                  (wasm2-emit :i32-store))

      ;; name slot
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit-misc-node-slot-address (+ +wasm2-closure-cells-base+ (length inherited-vars)))
      (wasm2-emit :const (target-nil-value))
      (wasm2-emit :i32-store)

      ;; lfun-bits slot (trampoline)
      (wasm2-emit :local.get vec-temp)
      (wasm2-emit-misc-node-slot-address (+ +wasm2-closure-cells-base+ (length inherited-vars) 1))
      (wasm2-emit :const (wasm2-box-fixnum (ash 1 $lfbits-trampoline-bit)))
      (wasm2-emit :i32-store)

      (wasm2-emit :local.get vec-temp)))
  nil)

(defwasm2 wasm2-%alloc-misc %make-uvector (seg vreg xfer element-count st &optional initval)
  (declare (ignore vreg))
  (let* ((misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
         (misc-alloc-init (wasm2-subprim-fixnum '.SPmisc-alloc-init)))
    (if initval
      (progn
        (wasm2-form seg nil nil element-count)
        (wasm2-emit :set-arg1)
        (wasm2-form seg nil nil st)
        (wasm2-emit :set-arg0)
        (wasm2-form seg nil nil initval)
        (wasm2-emit :set-arg2)
        (wasm2-emit-call-subprim misc-alloc-init)
        (wasm2-emit :arg0))
      (progn
        (wasm2-form seg nil nil element-count)
        (wasm2-emit :set-arg1)
        (wasm2-form seg nil nil st)
        (wasm2-emit :set-arg0)
        (wasm2-emit-call-subprim misc-alloc)
        (wasm2-emit :arg0)))
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-uvsize uvsize (seg vreg xfer v)
  (declare (ignore vreg))
  (let* ((mask (logand #xffffffff (lognot wasm::subtag-mask)))
         (shift (- wasm::num-subtag-bits wasm::fixnum-shift)))
    (wasm2-form seg nil nil v)
    (unless (zerop wasm::misc-header-offset)
      (wasm2-emit :const wasm::misc-header-offset)
      (wasm2-emit :i32-add))
    (wasm2-emit :i32-load)
    (wasm2-emit :const mask)
    (wasm2-emit :i32-and)
    (wasm2-emit :const shift)
    (wasm2-emit :i32-shr-u)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%aref1 %aref1 (seg vreg xfer vector index)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPbuiltin-aref1)))
    (wasm2-form seg nil nil vector)
    (wasm2-form seg nil nil index)
    (wasm2-emit :set-arg1)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim subprim)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defwasm2 wasm2-%aset1 aset1 (seg vreg xfer vector index value)
  (declare (ignore vreg))
  (let* ((subprim (wasm2-subprim-fixnum '.SPbuiltin-aset1)))
    (wasm2-form seg nil nil vector)
    (wasm2-form seg nil nil index)
    (wasm2-form seg nil nil value)
    (wasm2-emit :set-arg2)
    (wasm2-emit :set-arg1)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim subprim)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(defun wasm2-uvref (seg vreg xfer vector index)
  (declare (ignore vreg))
  (let* ((misc-ref (wasm2-subprim-fixnum '.SPmisc-ref)))
    (wasm2-form seg nil nil vector)
    (wasm2-form seg nil nil index)
    (wasm2-emit :set-arg1)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-ref)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(eval-when (:compile-toplevel :load-toplevel :execute)
  (setf (svref *wasm2-specials* (%ilogand operator-id-mask (%nx1-operator uvref)))
        #'wasm2-uvref))

(defun wasm2-uvset (seg vreg xfer vector index value)
  (declare (ignore vreg))
  (let* ((misc-set (wasm2-subprim-fixnum '.SPmisc-set)))
    (wasm2-form seg nil nil vector)
    (wasm2-form seg nil nil index)
    (wasm2-form seg nil nil value)
    (wasm2-emit :set-arg2)
    (wasm2-emit :set-arg1)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-set)
    (wasm2-emit :arg0)
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return)))
  nil)

(eval-when (:compile-toplevel :load-toplevel :execute)
  (setf (svref *wasm2-specials* (%ilogand operator-id-mask (%nx1-operator uvset)))
        #'wasm2-uvset))

(defun wasm2-emit-funcall-subprim (seg xfer fn-temp args)
  (let* ((argc (length args))
         (mvpass (wasm2-mv-p xfer))
         (funcall-fixnum (wasm2-subprim-fixnum '.SPfuncall)))
    (dolist (arg args)
      (wasm2-form seg nil nil arg)
      (wasm2-emit :vpush))
    (wasm2-emit :local.get fn-temp)
    (wasm2-emit :set-nfn)
    (wasm2-emit :set-nargs argc)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :call-subprim funcall-fixnum)
        (wasm2-emit :pending-throw-branch)))
    (unless mvpass
      (wasm2-emit :restore-vsp))
    (if (wasm2-returning-p xfer)
      (wasm2-emit :return)
      (wasm2-emit :arg0))))

(defun wasm2-emit-spread-call (seg xfer fn-emitter args spread-p)
  (let* ((fixed-args (butlast args))
         (list-arg (car (last args)))
         (argc (length fixed-args))
         (mvpass (wasm2-mv-p xfer))
         (fn-temp (wasm2-ensure-temp-local))
         (list-temp (and list-arg (wasm2-ensure-temp-local)))
         (spread-subprim (wasm2-subprim-fixnum
                          (if (eql spread-p 0) '.SPspread-lexprz '.SPspreadargz)))
         (funcall-fixnum (wasm2-subprim-fixnum '.SPfuncall)))
    (funcall fn-emitter fn-temp)
    (dolist (arg fixed-args)
      (wasm2-form seg nil nil arg)
      (wasm2-emit :vpush))
    (unless list-arg
      (error "WASM2: spread call missing list argument"))
    (wasm2-form seg nil nil list-arg)
    (wasm2-emit :local.set list-temp)
    (wasm2-emit :local.get list-temp)
    (wasm2-emit :set-arg0)
    (wasm2-emit :set-nargs argc)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :call-subprim spread-subprim)))
    (wasm2-emit :local.get fn-temp)
    (wasm2-emit :set-nfn)
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :call-subprim funcall-fixnum)
        (wasm2-emit :pending-throw-branch)))
    (unless mvpass
      (wasm2-emit :restore-vsp))
    (if (wasm2-returning-p xfer)
      (wasm2-emit :return)
      (wasm2-emit :arg0))))

(defun wasm2-emit-call (seg fn arglist spread-p &optional xfer)
  (let* ((args (wasm2-arglist-forms arglist))
         (argc (length args))
         (mvpass (wasm2-mv-p xfer))
         (tmp (wasm2-ensure-temp-local)))
    (when spread-p
      (wasm2-emit-spread-call
       seg xfer
       (lambda (fn-temp)
         (wasm2-form seg nil nil fn)
         (wasm2-emit :local.set fn-temp))
       args
       spread-p)
      (return-from wasm2-emit-call nil))
    (flet ((emit-fixnum-binary (opcode x y)
             (if (and (wasm2-returning-p xfer)
                      (wasm2-arg0-form-p x)
                      (wasm2-arg1-form-p y))
               (progn
                 (wasm2-emit opcode)
                 (wasm2-emit :return))
               (let* ((x-temp (wasm2-allocate-temp))
                      (y-temp (wasm2-allocate-temp)))
                 (wasm2-form seg nil nil x)
                 (wasm2-emit :local.set x-temp)
                 (wasm2-form seg nil nil y)
                 (wasm2-emit :local.set y-temp)
                 (wasm2-emit :local.get x-temp)
                 (wasm2-emit :local.get y-temp)
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
    (when (> argc 10)
      (let* ((fn-temp (wasm2-ensure-temp-local)))
        (wasm2-form seg nil nil fn)
        (wasm2-emit :local.set fn-temp)
        (wasm2-emit-funcall-subprim seg xfer fn-temp args)
        (return-from wasm2-emit-call nil)))
    (let* ((fn-temp (wasm2-allocate-temp))
           (arg-temps nil))
      (wasm2-form seg nil nil fn)
      (wasm2-emit :local.set fn-temp)
      (dolist (arg args)
        (let* ((arg-temp (wasm2-allocate-temp)))
          (wasm2-form seg nil nil arg)
          (wasm2-emit :local.set arg-temp)
          (push arg-temp arg-temps)))
      (wasm2-emit :local.get fn-temp)
      (dolist (arg-temp (nreverse arg-temps))
        (wasm2-emit :local.get arg-temp)))
    (case argc
      (0 (wasm2-emit (if mvpass :call0-mv :call0) tmp))
      (1 (wasm2-emit (if mvpass :call1-mv :call1) tmp))
      (2 (wasm2-emit (if mvpass :call2-mv :call2) tmp))
      (3 (wasm2-emit (if mvpass :call3-mv :call3) tmp))
      (4 (wasm2-emit (if mvpass :call4-mv :call4) tmp))
      (5 (wasm2-emit (if mvpass :call5-mv :call5) tmp))
      (6 (wasm2-emit (if mvpass :call6-mv :call6) tmp))
      (7 (wasm2-emit (if mvpass :call7-mv :call7) tmp))
      (8 (wasm2-emit (if mvpass :call8-mv :call8) tmp))
      (9 (wasm2-emit (if mvpass :call9-mv :call9) tmp))
      (10 (wasm2-emit (if mvpass :call10-mv :call10) tmp))
      (t (error "WASM2: unsupported call arity: ~d" argc))))
    (when (wasm2-returning-p xfer)
      ;; Consume the wasm stack result; arg regs already hold the values.
      (wasm2-emit :drop)
      (wasm2-emit :return)))

(defwasm2 wasm2-call call (seg vreg xfer fn arglist &optional spread-p)
  (declare (ignore vreg))
  (wasm2-emit-call seg fn arglist spread-p xfer)
  nil)

(defwasm2 wasm2-ff-call wasm-ff-call (seg vreg xfer name argspecs argvals resultspec &optional monitor)
  (declare (ignore vreg monitor))
  (wasm2-emit-external-call seg xfer name argspecs argvals resultspec)
  nil)

(defwasm2 wasm2-builtin-call builtin-call (seg vreg xfer fn arglist)
  (declare (ignore vreg))
  (wasm2-emit-call seg fn arglist nil xfer)
  nil)

(defwasm2 wasm2-lexical-function-call lexical-function-call (seg vreg xfer afunc arglist &optional spread-p)
  (declare (ignore vreg))
  (let* ((lfun (wasm2-afunc-lfun afunc)))
    (let* ((args (wasm2-arglist-forms arglist))
           (argc (length args))
           (mvpass (wasm2-mv-p xfer))
           (tmp (wasm2-ensure-temp-local)))
      (when spread-p
        (wasm2-emit-spread-call
         seg xfer
         (lambda (fn-temp)
           (wasm2-emit-const lfun)
           (wasm2-emit :local.set fn-temp))
         args
         spread-p)
        (return-from wasm2-lexical-function-call nil))
      (when (> argc 10)
        (let* ((fn-temp (wasm2-ensure-temp-local)))
          (wasm2-emit-const lfun)
          (wasm2-emit :local.set fn-temp)
          (wasm2-emit-funcall-subprim seg xfer fn-temp args)
          (return-from wasm2-lexical-function-call nil)))
      (let* ((fn-temp (wasm2-allocate-temp))
             (arg-temps nil))
        (wasm2-emit-const lfun)
        (wasm2-emit :local.set fn-temp)
        (dolist (arg args)
          (let* ((arg-temp (wasm2-allocate-temp)))
            (wasm2-form seg nil nil arg)
            (wasm2-emit :local.set arg-temp)
            (push arg-temp arg-temps)))
        (wasm2-emit :local.get fn-temp)
        (dolist (arg-temp (nreverse arg-temps))
          (wasm2-emit :local.get arg-temp)))
      (case argc
        (0 (wasm2-emit (if mvpass :call0-mv :call0) tmp))
        (1 (wasm2-emit (if mvpass :call1-mv :call1) tmp))
        (2 (wasm2-emit (if mvpass :call2-mv :call2) tmp))
        (3 (wasm2-emit (if mvpass :call3-mv :call3) tmp))
        (4 (wasm2-emit (if mvpass :call4-mv :call4) tmp))
        (5 (wasm2-emit (if mvpass :call5-mv :call5) tmp))
        (6 (wasm2-emit (if mvpass :call6-mv :call6) tmp))
        (7 (wasm2-emit (if mvpass :call7-mv :call7) tmp))
        (8 (wasm2-emit (if mvpass :call8-mv :call8) tmp))
        (9 (wasm2-emit (if mvpass :call9-mv :call9) tmp))
        (10 (wasm2-emit (if mvpass :call10-mv :call10) tmp))
        (t (error "WASM2: unsupported call arity: ~d" argc)))))
  nil)

(defwasm2 wasm2-self-call self-call (seg vreg xfer arglist &optional spread-p)
  (declare (ignore vreg))
  (let* ((lfun (afunc-lfun *wasm2-cur-afunc*)))
    (let* ((args (wasm2-arglist-forms arglist))
           (argc (length args))
           (mvpass (wasm2-mv-p xfer))
           (tmp (wasm2-ensure-temp-local)))
      (when spread-p
        (wasm2-emit-spread-call
         seg xfer
         (lambda (fn-temp)
           (if lfun
             (wasm2-emit-const lfun)
             (wasm2-emit :get-nfn))
           (wasm2-emit :local.set fn-temp))
         args
         spread-p)
        (return-from wasm2-self-call nil))
      (when (> argc 10)
        (let* ((fn-temp (wasm2-ensure-temp-local)))
          (if lfun
            (wasm2-emit-const lfun)
            (wasm2-emit :get-nfn))
          (wasm2-emit :local.set fn-temp)
          (wasm2-emit-funcall-subprim seg xfer fn-temp args)
          (return-from wasm2-self-call nil)))
      (let* ((fn-temp (wasm2-allocate-temp))
             (arg-temps nil))
        (if lfun
          (wasm2-emit-const lfun)
          (wasm2-emit :get-nfn))
        (wasm2-emit :local.set fn-temp)
        (dolist (arg args)
          (let* ((arg-temp (wasm2-allocate-temp)))
            (wasm2-form seg nil nil arg)
            (wasm2-emit :local.set arg-temp)
            (push arg-temp arg-temps)))
        (wasm2-emit :local.get fn-temp)
        (dolist (arg-temp (nreverse arg-temps))
          (wasm2-emit :local.get arg-temp)))
      (case argc
        (0 (wasm2-emit (if mvpass :call0-mv :call0) tmp))
        (1 (wasm2-emit (if mvpass :call1-mv :call1) tmp))
        (2 (wasm2-emit (if mvpass :call2-mv :call2) tmp))
        (3 (wasm2-emit (if mvpass :call3-mv :call3) tmp))
        (4 (wasm2-emit (if mvpass :call4-mv :call4) tmp))
        (5 (wasm2-emit (if mvpass :call5-mv :call5) tmp))
        (6 (wasm2-emit (if mvpass :call6-mv :call6) tmp))
        (7 (wasm2-emit (if mvpass :call7-mv :call7) tmp))
        (8 (wasm2-emit (if mvpass :call8-mv :call8) tmp))
        (9 (wasm2-emit (if mvpass :call9-mv :call9) tmp))
        (10 (wasm2-emit (if mvpass :call10-mv :call10) tmp))
        (t (error "WASM2: unsupported call arity: ~d" argc)))))
  nil)

(defvar *wasm2-cur-afunc* nil)
(defvar *wasm2-vstack* 0)
(defvar *wasm2-cstack* 0)
(defvar *wasm2-target-fixnum-shift* 0)
(defvar *wasm2-target-node-shift* 0)
(defvar *wasm2-target-bits-in-word* 0)
(defvar *wasm2-target-node-size* 0)
(defvar *wasm2-target-lisptag-mask* 0)
(defvar *wasm2-target-fulltag-misc* 0)
(defvar *wasm2-target-fulltagmask* 0)
(defvar *wasm2-target-misc-data-offset* 0)
(defvar *wasm2-target-misc-dfloat-offset* 0)
(defvar *wasm2-target-unbound-marker* 0)
(defvar *wasm2-target-slot-unbound-marker* 0)
(defvar *wasm2-target-illegal-marker* 0)
(defvar *wasm2-target-single-float-count* 1)
(defvar *wasm2-target-double-float-count* 2)
(defvar *wasm2-ir* nil)
(defvar *wasm2-locals* nil)
(defvar *wasm2-local-types* nil)
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
(defvar *wasm2-collect-module-debug* nil)
(defvar *wasm2-compiled-modules-debug* nil)

(defun wasm2-reset-compiled-modules-debug ()
  (setf *wasm2-compiled-modules-debug* nil))

(defun wasm2-ir-walk (ir fn)
  (dolist (ins ir)
    (funcall fn ins)
    (case (car ins)
      ((:if :if-void)
       (destructuring-bind (then-ir else-ir) (cdr ins)
         (wasm2-ir-walk then-ir fn)
         (wasm2-ir-walk else-ir fn)))
      (:block
       (destructuring-bind (_label block-ir) (cdr ins)
         (declare (ignore _label))
         (wasm2-ir-walk block-ir fn)))
      (:loop
       (destructuring-bind (_label loop-ir) (cdr ins)
         (declare (ignore _label))
         (wasm2-ir-walk loop-ir fn))))))

(defun wasm2-ir-count-op (ir op)
  (let ((count 0))
    (wasm2-ir-walk ir (lambda (ins)
                        (when (eq (car ins) op)
                          (incf count))))
    count))

(defun wasm2-ir-tail-ops (ir &optional (limit 32))
  (let* ((ops (mapcar #'car ir))
         (len (length ops)))
    (if (<= len limit)
      ops
      (nthcdr (- len limit) ops))))

(defun wasm2-ir-gc-root-boundary-ops (ir)
  (let ((ops nil))
    (wasm2-ir-walk ir
                   (lambda (ins)
                     (let ((op (car ins)))
                       (when (member op *wasm2-gc-root-default-required-ops* :test #'eq)
                         (pushnew op ops :test #'eq)))))
    (nreverse ops)))

(defun wasm2-ir-requires-runtime-default-mode-p (ir)
  (not (null (wasm2-ir-gc-root-boundary-ops ir))))

(defun wasm2-ir-gc-root-policy-mode (ir)
  (if (wasm2-ir-requires-runtime-default-mode-p ir)
    +wasm2-gc-root-mode-runtime-default+
    +wasm2-gc-root-mode-runtime-bootstrap+))

(defun wasm2-make-module-debug-info (export-name entry-index module-version
                                                &key afunc ir gc-root-policy-mode gc-root-boundary-ops)
  (let* ((name (and afunc (afunc-name afunc)))
         (ir-len (and ir (length ir)))
         (tail (and ir (wasm2-ir-tail-ops ir 48)))
         (ir-short (and ir (<= ir-len 64)
                        (mapcar #'prin1-to-string ir))))
    (list :export-name export-name
          :entry-index entry-index
          :module-version module-version
          :gc-root-policy-mode gc-root-policy-mode
          :gc-root-boundary-ops (and gc-root-boundary-ops
                                     (mapcar #'symbol-name gc-root-boundary-ops))
          :afunc-name (and name (prin1-to-string name))
          :ir-len ir-len
          :if-count (and ir (wasm2-ir-count-op ir :if))
          :if-void-count (and ir (wasm2-ir-count-op ir :if-void))
          :ir-tail (and tail (mapcar #'symbol-name tail))
          :ir-short ir-short)))

(defstruct wasm2-tagbody-context
  tag-map
  loop-label
  state-local)

(defun wasm2-register-compiled-module (module-bytes export-name entry-index module-version
                                         &optional const-pool-bytes debug-info
                                                   (gc-root-policy-mode +wasm2-gc-root-mode-runtime-default+))
  (when module-bytes
    (let* ((entry (make-array 6 :initial-contents
                              (list module-bytes
                                    export-name
                                    entry-index
                                    module-version
                                    const-pool-bytes
                                    gc-root-policy-mode))))
      (unless (find entry-index %wasm-compiled-modules%
                    :key (lambda (item) (svref item 2))
                    :test #'eql)
        (setf %wasm-compiled-modules% (cons entry %wasm-compiled-modules%)))
      (when *wasm2-collect-module-debug*
        (push (or debug-info
                  (list :export-name export-name
                        :entry-index entry-index
                        :module-version module-version
                        :gc-root-policy-mode gc-root-policy-mode))
              *wasm2-compiled-modules-debug*)))))

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
  (setf *wasm2-local-types* (make-array 0 :adjustable t :fill-pointer 0))
  (setf *wasm2-temp-local* nil)
  (setf *wasm2-spillable-locals* nil)
  nil)

(defun wasm2-allocate-local (&optional (spillp t) (type :i32))
  (let* ((idx *wasm2-local-count*))
    (incf *wasm2-local-count*)
    (vector-push-extend type *wasm2-local-types*)
    (when spillp
      (push idx *wasm2-spillable-locals*))
    idx))

(defun wasm2-ensure-local (var)
  (or (gethash var *wasm2-locals*)
      (setf (gethash var *wasm2-locals*)
            (wasm2-allocate-local))))

(defun wasm2-allocate-temp ()
  (wasm2-allocate-local))

(defun wasm2-allocate-f32-temp ()
  (wasm2-allocate-local nil :f32))

(defun wasm2-allocate-f64-temp ()
  (wasm2-allocate-local nil :f64))

(defun wasm2-allocate-raw-temp ()
  (wasm2-allocate-local nil))

(defun wasm2-ensure-temp-local ()
  (or *wasm2-temp-local*
      (setf *wasm2-temp-local* (wasm2-allocate-temp))))

(defun wasm2-var-closed-p (var)
  (logbitp $vbitclosed (nx-var-bits var)))

(defun wasm2-var-live-p (var)
  (let ((refs (var-refs var)))
    (and (integerp refs) (> refs 0))))

(defun wasm2-closed-var-index (var)
  (let* ((vars (afunc-inherited-vars *wasm2-cur-afunc*)))
    (position var vars :test #'eq)))

(defun wasm2-closed-var-slot (var)
  (let* ((idx (wasm2-closed-var-index var)))
    (when idx
      (+ +wasm2-closure-cells-base+ idx))))

(defun wasm2-subprim-fixnum (name &optional allow-compat-boundary)
  (when (and (not allow-compat-boundary)
             (member name *wasm2-compat-boundary-subprim-symbols* :test #'eq))
    (error "WASM2: compat-boundary subprim ~s requires explicit boundary key" name))
  (wasm2-box-fixnum (subprim-name->offset name)))

(defun wasm2-compat-boundary-subprim-fixnum (compat-key)
  (wasm2-subprim-fixnum (wasm2-compat-boundary-subprim-symbol compat-key) t))

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

(defun wasm2-emit-var-value (var)
  (if (wasm2-var-closed-p var)
    (wasm2-emit-closed-var-value var)
    (wasm2-emit :local.get (wasm2-ensure-local var))))

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

(defun wasm2-emit-misc-set-fallback-local (obj-local slot value-local
                                           &optional return-value-p slot-is-local-p)
  (let* ((misc-set (wasm2-subprim-fixnum '.SPmisc-set)))
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :local.get obj-local)
        (if slot-is-local-p
          (wasm2-emit :local.get slot)
          (wasm2-emit :const slot))
        (wasm2-emit :local.get value-local)
        (wasm2-emit :set-arg2)
        (wasm2-emit :set-arg1)
        (wasm2-emit :set-arg0)
        (wasm2-emit-call-subprim misc-set)
        (when return-value-p
          (wasm2-emit :arg0))))))

(defun wasm2-emit-misc-slot-set-with-subtag-guard (obj-local slot value-local expected-subtag
                                                    &optional return-value-p)
  (let* ((slot-fixnum (wasm2-box-fixnum slot)))
    (wasm2-emit-misc-subtag-test obj-local expected-subtag)
    (let* ((then-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit :local.get obj-local)
                        (wasm2-emit-misc-node-slot-address slot)
                        (wasm2-emit :local.get value-local)
                        (wasm2-emit :i32-store)
                        (when return-value-p
                          (wasm2-emit :local.get value-local)))))
           (else-ir (wasm2-with-ir
                      (lambda ()
                        (wasm2-emit-misc-set-fallback-local obj-local slot-fixnum value-local
                                                             return-value-p)))))
      (if return-value-p
        (wasm2-emit :if then-ir else-ir)
        (wasm2-emit :if-void then-ir else-ir)))))

(defun wasm2-proven-svset-slot-p (slot-form)
  (let* ((slot (acode-fixnum-form-p slot-form)))
    (and (typep slot 'fixnum)
         (nx2-constant-index-ok-for-type-keyword slot :simple-vector)
         slot)))

(defun wasm2-proven-closure-forward-ref-slot-p (slot)
  (and (typep slot 'fixnum)
       (>= slot +wasm2-closure-cells-base+)))

(defun wasm2-emit-closed-var-set (seg var value-form)
  (let* ((val-temp (wasm2-allocate-temp))
         (cell-temp (wasm2-allocate-temp))
         (simple-vector-subtag (nx-lookup-target-uvector-subtag :simple-vector)))
    (wasm2-form seg nil nil value-form)
    (wasm2-emit :local.set val-temp)
    (wasm2-emit-closed-var-cell var)
    (wasm2-emit :local.set cell-temp)
    (wasm2-emit-misc-slot-set-with-subtag-guard cell-temp 0 val-temp simple-vector-subtag t)))

(defun wasm2-emit-set-closure-forward-ref (closure-var slot ref-var)
  (let* ((closure-temp (wasm2-allocate-temp))
         (ref-temp (wasm2-allocate-temp))
         (slot-fixnum (and (typep slot 'fixnum)
                           (wasm2-box-fixnum slot)))
         (function-subtag (nx-lookup-target-uvector-subtag :function)))
    (unless slot-fixnum
      (error "WASM2: unsupported non-fixnum closure forward-ref slot ~s" slot))
    (wasm2-emit-var-value closure-var)
    (wasm2-emit :local.set closure-temp)
    (wasm2-emit-closed-var-cell ref-var)
    (wasm2-emit :local.set ref-temp)
    (if (wasm2-proven-closure-forward-ref-slot-p slot)
      (wasm2-emit-misc-slot-set-with-subtag-guard closure-temp slot ref-temp function-subtag)
      (wasm2-emit-misc-set-fallback-local closure-temp slot-fixnum ref-temp))))

(defun wasm2-emit-make-closed-var-cell (seg value-form)
  (let* ((val-temp (wasm2-allocate-temp))
         (vec-temp (wasm2-allocate-temp))
         (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
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
    (wasm2-emit-misc-node-slot-address 0)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :i32-store)
    (wasm2-emit :local.get vec-temp)))

(defun wasm2-emit-make-closed-var-cell-from-stack ()
  (let* ((val-temp (wasm2-allocate-temp))
         (vec-temp (wasm2-allocate-temp))
         (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
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
    (wasm2-emit-misc-node-slot-address 0)
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :i32-store)
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
          (when (and (wasm2-var-live-p var)
                     (not (wasm2-var-closed-p var))
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
  (wasm2-emit-const value)
  (wasm2-emit :return-constant)
  (wasm2-emit :return)
  nil)

(defun wasm2-emit-const (value)
  (if (integerp value)
    (wasm2-emit :const value)
    (if *wasm2-enable-const-pool*
      (let ((index (wasm2-const-pool-index value)))
        (wasm2-emit :const-pool-ref index))
      (error "WASM2: non-immediate constant requires const-pool: ~S" value)))
  nil)

(defun wasm2-reset-const-pool ()
  (setf *wasm2-const-pool* (make-array 0 :adjustable t :fill-pointer 0))
  (setf *wasm2-const-pool-map* (make-hash-table :test #'eq))
  *wasm2-const-pool*)

(defun wasm2-const-pool-sanitize (value)
  (cond ((macptrp value) nil)
        ((eq value (%unbound-marker)) *wasm2-target-unbound-marker*)
        ((eq value (%slot-unbound-marker)) *wasm2-target-slot-unbound-marker*)
        ((eq value (%illegal-marker)) *wasm2-target-illegal-marker*)
        (t value)))

(defun wasm2-const-pool-function-slot (value)
  (cond
    ((and (integerp value) (not (fixnump value)))
     nil)
    ((or (typep value 'xcode-vector)
         (typep value 'code-vector))
     nil)
    (t value)))

(defconstant +wasm2-const-pool-version+ 2)
(defconstant +wasm2-const-pool-tag-symbol+ 1)
(defconstant +wasm2-const-pool-tag-string+ 2)
(defconstant +wasm2-const-pool-tag-vector+ 3)
(defconstant +wasm2-const-pool-tag-function+ 4)
(defconstant +wasm2-const-pool-tag-function-vector+ 5)
(defconstant +wasm2-const-pool-tag-fixnum+ 6)
(defconstant +wasm2-const-pool-tag-package+ 7)
(defconstant +wasm2-const-pool-tag-cons+ 8)
(defconstant +wasm2-const-pool-tag-gvector+ 9)
(defconstant +wasm2-const-pool-tag-character+ 10)
(defconstant +wasm2-const-pool-tag-single-float+ 11)
(defconstant +wasm2-const-pool-tag-double-float+ 12)
(defconstant +wasm2-const-pool-tag-int64+ 13)
(defconstant +wasm2-const-pool-tag-uint64+ 14)
(defconstant +wasm2-const-pool-tag-bignum+ 15)
(defconstant +wasm2-const-pool-tag-entry-function+ 16)

(defconstant +wasm2-const-pool-int64-min+ (- (ash 1 63)))
(defconstant +wasm2-const-pool-int64-max+ (1- (ash 1 63)))
(defconstant +wasm2-const-pool-uint64-max+ (1- (ash 1 64)))

(defun wasm2-const-pool-unbox-entry-index (raw)
  (when (and (fixnump raw)
             (boundp '*wasm2-target-fixnum-shift*)
             (fixnump *wasm2-target-fixnum-shift*)
             (>= *wasm2-target-fixnum-shift* 0))
    (let* ((shift *wasm2-target-fixnum-shift*)
           (entry (ash raw (- shift))))
      (when (and (integerp entry)
                 (>= entry 0)
                 (<= entry #xffffffff)
                 (= raw (ash entry shift)))
        entry))))

(defun wasm2-const-pool-entry-function-index (value)
  (when (and (uvectorp value)
             (> (uvsize value) 0))
    (let* ((slot0 (ignore-errors (uvref value 0)))
           (entry (and slot0 (wasm2-const-pool-unbox-entry-index slot0))))
      (when entry
        entry))))

(defun wasm2-const-pool-bignum-digits (value)
  (let* ((neg (minusp value))
         (bits (integer-length (if neg (lognot value) value)))
         (digits (max 1 (ceiling bits 32))))
    (let* ((hi (ldb (byte 32 (* 32 (1- digits))) value)))
      (if neg
        (when (< hi #x80000000)
          (incf digits))
        (when (>= hi #x80000000)
          (incf digits))))
    (loop for i below digits
          collect (ldb (byte 32 (* 32 i)) value))))

(defun wasm2-const-pool-entry (value)
  (cond
    ((fixnump value)
     (list :type "fixnum" :value value))
    ((characterp value)
     (list :type "character" :code (char-code value)))
    ((typep value 'single-float)
     (list :type "single-float" :bits (single-float-bits value)))
    ((typep value 'double-float)
     (multiple-value-bind (hi lo) (double-float-bits value)
       (list :type "double-float" :hi hi :lo lo)))
    ((and (integerp value) (not (fixnump value)))
     (let* ((lo (ldb (byte 32 0) value))
            (hi (ldb (byte 32 32) value)))
       (cond
         ((and (>= value +wasm2-const-pool-int64-min+)
               (<= value +wasm2-const-pool-int64-max+))
          (list :type "int64" :hi hi :lo lo))
         ((and (>= value 0)
               (<= value +wasm2-const-pool-uint64-max+))
          (list :type "uint64" :hi hi :lo lo))
        (t
          (list :type "bignum"
                :digits (wasm2-const-pool-bignum-digits value))))))
    ((and (uvectorp value)
          (eql (typecode value) target::subtag-xfunction))
     ;; Cross-compiled functions always carry an entry index in slot 0.
     ;; Encode these by entry index to avoid serializing the full slot graph.
     (let ((entry-index (wasm2-const-pool-entry-function-index value)))
       (if entry-index
         (list :type "entry-function"
               :entry-index entry-index)
         ;; Some host/runtime xfunction constants do not carry a wasm entry
         ;; index in slot 0. Preserve prior behavior by serializing slots.
         (let* ((count (uvsize value))
                (elements (loop for i below count
                                collect (wasm2-const-pool-index
                                         (wasm2-const-pool-function-slot (uvref value i))))))
           (list :type "function-vector"
                 :elements elements)))))
    ((symbolp value)
     (list :type "symbol"
           :name (symbol-name value)
           :package (let ((pkg (symbol-package value)))
                      (when pkg (package-name pkg)))))
    ((stringp value)
     (list :type "string" :value value))
    ((typep value 'package)
     (list :type "package" :name (package-name value)))
    ((consp value)
     (list :type "cons"
           :car (wasm2-const-pool-index (car value))
           :cdr (wasm2-const-pool-index (cdr value))))
    ((and (vectorp value) (not (stringp value)))
     (list :type "vector"
           :elements (map 'list #'wasm2-const-pool-index value)))
    ((typep value 'function-vector)
     ;; Prefer compact entry-index references for WASM function objects.
     (let ((entry-index (wasm2-const-pool-entry-function-index value)))
       (if entry-index
         (list :type "entry-function"
               :entry-index entry-index)
         ;; Fallback for non-WASM function vectors.
         (let* ((count (uvsize value))
                (elements (loop for i below count
                                collect (wasm2-const-pool-index
                                         (wasm2-const-pool-function-slot (uvref value i))))))
           (list :type "function-vector"
                 :elements elements)))))
    ((and (gvectorp value) (not (typep value 'function-vector)))
     (let* ((count (uvsize value))
            (subtag (typecode value))
            (elements (loop for i below count
                            collect (wasm2-const-pool-index (uvref value i)))))
       (list :type "gvector"
             :subtag subtag
             :elements elements)))
    ((functionp value)
     (let ((name (function-name value)))
       (if (symbolp name)
         (list :type "function"
               :name (symbol-name name)
               :package (let ((pkg (symbol-package name)))
                          (when pkg (package-name pkg))))
         (let ((fv (and (fboundp 'function-to-function-vector)
                        (ignore-errors (function-to-function-vector value)))))
           (unless fv
             (error "WASM2: unsupported function constant: ~S" value))
           (let ((entry-index (wasm2-const-pool-entry-function-index fv)))
             (if entry-index
               (list :type "entry-function"
                     :entry-index entry-index)
               (let* ((count (uvsize fv))
                      (elements (loop for i below count
                                      collect (wasm2-const-pool-index
                                               (wasm2-const-pool-function-slot (uvref fv i))))))
                 (list :type "function-vector"
                       :elements elements))))))))
    (t
     (error "WASM2: unsupported const-pool value: ~S" value))))

(defun wasm2-const-pool-index (value)
  (let* ((value (wasm2-const-pool-sanitize value))
         (existing (and *wasm2-const-pool-map*
                        (gethash value *wasm2-const-pool-map*))))
    (if existing
      existing
      (let ((idx (fill-pointer *wasm2-const-pool*)))
        (vector-push-extend nil *wasm2-const-pool*)
        (setf (gethash value *wasm2-const-pool-map*) idx)
        (setf (aref *wasm2-const-pool* idx) (wasm2-const-pool-entry value))
        idx))))

(defun wasm2-const-pool-entries ()
  (when *wasm2-const-pool*
    (let ((out nil))
      (dotimes (i (fill-pointer *wasm2-const-pool*) (nreverse out))
        (push (aref *wasm2-const-pool* i) out)))))


(defun wasm2-const-pool-emit-u32 (out value)
  (let ((v (logand value #xffffffff)))
    (vector-push-extend (ldb (byte 8 0) v) out)
    (vector-push-extend (ldb (byte 8 8) v) out)
    (vector-push-extend (ldb (byte 8 16) v) out)
    (vector-push-extend (ldb (byte 8 24) v) out))
  out)

(defun wasm2-const-pool-emit-uleb32 (out value)
  (let ((v (logand value #xffffffff)))
    (loop
      (let* ((byte (logand v #x7f)))
        (setf v (ash v -7))
        (if (zerop v)
          (progn
            (vector-push-extend byte out)
            (return))
          (vector-push-extend (logior byte #x80) out)))))
  out)

(defun wasm2-const-pool-emit-sleb32 (out value)
  (let ((v (logior (logand value #xffffffff)
                   (if (logbitp 31 value) -4294967296 0))))
    (loop
      (let* ((byte (logand v #x7f))
             (next (ash v -7))
             (sign-bit-set (not (zerop (logand byte #x40))))
             (done (or (and (zerop next) (not sign-bit-set))
                       (and (= next -1) sign-bit-set))))
        (vector-push-extend (if done byte (logior byte #x80)) out)
        (when done
          (return))
        (setf v next))))
  out)

(defun wasm2-const-pool-emit-string (out value)
  (let* ((s (string value))
         (len (length s)))
    (wasm2-const-pool-emit-uleb32 out len)
    (dotimes (i len)
      (vector-push-extend (logand (char-code (char s i)) #xff) out)))
  out)

(defun wasm2-const-pool-emit-maybe-string (out value)
  (if value
    (wasm2-const-pool-emit-string out value)
    (wasm2-const-pool-emit-uleb32 out 0)))

(defun wasm2-const-pool-bytes (entries)
  (when entries
    (let ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-version+)
      (wasm2-const-pool-emit-uleb32 out (length entries))
      (dolist (entry entries)
        (let ((etype (getf entry :type)))
          (cond
            ((string= etype "fixnum")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-fixnum+)
             (wasm2-const-pool-emit-sleb32 out (getf entry :value)))
            ((string= etype "character")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-character+)
             (wasm2-const-pool-emit-uleb32 out (getf entry :code)))
            ((string= etype "single-float")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-single-float+)
             (wasm2-const-pool-emit-u32 out (getf entry :bits)))
            ((string= etype "double-float")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-double-float+)
             (wasm2-const-pool-emit-u32 out (getf entry :hi))
             (wasm2-const-pool-emit-u32 out (getf entry :lo)))
            ((string= etype "int64")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-int64+)
             (wasm2-const-pool-emit-u32 out (getf entry :hi))
             (wasm2-const-pool-emit-u32 out (getf entry :lo)))
            ((string= etype "uint64")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-uint64+)
             (wasm2-const-pool-emit-u32 out (getf entry :hi))
             (wasm2-const-pool-emit-u32 out (getf entry :lo)))
            ((string= etype "bignum")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-bignum+)
             (let ((digits (getf entry :digits)))
               (wasm2-const-pool-emit-uleb32 out (length digits))
               (dolist (digit digits)
                 (wasm2-const-pool-emit-u32 out digit))))
            ((string= etype "symbol")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-symbol+)
             (wasm2-const-pool-emit-string out (getf entry :name))
             (wasm2-const-pool-emit-maybe-string out (getf entry :package)))
            ((string= etype "string")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-string+)
             (wasm2-const-pool-emit-string out (getf entry :value)))
            ((string= etype "package")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-package+)
             (wasm2-const-pool-emit-string out (getf entry :name)))
            ((string= etype "cons")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-cons+)
             (wasm2-const-pool-emit-uleb32 out (getf entry :car))
             (wasm2-const-pool-emit-uleb32 out (getf entry :cdr)))
            ((string= etype "vector")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-vector+)
             (let ((elements (getf entry :elements)))
               (wasm2-const-pool-emit-uleb32 out (length elements))
               (dolist (idx elements)
                 (wasm2-const-pool-emit-uleb32 out idx))))
            ((string= etype "function")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-function+)
             (wasm2-const-pool-emit-string out (getf entry :name))
             (wasm2-const-pool-emit-maybe-string out (getf entry :package)))
            ((string= etype "function-vector")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-function-vector+)
             (let ((elements (getf entry :elements)))
               (wasm2-const-pool-emit-uleb32 out (length elements))
               (dolist (idx elements)
                 (wasm2-const-pool-emit-uleb32 out idx))))
            ((string= etype "gvector")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-gvector+)
             (wasm2-const-pool-emit-uleb32 out (getf entry :subtag))
             (let ((elements (getf entry :elements)))
               (wasm2-const-pool-emit-uleb32 out (length elements))
               (dolist (idx elements)
                 (wasm2-const-pool-emit-uleb32 out idx))))
            ((string= etype "entry-function")
             (wasm2-const-pool-emit-uleb32 out +wasm2-const-pool-tag-entry-function+)
             (wasm2-const-pool-emit-uleb32 out (getf entry :entry-index)))
            (t
             (error "WASM2: unknown const-pool entry type: ~S" etype)))))
      out)))

(defun wasm2-reset-external-imports ()
  (setf *wasm2-external-imports* nil)
  (setf *wasm2-external-import-map* (make-hash-table :test #'equal))
  *wasm2-external-imports*)

(defun wasm2-external-import-index (name type-index)
  (let ((entry (and *wasm2-external-import-map*
                    (gethash name *wasm2-external-import-map*))))
    (if entry
      (let ((idx (car entry))
            (existing-type (cdr entry)))
        (unless (eql existing-type type-index)
          (error "WASM2: external import ~s type mismatch: ~s vs ~s"
                 name existing-type type-index))
        idx)
      (let ((idx (length *wasm2-external-imports*)))
        (setf *wasm2-external-imports*
              (append *wasm2-external-imports* (list (list name type-index))))
        (setf (gethash name *wasm2-external-import-map*)
              (cons idx type-index))
        idx))))

(defun wasm2-external-import-call-index (name type-index)
  (+ (length *wasm2-generic-imports*)
     (wasm2-external-import-index name type-index)))

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
  (wasm2-emit :call-subprim-no-spill fixnum))

(defparameter *wasm2-no-spill-subprim-symbols*
  '(.SPthrow
    .SPmkcatch1v
    .SPmkcatchmv
    .SPnthrowvalues
    .SPnthrow1value
    .SPsave-values
    .SPadd-values
    .SPrecover-values
    .SPprogvsave
    .SPprogvrestore
    .SPconslist))

(defun wasm2-no-spill-subprim-fixnum-p (fixnum)
  (member fixnum
          (mapcar #'wasm2-subprim-fixnum *wasm2-no-spill-subprim-symbols*)
          :test #'eql))

(defun wasm2-macptr->fixnum-fn ()
  (or (and (fboundp 'macptr->fixnum)
           (symbol-function 'macptr->fixnum))
      (error "WASM2: macptr->fixnum is not defined")))

(defun wasm2-emit-external-arg (seg spec arg)
  (case spec
    ((:signed-fullword :unsigned-fullword :signed-halfword :unsigned-halfword :signed-byte :unsigned-byte)
     (wasm2-form seg nil nil arg)
     (wasm2-emit-unbox-fixnum))
    (:address
     (let* ((misc-ref (wasm2-subprim-fixnum '.SPmisc-ref)))
       (wasm2-form seg nil nil arg)
       (wasm2-emit :const (wasm2-box-fixnum 1))
       (wasm2-emit :set-arg1)
       (wasm2-emit :set-arg0)
       (wasm2-emit-call-subprim misc-ref)
       (wasm2-emit :arg0)))
    (t
     (error "WASM2: unsupported external-call arg type: ~s" spec))))

(defun wasm2-emit-external-call (seg xfer name argspecs argvals resultspec)
  (let* ((argc (length argspecs))
         (type-index (wasm2-external-call-type-index argc))
         (import-index (wasm2-external-import-call-index name type-index)))
    (loop for spec in argspecs
          for arg in argvals
          do (wasm2-emit-external-arg seg spec arg))
    (wasm2-with-spilled-locals
      (lambda ()
        (wasm2-emit :call-external import-index)))
    (cond
      ((eq resultspec :void)
       (wasm2-emit :drop)
       (wasm2-emit-const (target-nil-value)))
      ((eq resultspec :address)
       (let* ((addr-temp (wasm2-allocate-temp))
              (obj-temp (wasm2-allocate-temp))
              (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc)))
         (wasm2-emit :local.set addr-temp)
         (wasm2-emit :const (wasm2-box-fixnum wasm::macptr.element-count))
         (wasm2-emit :set-arg1)
         (wasm2-emit :const (wasm2-box-fixnum wasm::subtag-macptr))
         (wasm2-emit :set-arg0)
         (wasm2-emit-call-subprim misc-alloc)
         (wasm2-emit :arg0)
         (wasm2-emit :local.set obj-temp)
         (wasm2-emit :local.get obj-temp)
         (wasm2-emit-misc-node-slot-address 1)
         (wasm2-emit :local.get addr-temp)
         (wasm2-emit :i32-store)
         (wasm2-emit :local.get addr-temp)))
      (t
       (wasm2-emit-box-fixnum)))
    (when (wasm2-returning-p xfer)
      (wasm2-emit :set-arg-z)
      (wasm2-emit :set-nargs 1)
      (wasm2-emit :return))))

(defun wasm2-validate-spill-discipline (ir &optional (depth 0))
  (let ((cur depth))
    (dolist (ins ir)
      (let* ((op (car ins))
             (args (cdr ins)))
        (case op
          (:spill-locals
           (incf cur))
          (:restore-locals
           (decf cur)
           (when (< cur 0)
             (error "WASM2 spill discipline: restore without spill")))
          (:call-subprim
           (when (<= cur 0)
             (error "WASM2 spill discipline: call-subprim without spill")))
          (:call-subprim-no-spill
           (let ((fixnum (car args)))
             (unless (wasm2-no-spill-subprim-fixnum-p fixnum)
               (error "WASM2 spill discipline: call-subprim-no-spill not allowlisted: ~s"
                      fixnum)))
           (when (> cur 1)
             (error "WASM2 spill discipline: call-subprim-no-spill inside nested spill region")))
          (:if
           (destructuring-bind (then-ir else-ir) args
             (let* ((then-depth (wasm2-validate-spill-discipline then-ir cur))
                    (else-depth (wasm2-validate-spill-discipline else-ir cur)))
               (unless (and (= then-depth cur) (= else-depth cur))
                 (error "WASM2 spill discipline: unbalanced spill across IF")))))
          (:block
           (destructuring-bind (_label block-ir) args
             (declare (ignore _label))
             (let* ((block-depth (wasm2-validate-spill-discipline block-ir cur)))
               (unless (= block-depth cur)
                 (error "WASM2 spill discipline: unbalanced spill across BLOCK")))))
          (:loop
           (destructuring-bind (_label loop-ir) args
             (declare (ignore _label))
             (let* ((loop-depth (wasm2-validate-spill-discipline loop-ir cur)))
               (unless (= loop-depth cur)
                 (error "WASM2 spill discipline: unbalanced spill across LOOP"))))))))
    cur))

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

(defun wasm2-emit-unbox-fixnum ()
  (wasm2-emit :const *wasm2-target-fixnum-shift*)
  (wasm2-emit :i32-shr-s))

(defun wasm2-emit-box-fixnum ()
  (wasm2-emit :const *wasm2-target-fixnum-shift*)
  (wasm2-emit :i32-shl))

(defun wasm2-emit-unbox-single ()
  (wasm2-emit :const *wasm2-target-fulltag-misc*)
  (wasm2-emit :i32-sub)
  (when (minusp *wasm2-target-misc-data-offset*)
    (wasm2-emit :const (- *wasm2-target-misc-data-offset*))
    (wasm2-emit :i32-sub))
  (wasm2-emit :f32-load (if (minusp *wasm2-target-misc-data-offset*) 0 *wasm2-target-misc-data-offset*)))

(defun wasm2-emit-unbox-double ()
  (wasm2-emit :const *wasm2-target-fulltag-misc*)
  (wasm2-emit :i32-sub)
  (when (minusp *wasm2-target-misc-dfloat-offset*)
    (wasm2-emit :const (- *wasm2-target-misc-dfloat-offset*))
    (wasm2-emit :i32-sub))
  (wasm2-emit :f64-load (if (minusp *wasm2-target-misc-dfloat-offset*) 0 *wasm2-target-misc-dfloat-offset*)))

(defun wasm2-emit-box-single ()
  (let* ((val-temp (wasm2-allocate-f32-temp))
         (obj-temp (wasm2-allocate-temp))
         (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
         (subtag (wasm2-box-fixnum (nx-lookup-target-uvector-subtag :single-float)))
         (count (wasm2-box-fixnum *wasm2-target-single-float-count*)))
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :const count)
    (wasm2-emit :set-arg1)
    (wasm2-emit :const subtag)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-alloc)
    (wasm2-emit :arg0)
    (wasm2-emit :local.set obj-temp)
    (wasm2-emit :local.get obj-temp)
    (wasm2-emit :const *wasm2-target-fulltag-misc*)
    (wasm2-emit :i32-sub)
    (when (minusp *wasm2-target-misc-data-offset*)
      (wasm2-emit :const (- *wasm2-target-misc-data-offset*))
      (wasm2-emit :i32-sub))
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :f32-store (if (minusp *wasm2-target-misc-data-offset*) 0 *wasm2-target-misc-data-offset*))
    (wasm2-emit :local.get obj-temp)))

(defun wasm2-emit-box-double ()
  (let* ((val-temp (wasm2-allocate-f64-temp))
         (obj-temp (wasm2-allocate-temp))
         (misc-alloc (wasm2-subprim-fixnum '.SPmisc-alloc))
         (subtag (wasm2-box-fixnum (nx-lookup-target-uvector-subtag :double-float)))
         (count (wasm2-box-fixnum *wasm2-target-double-float-count*)))
    (wasm2-emit :local.set val-temp)
    (wasm2-emit :const count)
    (wasm2-emit :set-arg1)
    (wasm2-emit :const subtag)
    (wasm2-emit :set-arg0)
    (wasm2-emit-call-subprim misc-alloc)
    (wasm2-emit :arg0)
    (wasm2-emit :local.set obj-temp)
    (wasm2-emit :local.get obj-temp)
    (wasm2-emit :const *wasm2-target-fulltag-misc*)
    (wasm2-emit :i32-sub)
    (when (minusp *wasm2-target-misc-dfloat-offset*)
      (wasm2-emit :const (- *wasm2-target-misc-dfloat-offset*))
      (wasm2-emit :i32-sub))
    (wasm2-emit :local.get val-temp)
    (wasm2-emit :f64-store (if (minusp *wasm2-target-misc-dfloat-offset*) 0 *wasm2-target-misc-dfloat-offset*))
    (wasm2-emit :local.get obj-temp)))

(defun wasm2-float-cc-op (cc singlep)
  (ecase cc
    (:eq (if singlep :f32-eq :f64-eq))
    (:ne (if singlep :f32-ne :f64-ne))
    (:lt (if singlep :f32-lt :f64-lt))
    (:gt (if singlep :f32-gt :f64-gt))
    (:le (if singlep :f32-le :f64-le))
    (:ge (if singlep :f32-ge :f64-ge))))

(defun wasm2-int-cc-op (cc signedp)
  (ecase cc
    (:eq :i32-eq)
    (:ne :i32-ne)
    (:lt (if signedp :i32-lt-s :i32-lt-u))
    (:gt (if signedp :i32-gt-s :i32-gt-u))
    (:le (if signedp :i32-le-s :i32-le-u))
    (:ge (if signedp :i32-ge-s :i32-ge-u))))

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

(defun wasm2-signed32 (value)
  (let ((v (logand value #xffffffff)))
    (if (>= v #x80000000)
      (- v #x100000000)
      v)))

(defun wasm2-emit-sleb32 (vec value)
  (let ((v (wasm2-signed32 value)))
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

(defun wasm2-emit-u32-le (vec value)
  (dotimes (i 4 vec)
    (wasm2-push-u8 vec (ldb (byte 8 (* 8 i)) value))))

(defun wasm2-emit-memarg (body align offset)
  (wasm2-emit-uleb body align)
  (wasm2-emit-uleb body offset))

(defun wasm2-emit-f32-const (body value)
  (let* ((f (if (typep value 'single-float) value (float value 0.0f0)))
         (bits (single-float-bits f)))
    (wasm2-push-u8 body #x43) ; f32.const
    (wasm2-emit-u32-le body bits)))

(defun wasm2-emit-f64-const (body value)
  (let* ((f (if (typep value 'double-float) value (float value 0.0d0))))
    (multiple-value-bind (hi lo) (double-float-bits f)
      (wasm2-push-u8 body #x44) ; f64.const
      (wasm2-emit-u32-le body lo)
      (wasm2-emit-u32-le body hi))))

(defun wasm2-emit-bytes (vec bytes)
  (dolist (b bytes vec)
    (wasm2-push-u8 vec b)))

(defun wasm2-emit-string (vec string)
  (let* ((octets (map 'vector #'char-code string)))
    (wasm2-emit-uleb vec (length octets))
    (dotimes (i (length octets) vec)
      (wasm2-push-u8 vec (aref octets i)))))

(defun wasm2-emit-import-memory (imports &optional (min-pages 0))
  (wasm2-emit-string imports "env")
  (wasm2-emit-string imports "memory")
  (wasm2-push-u8 imports #x02) ; import kind: memory
  (wasm2-push-u8 imports #x00) ; limits: min only
  (wasm2-emit-uleb imports min-pages))

(defun wasm2-section (id contents)
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
    (wasm2-push-u8 out id)
    (wasm2-emit-uleb out (length contents))
    (dotimes (i (length contents) out)
      (wasm2-push-u8 out (aref contents i)))))

(defconstant +wasm2-valtype-i32+ #x7f)
(defconstant +wasm2-valtype-f32+ #x7d)
(defconstant +wasm2-valtype-f64+ #x7c)

(defun wasm2-valtype (type)
  (ecase type
    (:i32 +wasm2-valtype-i32+)
    (:f32 +wasm2-valtype-f32+)
    (:f64 +wasm2-valtype-f64+)))

(defun wasm2-emit-local-decls (body local-types)
  (let* ((count (length local-types)))
    (if (zerop count)
      (wasm2-emit-uleb body 0)
      (let* ((groups nil)
             (current (aref local-types 0))
             (run 0))
        (dotimes (i count)
          (let* ((local-type (aref local-types i)))
            (if (eql local-type current)
              (incf run)
              (progn
                (push (cons run current) groups)
                (setf current local-type
                      run 1)))))
        (push (cons run current) groups)
        (setf groups (nreverse groups))
        (wasm2-emit-uleb body (length groups))
        (dolist (g groups)
          (wasm2-emit-uleb body (car g))
          (wasm2-push-u8 body (wasm2-valtype (cdr g)))))))
  body)

(defconstant +wasm2-type-void-i32+ 0)
(defconstant +wasm2-type-i32-void+ 1)
(defconstant +wasm2-type-void-void+ 2)
(defconstant +wasm2-type-i32-i32+ 3)
(defconstant +wasm2-type-i32-i32-i32+ 4)
(defconstant +wasm2-type-i32-i32-ret+ 5)
(defconstant +wasm2-type-i32-i32-i32-i32+ 6)
(defconstant +wasm2-type-i32x5-i32+ 7)
(defconstant +wasm2-type-i32x6-i32+ 8)
(defconstant +wasm2-type-i32x7-i32+ 9)
(defconstant +wasm2-type-i32x8-i32+ 10)
(defconstant +wasm2-type-i32x9-i32+ 11)
(defconstant +wasm2-type-i32x10-i32+ 12)
(defconstant +wasm2-type-i32x11-i32+ 13)

(defparameter *wasm2-generic-imports*
  (list
   (list :pending-throw "wasm_pending_throw_p" +wasm2-type-void-i32+)
   (list :get-arg-z "wasm_get_arg_z" +wasm2-type-void-i32+)
   (list :get-arg-y "wasm_get_arg_y" +wasm2-type-void-i32+)
   (list :get-nfn "wasm_get_nfn" +wasm2-type-void-i32+)
   (list :get-nargs "wasm_get_nargs" +wasm2-type-void-i32+)
   (list :get-lisp-nil "wasm_get_lisp_nil" +wasm2-type-void-i32+)
   (list :const-pool-ref "wasm_const_pool_ref" +wasm2-type-i32-i32+)
   (list :lisp-word-ref "wasm_lisp_word_ref" +wasm2-type-i32-i32+)
   (list :return-constant "wasm_return_constant" +wasm2-type-i32-void+)
   (list :set-arg-z "wasm_set_arg_z" +wasm2-type-i32-void+)
   (list :set-arg-y "wasm_set_arg_y" +wasm2-type-i32-void+)
   (list :set-arg-x "wasm_set_arg_x" +wasm2-type-i32-void+)
   (list :set-nargs "wasm_set_nargs" +wasm2-type-i32-void+)
   (list :set-nfn "wasm_set_nfn" +wasm2-type-i32-void+)
   ;; Compatibility-only helpers: direct fixnum lowering must stay in :fixnum-*
   ;; hot lanes and branch here only on explicit fallback edges.
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
   (list :funcall3 "wasm_funcall3" +wasm2-type-i32-i32-i32-i32+)
   (list :funcall4 "wasm_funcall4" +wasm2-type-i32x5-i32+)
   (list :funcall5 "wasm_funcall5" +wasm2-type-i32x6-i32+)
   (list :funcall6 "wasm_funcall6" +wasm2-type-i32x7-i32+)
   (list :funcall7 "wasm_funcall7" +wasm2-type-i32x8-i32+)
   (list :funcall8 "wasm_funcall8" +wasm2-type-i32x9-i32+)
   (list :funcall9 "wasm_funcall9" +wasm2-type-i32x10-i32+)
   (list :funcall10 "wasm_funcall10" +wasm2-type-i32x11-i32+)
   (list :funcall0-mv "wasm_funcall0_mv" +wasm2-type-i32-i32-ret+)
   (list :funcall1-mv "wasm_funcall1_mv" +wasm2-type-i32-i32+)
   (list :funcall2-mv "wasm_funcall2_mv" +wasm2-type-i32-i32-i32+)
   (list :funcall3-mv "wasm_funcall3_mv" +wasm2-type-i32-i32-i32-i32+)
   (list :funcall4-mv "wasm_funcall4_mv" +wasm2-type-i32x5-i32+)
   (list :funcall5-mv "wasm_funcall5_mv" +wasm2-type-i32x6-i32+)
   (list :funcall6-mv "wasm_funcall6_mv" +wasm2-type-i32x7-i32+)
   (list :funcall7-mv "wasm_funcall7_mv" +wasm2-type-i32x8-i32+)
   (list :funcall8-mv "wasm_funcall8_mv" +wasm2-type-i32x9-i32+)
   (list :funcall9-mv "wasm_funcall9_mv" +wasm2-type-i32x10-i32+)
   (list :funcall10-mv "wasm_funcall10_mv" +wasm2-type-i32x11-i32+)
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
   (list :vsp-ref "wasm_vsp_ref" +wasm2-type-i32-i32-ret+)
   (list :spill-push "wasm_spill_push" +wasm2-type-i32-void+)
   (list :spill-pop "wasm_spill_pop" +wasm2-type-void-i32+)
   (list :clear-pending-throw "wasm_clear_pending_throw" +wasm2-type-void-void+)
   (list :get-current-tcr "wasm_get_current_tcr" +wasm2-type-void-i32+)
   (list :get-tcr-toplevel-function "wasm_get_tcr_toplevel_function" +wasm2-type-i32-i32-ret+)
   (list :set-tcr-toplevel-function "wasm_set_tcr_toplevel_function" +wasm2-type-i32-i32+)))

(defun wasm2-external-call-type-index (argc)
  (case argc
    (0 +wasm2-type-void-i32+)
    (1 +wasm2-type-i32-i32-ret+)
    (2 +wasm2-type-i32-i32+)
    (3 +wasm2-type-i32-i32-i32+)
    (4 +wasm2-type-i32-i32-i32-i32+)
    (5 +wasm2-type-i32x5-i32+)
    (6 +wasm2-type-i32x6-i32+)
    (7 +wasm2-type-i32x7-i32+)
    (t
     (error "WASM2: unsupported external-call arity: ~d" argc))))

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
      (wasm2-emit-call-index body (wasm2-generic-import-index :spill-push)))))

(defun wasm2-emit-restore-locals (body &optional locals)
  (let* ((spill-locals (or locals *wasm2-emit-spillable-locals*)))
    (dolist (idx (reverse spill-locals))
      (wasm2-emit-call-index body (wasm2-generic-import-index :spill-pop))
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

(defparameter *wasm2-entry-pending-throw-guard-safe-ops*
  '(:const :arg0 :arg1 :local.get :local.set :local.tee
    :get-arg-z :get-arg-y :get-nfn :get-nargs :get-lisp-nil
    :i32-add :i32-sub :i32-mul :i32-div-s :i32-div-u :i32-rem-s :i32-rem-u
    :i32-and :i32-or :i32-xor :i32-shl :i32-shr-s :i32-shr-u :i32-rotl :i32-rotr
    :i32-eq :i32-ne :i32-lt-s :i32-lt-u :i32-gt-s :i32-gt-u :i32-le-s :i32-le-u
    :i32-ge-s :i32-ge-u :i32-eqz :i32-clz :i32-ctz :i32-popcnt
    :i32-load :i32-load8-u :i32-load16-u :i32-load8-s :i32-load16-s
    :f32-const :f64-const :f32-add :f32-sub :f32-mul :f32-div :f32-neg
    :f64-add :f64-sub :f64-mul :f64-div :f64-neg :f32-convert-i32-s
    :f64-convert-i32-s :f64-promote-f32 :f32-demote-f64
    :f32-eq :f32-ne :f32-lt :f32-gt :f32-le :f32-ge
    :f64-eq :f64-ne :f64-lt :f64-gt :f64-le :f64-ge
    :select
    :fixnum-add :fixnum-sub :fixnum-mul :fixnum-ash :fixnum-logand
    :fixnum-logior :fixnum-logxor :fixnum-lognot :fixnum-neg
    :set-arg-z :set-arg-y :set-arg-x :set-nargs :set-nfn
    :return-arg0 :return-arg1
    :pending-throw-return :pending-throw-branch
    :return-constant :return
    :drop :nop :unreachable
    :br :br-table))

(defun wasm2-ir-requires-entry-pending-throw-guard-p (ir)
  (labels ((op-requires-guard-p (ins)
             (let* ((op (car ins))
                    (args (cdr ins)))
               (case op
                 (:if
                  (destructuring-bind (then-ir else-ir) args
                    (or (ir-requires-guard-p then-ir)
                        (ir-requires-guard-p else-ir))))
                 (:if-void
                  (destructuring-bind (then-ir else-ir) args
                    (or (ir-requires-guard-p then-ir)
                        (ir-requires-guard-p else-ir))))
                 (:block
                  (destructuring-bind (_label block-ir) args
                    (declare (ignore _label))
                    (ir-requires-guard-p block-ir)))
                 (:loop
                  (destructuring-bind (_label loop-ir) args
                    (declare (ignore _label))
                    (ir-requires-guard-p loop-ir)))
                 (t
                  (not (member op *wasm2-entry-pending-throw-guard-safe-ops*
                               :test #'eq))))))
           (ir-requires-guard-p (sub-ir)
             (dolist (sub-ins sub-ir nil)
               (when (op-requires-guard-p sub-ins)
                 (return t)))))
    (ir-requires-guard-p ir)))

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

(defun wasm2-ir-ensure-value (ir)
  (if (null ir)
    (list (list :const (target-nil-value)))
    (let* ((ins (car (last ir)))
           (op (car ins))
           (args (cdr ins)))
      (case op
        (:if
         (destructuring-bind (then-ir else-ir) args
           (let* ((then2 (wasm2-ir-ensure-value then-ir))
                  (else2 (wasm2-ir-ensure-value else-ir)))
             (append (butlast ir) (list (list :if then2 else2))))))
        (:if-void
         (append ir (list (list :const (target-nil-value)))))
        (:block
         (append ir (list (list :const (target-nil-value)))))
        (:loop
         (append ir (list (list :const (target-nil-value)))))
        (t
         (if (wasm2-ir-produces-value-p ir)
           ir
           (append ir (list (list :const (target-nil-value))))))))))

(defun wasm2-ir-voidify (ir)
  (append (wasm2-ir-ensure-value ir) (list (list :drop))))

(defun wasm2-emit-generic-if-void (body then-ir else-ir label-stack)
  (let* ((if-label :if)
         (then-body (wasm2-ir-voidify then-ir))
         (else-body (wasm2-ir-voidify else-ir)))
    (wasm2-emit-call-index body (wasm2-generic-import-index :get-lisp-nil))
    (wasm2-push-u8 body #x47) ; i32.ne
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x40) ; blocktype void
    (wasm2-emit-generic-ir body then-body (cons if-label label-stack))
    (wasm2-push-u8 body #x05) ; else
    (wasm2-emit-generic-ir body else-body (cons if-label label-stack))
    (wasm2-push-u8 body #x0b))) ; end

(defconstant +wasm2-fixnum-direct-scratch-count+ 3)

;; Once we're fully on pure direct WASM lanes, we can likely tighten this by:
;; Keeping one invariant check at module-emission setup, and
;; Making the accessor a simple (+ base offset) in hot compiler paths
;; (or inlining offsets).
(defun wasm2-fixnum-direct-scratch-local (offset)
  (let ((base *wasm2-fixnum-direct-scratch-base*))
    (unless (and (fixnump base) (>= base 0))
      (error "WASM2: fixnum direct scratch locals unavailable"))
    (+ base offset)))

(defun wasm2-emit-local-get-op (body local-index)
  (wasm2-push-u8 body #x20)
  (wasm2-emit-uleb body local-index))

(defun wasm2-emit-local-set-op (body local-index)
  (wasm2-push-u8 body #x21)
  (wasm2-emit-uleb body local-index))

(defun wasm2-emit-local-tee-op (body local-index)
  (wasm2-push-u8 body #x22)
  (wasm2-emit-uleb body local-index))

(defun wasm2-emit-i32-const-op (body value)
  (wasm2-push-u8 body #x41)
  (wasm2-emit-sleb32 body (logand value #xffffffff)))

(defun wasm2-emit-i64-const-op (body value)
  ;; All i64 constants used in direct fixnum lowering are 32-bit range.
  (wasm2-push-u8 body #x42)
  (wasm2-emit-sleb32 body value))

(defun wasm2-emit-unboxed-fixnum-local-i32 (body local-index)
  (wasm2-emit-local-get-op body local-index)
  (wasm2-emit-i32-const-op body *wasm2-target-fixnum-shift*)
  (wasm2-push-u8 body #x75)) ; i32.shr_s

(defun wasm2-emit-unboxed-fixnum-local-i64 (body local-index)
  (wasm2-emit-unboxed-fixnum-local-i32 body local-index)
  (wasm2-push-u8 body #xac)) ; i64.extend_i32_s

(defun wasm2-emit-local-i32-as-i64 (body local-index)
  (wasm2-emit-local-get-op body local-index)
  (wasm2-push-u8 body #xac)) ; i64.extend_i32_s

(defun wasm2-emit-fixnum-local-tag-check (body local-index)
  (let ((mask (1- (ash 1 *wasm2-target-fixnum-shift*))))
    (wasm2-emit-local-get-op body local-index)
    (wasm2-emit-i32-const-op body mask)
    (wasm2-push-u8 body #x71) ; i32.and
    (wasm2-push-u8 body #x45))) ; i32.eqz

(defun wasm2-emit-fixnum-stack-tag-check (body)
  (let ((mask (1- (ash 1 *wasm2-target-fixnum-shift*))))
    (wasm2-emit-i32-const-op body mask)
    (wasm2-push-u8 body #x71) ; i32.and
    (wasm2-push-u8 body #x45))) ; i32.eqz

(defun wasm2-emit-fixnum-local-pair-tag-check (body x-local y-local)
  (let ((mask (1- (ash 1 *wasm2-target-fixnum-shift*))))
    ;; ((x | y) & lowtag-mask) == 0  <=> both boxed operands are fixnums.
    (wasm2-emit-local-get-op body x-local)
    (wasm2-emit-local-get-op body y-local)
    (wasm2-push-u8 body #x72) ; i32.or
    (wasm2-emit-i32-const-op body mask)
    (wasm2-push-u8 body #x71) ; i32.and
    (wasm2-push-u8 body #x45))) ; i32.eqz

(defun wasm2-emit-fixnum-local-pair-tag-check-from-x-stack (body y-local)
  (let ((mask (1- (ash 1 *wasm2-target-fixnum-shift*))))
    ;; x is already on stack from local.tee.
    (wasm2-emit-local-get-op body y-local)
    (wasm2-push-u8 body #x72) ; i32.or
    (wasm2-emit-i32-const-op body mask)
    (wasm2-push-u8 body #x71) ; i32.and
    (wasm2-push-u8 body #x45))) ; i32.eqz

(defun wasm2-emit-hot-direct-fixnum-binary-fallback (body x-local y-local compat-op-key)
  (wasm2-emit-local-get-op body x-local)
  (wasm2-emit-local-get-op body y-local)
  (wasm2-emit-compat-fallback-fixnum-binary-op body compat-op-key))

(defun wasm2-emit-hot-direct-fixnum-unary-fallback (body x-local compat-op-key)
  (wasm2-emit-local-get-op body x-local)
  (wasm2-emit-compat-fallback-fixnum-unary-op body compat-op-key))

(defun wasm2-emit-hot-direct-fixnum-add (body x-local y-local result-local compat-op-key)
  (wasm2-emit-local-get-op body x-local)
  (wasm2-emit-local-get-op body y-local)
  (wasm2-push-u8 body #x6a) ; i32.add
  ;; Keep the computed result in a local while consuming one copy for overflow
  ;; math to avoid an extra local.get in the hot path.
  (wasm2-emit-local-tee-op body result-local)
  (wasm2-emit-local-get-op body x-local)
  (wasm2-push-u8 body #x73) ; i32.xor
  (wasm2-emit-local-get-op body y-local)
  (wasm2-emit-local-get-op body result-local)
  (wasm2-push-u8 body #x73) ; i32.xor
  (wasm2-push-u8 body #x71) ; i32.and
  (wasm2-emit-i32-const-op body 0)
  (wasm2-push-u8 body #x48) ; i32.lt_s
  (wasm2-push-u8 body #x04) ; if
  (wasm2-push-u8 body #x7f) ; blocktype i32
  (wasm2-emit-hot-direct-fixnum-binary-fallback body x-local y-local compat-op-key)
  (wasm2-push-u8 body #x05) ; else
  (wasm2-emit-local-get-op body result-local)
  (wasm2-push-u8 body #x0b)) ; end

(defun wasm2-emit-hot-direct-fixnum-sub (body x-local y-local result-local compat-op-key)
  (wasm2-emit-local-get-op body x-local)
  (wasm2-emit-local-get-op body y-local)
  (wasm2-push-u8 body #x6b) ; i32.sub
  ;; Keep the computed result in a local while consuming one copy for overflow
  ;; math to avoid an extra local.get in the hot path.
  (wasm2-emit-local-tee-op body result-local)
  (wasm2-emit-local-get-op body x-local)
  (wasm2-push-u8 body #x73) ; i32.xor
  (wasm2-emit-local-get-op body x-local)
  (wasm2-emit-local-get-op body y-local)
  (wasm2-push-u8 body #x73) ; i32.xor
  (wasm2-push-u8 body #x71) ; i32.and
  (wasm2-emit-i32-const-op body 0)
  (wasm2-push-u8 body #x48) ; i32.lt_s
  (wasm2-push-u8 body #x04) ; if
  (wasm2-push-u8 body #x7f) ; blocktype i32
  (wasm2-emit-hot-direct-fixnum-binary-fallback body x-local y-local compat-op-key)
  (wasm2-push-u8 body #x05) ; else
  (wasm2-emit-local-get-op body result-local)
  (wasm2-push-u8 body #x0b)) ; end

(defun wasm2-emit-hot-direct-fixnum-mul (body x-local y-local compat-op-key)
  (let* ((fixnum-bits (1- (- *wasm2-target-bits-in-word* *wasm2-target-fixnum-shift*)))
         (min-fixnum (ash -1 fixnum-bits))
         (max-fixnum (1- (ash 1 fixnum-bits))))
    (wasm2-emit-unboxed-fixnum-local-i64 body x-local)
    (wasm2-emit-unboxed-fixnum-local-i64 body y-local)
    (wasm2-push-u8 body #x7e) ; i64.mul
    (wasm2-emit-i64-const-op body min-fixnum)
    (wasm2-push-u8 body #x53) ; i64.lt_s
    (wasm2-emit-unboxed-fixnum-local-i64 body x-local)
    (wasm2-emit-unboxed-fixnum-local-i64 body y-local)
    (wasm2-push-u8 body #x7e) ; i64.mul
    (wasm2-emit-i64-const-op body max-fixnum)
    (wasm2-push-u8 body #x55) ; i64.gt_s
    (wasm2-push-u8 body #x72) ; i32.or
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x7f) ; blocktype i32
    (wasm2-emit-hot-direct-fixnum-binary-fallback body x-local y-local compat-op-key)
    (wasm2-push-u8 body #x05) ; else
    (wasm2-emit-unboxed-fixnum-local-i64 body x-local)
    (wasm2-emit-unboxed-fixnum-local-i64 body y-local)
    (wasm2-push-u8 body #x7e) ; i64.mul
    (wasm2-emit-i64-const-op body *wasm2-target-fixnum-shift*)
    (wasm2-push-u8 body #x86) ; i64.shl
    (wasm2-push-u8 body #xa7) ; i32.wrap_i64
    (wasm2-push-u8 body #x0b))) ; end

(defun wasm2-emit-hot-direct-fixnum-ash-left (body x-local y-local shift-local compat-op-key)
  (let* ((fixnum-bits (1- (- *wasm2-target-bits-in-word* *wasm2-target-fixnum-shift*)))
         (min-fixnum (ash -1 fixnum-bits))
         (max-fixnum (1- (ash 1 fixnum-bits)))
         (max-shift (1- *wasm2-target-bits-in-word*)))
    ;; Keep direct lowering only for bounded shift counts; route out-of-range
    ;; counts through the explicit compatibility fallback edge.
    (wasm2-emit-local-get-op body shift-local)
    (wasm2-emit-i32-const-op body max-shift)
    (wasm2-push-u8 body #x4a) ; i32.gt_s
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x7f) ; blocktype i32
    (wasm2-emit-hot-direct-fixnum-binary-fallback body x-local y-local compat-op-key)
    (wasm2-push-u8 body #x05) ; else
    ;; Explicit overflow edge: if shifted value leaves fixnum bounds, fall back.
    (wasm2-emit-unboxed-fixnum-local-i64 body x-local)
    (wasm2-emit-local-i32-as-i64 body shift-local)
    (wasm2-push-u8 body #x86) ; i64.shl
    (wasm2-emit-i64-const-op body min-fixnum)
    (wasm2-push-u8 body #x53) ; i64.lt_s
    (wasm2-emit-unboxed-fixnum-local-i64 body x-local)
    (wasm2-emit-local-i32-as-i64 body shift-local)
    (wasm2-push-u8 body #x86) ; i64.shl
    (wasm2-emit-i64-const-op body max-fixnum)
    (wasm2-push-u8 body #x55) ; i64.gt_s
    (wasm2-push-u8 body #x72) ; i32.or
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x7f) ; blocktype i32
    (wasm2-emit-hot-direct-fixnum-binary-fallback body x-local y-local compat-op-key)
    (wasm2-push-u8 body #x05) ; else
    (wasm2-emit-unboxed-fixnum-local-i64 body x-local)
    (wasm2-emit-local-i32-as-i64 body shift-local)
    (wasm2-push-u8 body #x86) ; i64.shl
    (wasm2-push-u8 body #xa7) ; i32.wrap_i64
    (wasm2-emit-i32-const-op body *wasm2-target-fixnum-shift*)
    (wasm2-push-u8 body #x74) ; i32.shl
    (wasm2-push-u8 body #x0b) ; end
    (wasm2-push-u8 body #x0b))) ; end

(defun wasm2-emit-hot-direct-fixnum-ash-right (body x-local y-local shift-local compat-op-key)
  (let* ((max-shift (1- *wasm2-target-bits-in-word*)))
    (wasm2-emit-i32-const-op body 0)
    (wasm2-emit-local-get-op body shift-local)
    (wasm2-push-u8 body #x6b) ; i32.sub
    (wasm2-emit-local-tee-op body shift-local)
    ;; Keep right-shift direct lane bounded; let compat handle extreme counts.
    (wasm2-emit-i32-const-op body max-shift)
    (wasm2-push-u8 body #x4a) ; i32.gt_s
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x7f) ; blocktype i32
    (wasm2-emit-hot-direct-fixnum-binary-fallback body x-local y-local compat-op-key)
    (wasm2-push-u8 body #x05) ; else
    (wasm2-emit-unboxed-fixnum-local-i32 body x-local)
    (wasm2-emit-local-get-op body shift-local)
    (wasm2-push-u8 body #x75) ; i32.shr_s
    (wasm2-emit-i32-const-op body *wasm2-target-fixnum-shift*)
    (wasm2-push-u8 body #x74) ; i32.shl
    (wasm2-push-u8 body #x0b))) ; end

(defun wasm2-emit-hot-direct-fixnum-ash (body x-local y-local shift-local compat-op-key)
  ;; `shift-local` stores unboxed shift count so both sign lanes can reuse it
  ;; without reloading or re-unboxing the original boxed operand.
  (wasm2-emit-unboxed-fixnum-local-i32 body y-local)
  (wasm2-emit-local-tee-op body shift-local)
  (wasm2-emit-i32-const-op body 0)
  (wasm2-push-u8 body #x4e) ; i32.ge_s
  (wasm2-push-u8 body #x04) ; if
  (wasm2-push-u8 body #x7f) ; blocktype i32
  (wasm2-emit-hot-direct-fixnum-ash-left body x-local y-local shift-local compat-op-key)
  (wasm2-push-u8 body #x05) ; else
  (wasm2-emit-hot-direct-fixnum-ash-right body x-local y-local shift-local compat-op-key)
  (wasm2-push-u8 body #x0b)) ; end

(defun wasm2-emit-hot-direct-fixnum-binary-op (body op compat-op-key)
  (unless (member op '(:fixnum-add :fixnum-sub :fixnum-mul
                       :fixnum-ash :fixnum-logand :fixnum-logior :fixnum-logxor))
    (return-from wasm2-emit-hot-direct-fixnum-binary-op nil))
  (let* ((x-local (wasm2-fixnum-direct-scratch-local 0))
         (y-local (wasm2-fixnum-direct-scratch-local 1))
         (result-local (wasm2-fixnum-direct-scratch-local 2)))
    ;; Preserve operands so both direct and explicit fallback edges can consume
    ;; the original boxed values.
    (wasm2-emit-local-set-op body y-local)
    (wasm2-emit-local-tee-op body x-local)
    (wasm2-emit-fixnum-local-pair-tag-check-from-x-stack body y-local)
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x7f) ; blocktype i32
    (case op
      (:fixnum-add
       (wasm2-emit-hot-direct-fixnum-add body x-local y-local result-local compat-op-key))
      (:fixnum-sub
       (wasm2-emit-hot-direct-fixnum-sub body x-local y-local result-local compat-op-key))
      (:fixnum-mul
       (wasm2-emit-hot-direct-fixnum-mul body x-local y-local compat-op-key))
      (:fixnum-ash
       (wasm2-emit-hot-direct-fixnum-ash body x-local y-local result-local compat-op-key))
      (:fixnum-logand
       (wasm2-emit-local-get-op body x-local)
       (wasm2-emit-local-get-op body y-local)
       (wasm2-push-u8 body #x71)) ; i32.and
      (:fixnum-logior
       (wasm2-emit-local-get-op body x-local)
       (wasm2-emit-local-get-op body y-local)
       (wasm2-push-u8 body #x72)) ; i32.or
      (:fixnum-logxor
       (wasm2-emit-local-get-op body x-local)
       (wasm2-emit-local-get-op body y-local)
       (wasm2-push-u8 body #x73))) ; i32.xor
    (wasm2-push-u8 body #x05) ; else
    (wasm2-emit-hot-direct-fixnum-binary-fallback body x-local y-local compat-op-key)
    (wasm2-push-u8 body #x0b)) ; end
  t)

(defun wasm2-emit-hot-direct-fixnum-neg (body x-local unboxed-local compat-op-key)
  (let* ((fixnum-bits (1- (- *wasm2-target-bits-in-word* *wasm2-target-fixnum-shift*)))
         (min-fixnum (ash -1 fixnum-bits)))
    (wasm2-emit-unboxed-fixnum-local-i32 body x-local)
    (wasm2-emit-local-tee-op body unboxed-local)
    (wasm2-emit-i32-const-op body min-fixnum)
    (wasm2-push-u8 body #x46) ; i32.eq
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x7f) ; blocktype i32
    (wasm2-emit-hot-direct-fixnum-unary-fallback body x-local compat-op-key)
    (wasm2-push-u8 body #x05) ; else
    (wasm2-emit-i32-const-op body 0)
    (wasm2-emit-local-get-op body unboxed-local)
    (wasm2-push-u8 body #x6b) ; i32.sub
    (wasm2-emit-i32-const-op body *wasm2-target-fixnum-shift*)
    (wasm2-push-u8 body #x74) ; i32.shl
    (wasm2-push-u8 body #x0b))) ; end

(defun wasm2-emit-hot-direct-fixnum-unary-op (body op compat-op-key)
  (unless (member op '(:fixnum-lognot :fixnum-neg))
    (return-from wasm2-emit-hot-direct-fixnum-unary-op nil))
  (let* ((x-local (wasm2-fixnum-direct-scratch-local 0))
         (unboxed-local (wasm2-fixnum-direct-scratch-local 2))
         (lognot-mask (lognot (1- (ash 1 *wasm2-target-fixnum-shift*)))))
    ;; Preserve operand so the direct lane and explicit fallback edges share
    ;; the original boxed value.
    (wasm2-emit-local-tee-op body x-local)
    (wasm2-emit-fixnum-stack-tag-check body)
    (wasm2-push-u8 body #x04) ; if
    (wasm2-push-u8 body #x7f) ; blocktype i32
    (case op
      (:fixnum-lognot
       (wasm2-emit-local-get-op body x-local)
       (wasm2-emit-i32-const-op body lognot-mask)
       (wasm2-push-u8 body #x73)) ; i32.xor
      (:fixnum-neg
       (wasm2-emit-hot-direct-fixnum-neg body x-local unboxed-local compat-op-key)))
    (wasm2-push-u8 body #x05) ; else
    (wasm2-emit-hot-direct-fixnum-unary-fallback body x-local compat-op-key)
    (wasm2-push-u8 body #x0b)) ; end
  t)

(defparameter *wasm2-fixnum-compat-op-keys*
  '(:return-fixnum-add
    :return-fixnum-sub
    :return-fixnum-mul
    :return-fixnum-ash
    :return-fixnum-neg
    :return-fixnum-logand
    :return-fixnum-logior
    :return-fixnum-logxor
    :return-fixnum-lognot))

(defparameter *wasm2-no-spill-fixnum-compat-op-keys*
  '(:return-fixnum-logand
    :return-fixnum-logior
    :return-fixnum-logxor
    :return-fixnum-lognot))

(defun wasm2-fixnum-compat-op-key-p (compat-op-key)
  (member compat-op-key *wasm2-fixnum-compat-op-keys* :test #'eq))

(defun wasm2-fixnum-compat-fallback-requires-spill-p (compat-op-key)
  ;; Keep spill envelopes only for compatibility helpers that can allocate/GC.
  (unless (wasm2-fixnum-compat-op-key-p compat-op-key)
    (error "WASM2: non-compat fixnum fallback key ~s" compat-op-key))
  (not (member compat-op-key *wasm2-no-spill-fixnum-compat-op-keys* :test #'eq)))

(defun wasm2-emit-compat-fallback-fixnum-call (body compat-op-key)
  (if (wasm2-fixnum-compat-fallback-requires-spill-p compat-op-key)
    (progn
      (wasm2-emit-spill-locals body)
      (wasm2-emit-call-index body (wasm2-generic-import-index compat-op-key))
      (wasm2-emit-restore-locals body))
    (wasm2-emit-call-index body (wasm2-generic-import-index compat-op-key))))

(defun wasm2-emit-compat-fallback-fixnum-binary-op (body compat-op-key)
  (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-y))
  (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-z))
  (wasm2-emit-compat-fallback-fixnum-call body compat-op-key)
  (wasm2-emit-call-index body (wasm2-generic-import-index :get-arg-z)))

(defun wasm2-emit-compat-fallback-fixnum-unary-op (body compat-op-key)
  (wasm2-emit-call-index body (wasm2-generic-import-index :set-arg-z))
  (wasm2-emit-compat-fallback-fixnum-call body compat-op-key)
  (wasm2-emit-call-index body (wasm2-generic-import-index :get-arg-z)))

(defun wasm2-emit-fixnum-binary-op (body op compat-op-key)
  (or (wasm2-emit-hot-direct-fixnum-binary-op body op compat-op-key)
      (wasm2-emit-compat-fallback-fixnum-binary-op body compat-op-key)))

(defun wasm2-emit-fixnum-unary-op (body op compat-op-key)
  (or (wasm2-emit-hot-direct-fixnum-unary-op body op compat-op-key)
      (wasm2-emit-compat-fallback-fixnum-unary-op body compat-op-key)))

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
        (:const-pool-ref
         (let ((entry-index *wasm2-emit-entry-index*))
           (unless entry-index
             (error "WASM2: const-pool-ref emitted without entry index"))
           (wasm2-push-u8 body #x41)
           (wasm2-emit-sleb32 body (logand entry-index #xffffffff))
           (wasm2-push-u8 body #x41)
           (wasm2-emit-sleb32 body (logand (car args) #xffffffff))
           (wasm2-emit-call-index body (wasm2-generic-import-index :const-pool-ref))))
        (:lisp-word-ref
         (wasm2-emit-call-index body (wasm2-generic-import-index :lisp-word-ref)))
        (:f32-const
         (wasm2-emit-f32-const body (car args)))
        (:f64-const
         (wasm2-emit-f64-const body (car args)))
        (:arg0
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-arg-z)))
        (:arg1
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-arg-y)))
        (:get-nfn
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-nfn)))
        (:get-nargs
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-nargs)))
        (:get-current-tcr
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-current-tcr)))
        (:get-tcr-toplevel-function
         (wasm2-emit-call-index body (wasm2-generic-import-index :get-tcr-toplevel-function)))
        (:set-tcr-toplevel-function
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-tcr-toplevel-function)))
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
        (:return-constant
         (wasm2-emit-call-index body (wasm2-generic-import-index :return-constant)))
        (:set-nargs
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (car args))
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-nargs)))
        (:set-nargs-dynamic
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-nargs)))
        (:set-nfn
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-nfn)))
        (:set-imm0
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (logand (car args) #xffffffff))
         (wasm2-emit-call-index body (wasm2-generic-import-index :set-imm0)))
        (:i32-add
         (wasm2-push-u8 body #x6a))
        (:i32-sub
         (wasm2-push-u8 body #x6b))
        (:i32-and
         (wasm2-push-u8 body #x71))
        (:i32-shl
         (wasm2-push-u8 body #x74))
        (:i32-shr-s
         (wasm2-push-u8 body #x75))
        (:i32-shr-u
         (wasm2-push-u8 body #x76))
        (:i32-eq
         (wasm2-push-u8 body #x46))
        (:i32-eqz
         (wasm2-push-u8 body #x45))
        (:i32-ne
         (wasm2-push-u8 body #x47))
        (:i32-lt-s
         (wasm2-push-u8 body #x48))
        (:i32-lt-u
         (wasm2-push-u8 body #x49))
        (:i32-gt-s
         (wasm2-push-u8 body #x4a))
        (:i32-gt-u
         (wasm2-push-u8 body #x4b))
        (:i32-le-s
         (wasm2-push-u8 body #x4c))
        (:i32-le-u
         (wasm2-push-u8 body #x4d))
        (:i32-ge-s
         (wasm2-push-u8 body #x4e))
        (:i32-ge-u
         (wasm2-push-u8 body #x4f))
        (:i32-load
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x28)
           (wasm2-emit-memarg body 2 offset)))
        (:i32-load8-s
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x2c)
           (wasm2-emit-memarg body 0 offset)))
        (:i32-load8-u
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x2d)
           (wasm2-emit-memarg body 0 offset)))
        (:i32-load16-s
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x2e)
           (wasm2-emit-memarg body 1 offset)))
        (:i32-load16-u
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x2f)
           (wasm2-emit-memarg body 1 offset)))
        (:f32-load
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x2a)
           (wasm2-emit-memarg body 2 offset)))
        (:f64-load
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x2b)
           (wasm2-emit-memarg body 3 offset)))
        (:f32-store
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x38)
           (wasm2-emit-memarg body 2 offset)))
        (:f64-store
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x39)
           (wasm2-emit-memarg body 3 offset)))
        (:i32-store
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x36)
           (wasm2-emit-memarg body 2 offset)))
        (:i32-store8
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x3a)
           (wasm2-emit-memarg body 0 offset)))
        (:i32-store16
         (let* ((offset (or (car args) 0)))
           (wasm2-push-u8 body #x3b)
           (wasm2-emit-memarg body 1 offset)))
        (:f32-add (wasm2-push-u8 body #x92))
        (:f32-sub (wasm2-push-u8 body #x93))
        (:f32-mul (wasm2-push-u8 body #x94))
        (:f32-div (wasm2-push-u8 body #x95))
        (:f32-neg (wasm2-push-u8 body #x8f))
        (:f64-add (wasm2-push-u8 body #xa0))
        (:f64-sub (wasm2-push-u8 body #xa1))
        (:f64-mul (wasm2-push-u8 body #xa2))
        (:f64-div (wasm2-push-u8 body #xa3))
        (:f64-neg (wasm2-push-u8 body #x9a))
        (:f32-convert-i32-s (wasm2-push-u8 body #xb2))
        (:f64-convert-i32-s (wasm2-push-u8 body #xb7))
        (:f64-promote-f32 (wasm2-push-u8 body #xbb))
        (:f32-demote-f64 (wasm2-push-u8 body #xb6))
        (:f32-eq (wasm2-push-u8 body #x5b))
        (:f32-ne (wasm2-push-u8 body #x5c))
        (:f32-lt (wasm2-push-u8 body #x5d))
        (:f32-gt (wasm2-push-u8 body #x5e))
        (:f32-le (wasm2-push-u8 body #x5f))
        (:f32-ge (wasm2-push-u8 body #x60))
        (:f64-eq (wasm2-push-u8 body #x61))
        (:f64-ne (wasm2-push-u8 body #x62))
        (:f64-lt (wasm2-push-u8 body #x63))
        (:f64-gt (wasm2-push-u8 body #x64))
        (:f64-le (wasm2-push-u8 body #x65))
        (:f64-ge (wasm2-push-u8 body #x66))
        (:select
         (wasm2-push-u8 body #x1b))
        (:fixnum-add (wasm2-emit-fixnum-binary-op body :fixnum-add :return-fixnum-add))
        (:fixnum-sub (wasm2-emit-fixnum-binary-op body :fixnum-sub :return-fixnum-sub))
        (:fixnum-mul (wasm2-emit-fixnum-binary-op body :fixnum-mul :return-fixnum-mul))
        (:fixnum-ash (wasm2-emit-fixnum-binary-op body :fixnum-ash :return-fixnum-ash))
        (:fixnum-logand (wasm2-emit-fixnum-binary-op body :fixnum-logand :return-fixnum-logand))
        (:fixnum-logior (wasm2-emit-fixnum-binary-op body :fixnum-logior :return-fixnum-logior))
        (:fixnum-logxor (wasm2-emit-fixnum-binary-op body :fixnum-logxor :return-fixnum-logxor))
        (:fixnum-lognot (wasm2-emit-fixnum-unary-op body :fixnum-lognot :return-fixnum-lognot))
        (:fixnum-neg (wasm2-emit-fixnum-unary-op body :fixnum-neg :return-fixnum-neg))
        (:call0 (wasm2-emit-call-with-pending body :funcall0 (car args) label-stack))
        (:call1 (wasm2-emit-call-with-pending body :funcall1 (car args) label-stack))
        (:call2 (wasm2-emit-call-with-pending body :funcall2 (car args) label-stack))
        (:call3 (wasm2-emit-call-with-pending body :funcall3 (car args) label-stack))
        (:call4 (wasm2-emit-call-with-pending body :funcall4 (car args) label-stack))
        (:call5 (wasm2-emit-call-with-pending body :funcall5 (car args) label-stack))
        (:call6 (wasm2-emit-call-with-pending body :funcall6 (car args) label-stack))
        (:call7 (wasm2-emit-call-with-pending body :funcall7 (car args) label-stack))
        (:call8 (wasm2-emit-call-with-pending body :funcall8 (car args) label-stack))
        (:call9 (wasm2-emit-call-with-pending body :funcall9 (car args) label-stack))
        (:call10 (wasm2-emit-call-with-pending body :funcall10 (car args) label-stack))
        (:call0-mv (wasm2-emit-call-with-pending body :funcall0-mv (car args) label-stack))
        (:call1-mv (wasm2-emit-call-with-pending body :funcall1-mv (car args) label-stack))
        (:call2-mv (wasm2-emit-call-with-pending body :funcall2-mv (car args) label-stack))
        (:call3-mv (wasm2-emit-call-with-pending body :funcall3-mv (car args) label-stack))
        (:call4-mv (wasm2-emit-call-with-pending body :funcall4-mv (car args) label-stack))
        (:call5-mv (wasm2-emit-call-with-pending body :funcall5-mv (car args) label-stack))
        (:call6-mv (wasm2-emit-call-with-pending body :funcall6-mv (car args) label-stack))
        (:call7-mv (wasm2-emit-call-with-pending body :funcall7-mv (car args) label-stack))
        (:call8-mv (wasm2-emit-call-with-pending body :funcall8-mv (car args) label-stack))
        (:call9-mv (wasm2-emit-call-with-pending body :funcall9-mv (car args) label-stack))
        (:call10-mv (wasm2-emit-call-with-pending body :funcall10-mv (car args) label-stack))
        (:call-subprim
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (logand (car args) #xffffffff))
         (wasm2-emit-call-index body (wasm2-generic-import-index :call-subprim)))
        (:call-subprim-no-spill
         (wasm2-push-u8 body #x41)
         (wasm2-emit-sleb32 body (logand (car args) #xffffffff))
         (wasm2-emit-call-index body (wasm2-generic-import-index :call-subprim)))
        (:call-external
         (wasm2-emit-call-index body (car args)))
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
        (:vsp-ref
         (let ((idx (car args)))
           (wasm2-push-u8 body #x41)
           (wasm2-emit-sleb32 body (logand idx #xffffffff))
           (wasm2-emit-call-index body (wasm2-generic-import-index :vsp-ref))))
        (:vsp-ref-dynamic
         (wasm2-emit-call-index body (wasm2-generic-import-index :vsp-ref)))
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
        (:if-void
         (destructuring-bind (then-ir else-ir) args
           (wasm2-emit-generic-if-void body then-ir else-ir label-stack)))
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

(defconstant +wasm2-entry-call-abi-legacy+ :legacy)
(defconstant +wasm2-entry-call-abi-unary-i32+ :unary-i32)
(defconstant +wasm2-entry-call-abi-binary-i32+ :binary-i32)

(defun wasm2-entry-call-abi-param-count (entry-call-abi)
  (case entry-call-abi
    (:legacy 0)
    (:unary-i32 1)
    (:binary-i32 2)
    (t
     (error "WASM2: unknown entry call ABI ~s" entry-call-abi))))

(defun wasm2-entry-call-abi-function-type-index (entry-call-abi)
  (case entry-call-abi
    (:legacy +wasm2-type-void-void+)
    (:unary-i32 +wasm2-type-i32-i32-ret+)
    (:binary-i32 +wasm2-type-i32-i32+)
    (t
     (error "WASM2: unknown entry call ABI ~s" entry-call-abi))))

(defun wasm2-generic-module-bytes (ir export-name local-types
                                   &optional spillable-locals entry-index
                                   (entry-call-abi +wasm2-entry-call-abi-legacy+))
  (let* ((out (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (types (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (imports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (funcs (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (exports (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (code (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0))
         (external-imports (or *wasm2-external-imports* nil))
         (entry-param-count (wasm2-entry-call-abi-param-count entry-call-abi))
         (entry-function-type-index (wasm2-entry-call-abi-function-type-index entry-call-abi))
         (entry-needs-pending-throw-guard (wasm2-ir-requires-entry-pending-throw-guard-p ir))
         (base-local-count (length local-types))
         (local-count (+ base-local-count +wasm2-fixnum-direct-scratch-count+))
         (effective-local-types (make-array local-count))
         (local-base-index (+ entry-param-count base-local-count)))
    (dotimes (i base-local-count)
      (setf (aref effective-local-types i) (aref local-types i)))
    (dotimes (i +wasm2-fixnum-direct-scratch-count+)
      (setf (aref effective-local-types (+ base-local-count i)) :i32))
    (wasm2-emit-bytes out '(0 #x61 #x73 #x6d 1 0 0 0))

    ;; Types
    (wasm2-emit-uleb types 14)
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
    ;; 7: (i32 i32 i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 5)
    (dotimes (_i 5)
      (wasm2-push-u8 types #x7f))
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 8: (i32 i32 i32 i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 6)
    (dotimes (_i 6)
      (wasm2-push-u8 types #x7f))
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 9: (i32 i32 i32 i32 i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 7)
    (dotimes (_i 7)
      (wasm2-push-u8 types #x7f))
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 10: (i32 i32 i32 i32 i32 i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 8)
    (dotimes (_i 8)
      (wasm2-push-u8 types #x7f))
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 11: (i32 i32 i32 i32 i32 i32 i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 9)
    (dotimes (_i 9)
      (wasm2-push-u8 types #x7f))
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 12: (i32 i32 i32 i32 i32 i32 i32 i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 10)
    (dotimes (_i 10)
      (wasm2-push-u8 types #x7f))
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)
    ;; 13: (i32 i32 i32 i32 i32 i32 i32 i32 i32 i32 i32) -> i32
    (wasm2-push-u8 types #x60)
    (wasm2-emit-uleb types 11)
    (dotimes (_i 11)
      (wasm2-push-u8 types #x7f))
    (wasm2-emit-uleb types 1)
    (wasm2-push-u8 types #x7f)

    ;; Imports (memory + functions)
    (wasm2-emit-uleb imports (+ 1
                                (length *wasm2-generic-imports*)
                                (length external-imports)))
    (wasm2-emit-import-memory imports)
    (dolist (imp *wasm2-generic-imports*)
      (destructuring-bind (_key name type-index) imp
        (declare (ignore _key))
        (wasm2-emit-string imports "ccl")
        (wasm2-emit-string imports name)
        (wasm2-push-u8 imports 0)
        (wasm2-emit-uleb imports type-index)))
    (dolist (imp external-imports)
      (destructuring-bind (name type-index) imp
        (wasm2-emit-string imports "ccl")
        (wasm2-emit-string imports name)
        (wasm2-push-u8 imports 0)
        (wasm2-emit-uleb imports type-index)))

    ;; Function section
    (wasm2-emit-uleb funcs 1)
    (wasm2-emit-uleb funcs entry-function-type-index)

    ;; Export
    (let* ((func-index (+ (length *wasm2-generic-imports*)
                          (length external-imports))))
      (wasm2-emit-uleb exports 1)
      (wasm2-emit-string exports export-name)
      (wasm2-push-u8 exports 0)
      (wasm2-emit-uleb exports func-index))

    ;; Code
    (let* ((body (make-array 0 :element-type '(unsigned-byte 8) :adjustable t :fill-pointer 0)))
      (wasm2-emit-local-decls body effective-local-types)
      (when (> base-local-count 0)
        (let* ((nil-value (target-nil-value)))
          ;; Direct-fixnum scratch locals are compiler-private and always
          ;; written before read, so avoid eager nil stores on appended slots.
          (dotimes (i base-local-count)
            (when (eql (aref effective-local-types i) :i32)
              (wasm2-push-u8 body #x41) ; i32.const
              (wasm2-emit-sleb32 body (logand nil-value #xffffffff))
              (wasm2-push-u8 body #x21) ; local.set
              (wasm2-emit-uleb body (+ entry-param-count i))))))
      (let* ((*wasm2-emit-local-count* local-count)
             (*wasm2-emit-spillable-locals* spillable-locals)
             (*wasm2-fixnum-direct-scratch-base* local-base-index)
             (*wasm2-emit-entry-index* entry-index))
        (unless (= (wasm2-validate-spill-discipline ir) 0)
          (error "WASM2 spill discipline: unbalanced spill depth at function end"))
        (when entry-needs-pending-throw-guard
          (wasm2-emit-pending-throw-guard body))
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

    ;; Imports: env.memory, ccl.wasm_pending_throw_p (func type 0), ccl.wasm_return_constant (func type 1)
    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    ;; Imports: env.memory, ccl.wasm_get_arg_z, ccl.wasm_get_lisp_nil,
    ;; ccl.wasm_return_constant, ccl.wasm_pending_throw_p
    (wasm2-emit-uleb imports 5)
    (wasm2-emit-import-memory imports)
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

    ;; Imports: env.memory, ccl.wasm_get_arg_z, ccl.wasm_get_lisp_nil,
    ;; ccl.wasm_return_constant, ccl.wasm_return_arg_z, ccl.wasm_pending_throw_p
    (wasm2-emit-uleb imports 6)
    (wasm2-emit-import-memory imports)
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
    (wasm2-emit-uleb imports 3)
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

    ;; Imports: env.memory, ccl.wasm_pending_throw_p (type 0), ccl.wasm_return_arg_z (type 1)
    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    ;; Imports: env.memory, ccl.wasm_pending_throw_p (type 0), ccl.wasm_return_arg_y (type 1)
    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

    (wasm2-emit-uleb imports 3)
    (wasm2-emit-import-memory imports)
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

(defun wasm2-make-stub-code-vector (entry-index)
  (let* ((cross-compiling (and (boundp '*host-backend*)
                               (boundp '*target-backend*)
                               (not (eq *host-backend* *target-backend*))))
         (host-arch (and (boundp '*host-backend*)
                         (backend-target-arch *host-backend*)))
         (host-subtags (and host-arch
                            (arch::target-uvector-subtags host-arch)))
         (xcode-subtag (cdr (assoc :xcode-vector host-subtags)))
         (code-subtag (cdr (assoc :code-vector host-subtags)))
         (subtag (if cross-compiling
                   (or xcode-subtag code-subtag)
                   (or code-subtag xcode-subtag))))
    (unless subtag
      (error "WASM2: missing code-vector subtag for host"))
    (let ((code-vector (%alloc-misc 1 subtag)))
      (setf (uvref code-vector 0) (wasm2-box-fixnum entry-index))
      code-vector)))

(defun wasm2-const-code-vector (entry-index)
  (if (and (boundp '*host-backend*)
           (boundp '*target-backend*)
           (not (eq *host-backend* *target-backend*)))
    ;; Avoid embedding host xcode-vectors in cross-compiled fasls.
    (wasm2-box-fixnum entry-index)
    (wasm2-make-stub-code-vector entry-index)))

(defun wasm2-make-const-function (entry-index const-value name &optional (lfun-bits 0))
  (let* ((entry-fixnum (wasm2-box-fixnum entry-index))
         (code-vector (wasm2-const-code-vector entry-index))
         ;; Cross-compilation needs xfunctions so fasl dumping won't treat them
         ;; as native code vectors.
         (subtag (if (and (boundp '*host-backend*)
                          (boundp '*target-backend*)
                          (not (eq *host-backend* *target-backend*)))
                   target::subtag-xfunction
                   target::subtag-function))
         (function (%alloc-misc 5 subtag)))
    (setf (uvref function 0) entry-fixnum
          (uvref function 1) code-vector
          (uvref function 2) const-value
          (uvref function 3) name
          (uvref function 4) lfun-bits)
    function))

(defun wasm2-const-ir-value (ir)
  (when (and (= (length ir) 3)
             (eq (caar ir) :const)
             (eq (caar (cdr ir)) :return-constant)
             (eq (caar (cddr ir)) :return))
    (return-from wasm2-const-ir-value (values (cadar ir) t)))
  (when (and (= (length ir) 4)
             (eq (caar ir) :const)
             (eq (caar (cdr ir)) :set-arg-z)
             (eq (caar (cddr ir)) :set-nargs)
             (eq (caar (cdddr ir)) :return))
    (values (cadar ir) t)))

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

(defun wasm2-simple-arg-local-indices (afunc)
  (let* ((arg0-name (wasm2-arg0-name afunc))
         (arg1-name (wasm2-arg1-name afunc))
         (arg0-local nil)
         (arg1-local nil))
    (when (or arg0-name arg1-name)
      (dolist (var (afunc-all-vars afunc))
        (unless (wasm2-var-closed-p var)
          (let* ((name (var-name var)))
            (when (and arg0-name (eq name arg0-name) (null arg0-local))
              (setf arg0-local (gethash var *wasm2-locals*)))
            (when (and arg1-name (eq name arg1-name) (null arg1-local))
              (setf arg1-local (gethash var *wasm2-locals*)))))))
    (values arg0-local arg1-local)))

(defun wasm2-ir-arg-source-p (ins arg-op local-index)
  (or (eq (car ins) arg-op)
      (and local-index
           (eq (car ins) :local.get)
           (eql (cadr ins) local-index))))

(defun wasm2-ir-set-nargs1-p (ins)
  (and (eq (car ins) :set-nargs)
       (eql (cadr ins) 1)))

(defun wasm2-ir-single-value-return-from-source-p (ir source-op source-local)
  (let* ((n (length ir)))
    (cond
      ((and (= n 2)
            (wasm2-ir-arg-source-p (first ir) source-op source-local)
            (eq (car (second ir)) :return))
       t)
      ((and (= n 3)
            (wasm2-ir-arg-source-p (first ir) source-op source-local)
            (eq (car (second ir)) :return-constant)
            (eq (car (third ir)) :return))
       t)
      ((and (= n 4)
            (wasm2-ir-arg-source-p (first ir) source-op source-local)
            (eq (car (second ir)) :set-arg-z)
            (wasm2-ir-set-nargs1-p (third ir))
            (eq (car (fourth ir)) :return))
       t)
      (t
       nil))))

(defun wasm2-return-arg0-ir-p (ir &optional arg0-local)
  (or (and (= (length ir) 2)
           (eq (caar ir) :return-arg0)
           (eq (caar (cdr ir)) :return))
      (wasm2-ir-single-value-return-from-source-p ir :arg0 arg0-local)))

(defun wasm2-return-arg1-ir-p (ir &optional arg1-local)
  (or (and (= (length ir) 2)
           (eq (caar ir) :return-arg1)
           (eq (caar (cdr ir)) :return))
      (wasm2-ir-single-value-return-from-source-p ir :arg1 arg1-local)))

(defparameter *wasm2-typed-fixnum-binary-ops*
  '(:fixnum-add :fixnum-sub :fixnum-mul :fixnum-ash
    :fixnum-logand :fixnum-logior :fixnum-logxor))

(defparameter *wasm2-typed-fixnum-unary-ops*
  '(:fixnum-neg :fixnum-lognot))

(defun wasm2-fixnum-binary-returning-op-ir-p (ir &optional arg0-local arg1-local)
  (let ((n (length ir)))
    (cond
      ((and (= n 2)
            (member (caar ir) *wasm2-typed-fixnum-binary-ops* :test #'eq)
            (eq (car (second ir)) :return))
       (values (caar ir) t))
      ((and (= n 4)
            (wasm2-ir-arg-source-p (first ir) :arg0 arg0-local)
            (wasm2-ir-arg-source-p (second ir) :arg1 arg1-local)
            (member (car (third ir)) *wasm2-typed-fixnum-binary-ops* :test #'eq)
            (eq (car (fourth ir)) :return))
       (values (car (third ir)) t))
      ((and (= n 5)
            (wasm2-ir-arg-source-p (first ir) :arg0 arg0-local)
            (wasm2-ir-arg-source-p (second ir) :arg1 arg1-local)
            (member (car (third ir)) *wasm2-typed-fixnum-binary-ops* :test #'eq)
            (eq (car (fourth ir)) :return-constant)
            (eq (car (fifth ir)) :return))
       (values (car (third ir)) t))
      ((and (= n 6)
            (wasm2-ir-arg-source-p (first ir) :arg0 arg0-local)
            (wasm2-ir-arg-source-p (second ir) :arg1 arg1-local)
            (member (car (third ir)) *wasm2-typed-fixnum-binary-ops* :test #'eq)
            (eq (car (fourth ir)) :set-arg-z)
            (wasm2-ir-set-nargs1-p (fifth ir))
            (eq (car (sixth ir)) :return))
       (values (car (third ir)) t))
      (t
       (values nil nil)))))

(defun wasm2-fixnum-unary-returning-op-ir-p (ir &optional arg0-local)
  (let ((n (length ir)))
    (cond
      ((and (= n 2)
            (member (caar ir) *wasm2-typed-fixnum-unary-ops* :test #'eq)
            (eq (car (second ir)) :return))
       (values (caar ir) t))
      ((and (= n 3)
            (wasm2-ir-arg-source-p (first ir) :arg0 arg0-local)
            (member (car (second ir)) *wasm2-typed-fixnum-unary-ops* :test #'eq)
            (eq (car (third ir)) :return))
       (values (car (second ir)) t))
      ((and (= n 4)
            (wasm2-ir-arg-source-p (first ir) :arg0 arg0-local)
            (member (car (second ir)) *wasm2-typed-fixnum-unary-ops* :test #'eq)
            (eq (car (third ir)) :return-constant)
            (eq (car (fourth ir)) :return))
       (values (car (second ir)) t))
      ((and (= n 5)
            (wasm2-ir-arg-source-p (first ir) :arg0 arg0-local)
            (member (car (second ir)) *wasm2-typed-fixnum-unary-ops* :test #'eq)
            (eq (car (third ir)) :set-arg-z)
            (wasm2-ir-set-nargs1-p (fourth ir))
            (eq (car (fifth ir)) :return))
       (values (car (second ir)) t))
      (t
       (values nil nil)))))

(defun wasm2-typed-entry-call-abi-plan (afunc ir &optional arg0-local arg1-local)
  (let* ((arglist (wasm2-simple-arglist afunc))
         (arity (length arglist)))
    (cond
      ((= arity 2)
       (multiple-value-bind (op ok)
           (wasm2-fixnum-binary-returning-op-ir-p ir arg0-local arg1-local)
         (when ok
           (values +wasm2-entry-call-abi-binary-i32+ op))))
      ((= arity 1)
       (multiple-value-bind (op ok)
           (wasm2-fixnum-unary-returning-op-ir-p ir arg0-local)
         (when ok
           (values +wasm2-entry-call-abi-unary-i32+ op))))
      (t
       (values nil nil)))))

(defun wasm2-typed-entry-ir (entry-call-abi op)
  (case entry-call-abi
    (:binary-i32
     (list (list :local.get 0)
           (list :local.get 1)
           (list op)
           (list :return)))
    (:unary-i32
     (list (list :local.get 0)
           (list op)
           (list :return)))
    (t
     nil)))

(defun wasm2-ir-ends-with-return-p (ir)
  (and ir (eq (caar (last ir)) :return)))

(defparameter *wasm2-ir-value-ops*
  '(:const :const-pool-ref :lisp-word-ref :arg0 :arg1 :local.get :local.tee
    :get-arg-z :get-arg-y :get-nfn :get-nargs
    :vsp-ref :vsp-ref-dynamic
    :i32-add :i32-sub :i32-mul :i32-div-s :i32-div-u :i32-rem-s :i32-rem-u
    :i32-and :i32-or :i32-xor :i32-shl :i32-shr-s :i32-shr-u :i32-rotl :i32-rotr
    :i32-eq :i32-ne :i32-lt-s :i32-lt-u :i32-gt-s :i32-gt-u :i32-le-s :i32-le-u
    :i32-ge-s :i32-ge-u :i32-eqz :i32-clz :i32-ctz :i32-popcnt
    :i32-load :i32-load8-u :i32-load16-u :i32-load8-s :i32-load16-s
    :f32-const :f64-const :f32-add :f32-sub :f32-mul :f32-div :f32-neg
    :f64-add :f64-sub :f64-mul :f64-div :f64-neg :f32-convert-i32-s
    :f64-convert-i32-s :f64-promote-f32 :f32-demote-f64
    :f32-eq :f32-ne :f32-lt :f32-gt :f32-le :f32-ge
    :f64-eq :f64-ne :f64-lt :f64-gt :f64-le :f64-ge
    :select
    :fixnum-add :fixnum-sub :fixnum-mul :fixnum-ash :fixnum-logand
    :fixnum-logior :fixnum-logxor :fixnum-lognot :fixnum-neg
    :call0 :call1 :call2 :call3 :call4 :call5 :call6 :call7 :call8 :call9 :call10
    :call0-mv :call1-mv :call2-mv :call3-mv :call4-mv :call5-mv :call6-mv
    :call7-mv :call8-mv :call9-mv :call10-mv
    :call-external
    :return-values2 :return-values3 :return-values4
    :get-mv :get-mv-indexed :vpop :spill-pop :get-current-tcr
    :get-tcr-toplevel-function :set-tcr-toplevel-function))

(defun wasm2-ir-produces-value-p (ir)
  (when (null ir)
    (return-from wasm2-ir-produces-value-p nil))
  (let* ((ins (car (last ir)))
         (op (car ins))
         (args (cdr ins)))
    (case op
      (:if
       (destructuring-bind (then-ir else-ir) args
         (and (wasm2-ir-produces-value-p then-ir)
              (wasm2-ir-produces-value-p else-ir))))
      (:if-void nil)
      (:block nil)
      (:loop nil)
      (t (member op *wasm2-ir-value-ops* :test #'eq)))))

(defun wasm2-allocate-entry-index ()
  (prog1 *wasm2-next-entry-index*
    (incf *wasm2-next-entry-index*)))

(defun wasm2-preallocated-entry-index (afunc)
  (getf (afunc-lfun-info afunc) 'wasm-preallocated-entry-index))

(defun wasm2-preallocate-afunc (afunc)
  (unless (afunc-lfun afunc)
    (let* ((entry-index (wasm2-allocate-entry-index))
           (bits (or (wasm2-const-lfun-bits afunc) 0))
           (keyvec (wasm2-const-lfun-keyvec afunc))
           (keyvec-slot (if keyvec keyvec 0))
           (name (afunc-name afunc)))
      (setf (afunc-lfun afunc)
            (wasm2-make-const-function entry-index keyvec-slot name bits))
      (setf (afunc-lfun-info afunc)
            (list* 'wasm-preallocated-entry-index entry-index
                   (afunc-lfun-info afunc)))))
  (afunc-lfun afunc))

(defun wasm2-afunc-lfun (afunc)
  (or (afunc-lfun afunc)
      (wasm2-preallocate-afunc afunc)))

(defun wasm2-set-afunc-lfun (afunc entry-index const-value bits)
  (let* ((existing (afunc-lfun afunc))
         (entry-fixnum (wasm2-box-fixnum entry-index))
         (code-vector (wasm2-const-code-vector entry-index))
         (name (afunc-name afunc)))
    (if existing
      (progn
        (setf (uvref existing 0) entry-fixnum
              (uvref existing 1) code-vector
              (uvref existing 2) const-value
              (uvref existing 3) name
              (uvref existing 4) bits)
        existing)
      (setf (afunc-lfun afunc)
            (wasm2-make-const-function entry-index const-value name bits)))))

(defun wasm2-const-lfun-bits (afunc)
  (let* ((lambda-form (afunc-lambdaform afunc)))
    (when (and (consp lambda-form) (consp (cdr lambda-form)))
      (or (encode-lambda-list (cadr lambda-form)) 0))))

(defun wasm2-const-lfun-keyvec (afunc &optional lambda-form)
  (let* ((form (or lambda-form (afunc-lambdaform afunc))))
    (when (and (consp form) (consp (cdr form)))
      (multiple-value-bind (_bits keyvec) (encode-lambda-list (cadr form) t)
        (declare (ignore _bits))
        keyvec))))

(defun wasm2-compile (afunc &optional lambda-form *wasm2-record-symbols*)
  ;; Preallocate function objects for inner functions so mutual recursion
  ;; can reference a stable entry index before their bodies compile.
  (dolist (a (afunc-inner-functions afunc))
    (when (neq 0 (afunc-fn-refcount a))
      (wasm2-preallocate-afunc a)))
  (dolist (a (afunc-inner-functions afunc))
    (wasm2-compile a
                   (if lambda-form (afunc-lambdaform a))
                   *wasm2-record-symbols*))
  (let* ((arch (backend-target-arch *target-backend*))
         (*wasm2-cur-afunc* afunc)
         (keyvec (wasm2-const-lfun-keyvec afunc lambda-form))
         (keyvec-slot (if keyvec keyvec 0))
         (*wasm2-vstack* 0)
         (*wasm2-cstack* 0)
         (*wasm2-target-fixnum-shift* (arch::target-fixnum-shift arch))
         (*wasm2-target-node-shift* (arch::target-word-shift arch))
         (*wasm2-target-bits-in-word* (arch::target-nbits-in-word arch))
         (*wasm2-target-node-size* (arch::target-lisp-node-size arch))
         (*wasm2-target-lisptag-mask* (1- (ash 1 (arch::target-nlisptagbits arch))))
         (*wasm2-target-fulltag-misc* (arch::target-fulltag-misc arch))
         (*wasm2-target-fulltagmask* (arch::target-fulltagmask arch))
         (*wasm2-target-misc-data-offset* (arch::target-misc-data-offset arch))
         (*wasm2-target-misc-dfloat-offset* (arch::target-misc-dfloat-offset arch))
         (*wasm2-target-unbound-marker* (arch::target-unbound-marker-value arch))
         (*wasm2-target-slot-unbound-marker* (arch::target-slot-unbound-marker-value arch))
         (*wasm2-target-illegal-marker* wasm::illegal-marker)
         (*wasm2-target-single-float-count* (truncate 4 (arch::target-lisp-node-size arch)))
         ;; Double-floats use an extra pad word on 32-bit targets.
         (*wasm2-target-double-float-count* (1+ (truncate 8 (arch::target-lisp-node-size arch))))
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
         (*wasm2-tagbody-global-map* (make-hash-table :test #'eq))
         (*wasm2-const-pool* nil)
         (*wasm2-const-pool-map* nil)
         (*wasm2-external-imports* nil)
         (*wasm2-external-import-map* nil))
    (wasm2-reset-locals)
    (wasm2-reset-external-imports)
    (when *wasm2-enable-const-pool*
      (wasm2-reset-const-pool))
    (backend-apply-acode (afunc-acode afunc) nil nil $backend-return)
    (let* ((body-ir (nreverse *wasm2-ir*))
           (specialization-ir body-ir)
           (closed-prologue-ir (wasm2-closed-arg-prologue-ir))
           (arg-prologue-ir (wasm2-arg-prologue-ir))
           (ir body-ir)
           (arg0-local nil)
           (arg1-local nil)
           (const-pool-entries (and *wasm2-enable-const-pool*
                                    (wasm2-const-pool-entries)))
           (prealloc-entry (wasm2-preallocated-entry-index afunc)))
      (unless (wasm2-ir-ends-with-return-p specialization-ir)
        (setf specialization-ir
              (append specialization-ir
                      (list (cons :return-constant nil)
                            (cons :return nil)))))
      (when closed-prologue-ir
        (setf ir (append closed-prologue-ir ir)))
      (when arg-prologue-ir
        (setf ir (append arg-prologue-ir ir)))
      (unless (wasm2-ir-ends-with-return-p ir)
        (setf ir (append ir
                         (list (cons :return-constant nil)
                               (cons :return nil)))))
      (multiple-value-setq (arg0-local arg1-local)
        (wasm2-simple-arg-local-indices afunc))
      (setf (afunc-lfun-info afunc)
            (list* 'wasm-ir ir (afunc-lfun-info afunc)))
      (unless prealloc-entry
        (multiple-value-bind (const-value const-p) (wasm2-const-ir-value specialization-ir)
          (when const-p
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-const-value const-value
                         'wasm-entry-index +wasm-const-entry-index+
                         (afunc-lfun-info afunc)))
            (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
              (let* ((module-bytes (wasm2-const-module-bytes const-value)))
                (wasm2-register-compiled-module module-bytes
                                                +wasm-const-export-name+
                                                +wasm-const-entry-index+
                                                +wasm-const-module-version+
                                                nil
                                                nil
                                                +wasm2-gc-root-mode-runtime-bootstrap+)
                (setf (afunc-lfun-info afunc)
                      (list* 'wasm-module-bytes module-bytes
                             'wasm-module-export +wasm-const-export-name+
                             'wasm-module-version +wasm-const-module-version+
                             (afunc-lfun-info afunc))))
              (setf (afunc-argsword afunc) bits)
              (wasm2-set-afunc-lfun afunc
                                    +wasm-const-entry-index+
                                    (if keyvec keyvec const-value)
                                    bits))
            (return-from wasm2-compile afunc)))
        ;; Deliberately avoid hard-mapping simple fixnum IR to fixed compatibility
        ;; entry slots (204..212). Those slots remain bootstrap/compatibility-only.
      (multiple-value-bind (true-val false-val ok) (wasm2-if-arg0-const-ir-p specialization-ir)
        (when ok
          (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
            (let* ((module-bytes (wasm2-if-module-bytes true-val false-val)))
              (wasm2-register-compiled-module module-bytes
                                              +wasm-if-export-name+
                                              +wasm-if-entry-index+
                                              +wasm-if-module-version+
                                              nil
                                              nil
                                              +wasm2-gc-root-mode-runtime-bootstrap+)
              (setf (afunc-lfun-info afunc)
                    (list* 'wasm-module-bytes module-bytes
                           'wasm-module-export +wasm-if-export-name+
                           'wasm-module-version +wasm-if-module-version+
                           (afunc-lfun-info afunc))))
            (setf (afunc-argsword afunc) bits)
            (wasm2-set-afunc-lfun afunc +wasm-if-entry-index+ keyvec-slot bits))
          (return-from wasm2-compile afunc)))
      (multiple-value-bind (else-val ok) (wasm2-if-arg0-else-ir-p specialization-ir)
        (when ok
          (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
            (let* ((module-bytes (wasm2-if-arg-module-bytes else-val)))
              (wasm2-register-compiled-module module-bytes
                                              +wasm-if-arg-export-name+
                                              +wasm-if-arg-entry-index+
                                              +wasm-if-arg-module-version+
                                              nil
                                              nil
                                              +wasm2-gc-root-mode-runtime-bootstrap+)
              (setf (afunc-lfun-info afunc)
                    (list* 'wasm-module-bytes module-bytes
                           'wasm-module-export +wasm-if-arg-export-name+
                           'wasm-module-version +wasm-if-arg-module-version+
                           (afunc-lfun-info afunc))))
            (setf (afunc-argsword afunc) bits)
            (wasm2-set-afunc-lfun afunc +wasm-if-arg-entry-index+ keyvec-slot bits))
          (return-from wasm2-compile afunc)))
      (when (wasm2-return-arg0-ir-p specialization-ir arg0-local)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-identity-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-identity-export-name+
                                            +wasm-identity-entry-index+
                                            +wasm-identity-module-version+
                                            nil
                                            nil
                                            +wasm2-gc-root-mode-runtime-bootstrap+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-identity-export-name+
                         'wasm-module-version +wasm-identity-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (wasm2-set-afunc-lfun afunc +wasm-identity-entry-index+ keyvec-slot bits))
        (return-from wasm2-compile afunc))
      (when (wasm2-return-arg1-ir-p specialization-ir arg1-local)
        (let* ((bits (or (wasm2-const-lfun-bits afunc) 0)))
          (let* ((module-bytes (wasm2-identity-y-module-bytes)))
            (wasm2-register-compiled-module module-bytes
                                            +wasm-identity-y-export-name+
                                            +wasm-identity-y-entry-index+
                                            +wasm-identity-y-module-version+
                                            nil
                                            nil
                                            +wasm2-gc-root-mode-runtime-bootstrap+)
            (setf (afunc-lfun-info afunc)
                  (list* 'wasm-module-bytes module-bytes
                         'wasm-module-export +wasm-identity-y-export-name+
                         'wasm-module-version +wasm-identity-y-module-version+
                         (afunc-lfun-info afunc))))
          (setf (afunc-argsword afunc) bits)
          (wasm2-set-afunc-lfun afunc +wasm-identity-y-entry-index+ keyvec-slot bits))
        (return-from wasm2-compile afunc))
      )
      (let* ((bits (or (wasm2-const-lfun-bits afunc) 0))
             (entry-index (or prealloc-entry (wasm2-allocate-entry-index)))
             (export-name (format nil "ccl_generic_entry_~d" entry-index))
             (entry-call-abi nil)
             (typed-entry-op nil))
        (multiple-value-setq (entry-call-abi typed-entry-op)
          (wasm2-typed-entry-call-abi-plan afunc specialization-ir arg0-local arg1-local))
        (unless entry-call-abi
          (setf entry-call-abi +wasm2-entry-call-abi-legacy+))
        (let* ((typed-entry-ir (wasm2-typed-entry-ir entry-call-abi typed-entry-op))
               (raw-spillable-locals (nreverse *wasm2-spillable-locals*))
               (module-ir (or typed-entry-ir ir))
               (module-local-types (if typed-entry-ir
                                     #()
                                     *wasm2-local-types*))
               (spillable-locals (if typed-entry-ir
                                   nil
                                   raw-spillable-locals))
               (gc-root-boundary-ops (wasm2-ir-gc-root-boundary-ops module-ir))
               (gc-root-policy-mode (if gc-root-boundary-ops
                                      +wasm2-gc-root-mode-runtime-default+
                                      +wasm2-gc-root-mode-runtime-bootstrap+))
               (const-pool-bytes (and const-pool-entries
                                      (wasm2-const-pool-bytes const-pool-entries)))
               (module-bytes (wasm2-generic-module-bytes module-ir export-name
                                                         module-local-types
                                                         spillable-locals
                                                         entry-index
                                                         entry-call-abi))
               (debug-info (and *wasm2-collect-module-debug*
                                (wasm2-make-module-debug-info export-name entry-index 1
                                                              :afunc afunc
                                                              :ir module-ir
                                                              :gc-root-policy-mode
                                                              gc-root-policy-mode
                                                              :gc-root-boundary-ops
                                                              gc-root-boundary-ops))))
        (wasm2-register-compiled-module module-bytes
                                        export-name
                                        entry-index
                                        1
                                        const-pool-bytes
                                        debug-info
                                        gc-root-policy-mode)
        (let ((info (list* 'wasm-module-bytes module-bytes
                           'wasm-module-export export-name
                           'wasm-module-version 1
                           'wasm-entry-index entry-index
                           (afunc-lfun-info afunc))))
          (when const-pool-bytes
            (setf info (list* 'wasm-const-pool const-pool-bytes info)))
          (unless (eq entry-call-abi +wasm2-entry-call-abi-legacy+)
            (setf info (list* 'wasm-entry-call-abi entry-call-abi info)))
          (setf (afunc-lfun-info afunc) info))
        (setf (afunc-argsword afunc) bits)
        (wasm2-set-afunc-lfun afunc entry-index keyvec-slot bits)
        (return-from wasm2-compile afunc)))
  )))

(provide "WASM2")
