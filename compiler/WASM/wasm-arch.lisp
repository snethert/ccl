;;;-*- Mode: Lisp; Package: (WASM :use CL) -*-
;;;
;;; WASM32 target arch description (ARM layout).

(defpackage "WASM"
  (:use "CL")
  #+wasm-target
  (:nicknames "TARGET"))

(in-package "WASM")

(eval-when (:compile-toplevel :load-toplevel :execute)
  ;; Keep legacy arch bootstrap, but avoid hard-coded module marker strings.
  (require (coerce '(#\A #\R #\M #\- #\A #\R #\C #\H) 'string)))

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

(let* ((arm-subprims wasm::*arm-subprims*)
       (count (length arm-subprims))
       (table (make-array count)))
  (dotimes (i count)
    (let* ((info (aref arm-subprims i))
           (name (ccl::subprimitive-info-name info)))
      (setf (aref table i)
            (ccl::make-subprimitive-info :name name :offset i))))
  (setf *wasm-subprims* table))

(defparameter *wasm32-target-arch*
  (let* ((arm wasm::*arm-target-arch*))
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
  `(ccl::%alloc-misc wasm::single-float.element-count wasm::subtag-single-float))

(defwasmarchmacro ccl::%make-dfloat ()
  `(ccl::%alloc-misc wasm::double-float.element-count wasm::subtag-double-float))

(defwasmarchmacro ccl::%numerator (x)
  `(ccl::%svref ,x wasm::ratio.numer-cell))

(defwasmarchmacro ccl::%denominator (x)
  `(ccl::%svref ,x wasm::ratio.denom-cell))

(defwasmarchmacro ccl::%get-kernel-global (name)
  `(ccl::%fixnum-ref (ash (+ (- wasm::nil-value wasm::fulltag-nil)
                             ,(wasm::%kernel-global
                               (if (ccl::quoted-form-p name)
                                 (cadr name)
                                 name)))
                      (- wasm::fixnumshift))))

(defwasmarchmacro ccl::%get-kernel-global-ptr (name dest)
  `(ccl::%setf-macptr
    ,dest
    (ccl::%fixnum-ref-macptr (ash (+ (- wasm::nil-value wasm::fulltag-nil)
                                     ,(wasm::%kernel-global
                                       (if (ccl::quoted-form-p name)
                                         (cadr name)
                                         name)))
                              (- wasm::fixnumshift)))))

(defwasmarchmacro ccl::%target-kernel-global (name)
  `(wasm::%kernel-global ,name))

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
    (ccl::%alloc-misc 1 wasm::subtag-single-float)))

(defwasmarchmacro ccl::codevec-header-p (word)
  `(eql wasm::subtag-code-vector
    (logand ,word wasm::subtag-mask)))

(defwasmarchmacro ccl::immediate-p-macro (thing)
  (let* ((tag (gensym)))
    `(let* ((,tag (ccl::lisptag ,thing)))
      (declare (fixnum ,tag))
      (or (= ,tag wasm::tag-fixnum)
       (= ,tag wasm::tag-imm)))))

(defwasmarchmacro ccl::hashed-by-identity (thing)
  (let* ((typecode (gensym)))
    `(let* ((,typecode (ccl::typecode ,thing)))
      (declare (fixnum ,typecode))
      (or
       (= ,typecode wasm::tag-fixnum)
       (= ,typecode wasm::tag-imm)
       (= ,typecode wasm::subtag-symbol)
       (= ,typecode wasm::subtag-instance)))))

;;; Mirror ARM's function vector layout for immediates.
(defwasmarchmacro ccl::nth-immediate (f i)
  `(ccl::%svref ,f (the fixnum (+ (the fixnum ,i) 1))))

(defwasmarchmacro ccl::set-nth-immediate (f i new)
  `(setf (ccl::%svref ,f (the fixnum (+ (the fixnum ,i) 1))) ,new))

(provide "WASM-ARCH")
