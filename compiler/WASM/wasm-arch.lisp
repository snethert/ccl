;;;-*- Mode: Lisp; Package: (WASM :use CL) -*-
;;;
;;; WASM32 target arch description (ARM layout).

(defpackage "WASM"
  (:use "CL")
  #+wasm-target
  (:nicknames "TARGET"))

(in-package "WASM")

(require "ARM-ARCH")

(eval-when (:compile-toplevel :load-toplevel :execute)
  ;; Mirror ARM layout constants into the WASM target package so
  ;; TARGET::subtag-* and related names resolve during cross-compilation.
  (let ((arm (find-package "ARM"))
        (wasm (find-package "WASM")))
    (when (and arm wasm)
      (do-symbols (sym arm)
        (when (eq (symbol-package sym) arm)
          (shadowing-import sym wasm))))))

(eval-when (:compile-toplevel :load-toplevel :execute)
  (defparameter *wasm-subprims-shift* 0)
  (defparameter *wasm-subprims-base* 0))

(defvar *wasm-subprims*)

(let* ((arm-subprims arm::*arm-subprims*)
       (count (length arm-subprims))
       (table (make-array count)))
  (dotimes (i count)
    (let* ((info (aref arm-subprims i))
           (name (ccl::subprimitive-info-name info)))
      (setf (aref table i)
            (ccl::make-subprimitive-info :name name :offset i))))
  (setf *wasm-subprims* table))

(defparameter *wasm32-target-arch*
  (let* ((arm arm::*arm-target-arch*))
    (arch::make-target-arch
     :name :wasm32
     :lisp-node-size (arch::target-lisp-node-size arm)
     :nil-value (arch::target-nil-value arm)
     :fixnum-shift (arch::target-fixnum-shift arm)
     :most-positive-fixnum (arch::target-most-positive-fixnum arm)
     :most-negative-fixnum (arch::target-most-negative-fixnum arm)
     :misc-data-offset (arch::target-misc-data-offset arm)
     :misc-dfloat-offset (arch::target-misc-dfloat-offset arm)
     :nbits-in-word (arch::target-nbits-in-word arm)
     :ntagbits (arch::target-ntagbits arm)
     :nlisptagbits (arch::target-nlisptagbits arm)
     :uvector-subtags (arch::target-uvector-subtags arm)
     :max-64-bit-constant-index (arch::target-max-64-bit-constant-index arm)
     :max-32-bit-constant-index (arch::target-max-32-bit-constant-index arm)
     :max-16-bit-constant-index (arch::target-max-16-bit-constant-index arm)
     :max-8-bit-constant-index (arch::target-max-8-bit-constant-index arm)
     :max-1-bit-constant-index (arch::target-max-1-bit-constant-index arm)
     :word-shift (arch::target-word-shift arm)
     :code-vector-prefix (arch::target-code-vector-prefix arm)
     :gvector-types (arch::target-gvector-types arm)
     :1-bit-ivector-types (arch::target-1-bit-ivector-types arm)
     :8-bit-ivector-types (arch::target-8-bit-ivector-types arm)
     :16-bit-ivector-types (arch::target-16-bit-ivector-types arm)
     :32-bit-ivector-types (arch::target-32-bit-ivector-types arm)
     :64-bit-ivector-types (arch::target-64-bit-ivector-types arm)
     :array-type-name-from-ctype-function (arch::target-array-type-name-from-ctype-function arm)
     :package-name "WASM"
     :t-offset (arch::target-t-offset arm)
     :array-data-size-function (arch::target-array-data-size-function arm)
     :fpr-mask-function (arch::target-fpr-mask-function arm)
     :subprims-base *wasm-subprims-base*
     :subprims-shift *wasm-subprims-shift*
     :subprims-table *wasm-subprims*
     :primitive->subprims `(((0 . 23) . ,(ccl::%subprim-name->offset '.SPbuiltin-plus *wasm-subprims*)))
     :unbound-marker-value (arch::target-unbound-marker-value arm)
     :slot-unbound-marker-value (arch::target-slot-unbound-marker-value arm)
     :fixnum-tag (arch::target-fixnum-tag arm)
     :single-float-tag (arch::target-single-float-tag arm)
     :single-float-tag-is-subtag (arch::target-single-float-tag-is-subtag arm)
     :double-float-tag (arch::target-double-float-tag arm)
     :cons-tag (arch::target-cons-tag arm)
     :null-tag (arch::target-null-tag arm)
     :symbol-tag (arch::target-symbol-tag arm)
     :symbol-tag-is-subtag (arch::target-symbol-tag-is-subtag arm)
     :function-tag (arch::target-function-tag arm)
     :function-tag-is-subtag (arch::target-function-tag-is-subtag arm)
     :big-endian (arch::target-big-endian arm)
     :misc-subtag-offset (arch::target-misc-subtag-offset arm)
     :car-offset (arch::target-car-offset arm)
     :cdr-offset (arch::target-cdr-offset arm)
     :subtag-char (arch::target-subtag-char arm)
     :charcode-shift (arch::target-charcode-shift arm)
     :fulltagmask (arch::target-fulltagmask arm)
     :fulltag-misc (arch::target-fulltag-misc arm)
     :char-code-limit (arch::target-char-code-limit arm))))

(defmacro defwasmarchmacro (name lambda-list &body body)
  `(arch::defarchmacro :wasm32 ,name ,lambda-list ,@body))

(defwasmarchmacro ccl::%make-sfloat ()
  `(ccl::%alloc-misc arm::single-float.element-count arm::subtag-single-float))

(defwasmarchmacro ccl::%make-dfloat ()
  `(ccl::%alloc-misc arm::double-float.element-count arm::subtag-double-float))

(defwasmarchmacro ccl::%numerator (x)
  `(ccl::%svref ,x arm::ratio.numer-cell))

(defwasmarchmacro ccl::%denominator (x)
  `(ccl::%svref ,x arm::ratio.denom-cell))

(defwasmarchmacro ccl::%get-kernel-global (name)
  `(ccl::%fixnum-ref (ash (+ (- arm::nil-value arm::fulltag-nil)
                             ,(arm::%kernel-global
                               (if (ccl::quoted-form-p name)
                                 (cadr name)
                                 name)))
                      (- arm::fixnumshift))))

(defwasmarchmacro ccl::%get-kernel-global-ptr (name dest)
  `(ccl::%setf-macptr
    ,dest
    (ccl::%fixnum-ref-macptr (ash (+ (- arm::nil-value arm::fulltag-nil)
                                     ,(arm::%kernel-global
                                       (if (ccl::quoted-form-p name)
                                         (cadr name)
                                         name)))
                              (- arm::fixnumshift)))))

(defwasmarchmacro ccl::%target-kernel-global (name)
  `(arm::%kernel-global ,name))

(defwasmarchmacro ccl::lfun-vector (fun)
  fun)

(defwasmarchmacro ccl::lfun-vector-lfun (lfv)
  lfv)

(defwasmarchmacro ccl::area-code ()
  area.code)

(defwasmarchmacro ccl::area-succ ()
  area.succ)

(defwasmarchmacro ccl::symptr->symvector (s)
  s)

(defwasmarchmacro ccl::symvector->symptr (s)
  s)

(defwasmarchmacro ccl::function-to-function-vector (f)
  f)

(defwasmarchmacro ccl::function-vector-to-function (v)
  v)

(defwasmarchmacro ccl::with-ffcall-results ((buf) &body body)
  (let* ((size (+ (* 8 4) (* 31 8))))
    `(%stack-block ((,buf ,size))
      ,@body)))

;; Mirror ARM helpers used by shared macros.
(defwasmarchmacro ccl::%get-single-float-from-double-ptr (ptr offset)
  `(ccl::%double-float->short-float (ccl::%get-double-float ,ptr ,offset)
    (ccl::%alloc-misc 1 arm::subtag-single-float)))

(defwasmarchmacro ccl::codevec-header-p (word)
  `(eql arm::subtag-code-vector
    (logand ,word arm::subtag-mask)))

(defwasmarchmacro ccl::immediate-p-macro (thing)
  (let* ((tag (gensym)))
    `(let* ((,tag (ccl::lisptag ,thing)))
      (declare (fixnum ,tag))
      (or (= ,tag arm::tag-fixnum)
       (= ,tag arm::tag-imm)))))

(defwasmarchmacro ccl::hashed-by-identity (thing)
  (let* ((typecode (gensym)))
    `(let* ((,typecode (ccl::typecode ,thing)))
      (declare (fixnum ,typecode))
      (or
       (= ,typecode arm::tag-fixnum)
       (= ,typecode arm::tag-imm)
       (= ,typecode arm::subtag-symbol)
       (= ,typecode arm::subtag-instance)))))

;;; Mirror ARM's function vector layout for immediates.
(defwasmarchmacro ccl::nth-immediate (f i)
  `(ccl::%svref ,f (the fixnum (+ (the fixnum ,i) 1))))

(defwasmarchmacro ccl::set-nth-immediate (f i new)
  `(setf (ccl::%svref ,f (the fixnum (+ (the fixnum ,i) 1))) ,new))

(provide "WASM-ARCH")
